import pytest

from aggregator.sanitizer import sanitize_entry_content


def sanitize(value, base_url="https://example.com/posts/1"):
    content = dict(type="text/html", language="en", value=value)
    return sanitize_entry_content(content, base_url=base_url)["value"]


def test_returns_none_without_content():
    assert sanitize_entry_content(None, base_url="https://example.com/") is None


def test_keeps_type_and_language():
    content = dict(type="text/html", language="en", value="<p>Hello</p>")

    assert sanitize_entry_content(content, base_url=None) == dict(type="text/html", language="en", value="<div><p>Hello</p></div>")


@pytest.mark.parametrize(
    "value",
    [
        '<base href="https://attacker.example/">',
        "<script>alert(1)</script>",
        '<img src="x" onerror="alert(1)">',
        '<a href="javascript:alert(1)">link</a>',
        '<a href="JavaScript:alert(1)">link</a>',
        '<svg><a xlink:href="javascript:alert(1)">link</a></svg>',
        '<iframe src="https://attacker.example/"></iframe>',
        "<style>body { display: none }</style>",
        '<p style="background: url(javascript:alert(1))">text</p>',
    ],
    ids=["base", "script", "event-handler", "javascript-link", "javascript-link-mixed-case", "svg-javascript-link", "iframe", "style-tag", "style-attribute"],
)
def test_removes_dangerous_markup(value):
    sanitized = sanitize(value)

    for dangerous in ("<base", "attacker.example", "<script", "onerror", "javascript:", "<iframe", "<style", "style="):
        assert dangerous not in sanitized.lower()


def test_makes_relative_urls_absolute():
    sanitized = sanitize('<a href="/about">About</a><img src="images/photo.jpg">')

    assert sanitized == '<div><a href="https://example.com/about">About</a><img src="https://example.com/posts/images/photo.jpg"></div>'


def test_removes_tracking_pixels():
    sanitized = sanitize('<p>Text</p><img src="https://tracker.example/pixel.gif" width="1" height="1">')

    assert sanitized == "<div><p>Text</p></div>"
