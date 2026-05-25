import re
from dataclasses import dataclass
from html import escape as html_escape

from flask import current_app, request
from werkzeug.datastructures import CombinedMultiDict, ImmutableMultiDict
from werkzeug.utils import secure_filename

# SECURITY: Central validation and filtering layer for VetSync.
# This module screens user-controlled data before business logic runs.
# It protects forms, JSON APIs, chatbot input, and file uploads from common
# injection payloads while still allowing normal names, notes, reports, and messages.

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .'\-]*$")
PHONE_RE = re.compile(r"^[0-9+\-() ]{7,30}$")
FIELD_RE = re.compile(r"^[A-Za-z0-9_.\-\[\]]+$")
CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
WHITESPACE_RE = re.compile(r"[ \t]+")

SUSPICIOUS_PATTERNS = {
    "xss": [
        re.compile(r"<\s*script\b", re.I),
        re.compile(r"<\s*/\s*script\s*>", re.I),
        re.compile(r"javascript\s*:", re.I),
        re.compile(r"\bon\w+\s*=", re.I),
        re.compile(r"<\s*(iframe|object|embed|svg|math)\b", re.I),
        re.compile(r"data\s*:\s*text/html", re.I),
    ],
    "sqli": [
        re.compile(r"(?:\bunion\b\s+\bselect\b|\bselect\b.+\bfrom\b)", re.I),
        re.compile(r"(?:\bdrop\b|\binsert\b|\bdelete\b|\bupdate\b)\s+\b(table|from|into|set)\b", re.I),
        re.compile(r"(?:'|\")\s*or\s*(?:'|\")?1(?:'|\")?\s*=\s*(?:'|\")?1", re.I),
        re.compile(r"--|/\*|\*/", re.I),
        re.compile(r"\binformation_schema\b|\bsleep\s*\(", re.I),
    ],
    "command": [
        re.compile(r"(?:;|&&|\|\|)\s*(?:rm|del|drop|curl|wget|bash|sh|cmd|powershell|python|php|nc|netcat)\b", re.I),
        re.compile(r"`[^`]+`"),
        re.compile(r"\$\([^)]{1,200}\)"),
        re.compile(r"\b(?:cmd(?:\.exe)?|powershell(?:\.exe)?|/bin/sh|/bin/bash)\b", re.I),
    ],
    "traversal": [
        re.compile(r"(?:\.\./|\.\.\\|%2e%2e%2f|%2e%2e\\)", re.I),
        re.compile(r"\b(?:etc/passwd|boot\.ini|win\.ini)\b", re.I),
    ],
    "template": [
        re.compile(r"\{\{.*\}\}|\{%.*%\}", re.I),
        re.compile(r"<\?php", re.I),
    ],
}

SAFE_PATTERN_FIELDS = {
    "csrf_token",
    "token",
    "reset_token",
    "access_token",
    "jwt",
    "p256dh",
    "auth",
    "endpoint",
    "otp",
    "password",
    "new_password",
    "confirm_password",
    "re_password",
}

SAFE_FILE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf", "txt", "csv"}
SAFE_FILE_MIME_PREFIXES = ("image/", "text/")
SAFE_FILE_MIME_EXACT = {"application/pdf", "text/csv"}


class ValidationError(ValueError):
    def __init__(self, message, field=None, code=400):
        super().__init__(message)
        self.message = message
        self.field = field
        self.code = code


@dataclass(frozen=True)
class FieldSpec:
    kind: str = "text"
    required: bool = False
    max_length: int | None = None
    allow_newlines: bool = False
    escape_html: bool = True
    choices: tuple[str, ...] | None = None


def normalize_text(value, *, allow_newlines=False):
    # SECURITY: Input normalization removes control characters and collapses unsafe whitespace.
    # This helps make downstream validation deterministic and reduces payload obfuscation tricks.
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    value = CONTROL_CHARS_RE.sub("", value)
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    if not allow_newlines:
        value = value.replace("\n", " ")
    value = WHITESPACE_RE.sub(" ", value)
    return value.strip()


def sanitize_text(value, *, allow_newlines=False, escape_html=True):
    cleaned = normalize_text(value, allow_newlines=allow_newlines)
    return html_escape(cleaned) if escape_html else cleaned


def ensure_safe_text(value, *, field="input", allow_newlines=False, max_length=None):
    # SECURITY: Shared guard for free-text input.
    # Enforces length limits and runs exploit-pattern detection before the value is accepted.
    cleaned = normalize_text(value, allow_newlines=allow_newlines)
    if max_length and len(cleaned) > max_length:
        raise ValidationError(f"{field.replace('_', ' ').title()} is too long.", field=field)
    detect_malicious_content(cleaned, field=field)
    return cleaned


def validate_name(value, *, field, max_length=80):
    cleaned = ensure_safe_text(value, field=field, max_length=max_length)
    if not cleaned:
        raise ValidationError(f"{field.replace('_', ' ').title()} is required.", field=field)
    if not NAME_RE.fullmatch(cleaned):
        raise ValidationError(f"Invalid {field.replace('_', ' ')}.", field=field)
    return cleaned


def validate_email(value, *, field="email"):
    cleaned = ensure_safe_text(value, field=field, max_length=120).lower()
    if not EMAIL_RE.fullmatch(cleaned):
        raise ValidationError("Please enter a valid email address.", field=field)
    return cleaned


def validate_phone(value, *, field="contact", required=False):
    cleaned = ensure_safe_text(value, field=field, max_length=30)
    if not cleaned and not required:
        return ""
    if not PHONE_RE.fullmatch(cleaned):
        raise ValidationError(f"Invalid {field.replace('_', ' ')}.", field=field)
    return cleaned


def validate_password(value, *, field="password", min_length=8, max_length=128):
    if not isinstance(value, str):
        value = str(value or "")
    if len(value) < min_length:
        raise ValidationError(f"{field.replace('_', ' ').title()} must be at least {min_length} characters.", field=field)
    if len(value) > max_length:
        raise ValidationError(f"{field.replace('_', ' ').title()} is too long.", field=field)
    detect_malicious_content(value, field=field)
    return value


def validate_choice(value, *, field, choices):
    cleaned = ensure_safe_text(value, field=field, max_length=80)
    if cleaned not in choices:
        raise ValidationError(f"Invalid {field.replace('_', ' ')} selected.", field=field)
    return cleaned


def validate_text_field(value, spec: FieldSpec, *, field):
    cleaned = ensure_safe_text(
        value,
        field=field,
        allow_newlines=spec.allow_newlines,
        max_length=spec.max_length,
    )
    if spec.required and not cleaned:
        raise ValidationError(f"{field.replace('_', ' ').title()} is required.", field=field)
    if not cleaned and not spec.required and spec.kind != "password":
        return ""
    if spec.kind == "email":
        return validate_email(cleaned, field=field)
    if spec.kind == "name":
        return validate_name(cleaned, field=field, max_length=spec.max_length or 80)
    if spec.kind == "phone":
        return validate_phone(cleaned, field=field, required=spec.required)
    if spec.kind == "password":
        return validate_password(value, field=field)
    if spec.kind == "choice":
        return validate_choice(cleaned, field=field, choices=spec.choices or ())
    return sanitize_text(cleaned, allow_newlines=spec.allow_newlines, escape_html=spec.escape_html)


def validate_fields(source, specs):
    normalized = {}
    for field, spec in specs.items():
        raw = source.get(field, "")
        normalized[field] = validate_text_field(raw, spec, field=field)
    return normalized


def detect_malicious_content(value, *, field="input"):
    # SECURITY: High-confidence exploit detection.
    # Blocks patterns associated with XSS, SQL injection, command injection,
    # traversal, and template/code execution attempts.
    if not isinstance(value, str) or not value:
        return

    field_name = (field or "").lower()
    if field_name and not FIELD_RE.fullmatch(field_name):
        raise ValidationError("Invalid request field name.", field=field)

    if field_name in SAFE_PATTERN_FIELDS:
        return

    sample = value[:500]
    for category, patterns in SUSPICIOUS_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(sample):
                raise ValidationError(
                    f"Suspicious content detected in {field.replace('_', ' ')}.",
                    field=field,
                    code=400,
                )


def validate_uploaded_file(file_storage):
    # SECURITY: File upload screening.
    # Restricts files by sanitized name, extension, and MIME type to reduce
    # malicious upload and disguised payload risks.
    filename = secure_filename(file_storage.filename or "")
    if not filename:
        raise ValidationError("Invalid uploaded file name.", field="file")

    if "." not in filename:
        raise ValidationError("Uploaded files must include a valid extension.", field="file")

    ext = filename.rsplit(".", 1)[1].lower()
    if ext not in SAFE_FILE_EXTENSIONS:
        raise ValidationError("This file type is not allowed.", field="file", code=415)

    mimetype = (file_storage.mimetype or "").lower()
    if not mimetype:
        raise ValidationError("Unable to verify uploaded file type.", field="file", code=415)
    if mimetype not in SAFE_FILE_MIME_EXACT and not mimetype.startswith(SAFE_FILE_MIME_PREFIXES):
        raise ValidationError("Suspicious file upload blocked.", field="file", code=415)


def validate_request_input_layers():
    # SECURITY: Global request inspection.
    # Applies request-size checks and scans query, form, JSON, and file inputs
    # before route handlers process the request.
    max_content_length = current_app.config.get("MAX_CONTENT_LENGTH")
    content_length = request.content_length or 0
    if max_content_length and content_length > max_content_length:
        raise ValidationError("Request payload is too large.", code=413)

    _scan_mapping(request.args)

    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        if request.form:
            _scan_mapping(request.form)
        if request.is_json:
            _scan_json(request.get_json(silent=True))
        if request.files:
            for _, file_storage in request.files.items():
                validate_uploaded_file(file_storage)


def _scan_mapping(mapping):
    if not mapping:
        return

    if isinstance(mapping, CombinedMultiDict):
        items = mapping.items(multi=True)
    elif isinstance(mapping, ImmutableMultiDict):
        items = mapping.items(multi=True)
    else:
        items = mapping.items()

    for field, value in items:
        if isinstance(value, str):
            detect_malicious_content(normalize_text(value, allow_newlines=True), field=field)


def _scan_json(value, *, path="json"):
    if isinstance(value, dict):
        for key, item in value.items():
            detect_malicious_content(str(key), field="json_key")
            _scan_json(item, path=str(key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _scan_json(item, path=f"{path}[{index}]")
    elif isinstance(value, str):
        detect_malicious_content(normalize_text(value, allow_newlines=True), field=path)
