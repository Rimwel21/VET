from flask import Blueprint, request, jsonify
from datetime import datetime
from app.extensions import db
from app.models.report import Report
from app.models.user import User
from app.middleware.decorators import role_required

api_reports_bp = Blueprint('api_reports', __name__)


@api_reports_bp.route('', methods=['GET', 'POST'])
@role_required(['staff', 'admin'])
def reports(current_user_jwt):
    if request.method == 'GET':
        if current_user_jwt.role == 'admin':
            items = Report.query.order_by(Report.created_at.desc()).all()
        else:
            items = Report.query.filter_by(user_id=current_user_jwt.id, is_deleted=False).order_by(Report.created_at.desc()).all()


        return jsonify([{
            'id': r.id, 'title': r.title, 'category': r.category,
            'description': r.description, 'status': r.status,
            'admin_comment': r.admin_comment, 
            'admin_review_status': r.admin_review_status,
            'reviewed_by': r.reviewed_by,
            'reviewed_at': r.reviewed_at.strftime('%b %d, %Y %H:%M') if r.reviewed_at else None,
            'user_id': r.user_id,
            'staff_name': _staff_name(r.user_id),
            'created_at': r.created_at.strftime('%b %d, %Y'),
            'is_deleted': r.is_deleted,
            'edit_history': r.edit_history
        } for r in items]), 200


    data = request.get_json()
    if not data.get('title') or not data.get('description'):
        return jsonify({'error': 'Title and description are required'}), 400

    report = Report(
        title=data.get('title'),
        category=data.get('category', 'Other'),
        description=data.get('description'),
        user_id=current_user_jwt.id
    )
    db.session.add(report)
    db.session.commit()
    return jsonify({'message': 'Report submitted successfully'}), 201


@api_reports_bp.route('/<int:report_id>', methods=['PUT', 'DELETE'])
@role_required(['admin'])
def report_detail(current_user_jwt, report_id):
    report = db.session.get(Report, report_id)
    if not report:
        return jsonify({'error': 'Report not found'}), 404

    if request.method == 'PUT':
        data = request.get_json()
        
        new_status = data.get('status', report.status)
        new_comment = data.get('admin_comment', report.admin_comment or '')
        new_title = data.get('title', report.title)
        new_desc = data.get('description', report.description)
        
        # Detect if anything actually changed
        content_changed = (new_title != report.title or new_desc != report.description)
        feedback_changed = (new_comment != (report.admin_comment or ''))
        status_changed = (new_status != report.status)
        
        if content_changed or feedback_changed or status_changed:
            history_entry = {
                "title": report.title,
                "content": report.description,
                "admin_comment": report.admin_comment or '',
                "status": report.status,
                "edited_at": datetime.utcnow().isoformat(),
                "edited_by": "admin"
            }
            hist = list(report.edit_history) if report.edit_history else []
            hist.append(history_entry)
            report.edit_history = hist
        
        report.status = new_status
        report.admin_comment = new_comment
        report.admin_review_status = new_status
        report.title = new_title
        report.description = new_desc
        report.reviewed_by = current_user_jwt.id
        report.reviewed_at = datetime.utcnow()

        db.session.commit()
        return jsonify({'message': 'Report updated successfully'})

    # Soft Delete
    report.is_deleted = True
    report.deleted_by = current_user_jwt.id
    report.deleted_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Report deleted successfully (Soft Delete)'})



@api_reports_bp.route('/<int:report_id>/review', methods=['PUT'])
@role_required(['admin'])
def review_report(current_user_jwt, report_id):
    data = request.get_json()
    report = db.session.get(Report, report_id)
    if not report:
        return jsonify({'error': 'Report not found'}), 404

    report.admin_comment = data.get("comment")
    report.admin_review_status = data.get("status", "reviewed")
    # Also update main status for legacy UI compatibility
    report.status = data.get("status", "reviewed").title()
    report.reviewed_by = current_user_jwt.id
    report.reviewed_at = datetime.utcnow()

    db.session.commit()
    return jsonify({"message": "Report reviewed successfully"})


def _staff_name(user_id):
    user = db.session.get(User, user_id)
    return f"{user.first_name} {user.last_name}" if user else "Unknown"
