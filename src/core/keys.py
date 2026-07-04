def user_pk(user_id):
    return f"USER#{user_id}"

def resume_sk(analysis_id):
    return f"RESUME#{analysis_id}"

def match_sk(match_id):
    return f"MATCH#{match_id}"

def tailoring_pk(match_id):
    return f"MATCH#{match_id}"

def tailoring_sk(tailoring_id):
    return f"TAILORING#{tailoring_id}"

def interview_sk(interview_prep_id):
    return f"INTERVIEW#{interview_prep_id}"

def profile_sk():
    return "PROFILE"

def target_career_sk():
    return "TARGET_CAREER"

def entity_gsi_pk(entity_id):
    return f"ENTITY#{entity_id}"

def base_keys(pk, sk, entity_id, record_type):
    return {
        "pk": pk,
        "sk": sk,
        "gsi1pk": entity_gsi_pk(entity_id),
        "gsi1sk": record_type,
    }
