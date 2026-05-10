try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app import create_app
from app.extensions import db
from app.models.service import Service

app = create_app()

with app.app_context():
    default_services = [
        {"name": "General Checkup", "icon": "🩺", "desc": "Comprehensive physical exam to ensure your pet's overall health."},
        {"name": "Vaccination",     "icon": "💉", "desc": "Core and non-core vaccines to protect against infectious diseases."},
        {"name": "Dental Care",     "icon": "🦷", "desc": "Teeth cleaning, polishing, and oral health assessments."},
        {"name": "Surgery",         "icon": "⚕️",  "desc": "Spaying, neutering, and other common surgical procedures."},
        {"name": "Grooming",        "icon": "✂️", "desc": "Professional bathing, hair trimming, and nail clipping."},
        {"name": "Diagnostics",     "icon": "🔬", "desc": "Blood tests, x-rays, and ultrasound imaging."},
    ]

    for data in default_services:
        s = Service.query.filter_by(name=data["name"]).first()
        if not s:
            s = Service(name=data["name"], icon=data["icon"], desc=data["desc"])
            db.session.add(s)
            print(f"[CREATED] Service: {data['name']}")
        else:
            print(f"[EXISTS] Service: {data['name']}")

    db.session.commit()
    print("\nAll default services are ready in Supabase!")
