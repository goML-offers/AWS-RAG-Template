import asyncio
import json
import os
import uuid
from datetime import datetime, timedelta
from typing import AsyncGenerator, Dict, List, Optional

import boto3
from dotenv import load_dotenv
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.memory import ChatMemoryBuffer

from src.utils.utils import load_yaml_config

load_dotenv()

script_dir = os.getcwd()
model_file_path = os.path.join(script_dir, "src", "config", "model_config.yaml")

# Load the configuration from the YAML file
model_config = load_yaml_config(model_file_path)


class BedrockServiceHandler:
    def __init__(self, region: str = "us-west-2"):
        self.model_config = model_config
        self.bedrock_client = boto3.client("bedrock-runtime", region_name=region)
        self.bedrock_agent_client = boto3.client("bedrock-agent-runtime", region_name=region)

        # Session management
        self.current_session_id = None
        self.session_start_time = None
        self.last_interaction_time = None
        self.session_timeout = timedelta(minutes=30)

        # Initialize chat memory
        self.memory = ChatMemoryBuffer.from_defaults(token_limit=2000)

        # Extract model configuration details
        self.model_id = self.model_config.get("modelId")
        self.inference_config = self.model_config.get("inferenceConfig", {})
        self.additional_model_request_fields = self.model_config.get(
            "additionalModelRequestFields", {}
        )
    
    
    def get_kb_id_by_name(self, kb_name: str) -> str:
        """Returns KB ID given a KB name"""
        try:
            response = self.bedrock_agent_client.list_knowledge_bases()
            for kb in response.get("knowledgeBaseSummaries", []):
                if kb["name"] == kb_name:
                    return kb["knowledgeBaseId"]
            raise ValueError(f"No KB found with name {kb_name}")
        except Exception as e:
            print(f"Error retrieving KB ID for {kb_name}: {e}")
            raise
    
    
    def retrieve_from_knowledge_base(self, knowledge_base_name: str, query: str) -> list:
        """
        Retrieve relevant context from Bedrock Knowledge Base
        Returns list of documents with content in format:
        [{'content': 'text from document'}, ...]
        """
        try:
            knowledge_base_id = self.get_kb_id_by_name(knowledge_base_name)
            response = self.bedrock_agent_client.retrieve(
                knowledgeBaseId=knowledge_base_id,
                retrievalQuery={'text': query},
                retrievalConfiguration={
                    'vectorSearchConfiguration': {
                        'numberOfResults': 3,  # Get top 3 results
                        'overrideSearchType': 'SEMANTIC'  # Use semantic search
                    }
                }
            )
            
            # Process results to match OpenSearch format
            processed_results = []
            for result in response.get('retrievalResults', []):
                try:
                    processed_results.append({
                        'content': result['content']['text']
                    })
                except KeyError:
                    continue
                    
            return processed_results
            
        except Exception as e:
            print(f"Knowledge base retrieval error: {str(e)}")
            return []

    def handle_session(
        self, session_token: Optional[str], query: Optional[str]
    ) -> Dict:
        """Handle session management based on input parameters"""
        # Case 1: Both parameters are blank - Stop session
        if not session_token and not query:
            self.stop_session()
            return {
                "status": "session_stopped",
                "message": "Session terminated due to blank parameters",
            }

        # Case 2: Both parameters are 'start_session' - Start new session
        if session_token == "start_session" and query == "start_session":
            new_session_id = self.start_new_session(force=True)
            return {
                "status": "session_started",
                "session_id": new_session_id,
                "message": "New session started",
            }

        # Case 3: Normal interaction - Update or start session as needed
        if self._should_start_new_session():
            self.start_new_session()
        self.update_session_activity()

        return {
            "status": "session_active",
            "session_id": self.current_session_id,
            "message": "Session is active",
        }

    def get_bedrock_embedding(self, text: str) -> List[float]:
        """Generate embeddings using Amazon Bedrock Titan."""
        body = json.dumps({"inputText": text})

        response = self.bedrock_client.invoke_model(
            modelId="amazon.titan-embed-text-v2:0", body=body
        )

        response_body = json.loads(response["body"].read())
        return response_body["embedding"]

    def get_chat_history(self) -> List[Dict]:
        """Get formatted chat history"""
        try:

            messages = self.memory.get()
            formatted_messages = []

            for msg in messages:
                formatted_messages.append(
                    {
                        "role": "user" if msg.role == MessageRole.USER else "assistant",
                        "content": msg.content,
                    }
                )

            return formatted_messages
        except Exception as e:
            print(f"Error getting chat history: {str(e)}")
            return []

    def update_session_activity(self):
        """Update the timestamp of the last interaction"""
        self.last_interaction_time = datetime.now()

    def _should_start_new_session(self) -> bool:
        """Check if a new session should be started"""
        if not self.current_session_id or not self.last_interaction_time:
            return True

        time_elapsed = datetime.now() - self.last_interaction_time
        return time_elapsed > self.session_timeout

    def reset_memory(self):
        """Reset the chat memory"""
        self.memory = ChatMemoryBuffer.from_defaults(token_limit=2000)
        print("Chat memory has been reset")

    def add_message(self, role: str, content: str):
        """Add a message to the chat history"""
        try:
            message = ChatMessage(role=MessageRole(role), content=content)
            self.memory.put(message)
        except Exception as e:
            print(f"Error adding message to memory: {str(e)}")

    def start_new_session(self, force: bool = False) -> str:
        """Start a new conversation session"""
        if force or self._should_start_new_session():
            self.current_session_id = str(uuid.uuid4())
            self.session_start_time = datetime.now()
            self.last_interaction_time = datetime.now()
            self.reset_memory()
            print(f"New session started: {self.current_session_id}")
        return self.current_session_id

    def stop_session(self):
        """Stop the current session"""
        self.current_session_id = None
        self.session_start_time = None
        self.last_interaction_time = None
        self.reset_memory()
        print("Session has been stopped")

    def get_session_info(self) -> Dict:
        """Get current session information"""
        if not self.current_session_id:
            return {"status": "No active session"}

        return {
            "session_id": self.current_session_id,
            "start_time": (
                self.session_start_time.isoformat() if self.session_start_time else None
            ),
            "last_interaction": (
                self.last_interaction_time.isoformat()
                if self.last_interaction_time
                else None
            ),
            "message_count": len(self.get_chat_history()) if self.memory else 0,
            "session_age": (
                str(datetime.now() - self.session_start_time)
                if self.session_start_time
                else None
            ),
        }

    def format_messages(self, system_prompt: str, user_prompt: str) -> List[Dict]:
        """Format messages for Claude converse API"""
        messages = []

        # Add system prompt separately (will be handled in _send_single_response)
        if system_prompt:
            messages.append({"role": "system", "content": [{"text": system_prompt}]})

        # Add chat history
        chat_history = self.get_chat_history()
        for msg in chat_history:
            messages.append(
                {"role": msg["role"], "content": [{"text": msg["content"]}]}
            )

        # Add current user prompt
        messages.append({"role": "user", "content": [{"text": user_prompt}]})

        return messages

    def send_simple_prompt(self, system_prompt: str, user_prompt: str) -> str:
        """Send a simple prompt to Bedrock and get the response without any session changes."""
        try:
            # Prepare the system prompt
            system_prompt_formatted = [{"text": system_prompt}]

            # Prepare the conversation with the user prompt
            conversation = [{"role": "user", "content": [{"text": user_prompt}]}]

            # Send the request to Bedrock
            response = self.bedrock_client.converse(
                modelId=self.model_id,
                messages=conversation,
                inferenceConfig=self.inference_config,
                additionalModelRequestFields=self.additional_model_request_fields,
                system=system_prompt_formatted,
            )

            # Extract the response text
            result_text = response["output"]["message"]["content"][0]["text"]

            return result_text

        except Exception as e:
            print(f"Error in send_simple_prompt: {str(e)}")
            raise

    def send_prompts(
        self, system_prompt: str, user_prompt: str, session_token: Optional[str] = None
    ) -> str:
        """Send prompts to Bedrock with session handling using converse"""
        try:
            # Handle session based on input parameters
            session_status = self.handle_session(session_token, user_prompt)

            # If session is stopped or starting, return early
            if session_status["status"] in ["session_stopped", "session_started"]:
                return session_status["message"]

            # Format messages with chat history
            messages = self.format_messages(system_prompt, user_prompt)

            # Send request and get response
            response = self._send_single_response(messages, user_prompt)

            return response

        except Exception as e:
            print(f"Error in send_prompts: {str(e)}")
            self.stop_session()
            raise

    def _send_single_response(self, messages: List[Dict], user_prompt: str) -> str:
        """Send a single request and get complete response using converse"""
        try:
            # Extract system message
            system_prompt = None
            conversation = []

            # Separate system message and format conversation
            for msg in messages:
                if msg["role"] == "system":
                    system_prompt = [{"text": msg["content"][0]["text"]}]
                else:
                    conversation.append(
                        {
                            "role": msg["role"],
                            "content": [
                                {"text": msg["content"][0]["text"]}
                            ],  # Simplified content format
                        }
                    )

            response = self.bedrock_client.converse(
                modelId=self.model_id,
                messages=conversation,
                inferenceConfig=self.inference_config,
                additionalModelRequestFields=self.additional_model_request_fields,
                system=system_prompt,
            )
            print("LLM RESPONSE: ", response)

            # Extract the response text
            result_text = response["output"]["message"]["content"][0]["text"]

            # Update memory with the interaction
            self.add_message("user", user_prompt)
            self.add_message("assistant", result_text)
            self.update_session_activity()

            return result_text

        except Exception as e:
            print(f"Error in _send_single_response: {str(e)}")
            # print(f"Request body: {json.dumps(request_body, indent=2)}")
            raise

    async def send_streaming_prompt(
        self, system_prompt: str, user_prompt: str
    ) -> AsyncGenerator[str, None]:
        """
        Send a prompt to AWS Bedrock using the Messages API with streaming response.

        Args:
            system_prompt: The system prompt to guide the model
            user_prompt: The user prompt/query

        Yields:
            Chunks of the response as they are generated
        """
        try:
            # Format the request using the Messages API format
            request_body = {
                "anthropic_version": model_config["anthropicVersion"],
                "max_tokens": model_config["inferenceConfig"]["maxTokens"],
                "temperature": model_config["inferenceConfig"]["temperature"],
                "top_p": 0.9,
                "messages": [{"role": "user", "content": user_prompt}],
            }

            # Add system prompt if provided
            if system_prompt:
                request_body["system"] = system_prompt

            # Invoke the model with streaming enabled
            response = self.bedrock_client.invoke_model_with_response_stream(
                modelId=model_config["modelId"],  # Your specific model
                body=json.dumps(request_body),
            )

            # Get the streaming body
            stream = response.get("body")

            # Process the stream chunks
            for event in stream:
                if "chunk" in event:
                    chunk_data = json.loads(event["chunk"]["bytes"].decode("utf-8"))
                    # The structure is different in Messages API responses
                    if "delta" in chunk_data and "text" in chunk_data["delta"]:
                        yield chunk_data["delta"]["text"]
                # Add a small delay to avoid blocking the event loop
                await asyncio.sleep(0.001)

        except Exception as e:
            yield f"Error generating response: {str(e)}"
