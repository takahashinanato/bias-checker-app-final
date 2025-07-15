import streamlit as st
import openai
import pandas as pd
import plotly.express as px
import json

st.set_page_config(page_title="政治バイアス検出ツール", layout="centered")
openai.api_key = st.secrets["OPENAI_API_KEY"]

st.title("🧠 政治バイアス検出ツール")

# セッション状態の初期化
if "latest_prompt" not in st.session_state:
    st.session_state.latest_prompt = None
if "latest_response" not in st.session_state:
    st.session_state.latest_response = None
if "input_text" not in st.session_state:
    st.session_state.input_text = ""
if "history" not in st.session_state:
    st.session_state.history = []

# UI: 入力欄とジャンル
genre = st.selectbox("ジャンルを選択してください", [
    "政治・政党", "防衛・外交", "福祉・格差", "経済政策", "教育と道徳",
    "ジェンダーと多様性", "表現・言論の自由", "家族観・伝統文化", "社会秩序・治安", "その他"
])
user_input = st.text_area("SNS投稿や意見（500文字以内）を入力", value=st.session_state.input_text, max_chars=500)
st.session_state.input_text = user_input

# 診断・クリアボタン
col1, col2 = st.columns(2)
with col1:
    run_diagnosis = st.button("診断する")
with col2:
    if st.button("🧹 入力をクリア"):
        st.session_state.input_text = ""
        st.session_state.latest_response = None
        st.experimental_rerun()

# GPTプロンプト生成（投稿診断）
def build_prompt(text):
    return f'''
あなたはSNS投稿のバイアス分析AIです。以下の投稿文について、以下の形式でJSONのみを出力してください：

- bias_score（-1.0=保守〜+1.0=リベラル）
- strength_score（0.0〜1.0）
- comment（投稿内容に即した200字以内の分析コメント）
- similar_opinion（{{"content": "...", "bias_score": 数値, "strength_score": 数値}})
- opposite_opinion（{{"content": "...", "bias_score": 数値, "strength_score": 数値}}）

【投稿文】:
{text}
'''

# GPTプロンプト生成（傾向要約）← 改善版
def build_summary_prompt(history):
    return f"""
あなたは、あるユーザーのSNS投稿診断履歴から政治的な傾向を要約するAIです。
以下の履歴には、それぞれの投稿の「バイアススコア（-1.0=保守、+1.0=リベラル）」「主張の強さ（0.0〜1.0）」「ジャンル」「コメント」が含まれています。

この情報をもとに、そのユーザーの傾向を**自然な日本語（200字以内）**で1文〜2文で要約してください。

ポイント：
- 特にバイアスの傾向（保守 or リベラル、どのくらいか）
- 主張の強さ（全体的に穏健か、強めか）
- 特定ジャンルに偏りがあるか（あれば言及）

【診断履歴】:
{json.dumps(history, ensure_ascii=False, indent=2)}

【出力フォーマット】:
あなたの投稿は◯◯寄りで、◯◯に関する意見が多く見られます。また、主張の強さは◯◯傾向にあります。
"""

# GPT呼び出し
def fetch_chatgpt(prompt):
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "あなたは政治的傾向を分析・要約するAIです。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "").strip()
        return json.loads(content) if content.startswith("{") else content
    except:
        return None

# 診断処理
if run_diagnosis and user_input:
    with st.spinner("診断中..."):
        result = fetch_chatgpt(build_prompt(user_input))
        if isinstance(result, dict):
            st.session_state.latest_prompt = user_input
            st.session_state.latest_response = result
            st.session_state.history.append({
                "Bias": result["bias_score"],
                "Strength": result["strength_score"],
                "ジャンル": genre,
                "コメント": result["comment"]
            })
        else:
            st.error("診断に失敗しました。")

# 診断結果表示
if st.session_state.latest_response:
    data = st.session_state.latest_response
    st.markdown("### 💬 コメント")
    st.markdown(data["comment"])

    df_latest = pd.DataFrame([{
        "Bias": data["bias_score"],
        "Strength": data["strength_score"],
        "ジャンル": genre
    }])
    fig = px.scatter(df_latest, x="Bias", y="Strength", text="ジャンル",
                     range_x=[-1, 1], range_y=[0, 1])
    fig.update_traces(textposition="top center")
    fig.update_layout(dragmode=False, modebar_remove=["zoom", "pan", "lasso2d", "select2d"])
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 🟦 似た意見")
    sim = data.get("similar_opinion")
    if sim:
        st.markdown(f"**内容**: {sim['content']}")
        st.markdown(f"**スコア**: {sim['bias_score']}, {sim['strength_score']}")

    st.markdown("### 🟥 反対意見")
    opp = data.get("opposite_opinion")
    if opp:
        st.markdown(f"**内容**: {opp['content']}")
        st.markdown(f"**スコア**: {opp['bias_score']}, {opp['strength_score']}")

# 履歴と傾向コメント
if st.session_state.history:
    st.markdown("### 🧮 診断履歴")
    df_all = pd.DataFrame(st.session_state.history)
    fig_all = px.scatter(df_all, x="Bias", y="Strength", color="ジャンル", text="ジャンル",
                         range_x=[-1, 1], range_y=[0, 1])
    fig_all.update_traces(textposition="top center")
    fig_all.update_layout(dragmode=False, modebar_remove=["zoom", "pan", "lasso2d", "select2d"])
    st.plotly_chart(fig_all, use_container_width=True)
    st.download_button("📥 CSVダウンロード", df_all.to_csv(index=False, encoding="utf-8-sig"), file_name="bias_results.csv")

    st.markdown("### 🧭 あなたの傾向まとめ")
    summary = fetch_chatgpt(build_summary_prompt(st.session_state.history))
    if summary:
        st.success(summary)
    else:
        st.warning("傾向コメントの生成に失敗しました。もう一度お試しください。")
