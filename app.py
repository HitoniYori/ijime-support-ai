import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import pandas as pd
from PIL import Image
import pypdf

# law_data.py からテキストを読み込む
try:
    from law_data import PROMPT_TEXT
except ImportError:
    PROMPT_TEXT = "（法律データファイル law_data.py が見つかりませんでした。）"

# ページ設定
st.set_page_config(page_title="いじめ対応支援AI", page_icon="🛡️")

st.title("🛡️ いじめ対応支援AIパートナー")
st.markdown("""
**「継続的な対話」でサポートします。**
資料をアップロードして分析した後も、「もっと詳しく教えて」「この部分は条文のどこ？」のように、会話を続けることができます。
""")

# APIキーの設定
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except:
    st.error("APIキー設定エラー：Streamlit CloudのSecretsを確認してください。")

# 参照資料リスト
REFERENCE_MAP = """
【重要資料のページ数・URL対応表】
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

# システムプロンプト
SYSTEM_INSTRUCTION = f"""
あなたは、いじめ被害児童とその家族を守るための「法務・教育行政アドバイザーAI」です。
ユーザーと継続的な対話を行い、学校側の対応に違法性がないかチェックしてください。

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
（初回分析時などは以下の形式を推奨しますが、会話の流れに応じて自然に応答してください）

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓

　📖 **根拠資料**
　**[資料名]**

　📍 **該当箇所**
　**【 P. 〇〇 】** （または 第〇条）

　🔗 **入手先URL**
　[URL]

┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

> **内容:** 「......」

**解説:** ...
"""

# 安全フィルターの解除
safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# ---------------------------------------------------------
# セッション管理（会話の記憶 & アップローダー管理）
# ---------------------------------------------------------

# 1. モデルの準備
if "model" not in st.session_state:
    st.session_state.model = genai.GenerativeModel(
        model_name="gemini-flash-latest",
        system_instruction=SYSTEM_INSTRUCTION
    )

# 2. チャットセッション（履歴）の初期化
if "chat_session" not in st.session_state:
    st.session_state.chat_session = st.session_state.model.start_chat(history=[])

# 3. 画面表示用の履歴初期化
if "messages" not in st.session_state:
    st.session_state.messages = []
    # 最初の挨拶
    st.session_state.messages.append({
        "role": "assistant",
        "content": "こんにちは。学校の対応やいじめの問題について、資料の分析や法的根拠の確認をお手伝いします。\n証拠資料（PDFや録音など）があればアップロードしてください。"
    })

# 4. アップローダーのリセット用キー（ここを追加！）
if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = 0

# ---------------------------------------------------------
# UI部分
# ---------------------------------------------------------

# アップロード機能（エクスパンダーに収納）
with st.expander("📂 証拠資料をアップロードする（PDF・音声・画像・Excel）", expanded=True):
    # keyを動的に設定することで、値を変化させればリセットできるようにする
    uploaded_files = st.file_uploader(
        "会話の中で分析してほしい資料があれば選択してください", 
        type=['png', 'jpg', 'jpeg', 'mp3', 'wav', 'm4a', 'xlsx', 'csv', 'pdf'], 
        accept_multiple_files=True,
        key=f"uploader_{st.session_state['uploader_key']}"
    )
    
    # ファイルがある場合のみ「削除ボタン」を表示
    if uploaded_files:
        if st.button("🗑️ 添付ファイルを全て削除する"):
            st.session_state["uploader_key"] += 1 # キーを更新してリセット
            st.rerun() # 画面を再読み込み

# チャット履歴の表示
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# チャット入力欄
if prompt := st.chat_input("相談内容を入力してください..."):
    
    # 1. ユーザーの入力を表示
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. AIの応答生成
    with st.chat_message("assistant"):
        with st.spinner("分析中..."):
            try:
                # 送信データの準備
                content_parts = []
                
                # テキストを追加
                content_parts.append(prompt)
                
                # ファイルがアップロードされていれば、それも一緒にAIに見せる
                if uploaded_files:
                    for uploaded_file in uploaded_files:
                        file_type = uploaded_file.type
                        
                        # PDF
                        if "pdf" in file_type:
                            try:
                                reader = pypdf.PdfReader(uploaded_file)
                                pdf_text = ""
                                for page in reader.pages:
                                    pdf_text += page.extract_text()
                                content_parts.append(f"【参照資料(PDF)】\n{pdf_text}")
                            except:
                                st.error("PDFの読み込みに失敗しました")
                        
                        # 画像
                        elif "image" in file_type:
                            img = Image.open(uploaded_file)
                            content_parts.append(img)
                        
                        # 音声
                        elif "audio" in file_type:
                            audio_bytes = uploaded_file.read()
                            content_parts.append({"mime_type": file_type, "data": audio_bytes})
                        
                        # Excel
                        elif "spreadsheet" in file_type or "csv" in file_type or "excel" in file_type:
                            try:
                                if "csv" in file_type:
                                    df = pd.read_csv(uploaded_file)
                                else:
                                    df = pd.read_excel(uploaded_file)
                                content_parts.append(f"【参照データ】\n{df.to_string()}")
                            except:
                                st.error("表データの読み込みに失敗しました")

                # AIに送信（セッションを使って会話を継続）
                response = st.session_state.chat_session.send_message(
                    content_parts,
                    generation_config={"temperature": 0.0},
                    safety_settings=safety_settings
                )
                
                # 結果を表示
                st.markdown(response.text)
                
                # 履歴に追加
                st.session_state.messages.append({"role": "assistant", "content": response.text})

            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
                st.info("※会話をリセットしたい場合は、サイドバーの「会話をリセット」ボタンを押してください。")

# サイドバー
with st.sidebar:
    st.header("ℹ️ 使い方")
    st.info("ブラウザを開いている間は、AIがこれまでの会話や資料の内容を覚えています。「さっきの件だけど…」と続けて質問できます。")
    if st.button("🗑️ 会話履歴をリセットする"):
        st.session_state.messages = []
        st.session_state.chat_session = st.session_state.model.start_chat(history=[])
        st.rerun()