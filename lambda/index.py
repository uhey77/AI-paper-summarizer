import os

from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

INDEX_PROMPT = """
    あなたは優秀な論文要約AIです。あなたはarxivの論文要約を読み、以下の出力形式に従って内容を端的にまとめて出力します。

    # 目的
    Notion のページの見出しにそのまま使用します。過度に長い出力は絶対に避けてください。必ず1文で出力すること。

    # 注意
    - 出力は日本語で行うこと。その他の言語は一切認めません。
    - 必ず60文字以内で出力すること。
    - 句読点など、余計な文字は出力しないこと。
    - 必ず１文で出力すること。
    - 「〇〇な〇〇」という形式で出力すること

    # 思考手順
    1. 【背景】と【目的】の部分を読んで概要をつかみます。
    2. その内容を30文字以内で要約します。
    3. 体言止めになっているか、句読点が入っていないかを確認します。

    # 出力例
    以下に3つの出力例を示します。このくらいの分量になるように文字数の規定は必ず守ってください。
    - スマートフォンで音声を別の声にリアルタイム変換できる高速モデル「LLVC」
    - 3.2兆以上のトークンで学習された、130億のパラメータを持つオープン大規模言語モデル「Skywork」
    - OpenAIの文字起こしAI「Whisper」を軽量かつ高速にするモデル「Distil-Whisper」
    """


def index(abstract):
    messages = [
        {"role": "system", "content": INDEX_PROMPT},
        {"role": "user", "content": abstract},
    ]

    res = client.chat.completions.create(model="gpt-4o", messages=messages)

    return res.choices[0].message.content
