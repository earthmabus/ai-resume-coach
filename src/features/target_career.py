from datetime import datetime, timezone

# imports from project specific files
from core.responses import build_response, parse_body
from core.auth import current_user_id
from core.keys import base_keys, target_career_sk, user_pk
from core.storage import table

def get_target_career_for_user(user_id):
    response = table.get_item(
        Key={
            "pk": user_pk(user_id),
            "sk": target_career_sk(),
        }
    )
    return response.get("Item")


def get_target_career(event):
    user_id = current_user_id(event)
    item = get_target_career_for_user(user_id)

    if not item:
        return build_response(200, {
            "recordType": "targetCareer",
            "userId": user_id,
            "roleTitle": "",
            "industry": "",
            "seniorityLevel": "",
            "workEnvironment": "",
            "keyResponsibilities": "",
            "requiredSkills": "",
            "certifications": "",
            "physicalRequirements": "",
            "technicalRequirements": "",
            "leadershipRequirements": "",
            "careerGoalSummary": "",
        })

    return build_response(200, item)


def update_target_career(event):
    user_id = current_user_id(event)
    body = parse_body(event)

    if body is None:
        return build_response(400, {"error": "Invalid JSON body"})

    role_title = body.get("roleTitle", "").strip()
    industry = body.get("industry", "").strip()

    if not role_title or not industry:
        return build_response(400, {"error": "roleTitle and industry are required"})

    target_career_id = f"target-career-{user_id}"
    updated_at = datetime.now(timezone.utc).isoformat()

    item = {
        **base_keys(
            pk=user_pk(user_id),
            sk=target_career_sk(),
            entity_id=target_career_id,
            record_type="targetCareer",
        ),
        "recordType": "targetCareer",
        "targetCareerId": target_career_id,
        "userId": user_id,
        "updatedAt": updated_at,
        "roleTitle": role_title,
        "industry": industry,
        "seniorityLevel": body.get("seniorityLevel", "").strip(),
        "workEnvironment": body.get("workEnvironment", "").strip(),
        "keyResponsibilities": body.get("keyResponsibilities", "").strip(),
        "requiredSkills": body.get("requiredSkills", "").strip(),
        "certifications": body.get("certifications", "").strip(),
        "physicalRequirements": body.get("physicalRequirements", "").strip(),
        "technicalRequirements": body.get("technicalRequirements", "").strip(),
        "leadershipRequirements": body.get("leadershipRequirements", "").strip(),
        "careerGoalSummary": body.get("careerGoalSummary", "").strip(),
    }

    table.put_item(Item=item)
    return build_response(200, item)
