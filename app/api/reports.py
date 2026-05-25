from flask import Blueprint, request, jsonify
from datetime import datetime
from app.extensions import db
from app.models.report import Report
from app.models.user import User
from app.middleware.decorators import role_required
from app.utils.validation import FieldSpec, ValidationError, validate_fields

api_reports_bp = Blueprint('api_reports', __name__)


@api_reports_bp.route('', methods=['GET', 'POST'])
@role_required(['staff', 'admin'])
def reports(current_user_jwt):
    if request.method == 'GET':
        if current_user_jwt.role == 'admin':
            items = Report.query.filter_by(is_deleted=False).order_by(Report.created_at.desc()).all()
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


    data = request.get_json() or {}
    try:
        payload = validate_fields(data, {
            'title': FieldSpec(required=True, max_length=150),
            'category': FieldSpec(required=False, max_length=50),
            'description': FieldSpec(required=True, max_length=4000, allow_newlines=True),
        })
    except ValidationError as exc:
        return jsonify({'error': exc.message, 'field': exc.field}), exc.code

    report = Report()
    report.title = payload['title']
    report.category = payload.get('category') or 'Other'
    report.description = payload['description']
    report.user_id = current_user_jwt.id
    db.session.add(report)
    db.session.commit()
    return jsonify({'message': 'Report submitted successfully'}), 201


@api_reports_bp.route('/<int:report_id>', methods=['GET', 'PUT', 'DELETE'])
@role_required(['staff', 'admin'])
def report_detail(current_user_jwt, report_id):
    report = db.session.get(Report, report_id)
    if not report:
        from app.models.audit_log import AuditLog
        deleted_log = AuditLog.query.filter(
            AuditLog.action_type == 'Report Deleted',
            AuditLog.description.like(f"Deleted report ID {report_id}%")
        ).first()
        if deleted_log:
            return jsonify({'error': 'This report has been deleted and is no longer available.'}), 410
        return jsonify({'error': 'Report not found'}), 404

    if request.method == 'GET':
        return jsonify({
            'id': report.id, 'title': report.title, 'category': report.category,
            'description': report.description, 'status': report.status,
            'admin_comment': report.admin_comment, 
            'admin_review_status': report.admin_review_status,
            'reviewed_by': report.reviewed_by,
            'reviewed_at': report.reviewed_at.strftime('%b %d, %Y %H:%M') if report.reviewed_at else None,
            'user_id': report.user_id,
            'staff_name': _staff_name(report.user_id),
            'created_at': report.created_at.strftime('%b %d, %Y'),
            'is_deleted': report.is_deleted,
            'edit_history': report.edit_history
        }), 200

    # Ensure only admin can modify/delete
    if current_user_jwt.role != 'admin':
        return jsonify({'error': 'Access denied: Admins only.'}), 403

    if request.method == 'PUT':
        data = request.get_json() or {}
        try:
            payload = validate_fields(data, {
                'status': FieldSpec(required=False, max_length=20, escape_html=False),
                'admin_comment': FieldSpec(required=False, max_length=4000, allow_newlines=True),
                'title': FieldSpec(required=False, max_length=150),
                'description': FieldSpec(required=False, max_length=4000, allow_newlines=True),
            })
        except ValidationError as exc:
            return jsonify({'error': exc.message, 'field': exc.field}), exc.code
        
        new_status = payload.get('status') or report.status
        new_comment = payload.get('admin_comment') if 'admin_comment' in data else (report.admin_comment or '')
        new_title = payload.get('title') or report.title
        new_desc = payload.get('description') or report.description
        
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

    # Hard Delete with Deletion Audit Log
    reason = None
    if request.is_json:
        try:
            data = request.get_json(silent=True) or {}
            reason = data.get('reason')
        except Exception:
            pass
    if not reason:
        reason = request.args.get('reason')

    reason_str = f" Reason: {reason}." if reason else " No reason provided."
    report_id = report.id
    report_title = report.title

    from app.utils.logger import log_action
    log_action(
        'Report Deleted',
        f"Deleted report ID {report_id} ('{report_title}').{reason_str}",
        user=current_user_jwt
    )

    db.session.delete(report)
    db.session.commit()
    return jsonify({'message': 'Report deleted successfully (Hard Delete)'})



@api_reports_bp.route('/<int:report_id>/review', methods=['PUT'])
@role_required(['admin'])
def review_report(current_user_jwt, report_id):
    data = request.get_json() or {}
    report = db.session.get(Report, report_id)
    if not report:
        return jsonify({'error': 'Report not found'}), 404

    try:
        payload = validate_fields(data, {
            'comment': FieldSpec(required=False, max_length=4000, allow_newlines=True),
            'status': FieldSpec(required=False, max_length=50, escape_html=False),
        })
    except ValidationError as exc:
        return jsonify({'error': exc.message, 'field': exc.field}), exc.code

    report.admin_comment = payload.get("comment")
    report.admin_review_status = payload.get("status") or "reviewed"
    # Also update main status for legacy UI compatibility
    report.status = (payload.get("status") or "reviewed").title()
    report.reviewed_by = current_user_jwt.id
    report.reviewed_at = datetime.utcnow()

    db.session.commit()
    return jsonify({"message": "Report reviewed successfully"})


def _staff_name(user_id):
    user = db.session.get(User, user_id)
    return f"{user.first_name} {user.last_name}" if user else "Unknown"
