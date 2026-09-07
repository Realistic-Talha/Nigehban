"""Tests for PII redaction."""

from app.utils.pii_redaction import redact_all, redact_cnic, redact_phone


def test_redact_phone():
    text = "Call me at 03001234567"
    assert "[PHONE REDACTED]" in redact_phone(text)


def test_redact_cnic():
    text = "CNIC 35201-1234567-1"
    assert "[CNIC REDACTED]" in redact_cnic(text)


def test_redact_all():
    text = "03001234567 35201-1234567-1 test@example.com"
    out = redact_all(text)
    assert "[PHONE REDACTED]" in out
    assert "[CNIC REDACTED]" in out
    assert "[EMAIL REDACTED]" in out
