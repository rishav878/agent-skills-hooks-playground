from app.core.redaction import SecretRedactor


def test_redact_api_key_header() -> None:
    redactor = SecretRedactor()
    result = redactor.redact({"Authorization": "Bearer sk-abc123def456ghi789jkl"})
    assert "***REDACTED***" in result["Authorization"]


def test_redact_google_api_key() -> None:
    redactor = SecretRedactor()
    result = redactor.redact({"api_key": "AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"})
    assert "***REDACTED***" in result["api_key"]


def test_redact_nested_dict() -> None:
    redactor = SecretRedactor()
    data = {
        "config": {
            "api_key": "sk-abcdefghijklmnopqrstuvwxyz123456",
            "model": "gpt-4",
        }
    }
    result = redactor.redact(data)
    assert "***REDACTED***" in result["config"]["api_key"]
    assert result["config"]["model"] == "gpt-4"


def test_redact_none() -> None:
    redactor = SecretRedactor()
    assert redactor.redact(None) is None


def test_redact_plain_data_no_secrets() -> None:
    redactor = SecretRedactor()
    data = {"query": "hello", "count": 42}
    result = redactor.redact(data)
    assert result == data
