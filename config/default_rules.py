"""
Default moderation rules configuration
"""

DEFAULT_MODERATION_RULES = [
    {
        "name": "Fraud & Impersonation",
        "description": "Content that misrepresents identity, scams users, or spreads fraudulent schemes.",
        "rule_type": "ai_prompt",
        "rule_data": {"prompt": "Content that misrepresents identity, scams users, or spreads fraudulent schemes."},
        "action": "reject",
        "priority": 100,
        "is_active": True,
    },
    {
        "name": "Phishing & Unauthorized Data Collection",
        "description": ("Any attempt to collect user data unlawfully, "
                        "including deceptive AI-generated content designed to steal credentials."),
        "rule_type": "ai_prompt",
        "rule_data": {"prompt": ("Any attempt to collect user data unlawfully, "
                                 "including deceptive AI-generated content designed to steal credentials.")},
        "action": "reject",
        "priority": 100,
        "is_active": True,
    },
    {
        "name": "Misleading AI Content",
        "description": ("AI-generated content that spreads false information, "
                        "deepfakes, or impersonates individuals without disclosure."),
        "rule_type": "ai_prompt",
        "rule_data": {"prompt": ("AI-generated content that spreads false information, "
                                 "deepfakes, or impersonates individuals without disclosure.")},
        "action": "reject",
        "priority": 100,
        "is_active": True,
    },
    {
        "name": "Illegal Content",
        "description": ("Content that violates applicable laws, "
                        "including terrorism, child exploitation, and financial crimes."),
        "rule_type": "ai_prompt",
        "rule_data": {"prompt": ("Content that violates applicable laws, "
                                 "including terrorism, child exploitation, and financial crimes.")},
        "action": "reject",
        "priority": 100,
        "is_active": True,
    },
    {
        "name": "Spam & Unsolicited Promotions",
        "description": "Unwanted advertising, excessive marketing, and pyramid schemes.",
        "rule_type": "ai_prompt",
        "rule_data": {"prompt": "Unwanted advertising, excessive marketing, and pyramid schemes."},
        "action": "reject",
        "priority": 100,
        "is_active": True,
    },
]


async def create_default_rules(db_service, project_id):
    """
    Create default moderation rules for a new project

    Args:
        db_service: Database service instance
        project_id: ID of the project to create rules for
    """
    for rule in DEFAULT_MODERATION_RULES:
        await db_service.create_moderation_rule(
            project_id=project_id,
            name=rule["name"],
            rule_type=rule["rule_type"],
            rule_content=str(rule["rule_data"]),
            action=rule["action"],
            priority=rule["priority"]
        )
