import streamlit as st
import openai
import pandas as pd
import plotly.express as px
import json

st.set_page_config(page_title="政治的バイアス診断アプリ", layout="centered")
openai.api_key = st.secrets["OPENAI_API_KEY"]

st.title("🧠 政治的バイアス診断アプリ")

genre = st.selectbox("ジャンルを選択してください", ["政治", "経済", "ジェンダー", "教育", "その他"])
user_input = st.text_area("SNS投稿や意見（500文字以内）を入力", max_chars=500)

# 履歴保持
if "history" not in st.session_state:
    st.session_state.history = []

if st.button("診断する") and user_input:
    with st.spinner("診断中..."):

        prompt = f"""
あなたはSNS投稿のバイアス分析AIです。以下の投稿文について、以下の形式でJSONのみを出力してください：

- bias_score（-1.0=保守〜+1.0=リベラル）float型
- strength_score（0.0〜1.0）float型
- comment（200字以内の中立的な分析コメント）
- similar_opinion（似た立場の架空意見＋bias_scoreとstrength_score）
- opposite_opinion（反対立場の架空意見＋bias_scoreとstrength_score）

【投稿文】:
{user_input}
"""

        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "あなたは政治的バイアスを診断する専門AIです。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )

            raw = response.choices[0].message.content.strip()
            data = json.loads(raw)

            # コメント
            st.markdown(f"### 🗨️ コメント:\n{data['comment']}")

            # 現在の診断結果を履歴に追加
            st.session_state.history.append({
                "Bias": data["bias_score"],
                "Strength": data["strength_score"],
                "ジャンル": genre
            })

            # 最新の診断結果のみを可視化
            st.markdown("### 📊 現在の診断結果")
            df_latest = pd.DataFrame([st.session_state.history[-1]])
            fig_latest = px.scatter(
                df_latest,
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
            fig_latest.update_traces(textposition="top center")
            st.plotly_chart(fig_latest, use_container_width=True)

            # 似た意見・反対意見
            st.markdown("### 🟦 似た意見の例")
            sim = data["similar_opinion"]
            st.markdown(f"**内容**: {sim['content']}  \n**スコア**: {sim['bias_score']:.2f}, {sim['strength_score']:.2f}")

            st.markdown("### 🟥 反対意見の例")
            opp = data["opposite_opinion"]
            st.markdown(f"**内容**: {opp['content']}  \n**スコア**: {opp['bias_score']:.2f}, {opp['strength_score']:.2f}")

        except Exception as e:
            st.error("診断に失敗しました。形式エラーの可能性があります。")
            st.code(raw)

# 診断履歴の表示（あれば）
if st.session_state.history:
    st.markdown("### 🧮 過去の診断履歴（セッション内）")
    df_all = pd.DataFrame(st.session_state.history)
    fig_all = px.scatter(
        df_all,
        x="Bias",
        y="Strength",
        color="ジャンル",
        text="ジャンル",
        range_x=[-1, 1],
        range_y=[0, 1],
        labels={
            "Bias": "Political Bias Score",
            "Strength": "Strength Score"
        }
    )
    fig_all.update_traces(textposition="top center")
    st.plotly_chart(fig_all, use_container_width=True)

    # CSVダウンロードボタン
    csv = df_all.to_csv(index=False, encoding="utf-8-sig")
    st.download_button("📥 CSVダウンロード", csv, file_name="bias_results.csv")
