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
st.set_page_config(page_title="政治的バイアス診断アプリ", layout="centered")
st.title("🧠 政治的バイアス診断アプリ")

# ジャンル一覧
genres = ["政治", "経済", "ジェンダー", "教育", "環境", "国際", "医療", "エンタメ"]

# 入力欄
genre = st.selectbox("診断するテーマを選んでください", genres)
user_input = st.text_area("SNS投稿や自身の意見などを入力（500文字以内）", max_chars=500, height=150)

# 履歴の初期化
if "diagnosis_history" not in st.session_state:
    st.session_state.diagnosis_history = []

# 診断実行
if st.button("診断する") and user_input:
    with st.spinner("ChatGPTによる診断中..."):
        try:
            prompt = f"""
以下の投稿について、次の5項目をJSON形式で出力してください：
1. "bias_score": -1.0〜+1.0（保守〜リベラル）
2. "strength_score": 0.0〜1.0（表現の強さ）
3. "comment": 中立的で簡潔な解説（200字以内）
4. "similar_opinion": 内容に似た意見（1文）
5. "opposite_opinion": 反対の立場の意見（1文）

投稿ジャンル: {genre}
投稿内容: {user_input}
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
            st.markdown(f"### 📊 診断結果")
            st.markdown(f"**傾向スコア:** {bias}  **主張の強さ:** {strength}")
            st.markdown(f"**コメント:** {comment}")

            st.markdown("---")
            st.markdown("### 🟦 似た意見（ChatGPTによる自動生成）")
            st.info(similar)
            st.markdown("### 🟥 反対意見（ChatGPTによる自動生成）")
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
                "type": "ユーザー投稿"
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
                color_discrete_map={"ユーザー投稿": "blue"}
            )
            fig.update_traces(marker=dict(size=12))
            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error("診断に失敗しました。形式エラーの可能性があります。")

# 履歴の表示とCSV保存
if st.session_state.diagnosis_history:
    df = pd.DataFrame(st.session_state.diagnosis_history)
    st.markdown("### 🗂️ 診断履歴")
    st.dataframe(df)
    csv = df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button("診断履歴をCSVでダウンロード", csv, file_name="diagnosis_history.csv", mime="text/csv")
