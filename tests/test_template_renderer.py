from campaign.template_renderer import extract_variables, missing_variables, render_template


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
