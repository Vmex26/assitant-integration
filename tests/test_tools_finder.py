import pytest
from core.tools.software_finder import SoftwareFinderTool

@pytest.mark.asyncio
async def test_finder_known_category():
    tool = SoftwareFinderTool()
    result = await tool.execute(category="web browser")
    assert "firefox" in result

@pytest.mark.asyncio
async def test_finder_unknown_category():
    tool = SoftwareFinderTool()
    result = await tool.execute(category="quantum computer")
    assert "not sure" in result.lower()
