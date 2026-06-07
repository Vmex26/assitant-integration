import logging

from core.logger import get_logger, set_verbose


def test_get_logger_returns_logger():
    logger = get_logger("test")
    assert isinstance(logger, logging.Logger)


def test_get_logger_default_level():
    get_logger("test_level")
    root = logging.getLogger("assistant")
    assert root.level == logging.INFO


def test_set_verbose_enables_debug():
    set_verbose(True)
    root = logging.getLogger("assistant")
    assert root.level == logging.DEBUG


def test_set_verbose_disables_debug():
    set_verbose(True)
    set_verbose(False)
    root = logging.getLogger("assistant")
    assert root.level == logging.INFO


def test_get_logger_naming():
    logger = get_logger("mymodule")
    assert logger.name == "assistant.mymodule"
