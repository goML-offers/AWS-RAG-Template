import warnings
warnings.filterwarnings("ignore")
import os
import asyncio
import base64
import json
import uuid
from aws_sdk_bedrock_runtime.client import BedrockRuntimeClient, InvokeModelWithBidirectionalStreamOperationInput
from aws_sdk_bedrock_runtime.models import InvokeModelWithBidirectionalStreamInputChunk, BidirectionalInputPayloadPart
from aws_sdk_bedrock_runtime.config import Config, HTTPAuthSchemeResolver, SigV4AuthScheme
from smithy_aws_core.credentials_resolvers.environment import EnvironmentCredentialsResolver
from dotenv import load_dotenv

class NovaSonicHandler:
    def __init__(self, model_id='amazon.nova-sonic-v1:0', region='us-east-1'):
        self.model_id = model_id
        self.region = region
        self.client = None
        self.stream = None
        self.is_active = False
        self.prompt_name = str(uuid.uuid4())
        self.content_name = str(uuid.uuid4())
        self.audio_content_name = str(uuid.uuid4())
        self.audio_queue = asyncio.Queue()
        self.text_queue = asyncio.Queue()
        self.stream_closed = False
        self.role = None
        self.display_assistant_text = False
        self.response_processor = None

    def _initialize_client(self):
        load_dotenv()
        access_key = os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        if not access_key or not secret_key:
            raise EnvironmentError("AWS credentials not found")
        config = Config(
            endpoint_uri=f"https://bedrock-runtime.{self.region}.amazonaws.com",
            region=self.region,
            aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
            http_auth_scheme_resolver=HTTPAuthSchemeResolver(),
            http_auth_schemes={"aws.auth#sigv4": SigV4AuthScheme()}
        )
        self.client = BedrockRuntimeClient(config=config)

    async def send_event(self, event_json):
        if self.stream_closed:
            return

        try:
            event = InvokeModelWithBidirectionalStreamInputChunk(
                value=BidirectionalInputPayloadPart(bytes_=event_json.encode('utf-8'))
            )
            await self.stream.input_stream.send(event)
        except OSError as e:
            if "closed" in str(e).lower():
                self.stream_closed = True
            else:
                raise

    async def start_session(self):
        if not self.client:
            self._initialize_client()

        self.stream = await self.client.invoke_model_with_bidirectional_stream(
            InvokeModelWithBidirectionalStreamOperationInput(model_id=self.model_id)
        )
        self.is_active = True
        self.stream_closed = False

        session_start = {
            "event": {
                "sessionStart": {
                    "inferenceConfiguration": {
                        "maxTokens": 512,  
                        "topP": 0.9,
                        "temperature": 0.7
                    }
                }
            }
        }
        await self.send_event(json.dumps(session_start))

        prompt_start = {
            "event": {
                "promptStart": {
                    "promptName": self.prompt_name,
                    "textOutputConfiguration": {"mediaType": "text/plain"},
                    "audioOutputConfiguration": {
                        "mediaType": "audio/lpcm",
                        "sampleRateHertz": 24000,
                        "sampleSizeBits": 16,
                        "channelCount": 1,
                        "voiceId": "matthew",
                        "encoding": "base64",
                        "audioType": "SPEECH"
                    }
                }
            }
        }
        await self.send_event(json.dumps(prompt_start))


        system_prompt = (
            "You are a professional assistant. "
            "Keep responses brief."
            "Answer technical questions using technical terms."
            )
        await self._send_text_content(system_prompt, "SYSTEM")

        # Start processing responses in the background
        self.response_processor = asyncio.create_task(self._process_responses_task())
    
    async def _process_responses_task(self):
        """Background task to process responses from the Nova Sonic API."""
        current_text_buffer = ""
        
        try:
            while self.is_active and not self.stream_closed:
                try:
                    output = await self.stream.await_output()
                    if output and len(output) > 1:
                        result = await output[1].receive()
                        if result is not None and result.value and result.value.bytes_:
                            response_data = result.value.bytes_.decode('utf-8')
                            json_data = json.loads(response_data)

                            if 'event' in json_data:
                                if 'contentStart' in json_data['event']:
                                    content_start = json_data['event']['contentStart']
                                    self.role = content_start['role']
                                    if 'additionalModelFields' in content_start:
                                        fields = json.loads(content_start['additionalModelFields'])
                                        self.display_assistant_text = (fields.get('generationStage') == 'SPECULATIVE')

                                elif 'textOutput' in json_data['event']:
                                    text = json_data['event']['textOutput']['content']
                                    current_text_buffer += text
                                    await self.text_queue.put({"type": "content", "content": text})
									
                                    if self.role == "ASSISTANT" and self.display_assistant_text:
                                        print(f"Assistant: {text}")
                                    elif self.role == "USER":
                                        print(f"User: {text}")

                                elif 'contentEnd' in json_data['event'] and self.role == 'ASSISTANT':
                                    if current_text_buffer:
                                        current_text_buffer = ""  

                                elif 'audioOutput' in json_data['event']:
                                    audio_content = json_data['event']['audioOutput']['content']
                                    audio_bytes = base64.b64decode(audio_content)
                                    await self.audio_queue.put(audio_bytes)
                        else:
                            await asyncio.sleep(0.05)
                    else:
                        await asyncio.sleep(0.05)

                except asyncio.CancelledError:
                    print("Response processor task cancelled")
                    break
                except Exception as e:
                    if not self.is_active:
                        break
                    print(f"Error receiving response: {e}")
                    await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Error in response processor task: {e}")
        finally:
            print("Response processor task ended.")

    async def _send_text_content(self, text_content, role):
        content_name = str(uuid.uuid4())
        content_start = {
            "event": {
                "contentStart": {
                    "promptName": self.prompt_name,
                    "contentName": content_name,
                    "type": "TEXT",
                    "interactive": True,
                    "role": role,
                    "textInputConfiguration": {"mediaType": "text/plain"}
                }
            }
        }
        await self.send_event(json.dumps(content_start))

        text_input = {
            "event": {
                "textInput": {
                    "promptName": self.prompt_name,
                    "contentName": content_name,
                    "content": text_content
                }
            }
        }
        await self.send_event(json.dumps(text_input))

        content_end = {
            "event": {
                "contentEnd": {
                    "promptName": self.prompt_name,
                    "contentName": content_name
                }
            }
        }
        await self.send_event(json.dumps(content_end))

    async def send_text_input(self, user_query, context=None):
        full_query = user_query
        if context and len(context) > 0:
            max_context_size = 500
            if len(context) > max_context_size:
                context = context[:max_context_size] + "..."
            full_query = f"{user_query}\n\nContext: {context}"
        
        await self._send_text_content(full_query, "USER")

    async def start_audio_input(self):
        audio_content_start = {
            "event": {
                "contentStart": {
                    "promptName": self.prompt_name,
                    "contentName": self.audio_content_name,
                    "type": "AUDIO",
                    "interactive": True,
                    "role": "USER",
                    "audioInputConfiguration": {
                        "mediaType": "audio/lpcm",
                        "sampleRateHertz": 16000,
                        "sampleSizeBits": 16,
                        "channelCount": 1,
                        "audioType": "SPEECH",
                        "encoding": "base64"
                    }
                }
            }
        }
        await self.send_event(json.dumps(audio_content_start))

    async def send_audio_chunk(self, audio_bytes):
        if not self.is_active or self.stream_closed:
            return
        blob = base64.b64encode(audio_bytes).decode('utf-8')
        audio_input = {
            "event": {
                "audioInput": {
                    "promptName": self.prompt_name,
                    "contentName": self.audio_content_name,
                    "content": blob
                }
            }
        }
        await self.send_event(json.dumps(audio_input))

    async def end_audio_input(self):
        if self.stream_closed:
            return
        audio_content_end = {
            "event": {
                "contentEnd": {
                    "promptName": self.prompt_name,
                    "contentName": self.audio_content_name
                }
            }
        }
        await self.send_event(json.dumps(audio_content_end))

    async def end_session(self):
        if not self.is_active:
            return

        if self.stream_closed:
            self.is_active = False
            return

        try:
            prompt_end = {
                "event": {
                    "promptEnd": {
                        "promptName": self.prompt_name
                    }
                }
            }
            await self.send_event(json.dumps(prompt_end))

            session_end = {
                "event": {
                    "sessionEnd": {}
                }
            }
            await self.send_event(json.dumps(session_end))

            try:
                await self.stream.input_stream.close()
                self.stream_closed = True
            except Exception as e:
                print(f"Error closing stream: {e}")
                self.stream_closed = True
        except Exception as e:
            print(f"Error during session end: {e}")
        finally:
            self.is_active = False
            if hasattr(self, 'response_processor') and self.response_processor and not self.response_processor.done():
                self.response_processor.cancel()
                try:
                    await self.response_processor
                except asyncio.CancelledError:
                    pass

    async def _process_responses(self):
        """Consume processed responses and yield them."""
        try:
            while self.is_active:
                try:
                    try:
                        text_data = await asyncio.wait_for(self.text_queue.get(), timeout=0.01)
                        yield text_data
                        self.text_queue.task_done()
                        continue  
                    except asyncio.TimeoutError:
                        pass 

                    try:
                        audio_data = await asyncio.wait_for(self.audio_queue.get(), timeout=0.01)
                        yield {"type": "audio", "content": audio_data}
                        self.audio_queue.task_done()
                    except asyncio.TimeoutError:
                        pass  

                    await asyncio.sleep(0.01)
                except asyncio.CancelledError:
                    print("_process_responses cancelled")
                    break
                except Exception as e:
                    print(f"Error in _process_responses: {e}")
        finally:
            print("Process responses ended.")