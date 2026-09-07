"""PII redaction utilities — mask phone numbers, CNIC, and email addresses."""

import re

# Pakistani phone patterns (local and international format)
_PHONE_PATTERN = re.compile(
    r"(?:\+92|0092|0)?3[0-9]{2}[-\s]?[0-9]{7}"  # mobile
    r"|(?:\+92|0092|0)?[2-9][0-9]{1,4}[-\s]?[0-9]{6,7}"  # landline
)

# Pakistani CNIC: 13 digits in XXXXX-XXXXXXX-X format
_CNIC_PATTERN = re.compile(r"[0-9]{5}-?[0-9]{7}-?[0-9]{1}")

# Email addresses
_EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)


def redact_phone(text: str) -> str:
    """Replace phone numbers with [PHONE REDACTED]."""
    return _PHONE_PATTERN.sub("[PHONE REDACTED]", text)


def redact_cnic(text: str) -> str:
    """Replace CNIC numbers with [CNIC REDACTED]."""
    return _CNIC_PATTERN.sub("[CNIC REDACTED]", text)


def redact_email(text: str) -> str:
    """Replace email addresses with [EMAIL REDACTED]."""
    return _EMAIL_PATTERN.sub("[EMAIL REDACTED]", text)


def redact_all(text: str) -> str:
    """Apply all PII redaction patterns to the given text."""
    text = redact_cnic(text)
    text = redact_phone(text)
    text = redact_email(text)
    return text
