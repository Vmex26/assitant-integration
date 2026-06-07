from utils.helpers import (
    format_api_error,
    format_file_size,
    is_image_file,
    is_text_file,
    safe_filename,
    truncate_text,
)


def test_truncate_text_short():
    assert truncate_text("Hello", 100) == "Hello"


def test_truncate_text_long():
    result = truncate_text("Hello World", 8)
    assert result == "Hello..."


def test_truncate_text_custom_suffix():
    result = truncate_text("Hello World", 8, suffix="!!")
    assert result == "Hello !!"


def test_safe_filename_normal():
    assert safe_filename("hello.txt") == "hello.txt"


def test_safe_filename_special_chars():
    assert safe_filename("hello/world:test") == "hello_world_test"


def test_safe_filename_empty():
    assert safe_filename("") == "untitled"


def test_format_file_size_bytes():
    assert format_file_size(500) == "500.0 B"


def test_format_file_size_kb():
    result = format_file_size(2048)
    assert "KB" in result


def test_format_file_size_mb():
    result = format_file_size(1048576)
    assert "MB" in result


def test_format_file_size_gb():
    result = format_file_size(1073741824)
    assert "GB" in result


def test_format_file_size_tb():
    result = format_file_size(1099511627776)
    assert "TB" in result


def test_is_image_file():
    assert is_image_file("photo.jpg") is True
    assert is_image_file("photo.png") is True
    assert is_image_file("document.pdf") is False


def test_is_text_file():
    assert is_text_file("main.py") is True
    assert is_text_file("readme.md") is True


def test_format_api_error_429():
    result = format_api_error("429 Too Many Requests")
    assert "Quota exceeded" in result
    assert "429" in result or "quota" in result.lower()


def test_format_api_error_403():
    result = format_api_error("403 Forbidden")
    assert "Access denied" in result


def test_format_api_error_401():
    result = format_api_error("401 Invalid API key")
    assert "Invalid credentials" in result


def test_format_api_error_timeout():
    result = format_api_error("Request timed out")
    assert "timed out" in result


def test_format_api_error_connection():
    result = format_api_error("connection refused")
    assert "Connection failed" in result


def test_format_api_error_generic():
    result = format_api_error("Something unexpected happened")
    assert "Error" in result
