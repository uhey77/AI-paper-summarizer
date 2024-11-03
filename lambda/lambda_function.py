import json


def lambda_handler(event: dict, context: dict) -> dict:
    # TODO implement
    return {"statusCode": 200, "body": json.dumps("Hello from Lambda!")}
