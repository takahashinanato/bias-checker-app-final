import streamlit as st
import openai
import pandas as pd
import matplotlib.pyplot as plt
import json
import math

client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

if "diagnosis_history" not in st.session_state:
    st.session_state.diagnosis_history = []

sample_posts = [
    {"content": "憲法改正は必要だと思う", "bias_score": -0.6, "strength_score": 0.7},
    {"content": "夫婦別姓制度は導入されるべきだ", "bias_score": 0.5, "strength_score": 0.6},
    {"content": "防衛費はもっと増やすべきだ", "bias_score": -0.8, "strength_score": 0.9},
    {"content": "同性婚は法的に認めるべき", "bias_score": 0.8, "strength_score": 0.7}
]

st.title("🧠 政治的バイアス診断アプリ")
genre = st.selectbox("診断するテーマを選んでください", ["政治", "経済", "ジェンダー", "その他"])
user_input = st.text_area("SNS投稿や自身の意見などを入力（200字以内）", max_chars=200)

if st.button("診断する") and user_input:
    prompt = f"""
以下のSNS投稿について、JSON形式で診断してください。
出力形式:
{{
  "bias_score": -1.0から1.0の数値（-1.0=保守、+1.0=リベラル）,
  "strength_score": 0.0から1.0の数値,
  "comment": "中立的かつ根拠を示した200字程度のコメント"
}}

投稿内容: {user_input}
"""

    with st.spinner("診断中..."):
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.choices[0].message.content

    try:
        data = json.loads(raw)
        bias_score = data["bias_score"]
        strength_score = data["strength_score"]
        comment = data["comment"]

        st.markdown(f"**傾向スコア:** {bias_score} **強さスコア:** {strength_score}")
        st.markdown(f"**コメント:** {comment}")

        st.session_state.diagnosis_history.append({
            "content": user_input,
            "genre": genre,
            "bias_score": bias_score,
            "strength_score": strength_score,
            "comment": comment
        })

        fig, ax = plt.subplots()
        for sample in sample_posts:
            ax.scatter(sample["bias_score"], sample["strength_score"], color="gray", alpha=0.6)
        ax.scatter(bias_score, strength_score, color="blue", s=100)
        ax.set_xlim(-1.0, 1.0)
        ax.set_ylim(0.0, 1.0)
        ax.set_xlabel("Political Bias Score (-1.0 = Conservative, +1.0 = Liberal)")
        ax.set_ylabel("Strength Score (0.0 = Mild, 1.0 = Strong)")
        ax.grid(True)
        st.pyplot(fig)

        def dist(a, b):
            return math.sqrt((a["bias_score"] - b["bias_score"])**2 + (a["strength_score"] - b["strength_score"])**2)

        closest = min(sample_posts, key=lambda s: dist(s, data))
        opposite = max(sample_posts, key=lambda s: dist(s, data))

        st.markdown("### 似た意見の例")
        st.markdown(f"**内容:** {closest['content']} **スコア:** {closest['bias_score']}, {closest['strength_score']}")

        st.markdown("### 反対意見の例")
        st.markdown(f"**内容:** {opposite['content']} **スコア:** {opposite['bias_score']}, {opposite['strength_score']}")

    except Exception as e:
        st.error(f"診断結果の解析に失敗しました: {e}")
        st.code(raw)

if st.session_state.diagnosis_history:
    df = pd.DataFrame(st.session_state.diagnosis_history)
    st.markdown("### 診断履歴")
    st.dataframe(df)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("診断履歴をCSVでダウンロード", csv, "diagnosis_history.csv", "text/csv")
