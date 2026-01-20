import streamlit as st
import google.generativeai as genai

# ページ設定
st.set_page_config(page_title="いじめ対応支援AI", page_icon="???")

st.title("??? いじめ対応支援AIパートナー")
st.write("学校とのやり取りや相談内容を入力すると、法律（いじめ防止対策推進法など）に基づいた分析とアドバイスを行います。")

# サイドバーに注意書き
with st.sidebar:
    st.header("利用上の注意")
    st.warning("入力された内容はAIによる分析に使用されます。個人情報（実名や特定できる詳細）は伏せて入力してください。")
    st.info("このAIは法的助言を行う弁護士ではありません。あくまで参考情報として活用し、最終的な判断は専門家にご相談ください。")

# APIキーの設定（Streamlit CloudのSecretsから読み込む設定）
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except:
    st.error("APIキーが設定されていません。")

# ---------------------------------------------------------
# ここに、HitoniYoriさんがGoogle AI Studioで作成した
# 「System Instructions（法律や役割）」を貼り付けます
# ---------------------------------------------------------
SYSTEM_PROMPT = """
あなたは、いじめ被害児童とその家族を守るための支援AIです。
以下の【判断基準となる法律・ガイドライン】を完全に理解し、それに照らし合わせて分析してください。

【判断基準となる法律・ガイドライン】
(ここに、準備したいじめ防止対策推進法やガイドラインの全文を貼り付けてください)

【出力のルール】
・保護者に寄り添う温かいトーンで。
・法的な指摘は条文を引用して鋭く。
"""
# ---------------------------------------------------------

# モデルの準備
model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    system_instruction=SYSTEM_PROMPT
)

# ユーザー入力エリア
user_input = st.text_area("相談内容・学校の対応などを入力してください", height=300)

if st.button("分析を開始する"):
    if user_input:
        with st.spinner("法律と照らし合わせて分析中..."):
            try:
                # AIへの問い合わせ（Temperatureを低く設定）
                response = model.generate_content(
                    user_input,
                    generation_config={"temperature": 0.1}
                )
                st.markdown("### ?? 分析結果")
                st.write(response.text)
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
    else:
        st.warning("文章を入力してください。")