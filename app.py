import streamlit as st
import pandas as pd
import plotly.express as px
import openai
import os
from dotenv import load_dotenv

# .envファイルからAPIキーを読み込み
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="政治的バイアス診断アプリ", layout="centered")

st.title("🧠 政治的バイアス診断アプリ")

# ジャンル選択
genre = st.selectbox("診断するテーマを選んでください", ["政治", "経済", "教育", "ジェンダー", "環境", "外交"])

# 入力欄（最大500字）
content = st.text_area("SNS投稿や自身の意見などを入力（500字以内）", max_chars=500)

if "diagnosis_history" not in st.session_state:
    st.session_state.diagnosis_history = []

# 残り回数の表示
remaining = 5 - len(st.session_state.diagnosis_history)
st.caption(f"🧪 診断可能回数の残り：{remaining} 回（最大5回まで）")

# 診断ボタン
if st.button("診断する") and content.strip():
    if remaining <= 0:
        st.warning("診断回数の上限に達しました。")
    else:
        with st.spinner("診断中..."):
            try:
                system_prompt = (
                    "以下の投稿文について、政治的傾向と主張の強さを以下の形式でJSONで出力してください：\n\n"
                    "```json\n"
                    "{\n"
                    "  \"bias_score\": 数値（-1.0〜1.0）,\n"
                    "  \"strength_score\": 数値（0.0〜1.0）,\n"
                    "  \"comment\": \"コメント（200字以内、日本語）\"\n"
                    "}\n"
                    "```\n\n"
                    "bias_scoreは保守派=-1.0、リベラル派=+1.0を基準に評価。\n"
                    "strength_scoreは言葉の強さや過激さに基づいて0.0〜1.0で評価してください。"
                )

                response = openai.ChatCompletion.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": content}
                    ],
                    temperature=0.7
                )

                raw = response.choices[0].message.content.strip()
                json_str = raw.split("```json")[-1].split("```")[0].strip()
                result = eval(json_str)

                bias_score = float(result["bias_score"])
                strength_score = float(result["strength_score"])
                comment = result["comment"]

                # 表示
                st.markdown(f"**傾向スコア**: {bias_score:.1f}　**強さスコア**: {strength_score:.1f}")
                st.markdown(f"**コメント**: {comment}")

                # データ保存
                st.session_state.diagnosis_history.append({
                    "content": content,
                    "genre": genre,
                    "bias_score": bias_score,
                    "strength_score": strength_score,
                    "comment": comment
                })

                # 類似・反対の例を生成
                example_prompt = (
                    f"以下の投稿文に対して、政治的立場と主張の強さが似た意見・反対の意見をそれぞれ1つずつ挙げてください。\n\n"
                    f"投稿文：{content}\n\n"
                    f"出力形式：\n"
                    f"```json\n"
                    f"{{\n"
                    f"  \"similar_opinion\": \"〜〜〜\",\n"
                    f"  \"opposite_opinion\": \"〜〜〜\"\n"
                    f"}}\n"
                    f"```"
                )

                ex_response = openai.ChatCompletion.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": example_prompt}
                    ],
                    temperature=0.7
                )
                ex_raw = ex_response.choices[0].message.content.strip()
                ex_json = ex_raw.split("```json")[-1].split("```")[0].strip()
                ex_result = eval(ex_json)

                st.markdown("### 🟦 似た意見の例")
                st.markdown(f"**内容**: {ex_result['similar_opinion']}")

                st.markdown("### 🟥 反対意見の例")
                st.markdown(f"**内容**: {ex_result['opposite_opinion']}")

            except Exception as e:
                st.error("診断に失敗しました。形式エラーの可能性があります。")
                st.code(str(e))

# グラフの表示
if st.session_state.diagnosis_history:
    df = pd.DataFrame(st.session_state.diagnosis_history)

    st.markdown("### 診断履歴グラフ")
    fig = px.scatter(
        df,
        x="bias_score",
        y="strength_score",
        text="genre",
        labels={
            "bias_score": "Political Bias Score (-1.0 = Conservative, +1.0 = Liberal)",
            "strength_score": "Strength Score (0.0 = Mild, 1.0 = Strong)"
        },
        color_discrete_sequence=["blue"]
    )
    fig.update_traces(marker=dict(size=10))
    fig.update_layout(height=500)
    st.plotly_chart(fig)

    # 表形式とCSVダウンロード
    st.markdown("### 診断履歴")
    st.dataframe(df)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("診断履歴をCSVでダウンロード", csv, file_name="diagnosis_history.csv", mime="text/csv")
