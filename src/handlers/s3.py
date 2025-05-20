import os
from io import BytesIO
from urllib.parse import unquote, urlparse

import boto3
from botocore.exceptions import ClientError
from docx import Document
from dotenv import load_dotenv
from pypdf import PdfReader

load_dotenv()

region_name = os.getenv("AWS_REGION")


class S3Handler:
    def __init__(self):
        self.s3_client = None

    def connect(self):
        try:
            # If testing locally
            # self.s3_client = boto3.client('s3',
            #                               aws_access_key_id=self.aws_access_key_id,
            #                               aws_secret_access_key=self.aws_secret_access_key)

            # For deploying on ECR
            self.s3_client = boto3.client("s3", region_name=region_name)

            print("Connected to S3 successfully!")
        except ClientError as e:
            print(f"Failed to connect to S3: {e}")

    def disconnect(self):
        self.s3_client = None
        # print("Disconnected from S3.")

    def read_file(self, bucket_name: str, file_key: str, file_type: str = "pdf"):
        try:
            text = ""
            response = self.s3_client.get_object(Bucket=bucket_name, Key=file_key)
            file_content = response["Body"].read()
            if file_type.lower() == "pdf":
                # Read PDF using pypdf
                reader = PdfReader(BytesIO(file_content))
                text = "\n".join([page.extract_text() or "" for page in reader.pages])
                return text
            elif file_type.lower() in ["doc", "docx"]:
                # Read Word documents using python-docx
                document = Document(BytesIO(file_content))
                text = "\n".join([para.text for para in document.paragraphs])
                return text
            else:
                return f"Not a supported format: {file_type}"
        except Exception as e:
            print(f"Error:{e}")
            return "Unable to read file"

    def check_file_exists(self, presigned_url):
        s3_client = self.s3_client
        try:
            s3_client.head_object(
                Bucket=presigned_url.split("/")[2],
                Key="/".join(presigned_url.split("/")[3:]),
            )
            return True
        except s3_client.exceptions.ClientError as e:
            print(e)
            if e.response["Error"]["Code"] == "404":
                return False
            else:
                raise e

    def extract_s3_details_with_read(self, signed_url):

        parsed_url = urlparse(signed_url)

        # Extract bucket name
        host_parts = parsed_url.netloc.split(".")
        bucket_name = host_parts[0]  # The first part is the bucket name

        # Extract and decode object key
        object_key = unquote(
            parsed_url.path.lstrip("/")
        )  # Remove leading slash and decode

        object_type = object_key.split(".")[-1]

        file_content = self.read_file(
            bucket_name=bucket_name, file_key=object_key, file_type=object_type
        )

        if str(file_content) == "Unable to read file":
            return "", "", ""

        elif "Not a supported format:" in file_content:
            return "unsupported_file", "", ""

        return bucket_name, object_key, str(file_content)

    def extract_s3_details(self, signed_url):

        parsed_url = urlparse(signed_url)

        # Extract bucket name
        host_parts = parsed_url.netloc.split(".")
        bucket_name = host_parts[0]  # The first part is the bucket name

        # Extract and decode object key
        object_key = unquote(
            parsed_url.path.lstrip("/")
        )  # Remove leading slash and decode

        return bucket_name, object_key

    def copy_files_within_buckets(self, source_url, destination_url):
        try:
            source_bucket_name, source_object_key = source_url.replace(
                "s3://", ""
            ).split("/", 1)
            destination_bucket_name, destination_object_key = destination_url.replace(
                "s3://", ""
            ).split("/", 1)
            copy_source = {"Bucket": source_bucket_name, "Key": source_object_key}

            self.s3_client.copy(
                copy_source, destination_bucket_name, destination_object_key
            )
        except Exception as e:
            return e

    def get_s3_files_details(self, s3_paths):
        # Initialize the S3 client

        file_details_list = []

        for s3_path_og in s3_paths:
            # Parse the s3 path
            if not s3_path_og.startswith("s3://"):
                raise ValueError(
                    f"Invalid S3 path: {s3_path_og}. Path must start with 's3://'"
                )

            # Remove the 's3://' prefix
            s3_path = s3_path_og[5:]

            # Split the path into bucket name and key
            bucket_name, key = s3_path.split("/", 1)

            # Get the file object
            file_obj = self.s3_client.get_object(Bucket=bucket_name, Key=key)

            # Get the file content
            file_content = file_obj["Body"].read()

            # Get the file size
            file_size = file_obj["ContentLength"]

            # Get the file name from the key
            file_name = key.split("/")[-1]

            file_details = {
                "file_name": file_name,
                "file_size": file_size,
                "file_content": file_content,
                "s3_path": s3_path_og,
            }

            file_details_list.append(file_details)

        return file_details_list
