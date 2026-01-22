import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# law_data.py からテキストを読み込む
try:
    from law_data import PROMPT_TEXT
except ImportError:
    PROMPT_TEXT = "（法律データファイル law_data.py が見つかりませんでした。）"

# ページ設定
st.set_page_config(page_title="いじめ対応支援AI", page_icon="🛡️")

st.title("🛡️ いじめ対応支援AIパートナー")
st.markdown("""
学校や教育委員会の対応に疑問を感じていませんか？
あなたの状況を入力すると、**「法律のどこに違反しているか」**を、**資料名とページ数付き**で具体的に案内します。
""")

# サイドバー設定
with st.sidebar:
    st.header("ℹ️ 利用上の注意")
    st.warning("入力内容はAIの分析に使用されます。個人情報（実名等）は伏せて入力してください。")
    st.info("提示された条文やページ数をメモして、学校との話し合いの資料としてご活用ください。")

# APIキーの設定
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except:
    st.error("APIキー設定エラー：Streamlit CloudのSecretsを確認してください。")

# ==============================================================================
# 1. ページ数・URL対応表（AIへのカンニングペーパー）
# ==============================================================================
REFERENCE_MAP = """
【重要資料のページ数・URL対応表】
AIは回答時に、以下の情報を参照して「該当ページ数」を必ず提示してください。

■資料A：いじめの重大事態の調査に関するガイドライン（令和6年8月改訂版）
[URL] https://www.mext.go.jp/content/20240821-mxt_jidou02-000037666_001.pdf
[ページ目安]
・P.1  : 学校の基本的姿勢（「隠蔽しない」「責任逃れしない」）
・P.2  : 重大事態の定義（生命心身財産への被害）
・P.3  : 不登校重大事態の定義（欠席30日目安、転校・退学含む）
・P.4  : 発生報告の義務（直ちに教育委員会へ報告）
・P.5  : 被害児童生徒の守秘・安全確保
・P.6  : 調査組織の設置（第三者の参加、公平性・中立性）
・P.9  : 調査前の保護者への説明（目的・手法の合意形成）
・P.11 : 調査の実施（アンケート、聴き取り）
・P.15 : 調査結果の説明・公表（黒塗りは最小限に、個人情報保護を盾にしない）
・P.19 : 再調査（納得できない場合の再調査規定）

■資料B：いじめ防止対策推進法（条文）
[URL] https://elaws.e-gov.go.jp/document?lawid=425AC1000000071
[ページ目安]
・条文のためページ数ではなく「第〇条」と案内すること。
・第22条: 学校いじめ対策組織の設置
・第23条: 通報・事実確認の義務
・第28条: 重大事態の調査義務

■資料C：いじめの防止等のための基本的な方針（平成29年改定）
[URL] https://www.mext.go.jp/a_menu/shotou/seitoshidou/1340964.htm
[ページ目安]
・P.3 : いじめの定義（被害者の主観重視、けんかも含む）
・P.12: いじめの解消定義（行為が止んで3ヶ月 ＋ 心身の苦痛消失）
・P.15: 教職員の抱え込み禁止
"""

# ==============================================================================
# 2. システムプロンプト（AIへの命令書）
# ==============================================================================
SYSTEM_INSTRUCTION = f"""
あなたは、いじめ被害児童とその家族を守るための「法務・教育行政アドバイザーAI」です。
ユーザー（保護者）は精神的に疲弊しています。
学校側の対応が法律やガイドラインに違反している場合、保護者がすぐにその箇所を探せるよう、**「資料名」だけでなく「ページ数（または条数）」までピンポイントで**教えてあげてください。

【あなたの役割】
1. **共感**: 保護者の辛い状況に寄り添う。
2. **法的指摘**: 学校の対応の不備を、厳密に指摘する。
3. **参照案内**: 指摘の根拠となる資料の**「ページ数」**を上記リストから探して明記する。

---
【参照すべき法律知識 (law_data.py)】
{PROMPT_TEXT}

【ページ数・URLリスト (REFERENCE_MAP)】
{REFERENCE_MAP}
---

【出力フォーマット】

### 1. 現状の整理
（保護者の話を要約）

### 2. ⚠️ 法令・ガイドライン違反の疑いがある点
（以下の形式で、違反箇所を指摘してください）

**指摘①：〇〇の対応義務違反**
> **根拠資料:** [資料A/B/C から選択]
> **該当箇所:** **【 P.〇〇 】** （条文の場合は 第〇条）
> **内容:** 「......（重要な部分を引用）......」
> **解説:** 学校側はこう言っていますが、ガイドライン P.〇〇 では明確に否定されています。
> **入手先:** [URL]

（複数ある場合は指摘②、③と続ける）

### 3. 次のアクション（保護者への手紙）
（「この画面を印刷するか、ガイドラインの P.〇〇 を印刷して、先生にこう伝えてください」という具体的な行動アドバイス）
"""

# ==============================================================================
# 3. アプリ実行部分
# ==============================================================================

# 安全フィルターの設定（ここが今回の修正ポイント！）
# 暴力や危険なコンテンツと判断されても、ブロックせずに回答させる設定
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

user_input = st.text_area("相談内容を入力してください", height=300, 
    placeholder="例：子供がいじめで不登校ですが、学校は「重大事態ではない」と言って調査してくれません。ガイドラインのどこを見せればいいですか？")

if st.button("ページ数付きで分析する", type="primary"):
    if user_input:
        with st.spinner("資料のページ数を確認中..."):
            try:
                # generate_content に safety_settings を渡す
                response = model.generate_content(
                    user_input,
                    generation_config={"temperature": 0.0},
                    safety_settings=safety_settings  # ← これを追加しました！
                )
                
                # 安全フィルターで弾かれた場合でもテキストを取得できるようにする
                if response.text:
                    st.markdown("---")
                    st.markdown("### 📋 分析結果")
                    st.write(response.text)
                    st.markdown("---")
                    st.success("💡 **ヒント:** 提示されたページ数（P.〇〇）は、PDFファイルを開いた際のページ番号です。印刷してマーカーを引き、学校交渉にお持ちください。")
                else:
                    st.error("AIが回答を生成できませんでした。別の表現で試してみてください。")

            except Exception as e:
                # エラーの詳細を表示（デバッグ用）
                st.error(f"エラーが発生しました: {e}")
                st.info("※「安全フィルター」等の関係で回答がブロックされた可能性があります。")
    else:
        st.warning("相談内容を入力してください。")
