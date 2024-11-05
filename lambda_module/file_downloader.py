from io import BytesIO

import arxiv
import requests
from markdownify import markdownify
from pypdf import PdfReader


class PDFProcessor:
    def __init__(self):
        self.text = ""

    def to_file(self, binary_content: bytes) -> BytesIO:
        return BytesIO(binary_content)

    def read_text(self, binary_content: bytes) -> str:
        reader = PdfReader(self.to_file(binary_content))
        self.text = ""  # 初期化
        for page in reader.pages:
            self.text += page.extract_text() or ""
        return self.text


def download_pdf_from_arxiv(arxiv_id: str) -> bytes:
    client = arxiv.Client()
    search = arxiv.Search(id_list=[arxiv_id], max_results=1)
    paper = next(client.results(search))
    try:
        return requests.get(paper.pdf_url).content
    except Exception as e:
        raise Exception(f"Cannot download PDF file from arXiv: {e}")


def download_pdf(url: str) -> bytes:
    try:
        return requests.get(url).content
    except Exception as e:
        raise Exception(f"Cannot download PDF file: {e}")


def download_html_as_markdown(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    try:
        html_text = requests.get(url, headers=headers).text
        return markdownify(html_text)
    except Exception as e:
        raise Exception(f"Cannot download HTML file: {e}") from e


def download_content(url: str) -> str:
    pdf_processor = PDFProcessor()

    # arXiv PDF ----------------
    if "arxiv" in url.lower():
        arxiv_id = url.split("/")[-1].removesuffix(".pdf")
        binary_content = download_pdf_from_arxiv(arxiv_id)
        return pdf_processor.read_text(binary_content)

    # Other PDF ----------------
    elif "pdf" in url.lower():
        binary_content = download_pdf(url)
        return pdf_processor.read_text(binary_content)

    # HTML ----------------
    else:
        return download_html_as_markdown(url)
