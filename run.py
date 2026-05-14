import os
from dotenv import load_dotenv

# load_dotenv must be called BEFORE importing the app to ensure config picks up .env values
load_dotenv()

from app import create_app
from app.extensions import db
from sqlalchemy import text

app = create_app(os.getenv('FLASK_ENV', 'default'))

# Auto-apply database schema updates
with app.app_context():
    try:
        # Ensure contact_messages table exists
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS contact_messages (
                id SERIAL PRIMARY KEY,
                name VARCHAR(120) NOT NULL,
                email VARCHAR(120) NOT NULL,
                subject VARCHAR(200),
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        # New audit system columns for reports
        db.session.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS admin_review_status VARCHAR(50) DEFAULT 'pending';"))
        db.session.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS reviewed_by INTEGER REFERENCES users(id);"))
        db.session.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP;"))
        db.session.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;"))
        db.session.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS deleted_by INTEGER REFERENCES users(id);"))
        db.session.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP;"))
        db.session.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS edit_history JSON DEFAULT '[]'::json;"))
        
        db.session.commit()
        print("Database schema successfully verified/updated (including contact_messages).")
    except Exception as e:
        db.session.rollback()
        print(f"Schema verification note: {e}")


if __name__ == '__main__':
    # host='0.0.0.0' allows external access (essential for ngrok/mobile testing)
    app.run(host='0.0.0.0', port=5000, debug=True)
