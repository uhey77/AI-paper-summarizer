from unittest.mock import patch

from lambda_module.lambda_function import (
    add_content_to_notion,
    answer_message_from_history,
    handle_main_message,
    parse_event_body,
)


# `parse_event_body` のテスト
def test_parse_event_body():
    event = {"body": '{"key": "value"}'}
    result = parse_event_body(event)
    assert result == {"key": "value"}

    event = {"body": "invalid json"}
    result = parse_event_body(event)
    assert result == "invalid json"


# `handle_main_message` のテスト
@patch("lambda_module.lambda_function.download_content", return_value="sample text")
@patch(
    "lambda_module.lambda_function.process_text",
    return_value=("Title", {"Q1": "Summary"}, "Category", "Brief Summary"),
)
@patch("lambda_module.lambda_function.SlackAPI.post_message")
def test_handle_main_message(
    mock_post_message, mock_process_text, mock_download_content
):
    slack_event = {
        "channel": "C12345",
        "blocks": [
            {
                "elements": [
                    {"elements": [{"type": "link", "url": "http://example.com"}]}
                ]
            }
        ],
        "ts": "1234567890.123456",
    }
    handle_main_message(slack_event)
    mock_download_content.assert_called_once_with("http://example.com")
    mock_process_text.assert_called_once_with("sample text", model="gpt-4o-mini")
    mock_post_message.assert_called()  # メッセージ送信が実行されていることを確認


# `add_content_to_notion` のテスト
@patch("lambda_module.lambda_function.add_to_notion_database")
def test_add_content_to_notion(mock_add_to_notion_database):
    title = "Title"
    url = "http://example.com"
    summary = {"Q1": "Summary"}
    category = "Category"
    briefly_summary = "Brief Summary"
    add_content_to_notion(title, url, summary, category, briefly_summary)
    contents = {
        "title": title,
        "url": url,
        "index": briefly_summary,
        "tag": category,
        "gpt_summary": summary,
    }
    mock_add_to_notion_database.assert_called_once_with(contents)


# `answer_message_from_history` のテスト
@patch("lambda_module.lambda_function.SlackAPI.get_conversations_replies")
@patch(
    "lambda_module.lambda_function.ChatAssistant.generate_completion",
    return_value="Generated answer",
)
@patch(
    "lambda_module.lambda_function.download_content", return_value="Downloaded content"
)
@patch(
    "lambda_module.lambda_function.URLExtract.find_urls",
    return_value=["http://example.com"],
)
def test_answer_message_from_history(
    mock_find_urls,
    mock_download_content,
    mock_generate_completion,
    mock_get_conversations_replies,
):
    mock_get_conversations_replies.return_value = {
        "ok": True,
        "messages": [{"text": "Message with URL", "bot_id": None}],
    }

    slack_event = {
        "channel": "C12345",
        "thread_ts": "1234567890.123456",
        "text": "User message text",
    }
    answer, url = answer_message_from_history(slack_event)
    assert answer == "Generated answer"
    assert url == "http://example.com"

    mock_generate_completion.assert_called()
    mock_download_content.assert_called_once_with("http://example.com")
    mock_get_conversations_replies.assert_called_once_with(
        "C12345", "1234567890.123456"
    )
