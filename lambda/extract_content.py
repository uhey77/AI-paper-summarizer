from io import BytesIO

import arxiv
import requests
from markdownify import markdownify as md
from pypdf import PdfReader


def extract_content(url):
    title = None

    if "arxiv" in url:
        arxiv_id = url.split("/")[-1].replace(".pdf", "")
        print(f"arxiv_id > {arxiv_id}")

        client = arxiv.Client()
        search = arxiv.Search(id_list=[arxiv_id], max_results=1)
        paper = next(client.results(search))
        title = paper.title
        binary_content = requests.get(paper.pdf_url).content

    elif "pdf" in url:
        print(f"url > {url}")
        try:
            binary_content = requests.get(url).content
        except Exception as e:
            print(f"Error: {e}")
            return None, None

    else:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
            }
            html_text = requests.get(url, headers=headers).text
            markdown_text = md(html_text)
        except Exception as e:
            print(f"Error: {e}")
            return None, None

        return None, markdown_text

    pdf_file = BytesIO(binary_content)

    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()

    return title, text
