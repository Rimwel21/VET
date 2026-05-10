try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app import create_app
from app.extensions import db
from app.models.user import User

app = create_app()
with app.app_context():
    # Seed all known real accounts that existed before the Supabase migration
    users_to_seed = [
        # Real accounts restored from old database
        {"first_name": "Admin",       "last_name": "Vet",   "email": "adminvetclinic@gmail.com",   "role": "admin",  "password": "vetadminclinic1214", "contact": ""},
        {"first_name": "Veterinarian","last_name": "Staff", "email": "veterinarian123@gmail.com",  "role": "staff",  "password": "vet121516",          "contact": ""},
        {"first_name": "Pogi",        "last_name": "User",  "email": "pogi@gmail.com",             "role": "client", "password": "pogi12345",          "contact": ""},
    ]

    for data in users_to_seed:
        u = User.query.filter_by(email=data["email"]).first()
        if not u:
            u = User(
                first_name=data["first_name"],
                last_name=data["last_name"],
                email=data["email"],
                role=data["role"],
                is_active=True,
                contact=data.get("contact", "")
            )
            u.set_password(data["password"])
            db.session.add(u)
            print(f"[CREATED] {data['role']:8} -> {data['email']}  (password: {data['password']})")
        else:
            u.role = data["role"]
            u.is_active = True
            u.set_password(data["password"])
            print(f"[UPDATED] {data['role']:8} -> {data['email']}  (password: {data['password']})")

    db.session.commit()
    print("\nDone! All accounts are ready.")
