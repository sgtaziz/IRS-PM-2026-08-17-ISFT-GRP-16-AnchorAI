"""The default retention-offer catalogue: scenario history and the app's seed share it."""

OFFER_CATALOG: list[dict] = [
    {
        "offer_id": "checkin_message",
        "name": "Personal check-in message",
        "cost": 0.0,
        "staff_minutes": 5,
        "inventory": None,
        "channels": ["sms", "email", "call"],
        "eligibility": "Any active member",
        "required_skill": "",
    },
    {
        "offer_id": "free_pt_session",
        "name": "Free personal training session",
        "cost": 40.0,
        "staff_minutes": 60,
        "inventory": 40,
        "channels": ["call", "in_person"],
        "eligibility": "Members without PT in the last 90 days",
        "required_skill": "trainer",
    },
    {
        "offer_id": "class_pass",
        "name": "Bring-a-friend class pass",
        "cost": 15.0,
        "staff_minutes": 10,
        "inventory": 100,
        "channels": ["sms", "email", "call"],
        "eligibility": "Any active member",
        "required_skill": "",
    },
    {
        "offer_id": "discount_1m",
        "name": "One month at 20% off",
        "cost": 12.0,
        "staff_minutes": 15,
        "inventory": None,
        "channels": ["email", "call"],
        "eligibility": "Month-to-month members only",
        "required_skill": "",
    },
]
