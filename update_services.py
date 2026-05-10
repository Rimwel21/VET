import os
from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.extensions import db
from app.models.service import Service

app = create_app(os.getenv('FLASK_ENV', 'default'))

SERVICES_DATA = [
    {
        "name": "General Checkup",
        "icon": "🩺",
        "desc": "Comprehensive health examination to assess your pet’s overall condition. Includes physical evaluation, weight monitoring, and early detection of potential health issues."
    },
    {
        "name": "Vaccination",
        "icon": "💉",
        "desc": "Protect your pet from common and serious diseases with scheduled vaccinations. Stay up to date with essential immunization plans recommended by veterinarians."
    },
    {
        "name": "Dental Care",
        "icon": "🦷",
        "desc": "Professional dental cleaning and oral health assessment to prevent plaque buildup, gum disease, and bad breath. Supports long-term dental health."
    },
    {
        "name": "Surgery",
        "icon": "🏥",
        "desc": "Safe and advanced surgical procedures performed by licensed veterinarians. Includes pre-operation assessment and post-surgery care monitoring."
    },
    {
        "name": "Grooming",
        "icon": "✂️",
        "desc": "Complete grooming services including bathing, trimming, nail care, and coat maintenance to keep your pet clean and comfortable."
    },
    {
        "name": "Emergency Care",
        "icon": "🚨",
        "desc": "Immediate veterinary assistance for critical and life-threatening situations. Designed for urgent care when your pet needs fast medical attention."
    }
]

with app.app_context():
    print("Updating clinical services...")
    
    # Track existing services by name to avoid duplicates
    existing_services = {s.name: s for s in Service.query.all()}
    
    for s_data in SERVICES_DATA:
        if s_data["name"] in existing_services:
            print(f"Updating: {s_data['name']}")
            s = existing_services[s_data["name"]]
            s.icon = s_data["icon"]
            s.desc = s_data["desc"]
        else:
            print(f"Adding: {s_data['name']}")
            s = Service(
                name=s_data["name"],
                icon=s_data["icon"],
                desc=s_data["desc"]
            )
            db.session.add(s)
    
    db.session.commit()
    print("✅ Services updated successfully without breaking database constraints!")
