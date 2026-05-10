from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.extensions import db
from app.models.user import User

app = create_app()
with app.app_context():
    u = User.query.filter_by(email="admin@vetsync.com").first()
    if not u:
        u = User(first_name="Admin", last_name="User", email="admin@vetsync.com", role="admin")
        u.set_password("admin123")
        db.session.add(u)
        db.session.commit()
        print("Admin created")
    else:
        u.role = "admin"
        u.set_password("admin123")
        db.session.commit()
        print("Admin updated")
