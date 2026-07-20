from services.gmail_service import _sanitize_header


def test_sanitize_header_collapses_embedded_newlines():
    assert _sanitize_header("Application for Product Manager Role\nat ABC") == (
        "Application for Product Manager Role at ABC"
    )


def test_sanitize_header_collapses_crlf_and_trims():
    assert _sanitize_header("  Hi\r\nThere  \n") == "Hi There"


def test_sanitize_header_leaves_normal_text_untouched():
    assert _sanitize_header("Welcome to Acme") == "Welcome to Acme"
