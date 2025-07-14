import streamlit as st
import openai
import pandas as pd
import plotly.express as px
import json

st.set_page_config(page_title="政治バイアス検出ツール", layout="centered")
openai.api_key = st.secrets["OPENAI_API_KEY"]

st.title("🧠 政治バイアス検出ツール")

# ✅ セッション初期化
if "latest_prompt" not in st.session_state:
    st.session_state.latest_prompt = None
if "latest_response" not in st.session_state:
    st.session_state.latest_response = None
if "input_text" not in st.session_state:
    st.session_state.input_text = ""
if "history" not in st.session_state:
    st.session_state.history = []

# 🔽 ジャンル選択
genre = st.selectbox("ジャンルを選択してください", [
    "政治・政党", "防衛・外交", "福祉・格差", "経済政策", "教育と道徳",
    "ジェンダーと多様性", "表現・言論の自由", "家族観・伝統文化", "社会秩序・治安", "その他"
])

# 入力欄
user_input = st.text_area("SNS投稿や意見（500文字以内）を入力", value=st.session_state.input_text, max_chars=500)
st.session_state.input_text = user_input

# ボタン群
col1, col2 = st.columns([1, 1])
with col1:
    run_diagnosis = st.button("診断する")
with col2:
    if st.button("🧹 入力をクリア"):
        st.session_state.input_text = ""
        st.session_state.latest_response = None
        st.experimental_rerun()

# プロンプト生成
def build_prompt(text):
    return f'''
あなたはSNS投稿のバイアス分析AIです。以下の投稿文について、以下の形式でJSONのみを出力してください：

- bias_score（-1.0=保守〜+1.0=リベラル）
- strength_score（0.0〜1.0）
- comment（投稿者の立場や価値観・思想の傾向を、投稿内容に即して簡潔に200字以内で分析）
- similar_opinion（{{"content": "...", "bias_score": 数値, "strength_score": 数値}})
- opposite_opinion（{{"content": "...", "bias_score": 数値, "strength_score": 数値}}）

【投稿文】:
{text}
'''

def build_regen_prompt(mode, text):
    key = f"{mode}_opinion"
    return f'''
次の投稿に対して、{"似た立場の意見" if mode=="similar" else "反対意見"}を1つだけJSON形式で返してください。
形式：
{{"{key}": {{"content": "...", "bias_score": 数値, "strength_score": 数値}}}}

投稿内容:
{text}
'''

def fetch_chatgpt(prompt):
    try:
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
    except:
        return None

# 診断処理
if run_diagnosis and user_input:
    with st.spinner("診断中..."):
        result = fetch_chatgpt(build_prompt(user_input))
        if result:
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

# 表示ブロック
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
    fig.update_layout(dragmode=False, modebar_remove=["zoom", "pan", "lasso2d", "select2d"])
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 🟦 似た意見の例")
    sim = data.get("similar_opinion")
    if sim:
        st.markdown(f"**内容**: {sim['content']}")
        st.markdown(f"**スコア**: {sim['bias_score']}, {sim['strength_score']}")
    if st.button("🔁 別の似た意見を表示"):
        new_sim = fetch_chatgpt(build_regen_prompt("similar", st.session_state.latest_prompt))
        if new_sim and "similar_opinion" in new_sim:
            st.session_state.latest_response["similar_opinion"] = new_sim["similar_opinion"]
        else:
            st.info("再生成は完了しましたが、もう一度押すと表示に反映される場合があります。")

    st.markdown("### 🟥 反対意見の例")
    opp = data.get("opposite_opinion")
    if opp:
        st.markdown(f"**内容**: {opp['content']}")
        st.markdown(f"**スコア**: {opp['bias_score']}, {opp['strength_score']}")
    if st.button("🔁 別の反対意見を表示"):
        new_opp = fetch_chatgpt(build_regen_prompt("opposite", st.session_state.latest_prompt))
        if new_opp and "opposite_opinion" in new_opp:
            st.session_state.latest_response["opposite_opinion"] = new_opp["opposite_opinion"]
        else:
            st.info("再生成は完了しましたが、もう一度押すと表示に反映される場合があります。")

# 履歴と総括コメント
if st.session_state.history:
    st.markdown("### 🧮 診断履歴")
    df_all = pd.DataFrame(st.session_state.history)
    fig_all = px.scatter(df_all, x="Bias", y="Strength", color="ジャンル", text="ジャンル",
                         range_x=[-1, 1], range_y=[0, 1])
    fig_all.update_traces(textposition="top center")
    fig_all.update_layout(dragmode=False, modebar_remove=["zoom", "pan", "lasso2d", "select2d"])
    st.plotly_chart(fig_all, use_container_width=True)

    st.download_button("📥 CSVダウンロード", df_all.to_csv(index=False, encoding="utf-8-sig"), file_name="bias_results.csv")

    st.markdown("### 📊 過去のコメント一覧")
    for i, row in df_all.iterrows():
        st.markdown(f"- **{row['ジャンル']}** → {row['コメント']}")

    st.markdown("### 🧭 あなたの傾向まとめ")

    avg_bias = df_all["Bias"].mean()
    avg_strength = df_all["Strength"].mean()

    if avg_bias < -0.4:
        bias_comment = "あなたの投稿は全体的に保守的な立場が明確に表れています。"
    elif avg_bias < -0.2:
        bias_comment = "あなたはやや保守寄りの傾向を持っているようです。"
    elif avg_bias > 0.4:
        bias_comment = "全体としてリベラル寄りな意見が多く、自由や多様性を重視する傾向が見られます。"
    elif avg_bias > 0.2:
        bias_comment = "ややリベラル寄りの発信が多く見受けられます。"
    else:
        bias_comment = "保守・リベラルの両方の視点をバランスよく取り入れた投稿が目立ちます。"

    if avg_strength < 0.3:
        strength_comment = "また、投稿は控えめで落ち着いた語り口が多いようです。"
    elif avg_strength > 0.7:
        strength_comment = "また、主張が非常に強く、明確な立場表明が特徴です。"
    else:
        strength_comment = "また、主張の強さも程よく、説得力を意識した発信が多いです。"

    st.success(f"{bias_comment} {strength_comment}")
