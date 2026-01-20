import streamlit as st
import google.generativeai as genai
import sys

st.set_page_config(page_title="診断中", page_icon="🔧")
st.title("🔧 システム診断モード")
st.write("この画面の情報を教えてください。")

# 1. ライブラリのバージョン確認
try:
    st.write(f"Python Version: {sys.version.split()[0]}")
    st.write(f"SDK Version: {genai.__version__}")
except:
    st.error("SDKのバージョン取得に失敗")

# 2. API接続とモデル一覧の確認
try:
    # APIキーの読み込み
    api_key = st.secrets["GEMINI_API_KEY"]
    
    # キーの前後に余計な空白がないかチェック
    if api_key.strip() != api_key:
        st.warning("⚠️ APIキーの前後に空白が含まれています。Secretsを修正してください。")
    
    genai.configure(api_key=api_key)
    
    st.write("---")
    st.write("📡 Googleのサーバーに問い合わせ中...")
    
    # 利用可能なモデルの一覧を取得
    models = list(genai.list_models())
    available_models = []
    for m in models:
        # 文章生成（generateContent）ができるモデルだけ抽出
        if 'generateContent' in m.supported_generation_methods:
            available_models.append(m.name)
    
    if available_models:
        st.success("✅ API接続成功！ 以下のモデルが使用可能です：")
        st.code(available_models)
        st.info("↑このリストの中に 'models/gemini-1.5-flash' などはありますか？")
    else:
        st.error("⚠️ APIには繋がりましたが、使えるモデルが見つかりませんでした。")

except Exception as e:
    st.error(f"❌ 接続エラーが発生しました:\n{e}")
