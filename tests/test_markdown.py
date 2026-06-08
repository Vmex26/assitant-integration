from gui.message_widget import markdown_to_html


def test_plain_text():
    result = markdown_to_html("Hello world")
    assert "<p>Hello world</p>" in result


def test_bold():
    result = markdown_to_html("**bold**")
    assert "<strong>bold</strong>" in result


def test_italic():
    result = markdown_to_html("*italic*")
    assert "<em>italic</em>" in result


def test_bold_italic():
    result = markdown_to_html("***both***")
    assert "<strong><em>both</em></strong>" in result


def test_inline_code():
    result = markdown_to_html("Use `code` here")
    assert "<code " in result
    assert ">code</code>" in result


def test_code_block():
    result = markdown_to_html("```python\nprint('hello')\n```")
    assert "<pre " in result
    assert 'class="language-python"' in result
    assert "print" in result


def test_code_block_no_lang():
    result = markdown_to_html("```\nplain code\n```")
    assert "<pre " in result
    assert "<code>" in result or "<code " in result


def test_header_h1():
    result = markdown_to_html("# Title")
    assert "<h1 " in result
    assert ">Title</h1>" in result


def test_header_h2():
    result = markdown_to_html("## Section")
    assert "<h2 " in result
    assert ">Section</h2>" in result


def test_header_h3():
    result = markdown_to_html("### Subsection")
    assert "<h3 " in result
    assert ">Subsection</h3>" in result


def test_link():
    result = markdown_to_html("[click](https://example.com)")
    assert '<a href="https://example.com"' in result
    assert ">click</a>" in result


def test_unordered_list():
    result = markdown_to_html("- item1\n- item2")
    assert "<ul " in result
    assert "<li " in result
    assert ">item1</li>" in result
    assert ">item2</li>" in result


def test_ordered_list():
    result = markdown_to_html("1. first\n2. second")
    assert "<ol " in result
    assert "<li " in result
    assert ">first</li>" in result


def test_blockquote():
    result = markdown_to_html("> quoted text")
    assert "<blockquote " in result
    assert ">quoted text</blockquote>" in result


def test_horizontal_rule():
    result = markdown_to_html("---")
    assert "<hr " in result or "<hr>" in result


def test_paragraphs():
    result = markdown_to_html("First paragraph.\n\nSecond paragraph.")
    assert "<p>First paragraph.</p>" in result
    assert "<p>Second paragraph.</p>" in result


def test_html_is_escaped():
    result = markdown_to_html("<script>alert('xss')</script>")
    assert "&lt;script&gt;" in result
    assert "<script>" not in result
