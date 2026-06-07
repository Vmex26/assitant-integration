from gui.message_widget import MarkdownTextBrowser


def md_to_html(text: str) -> str:
    """Helper to call the static markdown converter."""
    return MarkdownTextBrowser._markdown_to_html(text)


def test_plain_text():
    result = md_to_html("Hello world")
    assert "<p>Hello world</p>" in result


def test_bold():
    result = md_to_html("**bold**")
    assert "<strong>bold</strong>" in result


def test_italic():
    result = md_to_html("*italic*")
    assert "<em>italic</em>" in result


def test_bold_italic():
    result = md_to_html("***both***")
    assert "<strong><em>both</em></strong>" in result


def test_inline_code():
    result = md_to_html("Use `code` here")
    assert "<code>code</code>" in result


def test_code_block():
    result = md_to_html("```python\nprint('hello')\n```")
    assert '<pre><code class="language-python">' in result
    assert "print(&#x27;hello&#x27;)" in result


def test_code_block_no_lang():
    result = md_to_html("```\nplain code\n```")
    assert "<pre><code>" in result


def test_header_h1():
    result = md_to_html("# Title")
    assert "<h1>Title</h1>" in result


def test_header_h2():
    result = md_to_html("## Section")
    assert "<h2>Section</h2>" in result


def test_header_h3():
    result = md_to_html("### Subsection")
    assert "<h3>Subsection</h3>" in result


def test_link():
    result = md_to_html("[click](https://example.com)")
    assert '<a href="https://example.com">click</a>' in result


def test_unordered_list():
    result = md_to_html("- item1\n- item2")
    assert "<ul>" in result
    assert "<li>item1</li>" in result
    assert "<li>item2</li>" in result


def test_ordered_list():
    result = md_to_html("1. first\n2. second")
    assert "<ol>" in result
    assert "<li>first</li>" in result


def test_blockquote():
    result = md_to_html("> quoted text")
    assert "<blockquote>quoted text</blockquote>" in result


def test_horizontal_rule():
    result = md_to_html("---")
    assert "<hr>" in result


def test_paragraphs():
    result = md_to_html("First paragraph.\n\nSecond paragraph.")
    assert "<p>First paragraph.</p>" in result
    assert "<p>Second paragraph.</p>" in result


def test_html_is_escaped():
    result = md_to_html("<script>alert('xss')</script>")
    assert "&lt;script&gt;" in result
    assert "<script>" not in result
