import json
import logging
import os
import re
import urllib.request

from urlextract import URLExtract

from .file_downloader import download_content
from .save_notion import add_to_notion_database, update_notion_content
from .text_processor import ChatAssistant, Questions, process_text

SLACK_TOKEN = os.environ["SLACK_TOKEN"]

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class SlackAPI:
    BASE_URL = "https://slack.com/api"
    HEADERS = {
        "Authorization": f"Bearer {SLACK_TOKEN}",
        "Content-Type": "application/json; charset=utf-8",
    }

    @staticmethod
    def post_message(channel, message, thread_ts=None):
        url = f"{SlackAPI.BASE_URL}/chat.postMessage"
        data = {"channel": channel, "text": message}
        if thread_ts:
            data["thread_ts"] = thread_ts
        SlackAPI._send_request(url, data)

    @staticmethod
    def get_conversations_replies(channel, ts):
        url = f"{SlackAPI.BASE_URL}/conversations.replies"
        params = {"channel": channel, "ts": ts}
        return SlackAPI._send_request(url, params)

    @staticmethod
    def _send_request(url, data):
        json_data = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            url=url, data=json_data, headers=SlackAPI.HEADERS, method="POST"
        )
        try:
            res = urllib.request.urlopen(req, timeout=5)
            return json.loads(res.read().decode("utf-8"))
        except Exception as e:
            logger.error(f"Error during Slack API request: {e}")
            raise


def lambda_handler(event: dict, context: dict) -> dict:
    logger.info("Received event: %s", event)
    logger.info("Received context: %s", context)

    # Ignore retries from Slack
    if "X-Slack-Retry-Num" in event.get("headers", {}):
        return {"statusCode": 200}

    body = parse_event_body(event)
    if "challenge" in body:
        return {"statusCode": 200, "body": json.dumps({"challenge": body["challenge"]})}

    slack_event = body.get("event", {})
    if slack_event.get("type") == "app_mention":
        handle_mention(slack_event)

    return {"statusCode": 200}


def parse_event_body(event):
    try:
        return json.loads(event["body"])
    except json.JSONDecodeError:
        return event["body"]
    finally:
        logger.info("Parsed body: %s", event["body"])


def handle_mention(slack_event):
    if "thread_ts" not in slack_event:
        handle_main_message(slack_event)
    else:
        handle_thread_message(slack_event)


def handle_main_message(slack_event):
    target_url = extract_url_from_blocks(slack_event.get("blocks", []))
    target_text = download_content(target_url)

    try:
        title, summary, category, briefly_summary = process_text(
            target_text, model="gpt-4o-mini"
        )
    except Exception as e:
        logger.error(f"Error processing text: {e}")
        SlackAPI.post_message(slack_event["channel"], "Failed to process the content.")
        return

    SlackAPI.post_message(
        slack_event["channel"], f"{title}\n{target_url}", slack_event["ts"]
    )

    questions = Questions()
    for question, summary in summary.items():
        message = f"{question}：{questions.to_question_str(question)}\n\n{summary}"
        SlackAPI.post_message(slack_event["channel"], message, slack_event["ts"])

    try:
        add_content_to_notion(
            title=title,
            url=target_url,
            summary=summary,
            category=category,
            briefly_summary=briefly_summary,
        )
    except Exception as e:
        logger.error(f"Failed to add content to Notion: {e}")


def add_content_to_notion(title, url, summary, category, briefly_summary):

    contents = {
        "title": title,
        "category": category,
        "briefly_summary": briefly_summary,
        "url": url,
        "summary": summary,
    }

    add_to_notion_database(contents)


def handle_thread_message(slack_event):
    input_context = re.sub(r"<[^>]*>", "", slack_event["text"])
    answer, url = answer_message_from_history(slack_event)

    SlackAPI.post_message(slack_event["channel"], answer, slack_event["thread_ts"])

    try:
        update_notion_content(url, {"question": input_context, "answer": answer})
    except Exception as e:
        logger.error(f"Error updating Notion: {e}")


def answer_message_from_history(slack_event):
    chat_assistant = ChatAssistant()
    settings = {"model": "gpt-4o-mini", "max_tokens": 4096}
    messages = []

    extractor = URLExtract(cache_dir="/tmp")
    replies = SlackAPI.get_conversations_replies(
        slack_event["channel"], slack_event["thread_ts"]
    )

    if replies.get("ok"):
        for reply in replies["messages"][-20:]:
            if reply.get("bot_id"):
                messages.append({"role": "assistant", "content": reply["text"]})
            else:
                urls = extractor.find_urls(reply["text"])
                if urls:
                    content = download_content(urls[0])
                    messages.append({"role": "user", "content": content})
                else:
                    messages.append({"role": "user", "content": reply["text"]})
    else:
        messages.append(
            {"role": "user", "content": re.sub(r"<[^>]*>", "", slack_event["text"])}
        )

    answer = chat_assistant.generate_completion(text=messages, **settings)

    if not urls:
        raise ValueError("URL not found in messages")

    return answer, urls[0]


def extract_url_from_blocks(blocks):
    for block in blocks:
        for element in block.get("elements", []):
            for inner_element in element.get("elements", []):
                if inner_element.get("type") == "link":
                    return inner_element.get("url", "").replace("\n", "")
    raise ValueError("URL not found in blocks")
