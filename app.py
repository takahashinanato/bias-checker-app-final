import streamlit as st
import openai
import pandas as pd
import plotly.express as px
import json

st.set_page_config(page_title="政治バイアス検出ツール", layout="centered")
openai.api_key = st.secrets["OPENAI_API_KEY"]

st.title("🧠 政治バイアス検出ツール")

# セッション初期化
if "input_text" not in st.session_state:
    st.session_state.input_text = ""
if "latest_prompt" not in st.session_state:
    st.session_state.latest_prompt = ""
if "latest_response" not in st.session_state:
    st.session_state.latest_response = None
if "history" not in st.session_state:
    st.session_state.history = []

# 入力UI
genre = st.selectbox("ジャンルを選択してください", ["政治", "経済", "ジェンダー", "教育", "その他"])
user_input = st.text_area("SNS投稿や意見（500文字以内）を入力", value=st.session_state.input_text, max_chars=500)
st.session_state.input_text = user_input

col1, col2 = st.columns([1, 1])
with col1:
    run_diagnosis = st.button("診断する")
with col2:
    if st.button("🧹 入力をクリア"):
        st.session_state.input_text = ""
        st.rerun()

# プロンプト生成
def build_prompt(text):
    return f"""
あなたはSNS投稿のバイアス分析AIです。以下の投稿文について、以下の形式で**JSONのみ**を出力してください：

- bias_score（-1.0=保守〜+1.0=リベラル）
- strength_score（0.0〜1.0）
- comment（200字以内の中立的な分析コメント）
- similar_opinion（{{"content": ..., "bias_score": ..., "strength_score": ...}})
- opposite_opinion（{{"content": ..., "bias_score": ..., "strength_score": ...}}）

【投稿文】:
{text}
"""

# 再生成専用プロンプト
def build_regen_prompt(mode, text):
    key = f"{mode}_opinion"
    title = "似た立場の意見" if mode == "similar" else "反対意見"
    return f"""
以下の投稿に対して、{title}を1つだけJSON形式で返してください。
形式：
{{"{key}": {{"content": "...", "bias_score": 数値, "strength_score": 数値}}}}

投稿内容:
{text}
"""

# GPT呼び出し
def fetch_chatgpt(prompt):
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "あなたは政治的バイアス診断AIです。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)

# 再生成関数（即時反映あり）
def regenerate_opinion(mode):
    prompt = build_regen_prompt(mode, st.session_state.input_text)
    try:
        result = fetch_chatgpt(prompt)
        if f"{mode}_opinion" in result:
            st.session_state.latest_response[f"{mode}_opinion"] = result[f"{mode}_opinion"]
            st.experimental_rerun()
    except:
        st.warning("再生成に失敗しました。")

# 診断実行
if run_diagnosis and user_input:
    try:
        prompt = build_prompt(user_input)
        result = fetch_chatgpt(prompt)
        st.session_state.latest_prompt = prompt
        st.session_state.latest_response = result

        st.session_state.history.append({
            "Bias": result["bias_score"],
            "Strength": result["strength_score"],
            "ジャンル": genre
        })
    except:
        st.error("診断に失敗しました。形式エラーの可能性があります。")

# 表示セクション
if st.session_state.latest_response:
    data = st.session_state.latest_response

    st.markdown("### 💬 コメント")
    st.markdown(data["comment"])

    st.markdown("### 📊 現在の診断結果")
    df_latest = pd.DataFrame([{
        "Bias": data["bias_score"],
        "Strength": data["strength_score"],
        "ジャンル": genre
    }])
    fig = px.scatter(df_latest, x="Bias", y="Strength", text="ジャンル",
                     range_x=[-1, 1], range_y=[0, 1])
    fig.update_traces(textposition="top center")
    st.plotly_chart(fig, use_container_width=True)

    # 似た意見
    st.markdown("### 🟦 似た意見の例")
    sim = data.get("similar_opinion")
    if sim:
        st.markdown(f"**内容**: {sim['content']}")
        st.markdown(f"**スコア**: {sim['bias_score']}, {sim['strength_score']}")
    if st.button("🔁 別の似た意見を表示"):
        regenerate_opinion("similar")

    # 反対意見
    st.markdown("### 🟥 反対意見の例")
    opp = data.get("opposite_opinion")
    if opp:
        st.markdown(f"**内容**: {opp['content']}")
        st.markdown(f"**スコア**: {opp['bias_score']}, {opp['strength_score']}")
    if st.button("🔁 別の反対意見を表示"):
        regenerate_opinion("opposite")

# 診断履歴・傾向
if st.session_state.history:
    st.markdown("### 🧮 診断履歴")
    df_all = pd.DataFrame(st.session_state.history)
    fig_all = px.scatter(df_all, x="Bias", y="Strength", color="ジャンル", text="ジャンル",
                         range_x=[-1, 1], range_y=[0, 1])
    fig_all.update_traces(textposition="top center")
    st.plotly_chart(fig_all, use_container_width=True)

    st.download_button("📥 CSVダウンロード", df_all.to_csv(index=False, encoding="utf-8-sig"), file_name="bias_results.csv")

    st.markdown("### 📈 あなたの傾向分析")
    avg_bias = df_all["Bias"].mean()
    avg_strength = df_all["Strength"].mean()

    st.markdown(f"- 平均バイアススコア：**{avg_bias:.2f}** → {'保守寄り' if avg_bias < -0.2 else 'リベラル寄り' if avg_bias > 0.2 else '中道'}")
    st.markdown(f"- 平均強さスコア：**{avg_strength:.2f}** → {'穏健' if avg_strength < 0.4 else 'やや強め' if avg_strength < 0.7 else '過激'}")

    feedback = ""
    if avg_bias < -0.3:
        feedback += "あなたは全体的に保守寄りの意見が多く見られます。"
    elif avg_bias > 0.3:
        feedback += "あなたはリベラル寄りの意見を多く表明している傾向があります。"
    else:
        feedback += "あなたの意見は比較的中道に位置しており、バランスが取れています。"

    if avg_strength > 0.7:
        feedback += " また、表現には強い主張が多く、過激さが感じられる場合があります。"
    elif avg_strength < 0.4:
        feedback += " また、主張は穏健で落ち着いたトーンが多い傾向です。"
    else:
        feedback += " また、主張の強さは中程度で比較的冷静な発信がされています。"

    st.info(feedback)
