import json
import os
from abc import abstractmethod

from openai import OpenAI


class Questions:
    def __init__(self):
        self.question_dict = {
            "Q1": "何に関する論文か、専門外の研究者向けに詳しく説明してください。",
            "Q2": "論文の内容を、背景、新規性、方法などに分けて詳しく説明してください。",
            "Q3": "本研究の手法について特筆すべき部分を、詳しく説明してください。",
            "Q4": "本研究の成果や知見について特筆すべき部分を、詳しく説明してください。",
            "Q5": "本研究の限界について特筆すべき部分を、詳しく説明してください。",
            "Q6": "この論文中の記載で曖昧な部分を、詳しく説明してください。",
            "Q7": "引用されている論文の中で特筆すべきものを列挙し、本研究との関連性や違いを詳しく説明してください。",
            "Q8": "本研究で用いたデータセットを網羅的に列挙し、名前やURLなどがあればそれらも含めて詳しく説明してください。",
        }

    def to_question_str(self, question: str) -> str:
        return self.question_dict.get(question, "No Question")


class AbstractLLM:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    def dict2json(self, python_dict):
        json_string = json.dumps(python_dict, indent=2, ensure_ascii=False)
        return json_string

    def json2dict(self, json_string, error_key="error") -> dict:
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

    def _extract_string(self, text, start_string=None, end_string=None) -> str:
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


class TitleExtractor(AbstractLLM):
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


class ContentSummarizer(AbstractLLM):
    def preprocess(self, text, questions):
        output_format = {
            question: f"(string) Answer to {question} in markdown format" for question in questions
        }
        system_prompt = (
            "与えられる文章を読み込み、以下の問いに答えて下さい。\n"
            "Q1: 何に関する論文か、専門外の研究者向けに詳しく説明してください。\n"
            "(以下の質問はその分野の専門家向けに詳しく説明してください。)\n"
            "Q2: 論文の内容を、背景、新規性、方法などに分けて詳しく説明してください。\n"
            "Q3: 本研究の手法について特筆すべき部分を、詳しく説明してください。\n"
            "Q4: 本研究の成果や知見について特筆すべき部分を、詳しく説明してください。\n"
            "Q5: 本研究の限界について特筆すべき部分を、詳しく説明してください。\n"
            "Q6: この論文中の記載で曖昧な部分を、詳しく説明してください。\n"
            "Q7: 引用されている論文の中で特筆すべきものを列挙し、本研究との関連性や違いを詳しく説明してください。\n"
            "Q8: 本研究で用いたデータセットを網羅的に列挙し、名前やURLなどがあればそれらも含めて詳しく説明してください。\n"
            "# 注意\n"
            "- 出力は日本語で行うこと。その他の言語は一切認めません。ただし、専門用語と思われる単語はそのままでも良い。\n"
            "- 可能な限り詳細に出力すること。\n"
            "- 敬語は使用しないこと。「〜である」、「〜だ」のような形式にすること。\n"
            "以下の番号の質問に対して、以下の形式で回答してください。\n"
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

    def _generate_partial_completion(self, text, questions, **kwargs):
        messages = self.preprocess(text, questions)
        response = self.client.chat.completions.create(messages=messages, **kwargs)
        return self.postprocess(response.choices[0].message.content)

    def generate_completion(self, text, **kwargs):
        questions = ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8"]
        return_results = {}
        for question_index in questions:
            partial_response = self._generate_partial_completion(
                text, [question_index], **kwargs
            )
            print(partial_response)
            return_results[question_index] = partial_response.get(question_index, "")
        return return_results


class CategoryClassifier(AbstractLLM):
    def preprocess(self, text):
        output_format = {
            "category": "(list) [Representation Learning, Self Supervised Learning, Generative Model, Audio, Theory, LLM, Agent, Survey, Robotics, NLP, CV, World Model, Foundation Model, Reinforcement Learning]"
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
        list_str = output_dict.get("category", "No Category")
        return self._parse_string_to_list(list_str)

    def _parse_string_to_list(self, list_str):
        list_str = list_str.strip("[]")
        parsed_list = [item.strip() for item in list_str.split(",")]
        return parsed_list


class BrieflySummarizer(AbstractLLM):
    def preprocess(self, text):
        few_shot_list = [
            {
                "summary": "スマートフォンで音声を別の声にリアルタイム変換できる高速モデル「LLVC」"
            },
            {
                "summary": "3.2兆以上のトークンで学習された、130億のパラメータを持つオープン大規模言語モデル「Skywork」"
            },
            {
                "summary": "OpenAIの文字起こしAI「Whisper」を軽量かつ高速にするモデル「Distil-Whisper」"
            },
        ]
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
            f"{self.dict2json(few_shot_list[0])}\n"
            f"{self.dict2json(few_shot_list[1])}\n"
            f"{self.dict2json(few_shot_list[2])}"
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


class ChatAssistant(AbstractLLM):
    def preprocess(self, text):
        if isinstance(text, list):
            return text
        return [{"role": "user", "content": text}]

    def postprocess(self, text):
        return text


def process_text(text: str, model: str):
    base_settings = {"model": model, "max_tokens": 100}
    # extract title ----------------
    title_extractor = TitleExtractor()
    title = title_extractor.generate_completion(text=text, **base_settings)

    # summarize content ----------------
    content_summarizer = ContentSummarizer()
    content_summarizer_settings = base_settings.copy()
    content_summarizer_settings["max_tokens"] = 2048
    content = content_summarizer.generate_completion(
        text=text, **content_summarizer_settings
    )

    # classify category ----------------
    category_classifier = CategoryClassifier()
    category = category_classifier.generate_completion(text=text, **base_settings)

    # briefly summarize content ----------------
    briefly_summarizer = BrieflySummarizer()
    summary = briefly_summarizer.generate_completion(text=content, **base_settings)

    return title, content, category, summary
