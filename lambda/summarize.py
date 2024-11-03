import os

from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

SUMMARIZE_PROMPT = """
    あなたは優秀な論文要約AIです。あなたはarxivの論文要約を読み、以下の出力形式に従って内容をまとめて出力します。
    # 注意
    - 出力は日本語で行うこと。その他の言語は一切認めません。
    - それぞれの項目について、箇条書きで出力すること。1つの項目につき、最大3つの文を出力すること。
    - 敬語は不要です。右の例のような形式にすること。ex) 〜である、〜だ
    # 出力形式
    【背景】
    - 背景1
    - 背景2
    【目的】
    - 目的1
    - 目的2
    【手法】
    - 手法1
    - 手法2
    【実験方法】
    - 実験方法1
    - 実験方法2
    【実験結果】
    - 実験結果1
    - 実験結果2
    【考察】
    - 考察1
    - 考察2
    """


def summarize(abstract):
    messages = [
        {"role": "system", "content": SUMMARIZE_PROMPT},
        {"role": "user", "content": abstract},
    ]

    res = client.chat.completions.create(model="gpt-4o", messages=messages)

    return res.choices[0].message.content
