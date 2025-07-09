import streamlit as st
import openai
import pandas as pd
import plotly.express as px
import os
import json
from dotenv import load_dotenv

# APIキーの読み込み
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# 初期設定
st.set_page_config(page_title="Political Bias Checker", layout="centered")
st.title("🧠 Political Bias Diagnosis App")

# ジャンル一覧
genres = ["Politics", "Economy", "Gender", "Education", "Environment", "International", "Healthcare", "Entertainment"]

# 入力欄
genre = st.selectbox("Choose a topic for diagnosis", genres)
user_input = st.text_area("Enter your opinion (up to 500 characters)", max_chars=500, height=150)

# 履歴の初期化
if "diagnosis_history" not in st.session_state:
    st.session_state.diagnosis_history = []

# 診断実行
if st.button("Run Diagnosis") and user_input:
    with st.spinner("Analyzing with GPT..."):
        try:
            prompt = f"""
You are a political bias diagnosis assistant.
Given the following post, return a JSON with the following keys:
- bias_score: from -1.0 (Conservative) to +1.0 (Liberal)
- strength_score: from 0.0 (Mild) to 1.0 (Strong)
- comment: short and neutral explanation in Japanese
- similar_opinion: a similar opinion in one sentence
- opposite_opinion: an opposite opinion in one sentence

Post: {user_input}
"""

            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            raw = response.choices[0].message.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            result = json.loads(raw)

            bias = result["bias_score"]
            strength = result["strength_score"]
            comment = result["comment"]
            similar = result["similar_opinion"]
            opposite = result["opposite_opinion"]

            # 表示
            st.markdown(f"### 📊 Diagnosis Result")
            st.markdown(f"**Bias Score:** {bias}  **Strength Score:** {strength}")
            st.markdown(f"**Comment:** {comment}")

            st.markdown("---")
            st.markdown("### 🟦 Similar Opinion")
            st.info(similar)
            st.markdown("### 🟥 Opposite Opinion")
            st.error(opposite)

            # 履歴に追加
            st.session_state.diagnosis_history.append({
                "content": user_input,
                "genre": genre,
                "bias_score": bias,
                "strength_score": strength,
                "comment": comment,
                "similar": similar,
                "opposite": opposite,
                "type": "User"
            })

            # プロット用データ
            df = pd.DataFrame(st.session_state.diagnosis_history)
            fig = px.scatter(
                df,
                x="bias_score",
                y="strength_score",
                color="type",
                hover_data=["content"],
                range_x=[-1, 1],
                range_y=[0, 1],
                labels={
                    "bias_score": "Political Bias Score (-1 = Conservative, +1 = Liberal)",
                    "strength_score": "Strength Score (0 = Mild, 1 = Strong)"
                },
                color_discrete_map={"User": "blue"}
            )
            fig.update_traces(marker=dict(size=12))
            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error("Failed to parse the response.")
            st.code(raw)

# 履歴の表示とCSV保存
if st.session_state.diagnosis_history:
    df = pd.DataFrame(st.session_state.diagnosis_history)
    st.markdown("### 🗂️ Diagnosis History")
    st.dataframe(df)
    csv = df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button("Download CSV", csv, file_name="diagnosis_history.csv", mime="text/csv")
