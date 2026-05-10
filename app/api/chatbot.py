from flask import Blueprint, request, jsonify

api_chatbot_bp = Blueprint('api_chatbot', __name__)

# ── Medical keywords that redirect to VetScan ────────────────────────────────
MEDICAL_KEYWORDS = [
    'vomit', 'bleeding', 'limp', 'limping', 'seizure', 'seizures', 'scratching',
    'coughing', 'diarrhea', 'diarrhoea', 'sneezing', 'swollen', 'swelling',
    'wound', 'discharge', 'rash', 'rashes', 'itching', 'fever', 'lethargy',
    'lethargic', 'shaking', 'trembling', 'not eating', 'not drinking',
    'loss of appetite', 'weight loss', 'hair loss', 'paralyz', 'collapse',
    'collapsed', 'unconscious', 'wheezing', 'panting', 'drooling',
    'broken bone', 'fracture', 'broken leg', 'broken paw', 'broken wing',
    'injured', 'injury', 'hit by', 'accident', 'bitten', 'bruise',
    'sick', 'sickness', 'disease', 'infection', 'diagnos', 'symptom',
    'what is wrong', 'something wrong', 'not feeling well', 'ill', 'illness',
    'condition', 'treatment', 'medicine', 'medication',
    'my dog is', 'my cat is', 'my pet is', 'my rabbit is', 'my bird is', 'my fish is',
    'emergency', 'poison', 'poisoning', 'swallowed', 'ate something', 'health concern',
]

FAQ_ANSWERS = {
    "how to book": (
        "<strong>To book an appointment:</strong><ol>"
        "<li>Log in to your account.</li>"
        "<li>Go to your Dashboard.</li>"
        "<li>Click 'Book Appointment'.</li>"
        "<li>Select your pet, service, date, and time slot.</li></ol>"
        "<em>Disclaimer: For urgent emergency cases, please call the clinic directly.</em>"
    ),
    "book appointment": (
        "<strong>To book an appointment:</strong><ol>"
        "<li>Log in to your account.</li>"
        "<li>Go to your Dashboard.</li>"
        "<li>Click 'Book Appointment'.</li>"
        "<li>Select your pet, service, date, and time slot.</li></ol>"
        "<em>Disclaimer: For urgent emergency cases, please call the clinic directly.</em>"
    ),
    "clinic hours": (
        "<strong>VetSync Clinic Hours:</strong><br><br>"
        "Monday - Saturday: 8:00 AM - 6:00 PM<br>"
        "Sunday & Holidays: CLOSED<br><br>"
        "<em>For emergencies outside clinic hours, call our 24/7 hotline: (02) 8123-4567</em>"
    ),
    "what are the offers": (
        "We frequently have seasonal offers! Right now, we offer a "
        "<strong>10% discount on first-time checkups</strong> and discounted vaccination bundles.<br><br>"
        "Book an appointment online to secure these offers."
    ),
    "how to view my pets": (
        "<strong>To view your pets:</strong><ol>"
        "<li>Log in to your account.</li>"
        "<li>Navigate to your Dashboard.</li>"
        "<li>Look for the 'My Pets' section to view all registered pet profiles.</li></ol>"
    ),
    "how to check services": (
        "Our primary services include:<br><ul>"
        "<li>General Checkup</li><li>Vaccination</li><li>Dental Care</li>"
        "<li>Surgery</li><li>Grooming</li><li>Emergency Care</li></ul><br>"
        "Click 'Services' on the top navigation bar to see detailed pricing."
    ),
    "how to leave a review": (
        "<strong>To leave a review:</strong><ol>"
        "<li>Log in to your account.</li>"
        "<li>Go to your Dashboard.</li>"
        "<li>Locate a completed appointment.</li>"
        "<li>Click 'Leave a Review' to share your experience!</li></ol>"
    ),
    "how to sign up": (
        "<strong>To sign up:</strong><ol>"
        "<li>Click 'Sign Up' at the top right.</li>"
        "<li>Fill in your name, email, contact, and password.</li>"
        "<li>Log in and start booking for your pet!</li></ol>"
    ),
    "how to log in": (
        "<strong>To log in:</strong><br>"
        "Click 'Log In' on the top right and enter your registered email and password."
    ),
}


@api_chatbot_bp.route('/astrid', methods=['POST'])
def astrid():
    data    = request.get_json() or {}
    message = data.get('message', '').lower().strip()

    # Medical intercept — always redirect to VetScan
    if any(kw in message for kw in MEDICAL_KEYWORDS):
        return jsonify({'mode': 'vetscan_redirect'})

    # Scripted FAQ matching
    for key, answer in FAQ_ANSWERS.items():
        if key in message:
            return jsonify({'mode': 'scripted', 'reply': answer, 'type': 'faq'})

    # Fallback
    return jsonify({
        'mode':  'scripted',
        'reply': (
            "I'm ASTRID, your VetSync system guide! I can help you navigate the platform "
            "and answer system questions. For any pet health concerns, please use "
            "<strong>VetScan</strong>. Choose a topic from the menu below!"
        ),
        'type': 'fallback'
    })


@api_chatbot_bp.route('/health', methods=['POST'])
def health_chat():
    """
    Dedicated pet health endpoint with species filtering.
    POST body: { "message": "...", "species": "dog" | "cat" | "rabbit" | "bird" | "" }
    """
    data           = request.get_json() or {}
    message        = data.get('message', '').lower().strip()
    species_filter = data.get('species', '').lower().strip()

    # Knowledge base is empty in scripted mode — return no-match
    return jsonify({
        'reply': (
            f"I couldn't find specific information for that symptom"
            f"{' in ' + species_filter + 's' if species_filter else ''}. "
            "Try describing the symptom differently or book an appointment for a proper diagnosis."
        ),
        'type':         'no_match',
        'show_booking': True,
        'species_filter': species_filter or 'any',
    })
