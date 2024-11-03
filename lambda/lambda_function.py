import json
import logging


def lambda_handler(event: dict, context: dict) -> dict:
    logging.info("Received event: %s", event)
    logging.info("Received context: %s", context)

    try:
        body = json.loads(event["body"])
    except json.JSONDecodeError:
        body = event["body"]
    else:
        logging.info("Received body: %s", body)

    if "challenge" in body:
        return {"statusCode": 200, "body": json.dumps({"challenge": body["challenge"]})}

    return {"statusCode": 200, "body": json.dumps("Hello from Lambda!")}
