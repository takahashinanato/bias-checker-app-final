import streamlit as st
import openai
import pandas as pd
import plotly.express as px
import os

# OpenAI APIキーをSecretsから取得
openai.api_key = os.getenv("OPENAI_API_KEY")

# アプリ設定
st.set_page_config(page_title="政治的バイアス診断アプリ", layout="centered")
st.title("🧠 政治的バイアス診断アプリ")

# 入力欄
genre = st.selectbox("ジャンルを選択してください", ["政治", "経済", "教育", "ジェンダー", "環境", "外交", "社会問題"])
text = st.text_area("SNS投稿や意見（500文字以内）を入力", max_chars=500)

# 履歴の保存
if "history" not in st.session_state:
    st.session_state.history = []

# ChatGPTへの問い合わせ関数（GPT-4o使用）
def run_diagnosis(user_text, topic):
    system_prompt = f"""
以下はSNS投稿の政治的バイアスを診断するAIです。
- bias_score（政治的傾向）: -1.0（保守）〜 +1.0（リベラル）
- strength_score（主張の強さ）: 0.0（穏健）〜 1.0（過激）
- comment: 診断結果に対する中立的な日本語コメント（200字以内）

JSON形式で以下のように返してください：

```json
{{
  "bias_score": 数値,
  "strength_score": 数値,
  "comment": "200字以内のコメント"
}}
"""
    user_prompt = f"ジャンル: {topic}\n投稿: {user_text}"

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()}
        ],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

# 診断ボタン
if st.button("診断する"):
    if not text:
        st.warning("投稿を入力してください。")
    else:
        with st.spinner("ChatGPTが診断中..."):
            try:
                raw = run_diagnosis(text, genre)
                raw_json = raw.split("```json")[-1].split("```")[0].strip()
                result = eval(raw_json)

                bias = float(result["bias_score"])
                strength = float(result["strength_score"])
                comment = result["comment"]

                # 表示
                st.markdown(f"**傾向スコア**：{bias}  **強さスコア**：{strength}")
                st.markdown(f"**コメント**：{comment}")

                # 履歴に追加
                st.session_state.history.append({
                    "content": text,
                    "genre": genre,
                    "bias_score": bias,
                    "strength_score": strength,
                    "comment": comment
                })

            except Exception as e:
                st.error("診断に失敗しました。形式エラーの可能性があります。")
                st.code(raw if 'raw' in locals() else str(e))

# 履歴・グラフ表示
if st.session_state.history:
    df = pd.DataFrame(st.session_state.history)

    st.markdown("### 📊 バイアス分布図")
    fig = px.scatter(
        df,
        x="bias_score",
        y="strength_score",
        color_discrete_sequence=["blue"],
        labels={
            "bias_score": "Political Bias Score (-1 = Conservative, +1 = Liberal)",
            "strength_score": "Strength Score (0 = Mild, 1 = Strong)"
        },
        text="genre"
    )
    fig.update_traces(marker=dict(size=12))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 🗂 診断履歴")
    st.dataframe(df[["genre", "content", "bias_score", "strength_score", "comment"]], use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("診断履歴をCSVでダウンロード", csv, file_name="diagnosis_history.csv")
