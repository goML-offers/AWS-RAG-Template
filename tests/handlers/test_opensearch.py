# UNIT TEST FOR OPENSEARCH SERVICE HANDLER

import pytest
from unittest.mock import patch, MagicMock
from src.handlers.opensearch import OpenSearchHandler


@pytest.fixture
def opensearch_handler():
    with patch("src.handlers.opensearch.OpenSearch") as mock_opensearch:
        handler = OpenSearchHandler(host="localhost", port=9200, service="es")
        yield handler, mock_opensearch


def test_opensearch_initialization(opensearch_handler):
    handler, mock_opensearch = opensearch_handler
    assert handler.opensearch_handler is not None
    mock_opensearch.assert_called_once()


def test_opensearch_query(opensearch_handler):
    handler, mock_opensearch = opensearch_handler

    # Mocking a search response
    mock_response = {"hits": {"hits": [{"_source": {"field": "value"}}]}}
    mock_opensearch.return_value.search.return_value = mock_response

    # Assuming you have a method called 'search' in your handler
    result = handler.opensearch_handler.search(index="test-index", body={})

    assert result == mock_response
