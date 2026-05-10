from flask import Blueprint, jsonify
from app.utils.sanitize import clean_input

debug_bp = Blueprint('debug', __name__)

@debug_bp.route('/api/debug/verify-xss')
def verify_xss():
    payload = "<script>alert(1)</script>"
    sanitized = clean_input(payload)
    return jsonify({
        "original": payload,
        "sanitized": sanitized,
        "is_safe": "<script>" not in sanitized
    })
