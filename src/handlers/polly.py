import logging

import boto3
from botocore.exceptions import BotoCoreError, ClientError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PollyHandler:
    def __init__(self):
        self.polly_client = boto3.client("polly")

    def synthesize_speech(self, text, voice_id="Joanna", output_format="mp3"):
        try:
            response = self.polly_client.synthesize_speech(
                Text=text, VoiceId=voice_id, OutputFormat=output_format
            )

            if "AudioStream" in response:
                audio_stream = response["AudioStream"].read()
                return audio_stream
            else:
                logger.error("No AudioStream returned by Polly")
                return None

        except (BotoCoreError, ClientError) as error:
            logger.error(f"Error occurred while synthesizing speech: {error}")
            return None
