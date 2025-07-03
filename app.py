"""

# app.py
import os
from openai import OpenAI
from flask import Flask, request, jsonify, render_template
from getpass import getpass

# --- Flaskアプリの初期設定 ---
app = Flask(__name__)

# --- OpenAI APIキーの設定 ---
# 環境変数から読み込むか、直接入力させる
# サーバーを起動したターミナルで入力することになります
try:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY") or getpass("Please enter your OpenAI API Key: "))
except Exception as e:
    print(f"APIキーの設定中にエラーが発生しました: {e}")
    # 実際にはここで終了する処理を入れるべきですが、今回はシンプルに進めます
    client = None

# --- メインページを表示するルート ---
@app.route('/')
def index():
    # index.html をブラウザに表示する
    return render_template('index.html')

# --- 音声分析を実行するルート ---
@app.route('/analyze', methods=['POST'])
def analyze_audio():
    if not client:
        return jsonify({'error': 'OpenAI client is not configured.'}), 500

    # Webページから送信された音声ファイルを受け取る
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file part'}), 400
    
    audio_file = request.files['audio']

    if audio_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        # Whisper APIで文字起こし
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=(audio_file.filename, audio_file.read()),
            language="ja"
        )
        result_text = transcript.text
        print(f"文字起こし結果: {result_text}") # サーバーのコンソールに表示

        # ネガティブ判定
        ng_words = ["ダメだ", "最悪", "話にならない", "絶対に"]
        is_negative = False
        for word in ng_words:
            if word in result_text:
                is_negative = True
                break
        
        # 判定結果をWebページに返す (JSON形式)
        return jsonify({'is_negative': is_negative, 'text': result_text})

    except Exception as e:
        print(f"分析中にエラーが発生しました: {e}")
        return jsonify({'error': str(e)}), 500

# --- サーバーの起動 ---
if __name__ == '__main__':
    # debug=True にすると、コードを修正した際に自動でサーバーが再起動して便利
    app.run(debug=True)

"""

"""無発話確率、幻聴フィルタリングの実装↓（dotを「」にして失敗）

# app.py (AI幻聴フィルタリング機能搭載 最終版)
import os
from openai import OpenAI
from flask import Flask, request, jsonify, render_template
from getpass import getpass

# --- Flaskアプリの初期設定 ---
app = Flask(__name__)

# --- OpenAI APIキーの設定 ---
try:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY") or getpass("Please enter your OpenAI API Key: "))
except Exception as e:
    print(f"APIキーの設定中にエラーが発生しました: {e}")
    client = None

# --- メインページを表示するルート ---
@app.route('/')
def index():
    return render_template('index.html')

# --- 音声分析を実行するルート ---
@app.route('/analyze', methods=['POST'])
def analyze_audio():
    if not client:
        return jsonify({'error': 'OpenAI client is not configured.'}), 500

    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file part'}), 400
    
    audio_file = request.files['audio']

    if audio_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        # --- ★★★ ここからがAIとの対話の進化部分 ★★★ ---

        # 会議の文脈に合わせたヒントを定義
        prompt_text = "穏やか会議システム、Flask、Python、API、UI、UX。ユーザーからのフィードバック。仕様変更。デバッグ。エラー。サーバー。クライアント。リアルタイム。プロトタイプ。"

        # verbose_json形式で、より詳細な情報をAIに要求する
        transcript_data = client.audio.transcriptions.create(
            model="whisper-1",
            file=(audio_file.filename, audio_file.read()),
            language="ja",
            prompt=prompt_text,
            response_format="verbose_json" # 詳細な情報を要求！
        )

        # --- 幻聴フィルタリングのロジック ---
        # フィルタリングのための設定値
        LOGPROB_THRESHOLD = -1.0  # 自信スコアのしきい値
        NO_SPEECH_PROB_THRESHOLD = 0.6  # 無発話確率のしきい値

        filtered_text = ""
        # AIからの返事をセグメント（区切り）ごとにチェック
        for segment in transcript_data["segments"]:
            avg_logprob = segment["avg_logprob"]
            no_speech_prob = segment["no_speech_prob"]
            
            # デバッグ用にコンソールに情報を表示
            print(f"セグメント: '{segment['text']}', 自信スコア: {avg_logprob:.2f}, 無発話確率: {no_speech_prob:.2f}")

            # 自信スコアが低すぎるか、無発話確率が高すぎる場合は、そのセグメントを無視する
            if avg_logprob < LOGPROB_THRESHOLD or no_speech_prob > NO_SPEECH_PROB_THRESHOLD:
                print(" -> 幻聴と判断し、このセグメントを無視します。")
                continue # 次のセグメントへ
            
            # 問題なければ、テキストを結合
            filtered_text += segment["text"]
        
        # --- ネガティブ判定は、フィルタリング後のテキストで行う ---
        is_negative = False
        if filtered_text: # テキストがある場合のみ判定
            ng_words = ["ダメだ", "最悪", "話にならない", "絶対に"]
            for word in ng_words:
                if word in filtered_text:
                    is_negative = True
                    break
        
        # 判定結果をWebページに返す
        return jsonify({'is_negative': is_negative, 'text': filtered_text})

    except Exception as e:
        print(f"分析中にエラーが発生しました: {e}")
        return jsonify({'error': str(e)}), 500

# --- サーバーの起動 ---
if __name__ == '__main__':
    app.run(debug=True)

"""
"""
無発話確率が甘い
# app.py (オブジェクト対応 最終版)
import os
from openai import OpenAI
from flask import Flask, request, jsonify, render_template
from getpass import getpass

# --- Flaskアプリの初期設定 ---
app = Flask(__name__)

# --- OpenAI APIキーの設定 ---
try:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY") or getpass("Please enter your OpenAI API Key: "))
except Exception as e:
    print(f"APIキーの設定中にエラーが発生しました: {e}")
    client = None

# --- メインページを表示するルート ---
@app.route('/')
def index():
    return render_template('index.html')

# --- 音声分析を実行するルート ---
@app.route('/analyze', methods=['POST'])
def analyze_audio():
    if not client:
        return jsonify({'error': 'OpenAI client is not configured.'}), 500

    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file part'}), 400
    
    audio_file = request.files['audio']

    if audio_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        # 会議の文脈に合わせたヒントを定義
        prompt_text = "穏やか会議システム、Flask、Python、API、UI、UX。ユーザーからのフィードバック。仕様変更。デバッグ。エラー。サーバー。クライアント。リアルタイム。プロトタイプ。"

        # verbose_json形式で、より詳細な情報をAIに要求する
        transcript_data = client.audio.transcriptions.create(
            model="whisper-1",
            file=(audio_file.filename, audio_file.read()),
            language="ja",
            prompt=prompt_text,
            response_format="verbose_json"
        )

        # --- ★★★ ここからが修正箇所 ★★★ ---
        # --- 幻聴フィルタリングのロジック ---
        LOGPROB_THRESHOLD = -1.0
        NO_SPEECH_PROB_THRESHOLD = 0.6

        filtered_text = ""
        # '[]'ではなく'.'でデータにアクセスするように修正
        for segment in transcript_data.segments:
            avg_logprob = segment.avg_logprob
            no_speech_prob = segment.no_speech_prob
            
            print(f"セグメント: '{segment.text}', 自信スコア: {avg_logprob:.2f}, 無発話確率: {no_speech_prob:.2f}")

            if avg_logprob < LOGPROB_THRESHOLD or no_speech_prob > NO_SPEECH_PROB_THRESHOLD:
                print(" -> 幻聴と判断し、この発言を無視します。")
                continue
            
            filtered_text += segment.text
        
        # --- ネガティブ判定は、フィルタリング後のテキストで行う ---
        is_negative = False
        if filtered_text:
            ng_words = ["ダメだ", "最悪", "話にならない", "絶対に"]
            for word in ng_words:
                if word in filtered_text:
                    is_negative = True
                    break
        
        # '[]'ではなく'.'で全体テキストにアクセスするように修正
        # ただし、今回はフィルタリングしたテキストを使うので、transcript_data.textは使わない
        return jsonify({'is_negative': is_negative, 'text': filtered_text})

    except Exception as e:
        print(f"分析中にエラーが発生しました: {e}")
        return jsonify({'error': str(e)}), 500

# --- サーバーの起動 ---
if __name__ == '__main__':
    app.run(debug=True)

"""
"""
# app.py (最終チューニング版)
import os
import math # 指数計算のためにmathライブラリをインポート
from openai import OpenAI
from flask import Flask, request, jsonify, render_template
from getpass import getpass

# --- Flaskアプリの初期設定 ---
app = Flask(__name__)

# --- OpenAI APIキーの設定 ---
try:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY") or getpass("Please enter your OpenAI API Key: "))
except Exception as e:
    print(f"APIキーの設定中にエラーが発生しました: {e}")
    client = None

# --- メインページを表示するルート ---
@app.route('/')
def index():
    return render_template('index.html')

# --- 音声分析を実行するルート ---
@app.route('/analyze', methods=['POST'])
def analyze_audio():
    if not client:
        return jsonify({'error': 'OpenAI client is not configured.'}), 500

    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file part'}), 400
    
    audio_file = request.files['audio']

    if audio_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        # 会議の文脈に合わせたヒントを定義
        prompt_text = ""

        transcript_data = client.audio.transcriptions.create(
            model="whisper-1",
            file=(audio_file.filename, audio_file.read()),
            language="ja",
            prompt=prompt_text,
            response_format="verbose_json"
        )

        # --- ★★★ ここからがチューニング部分 ★★★ ---
        
        # 1. フィルタリング基準をより厳しく設定
        # 自信スコアのしきい値。-1.0から-0.6へ（0に近いほど厳しい）
        LOGPROB_THRESHOLD = -0.6
        # 無発話確率のしきい値。0.6から0.4へ（低いほど厳しい）
        NO_SPEECH_PROB_THRESHOLD = 0.4

        filtered_text = ""
        for segment in transcript_data.segments:
            avg_logprob = segment.avg_logprob
            no_speech_prob = segment.no_speech_prob
            
            # 2. スコアをパーセントに変換して、コンソールに分かりやすく表示
            # 自信スコアは、exp(logprob)で確率に変換できる
            confidence_percent = math.exp(avg_logprob) * 100
            no_speech_percent = no_speech_prob * 100
            
            print(f"セグメント: '{segment.text}', 自信: {confidence_percent:.1f}%, 無発話確率: {no_speech_percent:.1f}%")

            # 厳しくなった基準でフィルタリング
            if avg_logprob < LOGPROB_THRESHOLD or no_speech_prob > NO_SPEECH_PROB_THRESHOLD:
                print(" -> 幻聴と判断し、このセグメントを無視します。")
                continue
            
            filtered_text += segment.text
        
        is_negative = False
        if filtered_text:
            ng_words = ["ダメだ", "最悪", "話にならない", "絶対に"]
            for word in ng_words:
                if word in filtered_text:
                    is_negative = True
                    break
        
        return jsonify({'is_negative': is_negative, 'text': filtered_text})

    except Exception as e:
        print(f"分析中にエラーが発生しました: {e}")
        return jsonify({'error': str(e)}), 500

# --- サーバーの起動 ---
if __name__ == '__main__':
    app.run(debug=True)

次に、LLMを実装します！
"""


"""
# app.py (分析スコア表示対応版)
import os
import math
from openai import OpenAI
from flask import Flask, request, jsonify, render_template
from getpass import getpass

app = Flask(__name__)

try:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY") or getpass("Please enter your OpenAI API Key: "))
except Exception as e:
    client = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_audio():
    if not client: return jsonify({'error': 'OpenAI client is not configured.'}), 500
    if 'audio' not in request.files: return jsonify({'error': 'No audio file part'}), 400
    audio_file = request.files['audio']
    if audio_file.filename == '': return jsonify({'error': 'No selected file'}), 400

    try:
        prompt_text = request.form.get('prompt', '')
        transcript_data = client.audio.transcriptions.create(
            model="whisper-1",
            file=(audio_file.filename, audio_file.read()),
            language="ja",
            prompt=prompt_text,
            response_format="verbose_json"
        )
        
        LOGPROB_THRESHOLD = -0.6
        NO_SPEECH_PROB_THRESHOLD = 0.4

        filtered_text = ""
        # --- ★★★ 発言全体の平均スコアを計算するためのリストを追加 ★★★ ---
        valid_confidences = []
        valid_no_speech_probs = []

        for segment in transcript_data.segments:
            avg_logprob = segment.avg_logprob
            no_speech_prob = segment.no_speech_prob
            
            confidence_percent = math.exp(avg_logprob) * 100
            no_speech_percent = no_speech_prob * 100
            
            print(f"セグメント: '{segment.text}', 自信: {confidence_percent:.1f}%, 無発話確率: {no_speech_percent:.1f}%")

            if avg_logprob < LOGPROB_THRESHOLD or no_speech_prob > NO_SPEECH_PROB_THRESHOLD:
                print(" -> 幻聴と判断し、このセグメントを無視します。")
                continue
            
            # フィルタリングを通過したセグメントのスコアをリストに追加
            valid_confidences.append(confidence_percent)
            valid_no_speech_probs.append(no_speech_percent)
            filtered_text += segment.text
        
        # --- ★★★ フィルタリング後の平均スコアを計算 ★★★ ---
        avg_confidence = sum(valid_confidences) / len(valid_confidences) if valid_confidences else 0
        avg_no_speech_prob = sum(valid_no_speech_probs) / len(valid_no_speech_probs) if valid_no_speech_probs else 0

        is_negative = False
        if filtered_text:
            ng_words = ["ダメだ", "最悪", "話にならない", "絶対に"]
            for word in ng_words:
                if word in filtered_text:
                    is_negative = True
                    break
        
        # --- ★★★ JSONレスポンスに平均スコアを追加 ★★★ ---
        return jsonify({
            'is_negative': is_negative,
            'text': filtered_text,
            'confidence': f"{avg_confidence:.1f}",
            'no_speech_prob': f"{avg_no_speech_prob:.1f}"
        })

    except Exception as e:
        print(f"分析中にエラーが発生しました: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
"""
"""
# app.py (LLM校正機能 + 全機能搭載 最終版)
import os
import math
from openai import OpenAI
from flask import Flask, request, jsonify, render_template
from getpass import getpass

app = Flask(__name__)

try:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY") or getpass("Please enter your OpenAI API Key: "))
except Exception as e:
    client = None
    print(f"APIキーの設定中にエラーが発生しました: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_audio():
    if not client: return jsonify({'error': 'OpenAI client is not configured.'}), 500
    if 'audio' not in request.files: return jsonify({'error': 'No audio file part'}), 400
    audio_file = request.files['audio']
    if audio_file.filename == '': return jsonify({'error': 'No selected file'}), 400

    try:
        prompt_text = request.form.get('prompt', '')
        transcript_data = client.audio.transcriptions.create(
            model="whisper-1",
            file=(audio_file.filename, audio_file.read()),
            language="ja",
            prompt=prompt_text,
            response_format="verbose_json"
        )
        
        LOGPROB_THRESHOLD = -1.0
        NO_SPEECH_PROB_THRESHOLD = 0.7

        filtered_text = ""
        segments_for_display = []

        for segment in transcript_data.segments:
            avg_logprob = segment.avg_logprob
            no_speech_prob = segment.no_speech_prob
            confidence_percent = math.exp(avg_logprob) * 100
            no_speech_percent = no_speech_prob * 100
            
            segments_for_display.append({
                "text": segment.text,
                "confidence": f"{confidence_percent:.1f}",
                "no_speech_prob": f"{no_speech_percent:.1f}"
            })

            print(f"セグメント: '{segment.text}', 自信: {confidence_percent:.1f}%, 無発話確率: {no_speech_percent:.1f}%")

            if avg_logprob < LOGPROB_THRESHOLD or no_speech_prob > NO_SPEECH_PROB_THRESHOLD:
                print(" -> 幻聴と判断し、このセグメントを無視します。")
                continue
            
            filtered_text += segment.text
        
        is_negative = False
        if filtered_text:
            ng_words = ["ダメだ", "最悪", "話にならない", "絶対に"]
            for word in ng_words:
                if word in filtered_text:
                    is_negative = True
                    break
        
        return jsonify({
            'is_negative': is_negative,
            'filtered_text': filtered_text,
            'raw_segments': segments_for_display
        })

    except Exception as e:
        print(f"分析中にエラーが発生しました: {e}")
        return jsonify({'error': str(e)}), 500

# --- LLMに校正を依頼する新しいルート ---
@app.route('/correct', methods=['POST'])
def correct_text_with_llm():
    if not client:
        return jsonify({'error': 'OpenAI client is not configured.'}), 500
    
    data = request.json
    if not data or 'text' not in data:
        return jsonify({'error': 'No text provided for correction.'}), 400

    original_text = data['text']

    try:
        # GPTモデルに校正を依頼
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "あなたは、ビジネス会議の議事録を校正するプロフェッショナルな書記です。以下のテキストの誤字脱字を修正し、文脈として不自然な部分（例：「天候をとります」→「点呼をとります」）を修正し、自然で読みやすい日本語の議事録に清書してください。"
                },
                {
                    "role": "user",
                    "content": original_text
                }
            ]
        )
        
        corrected_text = response.choices[0].message.content
        return jsonify({'corrected_text': corrected_text})

    except Exception as e:
        print(f"LLM校正中にエラーが発生しました: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)


"""
"""
# app.py (リアルタイム感情分析搭載 最終版)
import os
import math
import librosa
import numpy as np
from openai import OpenAI
from flask import Flask, request, jsonify, render_template
from getpass import getpass

app = Flask(__name__)

try:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY") or getpass("Please enter your OpenAI API Key: "))
except Exception as e:
    client = None
    print(f"APIキーの設定中にエラーが発生しました: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_audio():
    if not client: return jsonify({'error': 'OpenAI client is not configured.'}), 500
    if 'audio' not in request.files: return jsonify({'error': 'No audio file part'}), 400
    audio_file = request.files['audio']
    if audio_file.filename == '': return jsonify({'error': 'No selected file'}), 400

    try:


        # --- AI ①：Whisperによる文字起こし ---
        prompt_text = request.form.get('prompt', '')
        transcript_data = client.audio.transcriptions.create(
            model="whisper-1",
            file=(audio_file.filename, audio_file.read()),
            language="ja",
            prompt=prompt_text,
            response_format="verbose_json"
        )
        
        # --- 幻聴フィルター ---
        LOGPROB_THRESHOLD = -1.0
        NO_SPEECH_PROB_THRESHOLD = 0.7
        filtered_text = ""
        segments_for_display = []
        for segment in transcript_data.segments:
            avg_logprob = segment.avg_logprob
            no_speech_prob = segment.no_speech_prob
            if avg_logprob < LOGPROB_THRESHOLD or no_speech_prob > NO_SPEECH_PROB_THRESHOLD:
                continue
            filtered_text += segment.text
            segments_for_display.append({
                "text": segment.text,
                "confidence": f"{math.exp(avg_logprob) * 100:.1f}",
                "no_speech_prob": f"{no_speech_prob * 100:.1f}"
            })
        
        # --- ★★★ ここからが新しい処理 ★★★ ---
        # --- AI ②：LLMによるリアルタイム感情分析 ---
        sentiment_score = 0.0 # デフォルト値
        is_negative_atmosphere = False

        if filtered_text.strip(): # 文字起こし結果がある場合のみ感情分析
            try:
                # Function Callingを使って、感情を数値で取得する
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "あなたはテキストの感情を分析する専門家です。ユーザーのテキストがポジティブかネガティブかを判断し、-1.0（完全にネガティブ）から1.0（完全にポジティブ）の間のスコアで評価してください。"},
                        {"role": "user", "content": filtered_text}
                    ],
                    functions=[
                        {
                            "name": "set_sentiment_score",
                            "description": "感情分析スコアを設定する",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "score": {
                                        "type": "number",
                                        "description": "感情スコア, -1.0から1.0"
                                    }
                                },
                                "required": ["score"]
                            }
                        }
                    ],
                    function_call={"name": "set_sentiment_score"}
                )
                
                # AIからの返事を解析
                import json
                function_args = json.loads(response.choices[0].message.function_call.arguments)
                sentiment_score = function_args.get("score", 0.0)
                
                # 雰囲気がネガティブかどうかの判定（-0.3より低い場合）
                if sentiment_score < -0.3:
                    is_negative_atmosphere = True

            except Exception as e:
                print(f"感情分析中にエラー: {e}")
                # 感情分析でエラーが起きても、文字起こしは続けられるようにする

        # is_negativeをis_negative_atmosphereに置き換え
        return jsonify({
            'is_negative': is_negative_atmosphere, 
            'filtered_text': filtered_text,
            'raw_segments': segments_for_display,
            'sentiment_score': f"{sentiment_score:.2f}" # 新しく感情スコアを追加
        })

    except Exception as e:
        print(f"分析中にエラーが発生しました: {e}")
        return jsonify({'error': str(e)}), 500

# /correct ルートと main の部分は変更ありません
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
    app.run(debug=True)


"""
"""
音声取り込みエラー
# app.py (librosaによるトーン分析機能を追加した最新版)
import os
import math
import librosa  # ★追加
import numpy as np # ★追加
from openai import OpenAI
from flask import Flask, request, jsonify, render_template
from getpass import getpass

app = Flask(__name__)

try:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY") or getpass("Please enter your OpenAI API Key: "))
except Exception as e:
    client = None
    print(f"APIキーの設定中にエラーが発生しました: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_audio():
    if not client: return jsonify({'error': 'OpenAI client is not configured.'}), 500
    if 'audio' not in request.files: return jsonify({'error': 'No audio file part'}), 400
    audio_file = request.files['audio']
    if audio_file.filename == '': return jsonify({'error': 'No selected file'}), 400

    try:
        # --- ★★★ ここからがトーン分析の新しい処理 ★★★ ---

        # 1. 一時的に音声ファイルを保存 (librosaで読み込むため)
        temp_filename = "temp_audio_for_librosa.webm"
        audio_file.save(temp_filename)

        # 2. librosaで音声ファイルを読み込み
        # y: 音声の波形データ, sr: サンプリングレート
        y, sr = librosa.load(temp_filename)

        # 3. 音響特徴量を抽出
        # ピッチ（声の高さ）を推定
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        # エネルギー（声の大きさ）を計算
        rms = librosa.feature.rms(y=y)

        # 4. 特徴量を代表的な数値に変換（平均値をとる）
        # 発話区間だけの平均ピッチを計算 (0より大きい値のみ)
        pitch_mean = np.mean(pitches[pitches > 0]) if np.any(pitches > 0) else 0.0
        # 平均エネルギーを計算
        rms_mean = np.mean(rms)

        # 5. 結果をサーバーのコンソールに表示して確認
        print("--- 🎶 トーン分析 中間結果 🎶 ---")
        print(f"平均ピッチ (声の高さ): {pitch_mean:.2f}")
        print(f"平均エネルギー (声の大きさ): {rms_mean:.2f}")
        print("-----------------------------------")
        
        # --- ★★★ トーン分析はここまで ★★★ ---
        # この後、これまで通りWhisper APIにファイルを渡すため、
        # audio_fileオブジェクトのポインタを先頭に戻す
        audio_file.seek(0)


        # --- AI ①：Whisperによる文字起こし (既存の処理) ---
        prompt_text = request.form.get('prompt', '')
        transcript_data = client.audio.transcriptions.create(
            model="whisper-1",
            file=(audio_file.filename, audio_file.read()),
            language="ja",
            prompt=prompt_text,
            response_format="verbose_json"
        )
        
        # --- 幻聴フィルター ---
        LOGPROB_THRESHOLD = -1.0
        NO_SPEECH_PROB_THRESHOLD = 0.7
        filtered_text = ""
        for segment in transcript_data.segments:
            avg_logprob = segment.avg_logprob
            no_speech_prob = segment.no_speech_prob
            if avg_logprob < LOGPROB_THRESHOLD or no_speech_prob > NO_SPEECH_PROB_THRESHOLD:
                continue
            filtered_text += segment.text
        
        # --- AI ②：LLMによるリアルタイム感情分析 ---
        sentiment_score = 0.0 # デフォルト値
        is_negative_atmosphere = False

        if filtered_text.strip():
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "あなたはテキストの感情を分析する専門家です。ユーザーのテキストがポジティブかネガティブかを判断し、-1.0（完全にネガティブ）から1.0（完全にポジティブ）の間のスコアで評価してください。"},
                        {"role": "user", "content": filtered_text}
                    ],
                    functions=[
                        {
                            "name": "set_sentiment_score",
                            "description": "感情分析スコアを設定する",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "score": {
                                        "type": "number",
                                        "description": "感情スコア, -1.0から1.0"
                                    }
                                },
                                "required": ["score"]
                            }
                        }
                    ],
                    function_call={"name": "set_sentiment_score"}
                )
                
                import json
                function_args = json.loads(response.choices[0].message.function_call.arguments)
                sentiment_score = function_args.get("score", 0.0)
                
                if sentiment_score < -0.3:
                    is_negative_atmosphere = True

            except Exception as e:
                print(f"感情分析中にエラー: {e}")

        return jsonify({
            'is_negative': is_negative_atmosphere, 
            'filtered_text': filtered_text,
            'sentiment_score': f"{sentiment_score:.2f}"
        })

    except Exception as e:
        print(f"分析中にエラーが発生しました: {e}")
        return jsonify({'error': str(e)}), 500

# /correct ルートと main の部分は変更ありません
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
    app.run(debug=True)

"""
"""
# app.py (pydubによる変換機能を追加した最終解決版)
import os
import math
import librosa
import numpy as np
from openai import OpenAI
from flask import Flask, request, jsonify, render_template
from getpass import getpass
from pydub import AudioSegment # ★pydubをインポート

app = Flask(__name__)

try:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY") or getpass("Please enter your OpenAI API Key: "))
except Exception as e:
    client = None
    print(f"APIキーの設定中にエラーが発生しました: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_audio():
    if not client: return jsonify({'error': 'OpenAI client is not configured.'}), 500
    if 'audio' not in request.files: return jsonify({'error': 'No audio file part'}), 400
    audio_file = request.files['audio']
    if audio_file.filename == '': return jsonify({'error': 'No selected file'}), 400

    try:
        # --- ★★★ トーン分析の処理をpydubを使って修正 ★★★ ---

        # 1. 一時的にwebmファイルを保存
        webm_filename = "temp_audio.webm"
        audio_file.save(webm_filename)

        # 2. pydubを使ってwebmファイルをwavファイルに変換
        sound = AudioSegment.from_file(webm_filename, format="webm")
        wav_filename = "temp_converted.wav"
        sound.export(wav_filename, format="wav")

        # 3. librosaで「変換後のwavファイル」を読み込み
        y, sr = librosa.load(wav_filename)

        # 4. 音響特徴量を抽出
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        rms = librosa.feature.rms(y=y)

        # 5. 特徴量を代表的な数値に変換
        pitch_mean = np.mean(pitches[pitches > 0]) if np.any(pitches > 0) else 0.0
        rms_mean = np.mean(rms)

        # 6. 結果をサーバーのコンソールに表示して確認
        print("--- 🎶 トーン分析 中間結果 🎶 ---")
        print(f"平均ピッチ (声の高さ): {pitch_mean:.2f}")
        print(f"平均エネルギー (声の大きさ): {rms_mean:.2f}")
        print("-----------------------------------")
        
        # --- ★★★ トーン分析ここまで ★★★ ---
        
        audio_file.seek(0) # Whisperに渡すためにポインタを戻す

        # --- AI ①：Whisperによる文字起こし (既存の処理) ---
        # (このセクションは変更ありません)
        prompt_text = request.form.get('prompt', '')
        transcript_data = client.audio.transcriptions.create(
            model="whisper-1",
            file=(audio_file.filename, audio_file.read()),
            language="ja",
            prompt=prompt_text,
            response_format="verbose_json"
        )
        
        # (以下、既存のコードは変更ありません)
        LOGPROB_THRESHOLD = -1.0
        NO_SPEECH_PROB_THRESHOLD = 0.7
        filtered_text = ""
        for segment in transcript_data.segments:
            avg_logprob = segment.avg_logprob
            no_speech_prob = segment.no_speech_prob
            if avg_logprob < LOGPROB_THRESHOLD or no_speech_prob > NO_SPEECH_PROB_THRESHOLD:
                continue
            filtered_text += segment.text
        
        sentiment_score = 0.0
        is_negative_atmosphere = False
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
                import json
                function_args = json.loads(response.choices[0].message.function_call.arguments)
                sentiment_score = function_args.get("score", 0.0)
                if sentiment_score < -0.3:
                    is_negative_atmosphere = True
            except Exception as e:
                print(f"感情分析中にエラー: {e}")

        return jsonify({
            'is_negative': is_negative_atmosphere, 
            'filtered_text': filtered_text,
            'sentiment_score': f"{sentiment_score:.2f}"
        })

    except Exception as e:
        print(f"分析中にエラーが発生しました: {e}")
        return jsonify({'error': str(e)}), 500

# /correct ルートと main の部分は変更ありません
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
    app.run(debug=True)

"""
"""
# app.py (怒り検知ロジック搭載版)
import os
import math
import librosa
import numpy as np
from openai import OpenAI
from flask import Flask, request, jsonify, render_template
from getpass import getpass
from pydub import AudioSegment

app = Flask(__name__)

try:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY") or getpass("Please enter your OpenAI API Key: "))
except Exception as e:
    client = None
    print(f"APIキーの設定中にエラーが発生しました: {e}")

# --- ★★★ 3つの特徴量からスコアを計算するよう変更 ★★★ ---
def calculate_tone_score(pitch, energy, spectral_centroid):

    # --- チューニング・ダイヤル ---
    # 喜びの判定基準
    PITCH_JOY_THRESHOLD = 180.0
    ENERGY_JOY_THRESHOLD = 0.04
    # 怒りの判定基準
    ENERGY_ANGER_THRESHOLD = 0.07  # 怒りはより大きなエネルギーを伴う
    SPECTRAL_ANGER_THRESHOLD = 2500 # 怒りの声は響きが鋭い（スペクトル重心が高い）

    # 1. 怒りの判定 (優先度を高く)
    if energy > ENERGY_ANGER_THRESHOLD and spectral_centroid > SPECTRAL_ANGER_THRESHOLD:
        # エネルギーが大きく、声が鋭い -> 怒り
        return -0.8 # 強いネガティブスコア

    # 2. 喜びの判定
    elif pitch > PITCH_JOY_THRESHOLD and energy > ENERGY_JOY_THRESHOLD:
        # 声が高く、エネルギーも大きい -> 喜び
        return 0.7

    # 3. それ以外
    else:
        return 0.0

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_audio():
    if not client: return jsonify({'error': 'OpenAI client is not configured.'}), 500
    if 'audio' not in request.files: return jsonify({'error': 'No audio file part'}), 400
    audio_file = request.files['audio']
    if audio_file.filename == '': return jsonify({'error': 'No selected file'}), 400

    try:
        # --- トーン分析処理 ---
        webm_filename = "temp_audio.webm"
        audio_file.save(webm_filename)
        sound = AudioSegment.from_file(webm_filename, format="webm")
        wav_filename = "temp_converted.wav"
        sound.export(wav_filename, format="wav")
        y, sr = librosa.load(wav_filename)
        
        # 3つの特徴量を抽出
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        rms = librosa.feature.rms(y=y)
        # ★★★ スペクトル重心を追加 ★★★
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)

        # 平均値を計算
        pitch_mean = np.mean(pitches[pitches > 0]) if np.any(pitches > 0) else 0.0
        rms_mean = np.mean(rms)
        spectral_centroid_mean = np.mean(spectral_centroid) # ★スペクトル重心の平均値

        # ★ 3つの特徴量を渡してトーンスコアを計算
        tone_score = calculate_tone_score(pitch_mean, rms_mean, spectral_centroid_mean)
        
        print("--- 🎶 トーン分析 結果 🎶 ---")
        print(f"平均ピッチ: {pitch_mean:.2f}, 平均エネルギー: {rms_mean:.2f}, スペクトル重心: {spectral_centroid_mean:.2f}")
        print(f"算出されたトーンスコア: {tone_score:.2f}")
        print("-----------------------------------")
        
        audio_file.seek(0)

        # (テキスト分析とスコア統合の部分は変更なし)
        prompt_text = request.form.get('prompt', '')
        transcript_data = client.audio.transcriptions.create(
            model="whisper-1", file=(audio_file.filename, audio_file.read()), language="ja", prompt=prompt_text, response_format="verbose_json"
        )
        filtered_text = ""
        for segment in transcript_data.segments:
            if segment.avg_logprob > -1.0 and segment.no_speech_prob < 0.7:
                 filtered_text += segment.text
        text_sentiment_score = 0.0
        if filtered_text.strip():
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "system", "content": "あなたはテキストの感情を分析する専門家です。ユーザーのテキストがポジティブかネガティブかを判断し、-1.0（完全にネガティブ）から1.0（完全にポジティブ）の間のスコアで評価してください。"},{"role": "user", "content": filtered_text}],
                    functions=[{"name": "set_sentiment_score","description": "感情分析スコアを設定する","parameters": {"type": "object","properties": {"score": {"type": "number","description": "感情スコア, -1.0から1.0"}},"required": ["score"]}}],
                    function_call={"name": "set_sentiment_score"}
                )
                import json
                function_args = json.loads(response.choices[0].message.function_call.arguments)
                text_sentiment_score = function_args.get("score", 0.0)
            except Exception as e:
                print(f"感情分析中にエラー: {e}")

        final_score = (text_sentiment_score * 0.7) + (tone_score * 0.3)
        final_score = max(-1.0, min(1.0, final_score))
        print(f"--- 📊 スコア統合結果 📊 ---")
        print(f"テキストスコア: {text_sentiment_score:.2f}, トーンスコア: {tone_score:.2f}, 最終スコア: {final_score:.2f}")
        print("-----------------------------")
        is_negative_atmosphere = True if final_score < -0.3 else False
        return jsonify({
            'is_negative': is_negative_atmosphere, 
            'filtered_text': filtered_text,
            'text_score': f"{text_sentiment_score:.2f}",
            'tone_score': f"{tone_score:.2f}",
            'final_score': f"{final_score:.2f}"
        })

    except Exception as e:
        print(f"分析中にエラーが発生しました: {e}")
        return jsonify({'error': str(e)}), 500

# /correct ルートは変更なし
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
    app.run(debug=True)

"""
"""
# app.py (正規化＋ルールベース搭載 最終形態)
import os
import math
import librosa
import numpy as np
from openai import OpenAI
from flask import Flask, request, jsonify, render_template
from getpass import getpass
from pydub import AudioSegment

app = Flask(__name__)

try:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY") or getpass("Please enter your OpenAI API Key: "))
except Exception as e:
    client = None
    print(f"APIキーの設定中にエラーが発生しました: {e}")

# --- ★★★ 正規化とルールベースを融合させた最終版の関数 ★★★ ---
def calculate_tone_score(pitch, energy, spectral_centroid):

    # --- チューニング・ダイヤル (正規化のための基準値) ---
    PITCH_MIN, PITCH_MAX = 85.0, 255.0
    ENERGY_MIN, ENERGY_MAX = 0.005, 0.15
    SPECTRAL_MIN, SPECTRAL_MAX = 500.0, 3500.0

    # 1. 各特徴量を 0.0 ~ 1.0 の範囲に正規化
    norm_pitch = (np.clip(pitch, PITCH_MIN, PITCH_MAX) - PITCH_MIN) / (PITCH_MAX - PITCH_MIN)
    norm_energy = (np.clip(energy, ENERGY_MIN, ENERGY_MAX) - ENERGY_MIN) / (ENERGY_MAX - ENERGY_MIN)
    norm_sharpness = (np.clip(spectral_centroid, SPECTRAL_MIN, SPECTRAL_MAX) - SPECTRAL_MIN) / (SPECTRAL_MAX - SPECTRAL_MIN)

    # 2. ルールベースによる特定パターンの判定 (優先)
    # 怒りのパターン：エネルギーが非常に高く(上位20%)、かつ、声が非常に鋭い(上位20%)
    if norm_energy > 0.8 and norm_sharpness > 0.8:
        return -0.8  # 強いネガティブスコアを返す

    # 喜びのパターン：エネルギーが高く(上位30%)、かつ、ピッチも高い(上位30%)
    elif norm_energy > 0.7 and norm_pitch > 0.7:
        return 0.7  # 強いポジティブスコアを返す

    # 3. 上記の特殊なパターン以外は、滑らかなスコアを計算
    else:
        # 正規化された値を -1.0 ~ 1.0 のスコアに変換
        pitch_score = (norm_pitch - 0.5) * 2
        energy_score = (norm_energy - 0.5) * 2
        
        # ピッチとエネルギーの平均を基本的なトーンスコアとする
        base_score = (pitch_score + energy_score) / 2.0
        return base_score

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_audio():
    if not client: return jsonify({'error': 'OpenAI client is not configured.'}), 500
    if 'audio' not in request.files: return jsonify({'error': 'No audio file part'}), 400
    audio_file = request.files['audio']
    if audio_file.filename == '': return jsonify({'error': 'No selected file'}), 400

    try:
        # --- トーン分析処理 ---
        webm_filename = "temp_audio.webm"
        audio_file.save(webm_filename)
        sound = AudioSegment.from_file(webm_filename, format="webm")
        wav_filename = "temp_converted.wav"
        sound.export(wav_filename, format="wav")
        y, sr = librosa.load(wav_filename)
        
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        rms = librosa.feature.rms(y=y)
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        
        pitch_mean = np.mean(pitches[pitches > 0]) if np.any(pitches > 0) else 0.0
        rms_mean = np.mean(rms)
        spectral_centroid_mean = np.mean(spectral_centroid)
        
        # 最終版の関数を呼び出してトーンスコアを計算
        tone_score = calculate_tone_score(pitch_mean, rms_mean, spectral_centroid_mean)
        
        print("--- 🎶 トーン分析 結果 🎶 ---")
        print(f"平均ピッチ: {pitch_mean:.2f}, 平均エネルギー: {rms_mean:.2f}, スペクトル重心: {spectral_centroid_mean:.2f}")
        print(f"算出されたトーンスコア: {tone_score:.2f}")
        print("-----------------------------------")
        
        audio_file.seek(0)

        # --- テキスト分析とスコア統合 (変更なし) ---
        prompt_text = request.form.get('prompt', '')
        transcript_data = client.audio.transcriptions.create(
            model="whisper-1", file=(audio_file.filename, audio_file.read()), language="ja", prompt=prompt_text, response_format="verbose_json"
        )
        filtered_text = ""
        for segment in transcript_data.segments:
            if segment.avg_logprob > -1.0 and segment.no_speech_prob < 0.7:
                 filtered_text += segment.text
        text_sentiment_score = 0.0
        if filtered_text.strip():
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "system", "content": "あなたはテキストの感情を分析する専門家です。ユーザーのテキストがポジティブかネガティブかを判断し、-1.0（完全にネガティブ）から1.0（完全にポジティブ）の間のスコアで評価してください。"},{"role": "user", "content": filtered_text}],
                    functions=[{"name": "set_sentiment_score","description": "感情分析スコアを設定する","parameters": {"type": "object","properties": {"score": {"type": "number","description": "感情スコア, -1.0から1.0"}},"required": ["score"]}}],
                    function_call={"name": "set_sentiment_score"}
                )
                import json
                function_args = json.loads(response.choices[0].message.function_call.arguments)
                text_sentiment_score = function_args.get("score", 0.0)
            except Exception as e:
                print(f"感情分析中にエラー: {e}")

        final_score = (text_sentiment_score * 0.7) + (tone_score * 0.3)
        final_score = max(-1.0, min(1.0, final_score))
        print(f"--- 📊 スコア統合結果 📊 ---")
        print(f"テキストスコア: {text_sentiment_score:.2f}, トーンスコア: {tone_score:.2f}, 最終スコア: {final_score:.2f}")
        print("-----------------------------")
        is_negative_atmosphere = True if final_score < -0.3 else False

        return jsonify({
            'is_negative': is_negative_atmosphere, 
            'filtered_text': filtered_text,
            'text_score': f"{text_sentiment_score:.2f}",
            'tone_score': f"{tone_score:.2f}",
            'final_score': f"{final_score:.2f}"
        })

    except Exception as e:
        print(f"分析中にエラーが発生しました: {e}")
        return jsonify({'error': str(e)}), 500

# /correct ルートと main の部分は変更ありません
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
    app.run(debug=True)
"""
"""
# app.py (省略一切なし・最終完成版)
import os
import math
import librosa
import numpy as np
from openai import OpenAI
from flask import Flask, request, jsonify, render_template
from getpass import getpass
from pydub import AudioSegment
import json

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
    感情辞書から正規化のための最小値・最大値を計算する
    global normalization_ranges
    
    if len(emotion_dictionary) < 4:
        return

    pitches = [vec[0] for vec in emotion_dictionary.values()]
    energies = [vec[1] for vec in emotion_dictionary.values()]
    sharpnesses = [vec[2] for vec in emotion_dictionary.values()]

    # 値が一つしかない場合にエラーになるのを防ぐため、少し幅を持たせる
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
    print("--- 正規化レンジを計算しました ---")
    print(normalization_ranges)
    print("------------------------------------------------")

def calculate_personalized_score(pitch, energy, sharpness, ranges):

    if not ranges:
        return 0.0

    def normalize(value, r):
        # 0除算を避ける
        if (r['max'] - r['min']) == 0:
            return 0.5
        return (np.clip(value, r['min'], r['max']) - r['min']) / (r['max'] - r['min'])

    norm_pitch = normalize(pitch, ranges['pitch'])
    norm_energy = normalize(energy, ranges['energy'])
    norm_sharpness = normalize(sharpness, ranges['sharpness'])

    if norm_energy > 0.8 and norm_sharpness > 0.8:
        return -0.8
    elif norm_energy > 0.7 and norm_pitch > 0.7:
        return 0.7
    else:
        pitch_score = (norm_pitch - 0.5) * 2
        energy_score = (norm_energy - 0.5) * 2
        return (pitch_score + energy_score) / 2.0

@app.route('/calibrate', methods=['POST'])
def calibrate_emotion():
    if 'audio' not in request.files: return jsonify({'status': 'error', 'error': 'No audio file part'}), 400
    emotion = request.args.get('emotion')
    if not emotion: return jsonify({'status': 'error', 'error': 'Emotion label is missing'}), 400
    audio_file = request.files['audio']
    try:
        webm_filename = f"temp_{emotion}.webm"
        audio_file.save(webm_filename)
        sound = AudioSegment.from_file(webm_filename, format="webm")
        wav_filename = f"temp_{emotion}.wav"
        sound.export(wav_filename, format="wav")
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
    if not normalization_ranges:
        return jsonify({'error': '調整が完了していません。全ての感情を登録してください。'})

    audio_file = request.files['audio']
    try:
        webm_filename = "temp_audio.webm"
        audio_file.save(webm_filename)
        sound = AudioSegment.from_file(webm_filename, format="webm")
        wav_filename = "temp_converted.wav"
        sound.export(wav_filename, format="wav")
        y, sr = librosa.load(wav_filename)
        
        pitches, _ = librosa.piptrack(y=y, sr=sr)
        rms = librosa.feature.rms(y=y)
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        
        current_features = [
            np.mean(pitches[pitches > 0]) if np.any(pitches > 0) else 0.0,
            np.mean(rms),
            np.mean(spectral_centroid)
        ]
        
        tone_score = calculate_personalized_score(current_features[0], current_features[1], current_features[2], normalization_ranges)
        
        audio_file.seek(0)
        prompt_text = request.form.get('prompt', '')
        transcript_data = client.audio.transcriptions.create(
            model="whisper-1", file=(audio_file.filename, audio_file.read()), language="ja", prompt=prompt_text, response_format="verbose_json"
        )
        
        filtered_text = ""
        for segment in transcript_data.segments:
            if segment.avg_logprob > -1.0 and segment.no_speech_prob < 0.7:
                 filtered_text += segment.text
        
        text_sentiment_score = 0.0
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
        print(f"分析中にエラーが発生しました: {e}")
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
    app.run(debug=True)
"""
"""
# app.py (デフォルトモード搭載・最終版)
import os
import math
import librosa
import numpy as np
from openai import OpenAI
from flask import Flask, request, jsonify, render_template
from getpass import getpass
from pydub import AudioSegment
import json

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

# ★★★ 関数名をより汎用的に変更 ★★★
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

@app.route('/calibrate', methods=['POST'])
def calibrate_emotion():
    # (この関数は変更ありません)
    emotion = request.args.get('emotion')
    audio_file = request.files['audio']
    try:
        webm_filename = f"temp_{emotion}.webm"; audio_file.save(webm_filename)
        sound = AudioSegment.from_file(webm_filename, format="webm"); wav_filename = f"temp_{emotion}.wav"; sound.export(wav_filename, format="wav")
        y, sr = librosa.load(wav_filename)
        pitches, _ = librosa.piptrack(y=y, sr=sr); rms = librosa.feature.rms(y=y); spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        pitch_mean = np.mean(pitches[pitches > 0]) if np.any(pitches > 0) else 0.0; rms_mean = np.mean(rms); spectral_centroid_mean = np.mean(spectral_centroid)
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
    try:
        # ★★★ ここからがハイブリッド化のキモ ★★★
        active_ranges = {}
        if normalization_ranges: # キャリブレーションが完了しているか？
            # 完了している -> あなた専用の物差しを使う
            active_ranges = normalization_ranges
            print("パーソナライズ設定で分析中...")
        else:
            # 未完了 -> デフォルトの物差しを使う
            active_ranges = {
                'pitch': {'min': 85.0, 'max': 255.0},
                'energy': {'min': 0.005, 'max': 0.15},
                'sharpness': {'min': 500.0, 'max': 3500.0}
            }
            print("デフォルト設定で分析中...")
        # ★★★ ここまで ★★★

        # (特徴量抽出のコードは同じ)
        webm_filename = "temp_audio.webm"; audio_file.save(webm_filename)
        sound = AudioSegment.from_file(webm_filename, format="webm"); wav_filename = "temp_converted.wav"; sound.export(wav_filename, format="wav")
        y, sr = librosa.load(wav_filename)
        pitches, _ = librosa.piptrack(y=y, sr=sr); rms = librosa.feature.rms(y=y); spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        current_features = [
            np.mean(pitches[pitches > 0]) if np.any(pitches > 0) else 0.0,
            np.mean(rms),
            np.mean(spectral_centroid)
        ]
        
        # 選択された物差し(active_ranges)を使ってスコアを計算
        tone_score = calculate_tone_score(current_features[0], current_features[1], current_features[2], active_ranges)
        
        # (テキスト分析とスコア統合、結果返却の部分は変更なし)
        audio_file.seek(0)
        prompt_text = request.form.get('prompt', '')
        transcript_data = client.audio.transcriptions.create(model="whisper-1", file=(audio_file.filename, audio_file.read()), language="ja", prompt=prompt_text, response_format="verbose_json")
        filtered_text = ""
        for segment in transcript_data.segments:
            if segment.avg_logprob > -1.0 and segment.no_speech_prob < 0.7: filtered_text += segment.text
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
        response = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "system", "content": "あなたはビジネス会議の議事録を校正するプロの書記です。誤字脱字を修正し、文脈として不自然な部分を修正し、自然で読みやすい日本語の議事録に清書してください。"},{"role": "user", "content": original_text}])
        corrected_text = response.choices[0].message.content
        return jsonify({'corrected_text': corrected_text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
"""

# app.py (小学生でもわかる解説コメント付き)

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
    """
    4つの感情サンプルが集まったら、あなただけの「声のものさし」を作る関数。
    """
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
    print("--- 🧠 あなた専用の正規化レンジ（ものさし）を計算しました ---")
    print(normalization_ranges)


def calculate_tone_score(pitch, energy, sharpness, ranges):
    """
    声のトーンから、今の気持ちを点数にする、このシステムの心臓部の一つ。
    """
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
    """
    ブラウザの「〇〇を録音」ボタンが押されたときに動く、サーバーの受付窓口。
    """
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
    """
    ユーザーが最初にアクセスしたときに、メインのWebページ（index.html）を表示する。
    """
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_audio():
    """
    「分析開始」のあと、リアルタイムでずっと動き続ける、メインの分析工場。
    """
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
            if segment.avg_logprob > -1.0 and segment.no_speech_prob < 0.7: filtered_text += segment.text
        
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
    """
    「LLMで校正」ボタンが押されたときに動く、特別な受付窓口。
    """
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