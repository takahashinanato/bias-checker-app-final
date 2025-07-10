import streamlit as st
import openai
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="政治的バイアス診断アプリ", layout="centered")
openai.api_key = st.secrets["OPENAI_API_KEY"]

st.title("🧠 政治的バイアス診断アプリ")

genre = st.selectbox("ジャンルを選択してください", ["政治", "経済", "ジェンダー", "教育", "その他"])
user_input = st.text_area("SNS投稿や意見（500文字以内）を入力", max_chars=500)

if "history" not in st.session_state:
    st.session_state.history = []

if st.button("診断する") and user_input:
    with st.spinner("診断中..."):

        prompt = f"""
あなたはSNS投稿のバイアス分析AIです。以下の投稿文について、以下の形式でJSONのみを出力してください：

- bias_score（政治的傾向スコア、-1.0=保守〜+1.0=リベラル）
- strength_score（主張の強さスコア、0.0〜1.0）
- comment（200字以内で内容に即した分析コメント）
- similar_opinion（似た立場の架空意見＋スコア）
- opposite_opinion（反対意見の架空意見＋スコア）

【投稿文】:
{user_input}
"""

        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "あなたは政治的バイアスを診断する専門AIです。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        try:
            raw = response.choices[0].message.content.strip()
            import json
            data = json.loads(raw)

            # コメント表示
            st.markdown(f"### 🗨️ コメント:\n{data['comment']}")

            # グラフ描画
            st.markdown("### 📊 バイアス分布図")
            df = pd.DataFrame([{
                "Bias": data["bias_score"],
                "Strength": data["strength_score"],
                "ジャンル": genre
            }])
            fig = px.scatter(
                df,
                x="Bias",
                y="Strength",
                text="ジャンル",
                range_x=[-1, 1],
                range_y=[0, 1],
                labels={
                    "Bias": "Political Bias Score (-1 = Conservative, +1 = Liberal)",
                    "Strength": "Strength Score (0 = Mild, 1 = Strong)"
                }
            )
            fig.update_traces(textposition="top center")
            st.plotly_chart(fig, use_container_width=True)

            # 似た意見・反対意見
            st.markdown("### 🟦 似た意見の例")
            st.markdown(f"**内容**: {data['similar_opinion']['content']}  \n**スコア**: {data['similar_opinion']['bias_score']}, {data['similar_opinion']['strength_score']}")

            st.markdown("### 🟥 反対意見の例")
            st.markdown(f"**内容**: {data['opposite_opinion']['content']}  \n**スコア**: {data['opposite_opinion']['bias_score']}, {data['opposite_opinion']['strength_score']}")

        except Exception as e:
            st.error("診断に失敗しました。形式エラーの可能性があります。")
            st.code(raw)
