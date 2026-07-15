import urllib.parse

def create_calendar_link(title: str, description: str, date_str: str) -> str:
    # date_str format: YYYYMMDDThhmmssZ/YYYYMMDDThhmmssZ or YYYYMMDD/YYYYMMDD
    base_url = "https://calendar.google.com/calendar/render"
    params = {
        "action": "TEMPLATE",
        "text": title,
        "details": description,
        "dates": date_str
    }
    query_string = urllib.parse.urlencode(params)
    return f"{base_url}?{query_string}"

def get_india_election_events() -> list:
    return [
        {
            "title": "Check Voter Registration",
            "description": "Reminder to verify your name on the electoral roll at voters.eci.gov.in.",
            "calendar_link": create_calendar_link(
                "Check Voter Registration",
                "Verify your name on the electoral roll at voters.eci.gov.in. Keep your EPIC number handy.",
                "20240401/20240402"
            ),
            "icon": "📝"
        },
        {
            "title": "Voter ID Application Deadline",
            "description": "General reminder to apply for a new Voter ID or corrections if needed.",
            "calendar_link": create_calendar_link(
                "Voter ID Application Deadline",
                "Submit Form 6 for new registration or Form 8 for correction on voters.eci.gov.in.",
                "20240315/20240316"
            ),
            "icon": "🪪"
        },
        {
            "title": "Election Day Preparation",
            "description": "What to carry, where to go, and your designated polling booth details.",
            "calendar_link": create_calendar_link(
                "Election Day Preparation",
                "Remember to carry your Voter ID or any of the 12 approved ID documents. Voting hours are usually 7 AM to 6 PM.",
                "20240418/20240419"
            ),
            "icon": "📍"
        },
        {
            "title": "Model Code of Conduct Awareness",
            "description": "When elections are announced, MCC comes into effect.",
            "calendar_link": create_calendar_link(
                "Model Code of Conduct Awareness",
                "Report MCC violations like hate speech or bribing using the cVIGIL app or 1950 helpline.",
                "20240301/20240302"
            ),
            "icon": "📋"
        }
    ]
