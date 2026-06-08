from unittest.mock import AsyncMock, patch

import pytest

from core.tools.software_assistant import SoftwareAssistantTool


@pytest.mark.asyncio
async def test_software_assistant_execute():
    tool = SoftwareAssistantTool()
    # Mock WebSearchTool to avoid actual web requests
    with patch(
        "core.tools.software_assistant.WebSearchTool.execute", new_callable=AsyncMock
    ) as mock_search:
        mock_search.return_value = "1. Result A\n2. Result B"
        result = await tool.execute(query="Photoshop")
        assert "Result A" in result
        mock_search.assert_called_once()
        assert "Photoshop" in mock_search.call_args.kwargs["query"]
