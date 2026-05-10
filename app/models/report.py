from datetime import datetime
from app.extensions import db


class Report(db.Model):
    __tablename__ = 'reports'

    id                  = db.Column(db.Integer, primary_key=True)
    title               = db.Column(db.String(150), nullable=False)
    category            = db.Column(db.String(50),  nullable=False)
    description         = db.Column(db.Text,        nullable=False)
    status              = db.Column(db.String(20),  default='Pending')  # Pending, Reviewed, Resolved
    admin_comment       = db.Column(db.Text,        nullable=True)
    admin_review_status = db.Column(db.String(50),  default="pending")
    reviewed_by         = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at         = db.Column(db.DateTime,    nullable=True)
    user_id             = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at          = db.Column(db.DateTime,    default=datetime.utcnow)

    # Audit Tracking Fields
    is_deleted          = db.Column(db.Boolean,     default=False)
    deleted_by          = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    deleted_at          = db.Column(db.DateTime,    nullable=True)
    edit_history        = db.Column(db.JSON,        default=list)

