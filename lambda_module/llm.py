import json
import os
from abc import abstractmethod

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


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
