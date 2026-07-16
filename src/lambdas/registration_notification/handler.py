import json
import os
from datetime import datetime, timezone

import boto3

sns = boto3.client("sns")
topic_arn = os.environ["REGISTRATION_NOTIFICATION_TOPIC_ARN"]


def lambda_handler(event, context):
    trigger_source = event.get("triggerSource", "")
    user_attributes = event.get("request", {}).get("userAttributes", {})

    # Avoid sending email for password reset confirmations.
    if trigger_source not in ("PostConfirmation_ConfirmSignUp", "PostConfirmation_AdminConfirmSignUp"):
        return event

    email = user_attributes.get("email", "unknown")
    sub = user_attributes.get("sub", "unknown")
    created_at = datetime.now(timezone.utc).isoformat()

    subject = "New AI Resume Coach user registered"

    message = {
        "event": "new_user_registration",
        "email": email,
        "userSub": sub,
        "createdAt": created_at,
        "triggerSource": trigger_source,
        "region": os.getenv("AWS_REGION", "unknown"),
        "deploymentId": os.getenv("DEPLOYMENT_ID", "unknown"),
        "environment": os.getenv("ENVIRONMENT", "unknown"),
    }

    sns.publish(
        TopicArn=topic_arn,
        Subject=subject,
        Message=json.dumps(message, indent=2),
    )

    return event
