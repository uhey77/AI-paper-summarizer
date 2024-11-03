import os

from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

TAGGING_PROMPT = """
    あなたは優秀な論文分類AIです。論文の内容からその技術の分野を判定します。

    # 判定ラベル
    必ず以下のラベルの中から選ぶようにしてください。適切であると判断できるラベルは全て選んでください。
    ["Transfer Learning", "Representation Learning", "Self Supervised Learning", "Generative Model", "Audio", "Theory", "LLM", "Agent", "Survey", "Robotics", "NLP", "CV", "World Model", "Foundation Model", "Reinforcement Learning", "Brain-Inspired Intelligence"]

    # 出力形式
    出力は必ず以下のようなJSON形式で出力してください。
    {
        "label": ["Generative Model", "Survey"]
    }
    """


def tagging(abstract):
    messages = [
        {"role": "system", "content": TAGGING_PROMPT},
        {"role": "user", "content": abstract},
    ]

    res = client.chat.completions.create(
        model="gpt-4o", messages=messages, response_format={"type": "json_object"}
    )

    return res.choices[0].message.content
