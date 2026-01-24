import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import pandas as pd
from PIL import Image
import pypdf # PDFを読むためのライブラリ

# law_data.py からテキストを読み込む
try:
    from law_data import PROMPT_TEXT
except ImportError:
    PROMPT_TEXT = "（法律データファイル law_data.py が見つかりませんでした。）"

# ページ設定
st.set_page_config(page_title="いじめ対応支援AI", page_icon="🛡️")

st.title("🛡️ いじめ対応支援AIパートナー")
st.markdown("""
**「証拠」をAIに分析させましょう。**
文章だけでなく、**「学校からの手紙(PDF)」「録音データ」「手書きメモの写真」**などをアップロードすると、法律違反がないか徹底的にチェックします。
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
ユーザーは文章だけでなく、**「PDF資料（学校からの手紙等）」「録音音声」「手書きメモ」「時系列表」**などの証拠資料を提示する場合があります。
これらを統合的に分析し、学校側の対応に違法性がないかチェックしてください。

【あなたの役割】
1. **証拠の解析**: 提示されたPDF、音声、画像の内容を読み取る。
2. **法的指摘**: 学校の対応の不備を指摘する。
3. **視覚的強調**: 根拠となる資料とページ数を、罫線を使って大きく表示する。

---
【参照すべき法律知識 (law_data.py)】
{PROMPT_TEXT}

【ページ数・URLリスト (REFERENCE_MAP)】
{REFERENCE_MAP}
---

【出力フォーマット】

### 1. 証拠資料の確認
（アップロードされた資料から、AIが読み取った内容を要約する）
「PDF資料（学校からの回答書）には、『調査は実施しない』と記載されています」など。

### 2. ⚠️ 法令・ガイドライン違反の疑いがある点

（以下を、違反ポイントごとに繰り返す）

**指摘①：〇〇義務違反の疑い**

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓

　📖 **根拠となる資料**
　**[ここに正式な資料名のみを書く]**

　📍 **該当箇所**
　**【 P. 〇〇 】** （または 第〇条）

　🔗 **入手先URL**
　[URLをここに書く]
　※「ガイドライン」等は「ページ内の【PDF】を開いてください」と添える

┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

> **条文・ガイドラインの内容:**
> 「......（重要な部分を引用）......」

**解説:**
証拠資料では学校側はこう言っていますが、これは資料の P.〇〇 に反しています。

### 3. 次のアクション
（保護者への具体的なアドバイス）
"""

# 安全フィルターの解除
safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

model = genai.GenerativeModel(
    model_name="gemini-flash-latest",
    system_instruction=SYSTEM_INSTRUCTION
)

# ---------------------------------------------------------
# メイン画面のUI
# ---------------------------------------------------------

st.markdown("---")
st.markdown("### 📂 1. 証拠資料のアップロード（任意）")
st.caption("PDF（学校からの手紙等）、録音データ、写真、Excelファイルなどを選択してください。")

# PDFも許可するように type に 'pdf' を追加しました
uploaded_files = st.file_uploader(
    "ここにファイルをドラッグするか、タップして選択", 
    type=['png', 'jpg', 'jpeg', 'mp3', 'wav', 'm4a', 'xlsx', 'csv', 'pdf'], 
    accept_multiple_files=True
)

st.markdown("---")
st.markdown("### 📝 2. 相談内容の入力")

user_input = st.text_area("補足情報や相談内容を入力してください", height=150, 
    placeholder="例：アップロードしたPDFは学校からの回答書です。「調査しない」と書かれている点が問題だと思うのですが、どうでしょうか？")

if st.button("証拠資料を含めて分析する", type="primary"):
    if not user_input and not uploaded_files:
         st.warning("相談内容を入力するか、資料をアップロードしてください。")
    else:
        with st.spinner("証拠資料（PDF・音声・画像・テキスト）を解析中..."):
            try:
                # AIに渡すデータのリスト作成
                content_parts = []
                
                # 1. ユーザーのテキスト入力があれば追加
                if user_input:
                    content_parts.append(user_input)
                
                # 2. アップロードされたファイルの処理
                if uploaded_files:
                    for uploaded_file in uploaded_files:
                        file_type = uploaded_file.type
                        
                        # === PDFの場合（ここを追加しました！）===
                        if "pdf" in file_type:
                            try:
                                reader = pypdf.PdfReader(uploaded_file)
                                pdf_text = ""
                                for page in reader.pages:
                                    pdf_text += page.extract_text()
                                content_parts.append(f"【PDF資料の内容】\n{pdf_text}")
                                content_parts.append("（このPDFの内容を読み、学校側の主張や対応に法的問題がないか分析してください）")
                            except Exception as e:
                                st.error(f"PDFの読み込みに失敗しました: {e}")

                        # 画像の場合
                        elif "image" in file_type:
                            img = Image.open(uploaded_file)
                            content_parts.append(img)
                            content_parts.append("（この画像の内容を読み取り、証拠として分析してください）")
                        
                        # 音声の場合
                        elif "audio" in file_type:
                            audio_bytes = uploaded_file.read()
                            content_parts.append({
                                "mime_type": file_type,
                                "data": audio_bytes
                            })
                            content_parts.append("（この音声の会話内容を聞き取り、文字起こしした上で、法的に問題がある発言を指摘してください）")
                        
                        # Excel/CSVの場合
                        elif "spreadsheet" in file_type or "csv" in file_type or "excel" in file_type:
                            try:
                                if "csv" in file_type:
                                    df = pd.read_csv(uploaded_file)
                                else:
                                    df = pd.read_excel(uploaded_file)
                                excel_text = df.to_string()
                                content_parts.append(f"【時系列・証拠データ】\n{excel_text}")
                                content_parts.append("（この表の時系列を確認し、学校の対応の遅れや矛盾点を指摘してください）")
                            except Exception as e:
                                st.error(f"Excelの読み込みに失敗しました: {e}")

                # AIへ送信
                response = model.generate_content(
                    content_parts,
                    generation_config={"temperature": 0.0},
                    safety_settings=safety_settings
                )
                
                if response.text:
                    st.markdown("---")
                    st.markdown("### 📋 マルチモーダル分析結果")
                    st.write(response.text)
                    st.markdown("---")
                    st.success("AIは資料（PDF等）の内容を理解しています。指摘された内容をメモして活用してください。")
                else:
                    st.error("分析できませんでした。")

            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
                st.info("※ファイルが大きすぎる場合や、破損している可能性があります。")

# サイドバーは注意事項のみにする
with st.sidebar:
    st.header("ℹ️ 利用上の注意")
    st.info("アップロードされたデータはAI分析のみに使用され、外部には保存されません。")