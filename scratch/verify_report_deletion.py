import sys
import os

# Add parent directory to path so app can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from run import app
from app.extensions import db
from app.models.user import User
from app.models.report import Report
from app.models.audit_log import AuditLog

def verify_all():
    print("=== Verification Script Started ===")
    with app.app_context():
        # 1. Ensure test admin and staff users exist
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            admin = User(
                first_name="Admin",
                last_name="Test",
                email="admin_test@vetsync.com",
                role="admin",
                privacy_consent=True
            )
            admin.set_password("adminpass")
            db.session.add(admin)
            db.session.commit()
            print(f"Created test admin: {admin.email}")
        else:
            print(f"Using existing admin: {admin.email}")

        staff = User.query.filter_by(role='staff').first()
        if not staff:
            staff = User(
                first_name="Staff",
                last_name="Test",
                email="staff_test@vetsync.com",
                role="staff",
                privacy_consent=True
            )
            staff.set_password("staffpass")
            db.session.add(staff)
            db.session.commit()
            print(f"Created test staff: {staff.email}")
        else:
            print(f"Using existing staff: {staff.email}")

        # 2. Create a test report
        report_title = "Verification Test Report Title"
        report_desc = "Verification Test Report Body Content"
        report = Report(
            title=report_title,
            category="Incident",
            description=report_desc,
            user_id=staff.id
        )
        db.session.add(report)
        db.session.commit()
        report_id = report.id
        print(f"Created test report ID {report_id}: '{report_title}'")

        # 3. Verify report is visible in lists
        client = app.test_client()

        # Generate fake session credentials to satisfy verify_request_safety and CSRF shields
        csrf_token_val = "test_csrf_token_value_1234567890"
        ua_val = "Werkzeug/TestClient"
        
        with client.session_transaction() as sess:
            sess['user_id'] = admin.id
            sess['ip'] = '127.0.0.1'
            sess['user_agent'] = ua_val
            sess['_csrf_token'] = csrf_token_val
        
        headers = {
            'User-Agent': ua_val,
            'X-CSRF-Token': csrf_token_val,
            'Accept': 'application/json'
        }

        # Test 1: GET `/api/v1/reports` lists active reports
        resp = client.get('/api/v1/reports', headers=headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        reports_list = resp.get_json()
        matching_reports = [r for r in reports_list if r['id'] == report_id]
        assert len(matching_reports) == 1, "Test report should be present in API report list"
        print("Success: Test report is present in GET reports list.")

        # Test 2: DELETE the report via API (sending a reason)
        reason_payload = {"reason": "Verification testing deletion reason"}
        resp = client.delete(f'/api/v1/reports/{report_id}', json=reason_payload, headers=headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        print("Success: DELETE request responded with 200.")

        # Test 3: Verify database states (Hard deleted!)
        deleted_report = db.session.get(Report, report_id)
        assert deleted_report is None, f"Expected report ID {report_id} to be completely removed from DB"
        print("Success: Report is permanently deleted from the database table.")

        # Test 4: Verify Audit Log has record of deletion with reason but no body content
        deleted_log = AuditLog.query.filter(
            AuditLog.action_type == 'Report Deleted',
            AuditLog.description.like(f"Deleted report ID {report_id}%")
        ).first()
        assert deleted_log is not None, "Expected an audit log entry for the deleted report"
        print(f"Audit Log description: {deleted_log.description}")
        assert "Verification testing deletion reason" in deleted_log.description, "Expected reason in description"
        assert report_desc not in deleted_log.description, "Expected report description/body to be excluded from audit log"
        print("Success: Audit log entry exists, contains reason, and excludes report description.")

        # Test 5: Verify direct GET `/api/v1/reports/<id>` returns 410 with the correct message
        resp = client.get(f'/api/v1/reports/{report_id}', headers=headers)
        assert resp.status_code == 410, f"Expected 410, got {resp.status_code}"
        err_msg = resp.get_json().get('error')
        assert err_msg == "This report has been deleted and is no longer available.", f"Unexpected error message: {err_msg}"
        print("Success: Direct API access of deleted ID returns 410 Gone with correct message.")

        # Test 6: Verify direct POST to edit route returns 410 with the correct message
        # Change session to staff user since edit_report is @staff_required
        with client.session_transaction() as sess:
            sess['user_id'] = staff.id
            sess['ip'] = '127.0.0.1'
            sess['user_agent'] = ua_val
            sess['_csrf_token'] = csrf_token_val
        resp = client.post(f'/staff/reports/edit/{report_id}', json={"title": "new", "content": "new"}, headers=headers)
        assert resp.status_code == 410, f"Expected 410 for edit POST on deleted report, got {resp.status_code}"
        err_msg_edit = resp.get_json().get('error')
        assert err_msg_edit == "This report has been deleted and is no longer available.", f"Unexpected edit error message: {err_msg_edit}"
        print("Success: Direct edit route POST on deleted ID returns 410 Gone with correct message.")

        print("=== All Verification Tests Passed Successfully ===")

if __name__ == '__main__':
    verify_all()
