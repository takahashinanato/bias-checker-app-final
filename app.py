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

# 🔧 通常診断用プロンプト
def build_prompt(text):
    return f"""
あなたはSNS投稿のバイアス分析AIです。以下の投稿文について、以下の形式で**JSONのみ**を出力してください：

- bias_score（-1.0=保守〜+1.0=リベラル）
- strength_score（0.0〜1.0）
- comment（200字以内の分析コメント）
- similar_opinion（{{"content": ..., "bias_score": ..., "strength_score": ...}})
- opposite_opinion（{{"content": ..., "bias_score": ..., "strength_score": ...}}）

【投稿文】:
{text}
"""

# 🔁 再生成用プロンプト（似た or 反対意見）
def build_regen_prompt(mode, text):
    key = f"{mode}_opinion"
    title = "似た立場の意見" if mode == "similar" else "反対意見"
    return f"""
以下の投稿に対して、{title}を1つだけ返してください。
出力形式（JSON）：
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
    st.code(raw)  # 🔍デバッグ用表示
    if raw.startswith("```"):
        raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)

# 再生成本体
def regenerate_opinion(mode):
    prompt = build_regen_prompt(mode, st.session_state.input_text)
    try:
        data = fetch_chatgpt(prompt)
        return data.get(f"{mode}_opinion", None)
    except:
        return None

# 診断実行
if run_diagnosis and user_input:
    try:
        prompt = build_prompt(user_input)
        data = fetch_chatgpt(prompt)
        st.session_state.latest_prompt = prompt
        st.session_state.latest_response = data

        st.markdown(f"### 🗨️ コメント:\n{data['comment']}")
        st.session_state.history.append({
            "Bias": data["bias_score"],
            "Strength": data["strength_score"],
            "ジャンル": genre
        })

        df_latest = pd.DataFrame([st.session_state.history[-1]])
        fig = px.scatter(df_latest, x="Bias", y="Strength", text="ジャンル",
                         range_x=[-1, 1], range_y=[0, 1])
        fig.update_traces(textposition="top center")
        st.markdown("### 📊 現在の診断結果")
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error("診断に失敗しました。形式エラーの可能性があります。")
        st.code(prompt)

# 意見表示と再生成ボタン
if st.session_state.latest_response:
    data = st.session_state.latest_response

    st.markdown("### 🟦 似た意見の例")
    sim = data.get("similar_opinion")
    if sim:
        st.markdown(f"**内容**: {sim['content']}  \n**スコア**: {sim['bias_score']}, {sim['strength_score']}")
    if st.button("🔁 別の似た意見を表示"):
        new_sim = regenerate_opinion("similar")
        if new_sim:
            st.session_state.latest_response["similar_opinion"] = new_sim
            st.rerun()
        else:
            st.warning("似た意見の再生成に失敗しました。")

    st.markdown("### 🟥 反対意見の例")
    opp = data.get("opposite_opinion")
    if opp:
        st.markdown(f"**内容**: {opp['content']}  \n**スコア**: {opp['bias_score']}, {opp['strength_score']}")
    if st.button("🔁 別の反対意見を表示"):
        new_opp = regenerate_opinion("opposite")
        if new_opp:
            st.session_state.latest_response["opposite_opinion"] = new_opp
            st.rerun()
        else:
            st.warning("反対意見の再生成に失敗しました。")

# 履歴と傾向分析
if st.session_state.history:
    st.markdown("### 🧮 診断履歴")
    df = pd.DataFrame(st.session_state.history)
    fig = px.scatter(df, x="Bias", y="Strength", color="ジャンル", text="ジャンル",
                     range_x=[-1, 1], range_y=[0, 1])
    fig.update_traces(textposition="top center")
    st.plotly_chart(fig, use_container_width=True)

    st.download_button("📥 CSVダウンロード", df.to_csv(index=False, encoding="utf-8-sig"), file_name="bias_results.csv")

    st.markdown("### 📈 あなたの傾向分析")
    avg_bias = df["Bias"].mean()
    avg_strength = df["Strength"].mean()

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
