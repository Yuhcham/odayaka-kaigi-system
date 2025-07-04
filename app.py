import os
import math
import librosa
import numpy as np
import json
import subprocess
from openai import OpenAI
from flask import Flask, request, jsonify, render_template
from getpass import getpass
from pydub import AudioSegment

#ウォームアップ処理
def _warmup_librosa():
    """
    サーバー起動時にlibrosaのJITコンパイルを強制的に実行させるための関数。
    これにより、最初のリクエストがタイムアウトやメモリ不足で失敗するのを防ぐ。
    """
    print("--- Warming up Librosa (JIT Compilation)... ---")
    try:
        # 1秒分の無音データを作成
        dummy_audio = np.zeros(22050, dtype=np.float32) 
        
        # JITコンパイルが走る主要な関数を一度呼び出しておく
        librosa.feature.rms(y=dummy_audio)
        librosa.feature.spectral_centroid(y=dummy_audio, sr=22050)
        librosa.piptrack(y=dummy_audio, sr=22050)
        
        print("--- ✅ Librosa warmup complete! ---")
    except Exception as e:
        print(f"--- An error occurred during Librosa warmup: {e} ---")

# サーバープロセス開始時にウォームアップを実行
_warmup_librosa()
# ウォームアップ処理終了

app = Flask(__name__)

try:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY") or getpass("Please enter your OpenAI API Key: "))
except Exception as e:
    client = None
    print(f"APIキーの設定中にエラーが発生しました: {e}")

# グローバル変数
emotion_dictionary = {}
normalization_ranges = {}

def _calculate_normalization_ranges():
    global normalization_ranges
    if len(emotion_dictionary) < 4: return
    pitches = [vec[0] for vec in emotion_dictionary.values()]; energies = [vec[1] for vec in emotion_dictionary.values()]; sharpnesses = [vec[2] for vec in emotion_dictionary.values()]
    def get_range(values):
        min_val, max_val = min(values), max(values)
        if min_val == max_val: return {'min': min_val * 0.9, 'max': max_val * 1.1} if min_val != 0 else {'min': -0.1, 'max': 0.1}
        return {'min': min_val, 'max': max_val}
    normalization_ranges = {'pitch': get_range(pitches), 'energy': get_range(energies), 'sharpness': get_range(sharpnesses)}
    print("--- あなた専用の正規化レンジを計算しました ---"); print(normalization_ranges)

def calculate_tone_score(pitch, energy, sharpness, ranges):
    if not ranges: return 0.0
    def normalize(value, r):
        if (r['max'] - r['min']) == 0: return 0.5
        return (np.clip(value, r['min'], r['max']) - r['min']) / (r['max'] - r['min'])
    norm_pitch = normalize(pitch, ranges['pitch']); norm_energy = normalize(energy, ranges['energy']); norm_sharpness = normalize(sharpness, ranges['sharpness'])
    if norm_energy > 0.8 and norm_sharpness > 0.8: return -0.8
    elif norm_energy > 0.7 and norm_pitch > 0.7: return 0.7
    else:
        pitch_score = (norm_pitch - 0.5) * 2; energy_score = (norm_energy - 0.5) * 2
        return (pitch_score + energy_score) / 2.0

def convert_audio_with_ffmpeg(input_path, output_path="temp_converted.wav"):
    command = ["ffmpeg", "-i", input_path, "-y", output_path]
    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print("ffmpegコマンド実行中にエラーが発生しました。"); print("Stderr:", e.stderr.decode('utf-8')); raise e

@app.route('/calibrate', methods=['POST'])
def calibrate_emotion():
    emotion = request.args.get('emotion'); ext = request.args.get('ext', 'webm'); audio_file = request.files['audio']
    try:
        input_filename = f"temp_{emotion}.{ext}"; audio_file.save(input_filename)
        wav_filename = f"temp_{emotion}.wav"; convert_audio_with_ffmpeg(input_filename, wav_filename)
        y, sr = librosa.load(wav_filename)
        pitches, _ = librosa.piptrack(y=y, sr=sr); rms = librosa.feature.rms(y=y); spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        pitch_mean = np.mean(pitches[pitches > 0]) if np.any(pitches > 0) else 0.0; rms_mean = np.mean(rms); spectral_centroid_mean = np.mean(spectral_centroid)
        emotion_dictionary[emotion] = [pitch_mean, rms_mean, spectral_centroid_mean]
        if len(emotion_dictionary) == 4: _calculate_normalization_ranges()
        return jsonify({'status': 'success', 'emotion': emotion})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_audio():
    try:
        if not client: return jsonify({'error': 'OpenAI client is not configured.'}), 500
        if 'audio' not in request.files: return jsonify({'error': 'No audio file part'}), 400
        
        audio_file = request.files['audio']
        ext = request.args.get('ext', 'webm')

        # トーン分析
        active_ranges = normalization_ranges if normalization_ranges else {'pitch': {'min': 85.0, 'max': 255.0},'energy': {'min': 0.005, 'max': 0.15},'sharpness': {'min': 500.0, 'max': 3500.0}}
        input_filename = f"temp_audio.{ext}"; audio_file.save(input_filename)
        wav_filename = "temp_converted.wav"; convert_audio_with_ffmpeg(input_filename, wav_filename)
        y, sr = librosa.load(wav_filename)
        pitches, _ = librosa.piptrack(y=y, sr=sr); rms = librosa.feature.rms(y=y); spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        current_features = [np.mean(pitches[pitches > 0]) if np.any(pitches > 0) else 0.0, np.mean(rms), np.mean(spectral_centroid)]
        tone_score = calculate_tone_score(current_features[0], current_features[1], current_features[2], active_ranges)
        
        # テキスト分析
        with open(wav_filename, 'rb') as clean_audio_file:
            transcript_data = client.audio.transcriptions.create(model="whisper-1", file=clean_audio_file, language="ja", response_format="verbose_json")
        
        filtered_text = ""
        for segment in transcript_data.segments:
            if segment.avg_logprob > -0.8 and segment.no_speech_prob < 0.5: filtered_text += segment.text
        
        text_sentiment_score = 0.0
        if filtered_text.strip():
            try:
                response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": "あなたはテキストの感情を分析する専門家です。ユーザーのテキストがポジティブかネガティブかを判断し、-1.0（完全にネガティブ）から1.0（完全にポジティブ）の間のスコアで評価してください。"},{"role": "user", "content": filtered_text}], functions=[{"name": "set_sentiment_score","description": "感情分析スコアを設定する","parameters": {"type": "object","properties": {"score": {"type": "number","description": "感情スコア, -1.0から1.0"}},"required": ["score"]}}], function_call={"name": "set_sentiment_score"})
                function_args = json.loads(response.choices[0].message.function_call.arguments)
                text_sentiment_score = function_args.get("score", 0.0)
            except Exception as e:
                print(f"GPT感情分析中にエラーが発生しましたが、処理を続行します: {e}")
                text_sentiment_score = 0.0
        
        # スコア統合
        final_score = (text_sentiment_score * 0.7) + (tone_score * 0.3)
        final_score = max(-1.0, min(1.0, final_score))
        
        # 最終的なJSONを返す
        return jsonify({'is_negative': True if final_score < -0.3 else False, 'filtered_text': filtered_text, 'text_score': f"{text_sentiment_score:.2f}",'tone_score': f"{tone_score:.2f}",'final_score': f"{final_score:.2f}"})

    except Exception as e:
        print(f"分析ルート全体で予期せぬエラーが発生しました: {e}")
        return jsonify({'error': f'サーバーで予期せぬエラーが発生しました: {e}'}), 500

@app.route('/correct', methods=['POST'])
def correct_text_with_llm():
    data = request.json; original_text = data['text']
    try:
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": "あなたはビジネス会議の議事録を校正するプロの書記だと思ってください。誤字脱字を修正し、文脈として不自然な部分を修正して、自然で読みやすい日本語の議事録に清書して。"},{"role": "user", "content": original_text}])
        corrected_text = response.choices[0].message.content
        return jsonify({'corrected_text': corrected_text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)