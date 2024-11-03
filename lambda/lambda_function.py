import json
import logging
import os
import re
import urllib.request

import notion_utils
from extract_content import extract_content
from index import index
from openai import OpenAI
from summarize import summarize
from tagging import tagging
from urlextract import URLExtract

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
SLACK_TOKEN = os.environ["SLACK_TOKEN"]

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: dict, context: dict) -> dict:
    logging.info("Received event: %s", event)
    logging.info("Received context: %s", context)

    # 再送を無視 --------------------
    headers = event.get("headers", [])
    if "X-Slack-Retry-Num" in headers:
        return {"statusCode": 200}

    try:
        body = json.loads(event["body"])
    except json.JSONDecodeError:
        body = event["body"]
    finally:
        logging.info("Received body: %s", body)

    # Event Subscriptions 対応 --------------------
    if "challenge" in body:
        return {"statusCode": 200, "body": json.dumps({"challenge": body["challenge"]})}

    slack_event = body["event"]

    # mention 以外は無視 --------------------
    if slack_event["type"] != "app_mention":
        return {"statusCode": 200}

    # メインメッセージの処理 --------------------
    if "thread_ts" not in slack_event:
        target_url = extract_url_from_blocks(slack_event.get("blocks", []))
        logging.info("target_url: %s", target_url)

        paper_title, paper_text = extract_content(target_url)

        if paper_title is None:
            paper_title = "No Title"  # TODO: タイトルを取得するリクエストを送る

        logging.info(f"paper_title : {paper_title}")

        # title と url を slack に送信
        title_message = f"{paper_title}\n{target_url}"
        send_slack(slack_event["channel"], title_message, slack_event["ts"])

        # 要約処理
        try:
            paper_summary = summarize(paper_text)
        except Exception as e:
            logging.error(f"Error: {e}")
            paper_summary = "要約に失敗しました"

        send_slack(slack_event["channel"], paper_summary, slack_event["ts"])

        # 1文要約/タグ付け処理
        paper_index = index(paper_summary)
        tags = json.loads(tagging(paper_summary))

        contents = {
            "title": paper_title,
            "url": target_url,
            "index": paper_index,
            "tag": tags["label"],
            "gpt_summary": paper_summary,
        }

        # Notion に追加
        notion_utils.add_to_notion_database(contents)

    # スレッドメッセージの処理 --------------------
    else:
        input_context = re.sub(r"<[^>]*>", "", slack_event["text"])
        messages = []
        extractor = URLExtract(cache_dir="/tmp")
        replies = get_conversations_replies(
            slack_event["channel"], slack_event["thread_ts"]
        )
        if replies.get("ok"):
            for reply in replies["messages"][-20:]:
                if reply.get("bot_id"):
                    messages.append({"role": "assistant", "content": reply["text"]})
                else:
                    urls = extractor.find_urls(reply["text"])  # URLを抽出
                    if urls:
                        url = urls[0]
                        title, content = extract_content(url)
                    messages.append(
                        {
                            "role": "user",
                            "content": reply["text"] if not urls else content,
                        }
                    )
        else:
            messages.append({"role": "user", "content": input_context})

        res = client.chat.completions.create(model="gpt-4o", messages=messages)
        answer = res.choices[0].message.content

        # slack に返信
        send_slack(slack_event["channel"], answer, slack_event["thread_ts"])

        contents = {"question": input_context, "answer": answer}

        try:
            notion_utils.update_notion_content(url, contents)
        except Exception as e:
            logging.error(f"Error: {e}")
            raise Exception("Notion への更新に失敗しました \n" + str(e))

    return {"statusCode": 200}


def extract_url_from_blocks(blocks):
    for block in blocks:
        elements = block.get("elements", [])
        for element in elements:
            inner_elements = element.get("elements", [])
            for inner_element in inner_elements:
                if inner_element.get("type") == "link":
                    return inner_element.get("url", None).replace("/n", "")

    raise ValueError("URL not found in blocks")


def get_prev_messages(channel):
    url = "https://slack.com/api/conversations.history"
    token = SLACK_TOKEN
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json; charset=utf-8",
    }
    params = {"channel": channel, "limit": 3}

    req = urllib.request.Request(
        "{}?{}".format(url, urllib.parse.urlencode(params)), headers=headers
    )
    res = urllib.request.urlopen(req, timeout=5)

    return json.loads(res.read().decode("utf-8"))


def get_conversations_replies(channel, ts):
    url = "https://slack.com/api/conversations.replies"
    token = SLACK_TOKEN
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json; charset=utf-8",
    }
    params = {"channel": channel, "ts": ts}

    req = urllib.request.Request(
        "{}?{}".format(url, urllib.parse.urlencode(params)), headers=headers
    )
    res = urllib.request.urlopen(req, timeout=5)

    return json.loads(res.read().decode("utf-8"))


def send_slack(channel, message, thread_ts=None) -> None:
    url = "https://slack.com/api/chat.postMessage"
    token = SLACK_TOKEN
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json; charset=utf-8",
    }
    method = "POST"
    data = {"channel": channel, "text": message}

    if thread_ts:
        data["thread_ts"] = thread_ts

    json_data = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url=url, data=json_data, headers=headers, method=method
    )
    urllib.request.urlopen(req, timeout=5)
