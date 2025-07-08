import streamlit as st
import openai
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
from dotenv import load_dotenv

# フォント設定（日本語化対応）
font_path = "./fonts/NotoSansCJKjp-Regular.otf"
if os.path.exists(font_path):
    fm.fontManager.addfont(font_path)
    plt.rcParams['font.family'] = 'Noto Sans CJK JP'

# 環境変数からAPIキー読み込み
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# ジャンル一覧
GENRES = ["政治", "経済", "ジェンダー", "教育", "環境", "国際", "医療", "エンタメ"]

# 初期化
if "diagnosis_history" not in st.session_state:
    st.session_state.diagnosis_history = []

st.title("🧠 政治的バイアス診断アプリ")

# UI
genre = st.selectbox("診断するテーマを選んでください", GENRES)
content = st.text_area("SNS投稿や自身の意見などを入力（200字以内）", max_chars=200)

if st.button("診断する") and content:
    with st.spinner("診断中..."):
        try:
            # ChatGPTで診断
            system_prompt = f"""
            あなたはSNS投稿の政治的バイアスや主張の強さを分析するAIです。
            以下の形式で出力してください：
            {{
              "bias_score": 数値（-1.0〜+1.0で保守〜リベラル）, 
              "strength_score": 数値（0.0〜1.0で穏健〜過激）, 
              "comment": "診断の根拠を簡潔に説明したコメント"
            }}
            """
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"投稿ジャンル: {genre}\n投稿内容: {content}"}
                ]
            )
            raw = response.choices[0].message.content.strip()
            result = eval(raw) if raw.startswith("{") else {}

            # スコア抽出
            bias = float(result["bias_score"])
            strength = float(result["strength_score"])
            comment = result["comment"]

            # 表示
            st.markdown(f"**傾向スコア**: {bias}　**強さスコア**: {strength}")
            st.markdown(f"**コメント:** {comment}")

            # グラフ描画
            fig, ax = plt.subplots()
            ax.set_title("バイアス診断マップ")
            ax.set_xlabel("Political Bias Score (-1.0 = 保守, +1.0 = リベラル)")
            ax.set_ylabel("Strength Score (0.0 = 穏健, 1.0 = 過激)")
            ax.grid(True)
            ax.set_xlim(-1, 1)
            ax.set_ylim(0, 1)

            # 履歴プロット
            for h in st.session_state.diagnosis_history:
                ax.plot(h["bias_score"], h["strength_score"], 'o', color='gray', alpha=0.5)

            # 現在の点
            ax.plot(bias, strength, 'o', color='blue')
            st.pyplot(fig)

            # ChatGPTで似た意見と反対意見も生成
            def generate_opinion(kind):
                opinion_prompt = f"""
                以下の投稿に対して、{kind}な意見を短く1文で出力してください。
                投稿: {content}
                """
                r = openai.ChatCompletion.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": opinion_prompt}]
                )
                return r.choices[0].message.content.strip()

            similar = generate_opinion("似た")
            opposite = generate_opinion("反対")

            st.markdown("### 🟦 似た意見の例")
            st.markdown(f"**{similar}**")
            st.markdown("### 🟥 反対意見の例")
            st.markdown(f"**{opposite}**")

            # 履歴に追加
            st.session_state.diagnosis_history.append({
                "content": content,
                "genre": genre,
                "bias_score": bias,
                "strength_score": strength,
                "comment": comment
            })

        except Exception as e:
            st.error(f"診断結果の解析に失敗しました: {e}")
            st.code(raw)

# 履歴表示とCSV保存
if st.session_state.diagnosis_history:
    df = pd.DataFrame(st.session_state.diagnosis_history)
    st.markdown("### 🗂️ 診断履歴")
    st.dataframe(df)
    csv = df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button("診断履歴をCSVでダウンロード", csv, "diagnosis_history.csv", "text/csv")
