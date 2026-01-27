import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import pandas as pd
from PIL import Image
import pypdf
import json

# law_data.py からテキストを読み込む
try:
    from law_data import PROMPT_TEXT
except ImportError:
    PROMPT_TEXT = "（法律データファイル law_data.py が見つかりませんでした。）"

# ページ設定
st.set_page_config(page_title="いじめ対応支援AI", page_icon="🛡️")

st.title("🛡️ いじめ対応支援AIパートナー")
st.markdown("""
**学校や教育委員会の対応に疑問を感じていませんか？**
文章だけでなく、**「学校からの手紙(PDF)」「録音データ」「手書きメモの写真」**などをアップロードすると、法律違反がないか徹底的にチェックし、**根拠となる資料とページ数**を案内します。
""")

# APIキーの設定
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except:
    st.error("APIキー設定エラー：Streamlit CloudのSecretsを確認してください。")

# 参照資料リスト
REFERENCE_MAP = """
【重要資料のページ数・URL対応表】
AIは回答時に、以下の情報を参照して「該当ページ数」を必ず提示してください。

■いじめの重大事態の調査に関するガイドライン（令和6年8月改訂版）
[URL] https://www.mext.go.jp/a_menu/shotou/seitoshidou/1302904.htm
[ページ目安] P.1(基本的姿勢), P.2(重大事態定義), P.4(報告義務), P.15(公表)

■いじめ防止対策推進法（条文）
[URL] https://elaws.e-gov.go.jp/document?lawid=425AC1000000071
[ページ目安] 第22条(組織), 第23条(通報義務), 第28条(重大事態)

■いじめの防止等のための基本的な方針（平成29年改定）
[URL] https://www.mext.go.jp/a_menu/shotou/seitoshidou/1302904.htm
[ページ目安] P.3(定義), P.12(解消定義), P.15(抱え込み禁止)
"""

# システムプロンプト（記憶に関する指示を強化）
SYSTEM_INSTRUCTION = f"""
あなたは、いじめ被害児童とその家族を守るための「法務・教育行政アドバイザーAI」です。
ユーザーと継続的な対話を行い、学校側の対応に違法性がないかチェックしてください。

【重要：記憶と履歴について】
あなたは、**現在提供されている「会話履歴（Context）」を、自分自身の「記憶」として扱ってください。**
ユーザーが「前回話した内容は？」や「さっきの資料は？」と質問した場合、**「記憶がありません」と答えるのではなく、履歴にある情報を読み返して回答してください。**

【あなたの役割】
1. **証拠の解析**: 提示されたPDF、音声、画像の内容を読み取る。
2. **法的指摘**: 学校の対応の不備を指摘する。
3. **視覚的強調**: 根拠となる資料とページ数を、罫線を使って大きく表示する。
4. **対話の維持**: ユーザーの追加質問にも、過去の文脈（資料内容など）を踏まえて回答する。

---
【参照すべき法律知識 (law_data.py)】
{PROMPT_TEXT}

【ページ数・URLリスト (REFERENCE_MAP)】
{REFERENCE_MAP}
---

【出力フォーマット】

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓

　📖 **根拠資料**
　**[資料名]**

　📍 **該当箇所**
　**【 第〇条 第〇項 】** （または P.〇〇）
　※条文の場合は必ず「第何項」まで特定すること！

　🔗 **入手先URL**
　[URL]
　※「ガイドライン」等は「ページ内の【PDF】を開いてください」と添える

┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

> **内容:** 「......」

**解説:** ...
"""

# 安全フィルターの完全解除
safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# ---------------------------------------------------------
# セッション管理
# ---------------------------------------------------------

# 1. モデルの準備
if "model" not in st.session_state:
    st.session_state.model = genai.GenerativeModel(
        model_name="gemini-flash-latest",
        system_instruction=SYSTEM_INSTRUCTION,
        safety_settings=safety_settings
    )

# 2. 画面表示用の履歴初期化
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant",
        "content": "こんにちは。学校の対応について、法律やガイドラインに基づいた分析を行います。\n証拠資料（PDF、録音、写真など）があればアップロードしてください。"
    })

# 3. アップローダーのリセット用キー
if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = 0

# ---------------------------------------------------------
# UI部分
# ---------------------------------------------------------

# サイドバー：保存・読み込み・リセット機能
with st.sidebar:
    st.header("💾 履歴の保存・読込")
    st.caption("相談内容を自分の端末に保存して、後で続きから再開できます。")

    # ダウンロードボタン
    chat_history_json = json.dumps(st.session_state.messages, ensure_ascii=False, indent=2)
    st.download_button(
        label="📥 今日の相談履歴を保存",
        data=chat_history_json,
        file_name="ijime_soudan_history.json",
        mime="application/json"
    )

    st.divider()

    # アップロードボタン
    uploaded_history = st.file_uploader("📤 過去の履歴を読み込む", type=["json"])
    
    if uploaded_history is not None:
        if st.button("🔄 読み込みを実行する"):
            try:
                uploaded_history.seek(0)
                loaded_messages = json.load(uploaded_history)
                st.session_state.messages = loaded_messages
                st.success("✅ 履歴を復元しました！画面右側を確認してください。")
            except Exception as e:
                st.error(f"読み込みに失敗しました: {e}")

    st.divider()

    # リセットボタン
    if st.button("🗑️ 会話履歴をリセット"):
        st.session_state.messages = []
        st.session_state.messages.append({
            "role": "assistant",
            "content": "こんにちは。学校の対応について、法律やガイドラインに基づいた分析を行います。\n証拠資料（PDF、録音、写真など）があればアップロードしてください。"
        })
        st.rerun()

# メイン画面：証拠アップロード
with st.expander("📂 証拠資料をアップロードする（PDF・音声・画像・Excel）", expanded=True):
    uploaded_files = st.file_uploader(
        "分析してほしい資料があれば選択してください", 
        type=['png', 'jpg', 'jpeg', 'mp3', 'wav', 'm4a', 'xlsx', 'csv', 'pdf'], 
        accept_multiple_files=True,
        key=f"uploader_{st.session_state['uploader_key']}"
    )
    
    if uploaded_files:
        if st.button("🗑️ 添付ファイルを全て削除する"):
            st.session_state["uploader_key"] += 1
            st.rerun()

# チャット履歴の表示
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# チャット入力欄
if prompt := st.chat_input("相談内容を入力してください..."):
    
    # 1. ユーザー入力を表示
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. AIの応答生成
    with st.chat_message("assistant"):
        with st.spinner("分析中..."):
            try:
                # -------------------------------------------------------------
                # ★ここが重要修正ポイント★
                # 履歴の順番を整理し、AIが理解しやすい形に変換します
                # -------------------------------------------------------------
                history_for_gemini = []
                
                # 履歴の先頭（挨拶など）が「AI」から始まっているとエラーになりやすいため、
                # ユーザーの発言から始まるように調整するか、順番通りに格納する
                for msg in st.session_state.messages[:-1]:
                    # ユーザーの入力か、AIの回答かを判定
                    role = "user" if msg["role"] == "user" else "model"
                    
                    # Geminiは「中身が空」のメッセージを嫌うのでチェック
                    if msg["content"] and msg["content"].strip() != "":
                        history_for_gemini.append({"role": role, "parts": [msg["content"]]})
                
                # 履歴を持った状態でチャットを新規開始（毎回リフレッシュ）
                chat = st.session_state.model.start_chat(history=history_for_gemini)

                # 送信コンテンツの準備
                content_parts = []
                content_parts.append(prompt)
                
                # ファイル処理
                if uploaded_files:
                    for uploaded_file in uploaded_files:
                        file_type = uploaded_file.type
                        if "pdf" in file_type:
                            try:
                                reader = pypdf.PdfReader(uploaded_file)
                                pdf_text = ""
                                for page in reader.pages:
                                    pdf_text += page.extract_text()
                                content_parts.append(f"【参照資料(PDF)】\n{pdf_text}")
                            except: st.error("PDF読込エラー")
                        elif "image" in file_type:
                            content_parts.append(Image.open(uploaded_file))
                        elif "audio" in file_type:
                            content_parts.append({"mime_type": file_type, "data": uploaded_file.read()})
                        elif "spreadsheet" in file_type or "csv" in file_type or "excel" in file_type:
                            try:
                                if "csv" in file_type: df = pd.read_csv(uploaded_file)
                                else: df = pd.read_excel(uploaded_file)
                                content_parts.append(f"【参照データ】\n{df.to_string()}")
                            except: st.error("表読込エラー")

                # AIへ送信
                response = chat.send_message(
                    content_parts,
                    generation_config={"temperature": 0.0},
                    safety_settings=safety_settings
                )
                
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})

            # エラー処理
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "ResourceExhausted" in error_msg or "quota" in error_msg:
                    st.warning("⚠️ **現在、アクセスが集中しています**\n\n1分ほど時間を空けてから、もう一度入力してください。")
                elif "finish_reason" in error_msg and "1" in error_msg:
                    st.error("⚠️ **回答できませんでした**\n\n言い回しを変えて再度お試しください。")
                else:
                    # 詳細なエラーを出してデバッグしやすくする
                    st.error(f"システムエラー: {e}")
