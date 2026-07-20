from campaign.template_renderer import (
    extract_variables,
    missing_variables,
    render_body_html,
    render_template,
    strip_bold_markers,
)


def test_render_template_replaces_variables_case_insensitively():
    result = render_template("Hi {{name}}, welcome to {{Company}}.", {"Name": "John", "company": "Google"})
    assert result == "Hi John, welcome to Google."


def test_render_template_leaves_unknown_placeholders():
    result = render_template("Hi {{Name}}", {})
    assert result == "Hi {{Name}}"


def test_extract_variables():
    assert extract_variables("{{A}} and {{B}}") == ["A", "B"]


def test_missing_variables():
    assert missing_variables("{{Name}} {{Company}}", {"Name": "John"}) == ["Company"]


def test_strip_bold_markers():
    assert strip_bold_markers("Hi **John**, welcome") == "Hi John, welcome"


def test_render_body_html_converts_bold_and_newlines():
    html_body = render_body_html("Hi **John**\nWelcome")
    assert html_body == "Hi <strong>John</strong><br>\nWelcome"


def test_render_body_html_escapes_html_special_characters():
    html_body = render_body_html("Tom & Jerry <3")
    assert html_body == "Tom &amp; Jerry &lt;3"
