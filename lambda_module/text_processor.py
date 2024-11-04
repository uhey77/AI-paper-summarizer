import json
import os
from abc import abstractmethod
from typing import Any

from openai import OpenAI


class OpenAIGPT:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    def dict2json(self, python_dict: dict[str, Any]) -> str:
        json_string = json.dumps(python_dict, indent=2, ensure_ascii=False)
        return json_string

    def json2dict(
        self, json_string: str, error_key: str | None = "error"
    ) -> dict[str, Any]:
        try:
            python_dict = json.loads(
                self._extract_string(json_string, start_string="{", end_string="}"),
                strict=False,
            )
        except ValueError:
            if error_key is None:
                return json_string
            python_dict = {error_key: json_string}
        if isinstance(python_dict, dict):
            return python_dict
        return {error_key: python_dict}

    def _extract_string(
        self, text: str, start_string: str | None = None, end_string: str | None = None
    ) -> str:
        # 最初の文字
        if start_string is not None and start_string in text:
            idx_head = text.index(start_string)
            text = text[idx_head:]
        # 最後の文字
        if end_string is not None and end_string in text:
            idx_tail = len(text) - text[::-1].index(end_string[::-1])
            text = text[:idx_tail]
        return text

    @abstractmethod
    def preprocess(self, text: str) -> list[dict]:
        pass

    def generate_completion(self, text: str, **kwargs) -> str:
        messages = self.preprocess(text)
        response = self.client.chat.completions.create(messages=messages, **kwargs)
        return self.postprocess(response.choices[0].message.content)

    @abstractmethod
    def postprocess(self, text: str):
        pass


class TitleExtractor(OpenAIGPT):
    def preprocess(self, text):
        output_format = {"title": "(string) Title of the content"}
        system_prompt = (
            "you are an assistant that helps summarize research papers. \n"
            "please **extract** the following research paper title.\n"
            "prease follow the format:\n"
            f"{self.dict2json(output_format)}"
        )
        return [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": "please extract the title from the following text:\n" + text,
            },
        ]

    def postprocess(self, text):
        output_dict = self.json2dict(text)
        return output_dict.get("title", "No Title")


class ContentSummarizer(OpenAIGPT):
    def preprocess(self, text):
        output_format = {
            "background": ["(string) Background 1", "(string) Background 2"],
            "purpose": ["(string) Purpose 1", "(string) Purpose 2"],
            "method": ["(string) Method 1", "(string) Method 2"],
            "experiment": ["(string) Experiment 1", "(string) Experiment 2"],
            "result": ["(string) Result 1", "(string) Result 2"],
            "discussion": ["(string) Discussion 1", "(string) Discussion 2"],
        }
        system_prompt = (
            "あなたは優秀な論文要約AIです。あなたはarxivの論文要約を読み、以下の出力形式に従って内容をまとめて出力します。\n"
            "# 注意\n"
            "- 出力は日本語で行うこと。その他の言語は一切認めません。ただし、専門用語と思われる単語はそのままでも良い。\n"
            "- それぞれの項目について、箇条書きで出力すること。1つの項目につき、最大3つの文を出力すること。\n"
            "- 敬語は使用しないこと。「〜である」、「〜だ」のような形式にすること。\n"
            "# 出力形式\n"
            f"{self.dict2json(output_format)}"
        )
        return [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": "please summarize the following text:\n" + text,
            },
        ]

    def postprocess(self, text):
        return self.json2dict(text)


class CategoryClassifier(OpenAIGPT):
    def preprocess(self, text):
        output_format = {
            "category": "(Enum) [Representation Learning, Self Supervised Learning, Generative Model, Audio, Theory, LLM, Agent, Survey, Robotics, NLP, CV, World Model, Foundation Model, Reinforcement Learning]"
        }
        system_prompt = (
            "あなたは優秀な論文分類AIです。論文の内容からその技術の分野を判定します。\n"
            "# 判定ラベル\n"
            "必ず以下のラベルの中から選ぶようにしてください。適切であると判断できるラベルは全て選んでください。\n"
            "# 出力形式\n"
            f"{self.dict2json(output_format)}"
        )
        return [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": "please classify the category from the following text:\n"
                + text,
            },
        ]

    def postprocess(self, text):
        output_dict = self.json2dict(text)
        return output_dict.get("category", "No Category")


class BrieflySummarizer(OpenAIGPT):
    def preprocess(self, text):
        output_format = {"summary": "(string) Short Summary of the content"}
        system_prompt = (
            "あなたは優秀な論文要約AIです。あなたはarxivの論文要約を読み、以下の出力形式に従って内容を端的にまとめて出力します。\n"
            "# 目的\n"
            "Notion のページの見出しにそのまま使用します。過度に長い出力は絶対に避けてください。必ず1文で出力すること。\n"
            "# 注意\n"
            "- 出力は日本語で行うこと。その他の言語は一切認めません。\n"
            "- 必ず60文字以内で出力すること。\n"
            "- 句読点など、余計な文字は出力しないこと。\n"
            "- 必ず１文で出力すること。\n"
            "- 「〇〇な〇〇」という形式で出力すること\n"
            "# 思考手順\n"
            "1. backgroundとpurposeの部分を読んで概要をつかみます。\n"
            "2. その内容を30文字以内で要約します。\n"
            "3. 体言止めになっているか、句読点が入っていないかを確認します。\n"
            "# 出力例\n"
            "以下に3つの出力例を示します。このくらいの分量になるように文字数の規定は必ず守ってください。\n"
            "- スマートフォンで音声を別の声にリアルタイム変換できる高速モデル「LLVC」\n"
            "- 3.2兆以上のトークンで学習された、130億のパラメータを持つオープン大規模言語モデル「Skywork」\n"
            "- OpenAIの文字起こしAI「Whisper」を軽量かつ高速にするモデル「Distil-Whisper」\n"
            f"{self.dict2json(output_format)}"
        )

        if isinstance(text, dict):
            text = self.dict2json(text)

        return [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": "please summarize the following text:\n" + text,
            },
        ]

    def postprocess(self, text):
        output_dict = self.json2dict(text)
        return output_dict.get("summary", "No Summary")


class ChatAssistant(OpenAIGPT):
    def preprocess(self, text):
        if isinstance(text, list):
            return text
        return [{"role": "user", "content": text}]

    def postprocess(self, text):
        return text


def process_text(text: str, model: str) -> str:
    base_settings = {"model": model, "max_tokens": 100}
    # extract title ----------------
    title_extractor = TitleExtractor()
    title = title_extractor.generate_completion(text=text, **base_settings)

    # summarize content ----------------
    content_summarizer = ContentSummarizer()
    content_summarizer_settings = base_settings.copy()["max_tokens"] = 2048
    content = content_summarizer.generate_completion(text=text, **content_summarizer_settings)

    # classify category ----------------
    category_classifier = CategoryClassifier()
    category = category_classifier.generate_completion(text=text, **base_settings)

    # briefly summarize content ----------------
    briefly_summarizer = BrieflySummarizer()
    summary = briefly_summarizer.generate_completion(text=content, **base_settings)

    return title, content, category, summary
