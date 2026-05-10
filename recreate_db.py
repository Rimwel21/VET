from app import create_app
from app.extensions import db

def recreate_db():
    app = create_app()
    with app.app_context():
        print("Dropping all tables...")
        db.drop_all()
        print("Creating all tables with new schema...")
        db.create_all()
        print("Database updated successfully! You can now restart the server.")

if __name__ == "__main__":
    recreate_db()
