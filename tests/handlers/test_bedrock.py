# UNIT TESTS FOR BEDROCK SERVICE HANDLER

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from src.handlers.bedrock import BedrockServiceHandler


@pytest.fixture
def mock_bedrock_client():
    with patch("boto3.client") as mock_client:
        mock_bedrock = Mock()
        mock_client.return_value = mock_bedrock
        yield mock_bedrock


@pytest.fixture
def bedrock_handler(mock_bedrock_client):
    handler = BedrockServiceHandler()
    handler.bedrock_client = mock_bedrock_client
    return handler


class TestBedrockServiceHandler:
    def test_handle_session_blank_params(self, bedrock_handler):
        """Test session handling when both parameters are blank"""
        result = bedrock_handler.handle_session(None, None)
        assert result["status"] == "session_stopped"
        assert "Session terminated" in result["message"]

    def test_handle_session_start_new(self, bedrock_handler):
        """Test starting a new session"""
        result = bedrock_handler.handle_session("start_session", "start_session")
        assert result["status"] == "session_started"
        assert "session_id" in result
        assert "New session started" in result["message"]

    def test_handle_session_active(self, bedrock_handler):
        """Test handling an active session"""
        bedrock_handler.start_new_session()
        result = bedrock_handler.handle_session("existing_session", "test_query")
        assert result["status"] == "session_active"
        assert "session_id" in result

    def test_get_bedrock_embedding(self, bedrock_handler, mock_bedrock_client):
        """Test getting embeddings from Bedrock"""
        mock_response = {"body": Mock(read=lambda: '{"embedding": [0.1, 0.2, 0.3]}')}
        mock_bedrock_client.invoke_model.return_value = mock_response

        result = bedrock_handler.get_bedrock_embedding("test text")
        assert result == [0.1, 0.2, 0.3]
        mock_bedrock_client.invoke_model.assert_called_once()

        # Verify correct model and parameters were used
        call_args = mock_bedrock_client.invoke_model.call_args[1]
        assert call_args["modelId"] == "amazon.titan-embed-text-v2:0"

    def test_send_simple_prompt(self, bedrock_handler, mock_bedrock_client):
        """Test sending a simple prompt without session management"""
        mock_response = {
            "output": {"message": {"content": [{"text": "test response"}]}}
        }
        mock_bedrock_client.converse.return_value = mock_response

        result = bedrock_handler.send_simple_prompt("system prompt", "user prompt")
        assert result == "test response"
        mock_bedrock_client.converse.assert_called_once()

    def test_send_prompts_with_session(self, bedrock_handler, mock_bedrock_client):
        """Test sending prompts with session management"""
        mock_response = {
            "output": {"message": {"content": [{"text": "test response"}]}}
        }
        mock_bedrock_client.converse.return_value = mock_response

        result = bedrock_handler.send_prompts(
            system_prompt="system test",
            user_prompt="user test",
            session_token="test_session",
        )
        assert result == "test response"
        assert bedrock_handler.current_session_id is not None

    def test_get_chat_history(self, bedrock_handler):
        """Test retrieving chat history"""
        bedrock_handler.add_message("user", "test message")
        bedrock_handler.add_message("assistant", "test response")

        history = bedrock_handler.get_chat_history()
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "test message"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "test response"

    def test_session_timeout(self, bedrock_handler):
        """Test session timeout behavior"""
        bedrock_handler.start_new_session()
        bedrock_handler.last_interaction_time = datetime.now() - timedelta(minutes=31)
        assert bedrock_handler._should_start_new_session() is True

    def test_reset_memory(self, bedrock_handler):
        """Test memory reset functionality"""
        bedrock_handler.add_message("user", "test message")
        bedrock_handler.reset_memory()
        history = bedrock_handler.get_chat_history()
        assert len(history) == 0

    def test_get_session_info(self, bedrock_handler):
        """Test retrieving session information"""
        bedrock_handler.start_new_session()
        session_info = bedrock_handler.get_session_info()

        assert "session_id" in session_info
        assert "start_time" in session_info
        assert "last_interaction" in session_info
        assert "message_count" in session_info
        assert "session_age" in session_info

    def test_format_messages(self, bedrock_handler):
        """Test message formatting for API requests"""
        bedrock_handler.add_message("user", "previous message")
        messages = bedrock_handler.format_messages(
            system_prompt="system test", user_prompt="user test"
        )

        assert len(messages) == 3  # system + previous + current
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"][0]["text"] == "user test"
