import os

from notion_client import Client

NOTION_TOKEN = os.environ["NOTION_KEY"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]

notion = Client(auth=NOTION_TOKEN)


def add_to_notion_database(contents, database_id=DATABASE_ID):

    try:
        response = notion.pages.create(
            **{
                "parent": {"database_id": database_id},
                "properties": {
                    "title": {"title": [{"text": {"content": contents["title"]}}]},
                    "url": {"url": contents["url"]},
                    "summary": {
                        "rich_text": [{"text": {"content": contents["index"]}}]
                    },
                    "tag": {"multi_select": [{"name": tag} for tag in contents["tag"]]},
                },  # end properties
                "children": [
                    {
                        "object": "block",
                        "type": "table_of_contents",
                        "table_of_contents": {},
                    },
                    {
                        "object": "block",
                        "type": "callout",
                        "callout": {
                            "color": "default",
                            "icon": {"emoji": "📄", "type": "emoji"},
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": "論文サマリー"},
                                    "annotations": {
                                        "bold": True,
                                        "italic": False,
                                        "strikethrough": False,
                                        "underline": False,
                                        "code": False,
                                        "color": "default",
                                    },
                                }
                            ],
                            "children": [
                                {"object": "block", "type": "divider", "divider": {}},
                                {
                                    "object": "block",
                                    "paragraph": {
                                        "rich_text": [
                                            {
                                                "text": {
                                                    "content": contents["gpt_summary"],
                                                }
                                            }
                                        ],
                                    },
                                },
                            ],
                        },
                    },
                ],
            }
        )
    except Exception as e:
        print(e)

    print("notion database create completed")
    print(response)  # 追加した内容を表示する


def fetch_page_from_database(url, database_id=DATABASE_ID):
    try:
        response = notion.databases.query(
            **{
                "database_id": database_id,
            }
        )
    except Exception as e:
        print(f"Error querying database: {e}")
        return None

    results = response.get("results", [])
    if not results:
        print("No results found in the database query.")
        return None

    for result in results:
        try:
            if result["properties"]["url"]["url"] == url:
                return result["id"]
        except KeyError as e:
            print(f"KeyError accessing result properties: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    return None


def update_notion_content(url, contents, database_id=DATABASE_ID):
    page_id = fetch_page_from_database(url, database_id)

    print(f"find page id >> {page_id}")

    if page_id is None:
        print("No page found with the specified URL.")

    try:
        response = notion.blocks.children.append(
            **{
                "block_id": page_id,
                "children": [
                    {
                        "object": "block",
                        "type": "callout",
                        "callout": {
                            "color": "default",
                            "icon": {"emoji": "❓", "type": "emoji"},
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": contents["question"]},
                                    "annotations": {
                                        "bold": True,
                                        "italic": False,
                                        "strikethrough": False,
                                        "underline": False,
                                        "code": False,
                                        "color": "default",
                                    },
                                }
                            ],
                            "children": [
                                {"object": "block", "type": "divider", "divider": {}},
                                {
                                    "object": "block",
                                    "paragraph": {
                                        "rich_text": [
                                            {
                                                "text": {
                                                    "content": contents["answer"],
                                                }
                                            }
                                        ],
                                    },
                                },
                            ],
                        },
                    }
                ],
            }
        )
    except Exception as e:
        print(f"Error updating Notion: {e}")

    print("Notion database update response:")
    print(response)
