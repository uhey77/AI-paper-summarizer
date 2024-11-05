import logging
import os

from notion_client import Client

from .text_processor import Questions

DATABASE_ID = os.environ["NOTION_DATABASE_ID"]

notion = Client(auth=os.environ["NOTION_KEY"])


def add_to_notion_database(contents, database_id=DATABASE_ID):
    questions = Questions()

    properties = {
        "title": {"title": [{"text": {"content": contents["title"]}}]},
        "url": {"url": contents["url"]},
        "summary": {"rich_text": [{"text": {"content": contents["briefly_summary"]}}]},
        "tag": {"multi_select": [{"name": tag} for tag in contents["category"]]},
    }

    children = [
        {"object": "block", "type": "table_of_contents", "table_of_contents": {}},
    ]

    for question, answer in contents["summary"].items():
        children.append(
            create_callout_block(
                "❓", f"{question}：{questions.to_question_str(question)}", answer
            )
        )

    try:
        response = notion.pages.create(
            parent={"database_id": database_id},
            properties=properties,
            children=children,
        )
        logging.info("Notion database response: %s", response)

    except Exception as e:
        logging.error(f"Error adding to Notion: {e}")
        raise Exception(f"Error adding to Notion: {e}")


def fetch_page_from_database(url, database_id=DATABASE_ID):
    try:
        response = notion.databases.query(database_id=database_id)
        results = response.get("results", [])

        if not results:
            return None

        for result in results:
            try:
                if result["properties"]["url"]["url"] == url:
                    return result["id"]
            except KeyError as e:
                logging.error(f"Error fetching page from database: {e}")
            except Exception as e:
                logging.error(f"Error fetching page from database: {e}")

    except Exception as e:
        logging.error(f"Error fetching page from database: {e}")

    return None


def update_notion_content(url, contents, database_id=DATABASE_ID):
    page_id = fetch_page_from_database(url, database_id)

    if not page_id:
        print("No page found with the specified URL.")
        return

    children = [create_callout_block("❓", contents["question"], contents["answer"])]

    try:
        response = notion.blocks.children.append(
            block_id=page_id,
            children=children,
        )
        logging.info("Notion update response: %s", response)
    except Exception as e:
        logging.error(f"Error updating Notion: {e}")
        raise Exception(f"Error updating Notion: {e}")


def create_callout_block(emoji, title, content):
    return {
        "object": "block",
        "type": "callout",
        "callout": {
            "color": "default",
            "icon": {"emoji": emoji, "type": "emoji"},
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": title},
                    "annotations": {"bold": True},
                }
            ],
            "children": [
                {"object": "block", "type": "divider", "divider": {}},
                {
                    "object": "block",
                    "paragraph": {"rich_text": [{"text": {"content": content}}]},
                },
            ],
        },
    }
