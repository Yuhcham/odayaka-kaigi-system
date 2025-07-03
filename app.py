"""
# ------------------------------------------------
# ① ライブラリのインポート（道具の準備）
# ------------------------------------------------
# これからプログラムを作るために、便利な道具（ライブラリ）を揃えます。
import os  # PCのファイルやフォルダを操作するための道具
import math  # 難しい計算をするための算数の道具
import librosa  # 音の博士。声の特徴を分析してくれる
import numpy as np  # 計算が得意な算数の道具（行列とかを扱える）
from openai import OpenAI  # OpenAI社のAIと話すための電話
from flask import Flask, request, jsonify, render_template  # Webサイトを作るための設計図や部品
from getpass import getpass  # パスワードなどを安全に入力するための道具
from pydub import AudioSegment  # 音声ファイルを編集するための道具
import json  # データを整理するための道具

# ------------------------------------------------
# ② 初期設定（下準備）
# ------------------------------------------------
# これからFlaskでWebアプリを作りますよ、という合図
app = Flask(__name__)

# OpenAIのAIと話すための電話を準備します。APIキーという秘密の合言葉が必要です。
try:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY") or getpass("Please enter your OpenAI API Key: "))
except Exception as e:
    client = None
    print(f"APIキーの設定中にエラーが発生しました: {e}")

# --- グローバル変数（プログラム全体で使うデータの保管場所） ---
# 「声の感情辞書」をしまうための、空っぽの本棚を準備します。
emotion_dictionary = {}
# 「あなた専用のものさし」をしまうための、空っぽの道具箱を準備します。
normalization_ranges = {}


# ------------------------------------------------
# ③ 関数（プログラムの部品）の定義
# ------------------------------------------------

def _calculate_normalization_ranges():

    global normalization_ranges  # 道具箱を操作しますよ、という宣言
    
    if len(emotion_dictionary) < 4:
        return # まだ4つ揃ってなければ何もしない

    # 本棚（感情辞書）から、それぞれの感情の「高さ」「大きさ」「鋭さ」の数値を全部取り出す
    pitches = [vec[0] for vec in emotion_dictionary.values()]
    energies = [vec[1] for vec in emotion_dictionary.values()]
    sharpnesses = [vec[2] for vec in emotion_dictionary.values()]

    # 一番小さい数値と大きい数値を見つけて、声の「最低音」と「最高音」の範囲を決める
    def get_range(values):
        min_val, max_val = min(values), max(values)
        if min_val == max_val: # もし全部同じだったら、少しだけ範囲を広げておく
            return {'min': min_val * 0.9, 'max': max_val * 1.1}
        return {'min': min_val, 'max': max_val}

    # 計算した「あなた専用のものさし」を道具箱にしまう
    normalization_ranges = {
        'pitch': get_range(pitches),
        'energy': get_range(energies),
        'sharpness': get_range(sharpnesses)
    }
    print("--- あなた専用の正規化レンジ（ものさし）を計算しました ---")
    print(normalization_ranges)


def calculate_tone_score(pitch, energy, sharpness, ranges):
    if not ranges:
        return 0.0 # まだものさしがなければ0点

    # どんな声でも0点から1点の間の点数に変換する「ものさし」機能
    def normalize(value, r):
        if (r['max'] - r['min']) == 0: return 0.5
        # 「今の声 - あなたの最低音) / (あなたの最高音 - あなたの最低音)」という計算
        return (np.clip(value, r['min'], r['max']) - r['min']) / (r['max'] - r['min'])

    # 3つの特徴を、それぞれ0〜1点の点数に変換する
    norm_pitch = normalize(pitch, ranges['pitch'])
    norm_energy = normalize(energy, ranges['energy'])
    norm_sharpness = normalize(sharpness, ranges['sharpness'])

    # --- ルールに基づいて点数を決める ---
    # もし声の大きさと鋭さがMAXに近かったら（あなたの声の80%以上なら）、「怒り」と判断してマイナス80点！
    if norm_energy > 0.8 and norm_sharpness > 0.8: return -0.8
    # もし声の大きさと高さがすごく高かったら（あなたの声の70%以上なら）、「喜び」と判断してプラス70点！
    elif norm_energy > 0.7 and norm_pitch > 0.7: return 0.7
    # それ以外の普通の声のときは、-100点から+100点の間の滑らかな点数をつける
    else:
        pitch_score = (norm_pitch - 0.5) * 2
        energy_score = (norm_energy - 0.5) * 2
        return (pitch_score + energy_score) / 2.0

# ------------------------------------------------
# ④ Flaskのルート（Webサイトのページや機能）の定義
# ------------------------------------------------

@app.route('/calibrate', methods=['POST'])
def calibrate_emotion():
    # どの感情の、どの声かを教えてもらう
    emotion = request.args.get('emotion')
    audio_file = request.files['audio']
    try:
        # 音声を分析しやすい形(.wav)に変換する
        webm_filename = f"temp_{emotion}.webm"; audio_file.save(webm_filename)
        sound = AudioSegment.from_file(webm_filename, format="webm"); wav_filename = f"temp_{emotion}.wav"; sound.export(wav_filename, format="wav")
        y, sr = librosa.load(wav_filename)
        
        # 音の博士（librosa）に声の「高さ」「大きさ」「鋭さ」を調べてもらう
        pitches, _ = librosa.piptrack(y=y, sr=sr); rms = librosa.feature.rms(y=y); spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        pitch_mean = np.mean(pitches[pitches > 0]) if np.any(pitches > 0) else 0.0; rms_mean = np.mean(rms); spectral_centroid_mean = np.mean(spectral_centroid)
        
        # 調べた結果をリストにまとめる
        emotion_dictionary[emotion] = [pitch_mean, rms_mean, spectral_centroid_mean]
        
        # もし4つの感情が全部集まったら、「ものさし作り」の関数を呼び出す
        if len(emotion_dictionary) == 4:
            _calculate_normalization_ranges()

        # ブラウザに「成功しました！」と伝える
        return jsonify({'status': 'success', 'emotion': emotion})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/')
def index():

    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_audio():

    # 必要なものが揃っているかチェック
    if not client: return jsonify({'error': 'OpenAI client is not configured.'}), 500
    if 'audio' not in request.files: return jsonify({'error': 'No audio file part'}), 400
    
    audio_file = request.files['audio']
    try:
        # --- トーン分析の準備 ---
        # もし「あなた専用のものさし」が完成していたらそれを使う。まだなら「みんな用のものさし」を使う。
        active_ranges = {}
        if normalization_ranges:
            active_ranges = normalization_ranges
            print("パーソナライズ設定で分析中...")
        else:
            active_ranges = {
                'pitch': {'min': 85.0, 'max': 255.0},
                'energy': {'min': 0.005, 'max': 0.15},
                'sharpness': {'min': 500.0, 'max': 3500.0}
            }
            print("デフォルト設定で分析中...")

        # --- トーン分析の実行 ---
        # 今、話している声の特徴を調べる
        webm_filename = "temp_audio.webm"; audio_file.save(webm_filename)
        sound = AudioSegment.from_file(webm_filename, format="webm"); wav_filename = "temp_converted.wav"; sound.export(wav_filename, format="wav")
        y, sr = librosa.load(wav_filename)
        pitches, _ = librosa.piptrack(y=y, sr=sr); rms = librosa.feature.rms(y=y); spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        current_features = [np.mean(pitches[pitches > 0]) if np.any(pitches > 0) else 0.0, np.mean(rms), np.mean(spectral_centroid)]
        
        # 調べた特徴と使う「ものさし」を渡して、トーンの点数を出してもらう
        tone_score = calculate_tone_score(current_features[0], current_features[1], current_features[2], active_ranges)
        
        # --- テキスト分析の実行 ---
        audio_file.seek(0)
        prompt_text = request.form.get('prompt', '')
        # AI電話でWhisperを呼び出し、音声を文字にしてもらう
        transcript_data = client.audio.transcriptions.create(model="whisper-1", file=(audio_file.filename, audio_file.read()), language="ja", prompt=prompt_text, response_format="verbose_json")
        
        # AIの幻聴や自信のない言葉を捨てるフィルター
        filtered_text = ""
        for segment in transcript_data.segments:
            if segment.avg_logprob > -0.8 and segment.no_speech_prob < 0.5: filtered_text += segment.text
        
        # AI電話で今度はGPTを呼び出し、文章の意味から気持ちを点数にしてもらう
        text_sentiment_score = 0.0
        if filtered_text.strip():
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "system", "content": "あなたはテキストの感情を分析する専門家です。ユーザーのテキストがポジティブかネガティブかを判断し、-1.0（完全にネガティブ）から1.0（完全にポジティブ）の間のスコアで評価してください。"},{"role": "user", "content": filtered_text}],
                    functions=[{"name": "set_sentiment_score","description": "感情分析スコアを設定する","parameters": {"type": "object","properties": {"score": {"type": "number","description": "感情スコア, -1.0から1.0"}},"required": ["score"]}}],
                    function_call={"name": "set_sentiment_score"}
                )
                function_args = json.loads(response.choices[0].message.function_call.arguments)
                text_sentiment_score = function_args.get("score", 0.0)
            except Exception as e:
                print(f"GPT感情分析中にエラー: {e}")
        
        # --- 最終結果の計算と返却 ---
        # 「言葉の点数」と「トーンの点数」を合体させて、最終的な点数を決める
        final_score = (text_sentiment_score * 0.7) + (tone_score * 0.3)
        final_score = max(-1.0, min(1.0, final_score)) # 点数が-100〜+100点に収まるように調整
        
        # 計算したすべての結果を、ブラウザに送り返す
        return jsonify({
            'is_negative': True if final_score < -0.3 else False, 
            'filtered_text': filtered_text,
            'text_score': f"{text_sentiment_score:.2f}",
            'tone_score': f"{tone_score:.2f}",
            'final_score': f"{final_score:.2f}"
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/correct', methods=['POST'])
def correct_text_with_llm():

    # GPTに「プロの編集者になって」とお願いして、議事録全体をキレイな文章に直してもらう
    original_text = request.json['text']
    try:
        response = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "system", "content": "あなたはビジネス会議の議事録を校正するプロの書記です。誤字脱字を修正し、文脈として不自然な部分を修正し、自然で読みやすい日本語の議事録に清書してください。"},{"role": "user", "content": original_text}])
        corrected_text = response.choices[0].message.content
        return jsonify({'corrected_text': corrected_text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ------------------------------------------------
# ⑤ プログラムの起動
# ------------------------------------------------
if __name__ == '__main__':
    from waitress import serve
    # 本番環境では debug=True は使わない
    serve(app, host="0.0.0.0", port=8080)
"""

# app.py (スマホ対応・最終完成版)
import os
import math
import librosa
import numpy as np
from openai import OpenAI
from flask import Flask, request, jsonify, render_template
from getpass import getpass
import json
import subprocess

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
    if len(emotion_dictionary) < 4:
        return
    pitches = [vec[0] for vec in emotion_dictionary.values()]
    energies = [vec[1] for vec in emotion_dictionary.values()]
    sharpnesses = [vec[2] for vec in emotion_dictionary.values()]
    def get_range(values):
        min_val, max_val = min(values), max(values)
        if min_val == max_val:
            return {'min': min_val * 0.9, 'max': max_val * 1.1}
        return {'min': min_val, 'max': max_val}
    normalization_ranges = {
        'pitch': get_range(pitches),
        'energy': get_range(energies),
        'sharpness': get_range(sharpnesses)
    }
    print("--- 🧠 あなた専用の正規化レンジを計算しました ---")
    print(normalization_ranges)

def calculate_tone_score(pitch, energy, sharpness, ranges):
    if not ranges:
        return 0.0
    def normalize(value, r):
        if (r['max'] - r['min']) == 0: return 0.5
        return (np.clip(value, r['min'], r['max']) - r['min']) / (r['max'] - r['min'])
    norm_pitch = normalize(pitch, ranges['pitch'])
    norm_energy = normalize(energy, ranges['energy'])
    norm_sharpness = normalize(sharpness, ranges['sharpness'])
    if norm_energy > 0.8 and norm_sharpness > 0.8: return -0.8
    elif norm_energy > 0.7 and norm_pitch > 0.7: return 0.7
    else:
        pitch_score = (norm_pitch - 0.5) * 2
        energy_score = (norm_energy - 0.5) * 2
        return (pitch_score + energy_score) / 2.0

def convert_audio_with_ffmpeg(input_path, output_path="temp_converted.wav"):
    command = ["ffmpeg", "-i", input_path, "-y", output_path]
    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"ffmpegによる変換成功: {input_path} -> {output_path}")
    except subprocess.CalledProcessError as e:
        print("ffmpegコマンド実行中にエラーが発生しました。")
        print("Stderr:", e.stderr.decode('utf-8'))
        raise e

@app.route('/calibrate', methods=['POST'])
def calibrate_emotion():
    if 'audio' not in request.files: return jsonify({'status': 'error', 'error': 'No audio file part'}), 400
    emotion = request.args.get('emotion')
    ext = request.args.get('ext', 'webm') # ★ 拡張子を受け取る
    if not emotion: return jsonify({'status': 'error', 'error': 'Emotion label is missing'}), 400
    audio_file = request.files['audio']
    try:
        input_filename = f"temp_{emotion}.{ext}" # ★
        audio_file.save(input_filename)
        wav_filename = f"temp_{emotion}.wav"
        convert_audio_with_ffmpeg(input_filename, wav_filename)
        y, sr = librosa.load(wav_filename)
        pitches, _ = librosa.piptrack(y=y, sr=sr)
        rms = librosa.feature.rms(y=y)
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        pitch_mean = np.mean(pitches[pitches > 0]) if np.any(pitches > 0) else 0.0
        rms_mean = np.mean(rms)
        spectral_centroid_mean = np.mean(spectral_centroid)
        emotion_dictionary[emotion] = [pitch_mean, rms_mean, spectral_centroid_mean]
        if len(emotion_dictionary) == 4:
            _calculate_normalization_ranges()
        return jsonify({'status': 'success', 'emotion': emotion})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_audio():
    if not client: return jsonify({'error': 'OpenAI client is not configured.'}), 500
    if 'audio' not in request.files: return jsonify({'error': 'No audio file part'}), 400
    audio_file = request.files['audio']
    ext = request.args.get('ext', 'webm') # ★ 拡張子を受け取る
    try:
        active_ranges = normalization_ranges if normalization_ranges else {
            'pitch': {'min': 85.0, 'max': 255.0},'energy': {'min': 0.005, 'max': 0.15},'sharpness': {'min': 500.0, 'max': 3500.0}
        }
        
        input_filename = f"temp_audio.{ext}" # ★
        audio_file.save(input_filename)
        wav_filename = "temp_converted.wav"
        convert_audio_with_ffmpeg(input_filename, wav_filename)

        y, sr = librosa.load(wav_filename)
        pitches, _ = librosa.piptrack(y=y, sr=sr)
        rms = librosa.feature.rms(y=y)
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        current_features = [
            np.mean(pitches[pitches > 0]) if np.any(pitches > 0) else 0.0,
            np.mean(rms),
            np.mean(spectral_centroid)
        ]
        
        tone_score = calculate_tone_score(current_features[0], current_features[1], current_features[2], active_ranges)
        
        with open(wav_filename, 'rb') as clean_audio_file:
            transcript_data = client.audio.transcriptions.create(
                model="whisper-1", 
                file=clean_audio_file, 
                language="ja", 
                response_format="verbose_json"
            )

        filtered_text = ""
        text_sentiment_score = 0.0
        for segment in transcript_data.segments:
            if segment.avg_logprob > -0.8 and segment.no_speech_prob < 0.5:
                filtered_text += segment.text
        
        if filtered_text.strip():
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "あなたはテキストの感情を分析する専門家です。ユーザーのテキストがポジティブかネガティブかを判断し、-1.0（完全にネガティブ）から1.0（完全にポジティブ）の間のスコアで評価してください。"},
                        {"role": "user", "content": filtered_text}
                    ],
                    functions=[{"name": "set_sentiment_score","description": "感情分析スコアを設定する","parameters": {"type": "object","properties": {"score": {"type": "number","description": "感情スコア, -1.0から1.0"}},"required": ["score"]}}],
                    function_call={"name": "set_sentiment_score"}
                )
                function_args = json.loads(response.choices[0].message.function_call.arguments)
                text_sentiment_score = function_args.get("score", 0.0)
            except Exception as e:
                print(f"GPT感情分析中にエラー: {e}")

        final_score = (text_sentiment_score * 0.7) + (tone_score * 0.3)
        final_score = max(-1.0, min(1.0, final_score))
        
        return jsonify({
            'is_negative': True if final_score < -0.3 else False, 
            'filtered_text': filtered_text,
            'text_score': f"{text_sentiment_score:.2f}",
            'tone_score': f"{tone_score:.2f}",
            'final_score': f"{final_score:.2f}"
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/correct', methods=['POST'])
def correct_text_with_llm():
    if not client: return jsonify({'error': 'OpenAI client is not configured.'}), 500
    data = request.json
    if not data or 'text' not in data: return jsonify({'error': 'No text provided.'}), 400
    original_text = data['text']
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたはビジネス会議の議事録を校正するプロの書記です。誤字脱字を修正し、文脈として不自然な部分を修正し、自然で読みやすい日本語の議事録に清書してください。"},
                {"role": "user", "content": original_text}
            ]
        )
        corrected_text = response.choices[0].message.content
        return jsonify({'corrected_text': corrected_text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # 開発用の起動コマンド (本番環境ではWaitressが使われる)
    app.run(debug=True)