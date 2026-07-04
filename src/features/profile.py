from datetime import datetime, timezone

# imports from project specific files
from core.responses import build_response, parse_body
from core.auth import current_user_id
from core.keys import profile_sk, user_pk
from core.storage import table

def get_profile(event):
    user_id = current_user_id(event)

    response = table.get_item(
        Key={
            "pk": user_pk(user_id),
            "sk": profile_sk(),
        }
    )

    item = response.get("Item")

    if not item:
        return build_response(
            200,
            {
                "pk": user_pk(user_id),
                "sk": profile_sk(),
                "recordType": "userProfile",
                "userId": user_id,
                "name": "",
                "currentTitle": "",
                "targetTitle": "",
                "yearsExperience": "",
                "certifications": "",
                "preferredProvider": "openai",
                "resumeStyle": "executive",
            },
        )

    return build_response(200, item)

def update_profile(event):
    user_id = current_user_id(event)
    body = parse_body(event)

    if body is None:
        return build_response(400, {"error": "Invalid JSON body"})

    updated_at = datetime.now(timezone.utc).isoformat()

    item = {
        "pk": user_pk(user_id),
        "sk": profile_sk(),
        "recordType": "userProfile",
        "userId": user_id,
        "updatedAt": updated_at,
        "name": body.get("name", "").strip(),
        "currentTitle": body.get("currentTitle", "").strip(),
        "targetTitle": body.get("targetTitle", "").strip(),
        "yearsExperience": body.get("yearsExperience", "").strip(),
        "certifications": body.get("certifications", "").strip(),
        "preferredProvider": body.get("preferredProvider", "openai").strip(),
        "resumeStyle": body.get("resumeStyle", "executive").strip(),
    }

    table.put_item(Item=item)

    return build_response(200, item)
