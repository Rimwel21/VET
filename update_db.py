from app import create_app
from app.extensions import db
from sqlalchemy import text

def add_columns():
    app = create_app()
    with app.app_context():
        try:
            print("Adding 'admin_review_status' column...")
            db.session.execute(text("ALTER TABLE reports ADD COLUMN admin_review_status VARCHAR(50) DEFAULT 'pending';"))
            db.session.commit()
            print("Success!")
        except Exception as e:
            db.session.rollback()
            print(f"Skipped admin_review_status (might already exist): {e}")

        try:
            print("Adding 'reviewed_by' column...")
            db.session.execute(text("ALTER TABLE reports ADD COLUMN reviewed_by INTEGER REFERENCES users(id);"))
            db.session.commit()
            print("Success!")
        except Exception as e:
            db.session.rollback()
            print(f"Skipped reviewed_by (might already exist): {e}")

        try:
            print("Adding 'reviewed_at' column...")
            db.session.execute(text("ALTER TABLE reports ADD COLUMN reviewed_at TIMESTAMP;"))
            db.session.commit()
            print("Success!")
        except Exception as e:
            db.session.rollback()
            print(f"Skipped reviewed_at (might already exist): {e}")

        print("Database updated successfully! You can now restart your server.")

if __name__ == "__main__":
    add_columns()
