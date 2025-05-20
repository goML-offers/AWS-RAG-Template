import json
import logging
import time
import urllib.request
from datetime import datetime

import boto3
from botocore.exceptions import BotoCoreError, ClientError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TranscribeHandler:
    def __init__(self):
        self.transcribe_client = boto3.client("transcribe")

    def start_transcription(
        self, job_name, file_uri, language_code="en-US", output_bucket_name=None
    ):
        try:
            params = {
                "TranscriptionJobName": job_name,
                "Media": {"MediaFileUri": file_uri},
                "MediaFormat": "mp3",
                "LanguageCode": language_code,
            }

            if output_bucket_name:
                params["OutputBucketName"] = output_bucket_name

            response = self.transcribe_client.start_transcription_job(**params)
            logger.info(f"Started transcription job: {job_name}")
            return response
        except (BotoCoreError, ClientError) as error:
            logger.error(f"Error occurred while starting transcription job: {error}")
            return None

    def get_transcription(self, job_name):
        try:
            while True:
                response = self.transcribe_client.get_transcription_job(
                    TranscriptionJobName=job_name
                )
                status = response["TranscriptionJob"]["TranscriptionJobStatus"]

                if status in ["COMPLETED", "FAILED"]:
                    break

                logger.info(f"Transcription job {job_name} is {status}. Waiting...")
                time.sleep(5)

            if status == "COMPLETED":
                transcription_url = response["TranscriptionJob"]["Transcript"][
                    "TranscriptFileUri"
                ]
                logger.info(
                    f"Transcription completed successfully. Transcript URL: {transcription_url}"
                )
                return transcription_url
            else:
                logger.error(f"Transcription job {job_name} failed.")
                return None

        except (BotoCoreError, ClientError) as error:
            logger.error(f"Error occurred while fetching transcription result: {error}")
            return None

    def download_and_print_transcription(self, transcription_url):
        try:
            with urllib.request.urlopen(transcription_url) as response:
                result = json.loads(response.read())
                transcript_text = result["results"]["transcripts"][0]["transcript"]
                logger.info("Transcription Text:\n")
                print(transcript_text)
        except Exception as e:
            logger.error(f"Failed to download or parse transcription: {e}")


if __name__ == "__main__":
    transcribe_handler = TranscribeHandler()

    # Create a unique job name to avoid conflicts
    job_name = f"transcription-job-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Replace with your actual file URL (public S3 or accessible with your IAM role)
    file_url = "s3://testing-bucket-dopp-s3/output.mp3"

    # Start Transcription Job
    response = transcribe_handler.start_transcription(job_name, file_url)

    if response:
        # Fetch Transcription Result
        transcription_url = transcribe_handler.get_transcription(job_name)

        if transcription_url:
            logger.info(f"Transcription result available at: {transcription_url}")
            # Download and print transcription text
            transcribe_handler.download_and_print_transcription(transcription_url)
