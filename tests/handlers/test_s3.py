# UNIT TEST FOR S3 HANDLER

import pytest
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError
from io import BytesIO
import pandas as pd
from src.handlers.s3 import S3Handler


@pytest.fixture
def s3_handler(mocker):
    handler = S3Handler()
    handler.s3_client = MagicMock()  # Mock the S3 client
    return handler


def test_connect_success(mocker, monkeypatch):
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    mock_boto3 = mocker.patch("boto3.client")
    handler = S3Handler()
    handler.connect()
    mock_boto3.assert_called_once_with("s3", region_name="us-east-1")
    assert handler.s3_client is not None


def test_read_file_pdf(s3_handler, mocker):
    mocker.patch.object(S3Handler, "read_file", return_value="extracted text")
    mocker.patch("time.sleep")  # Skip slee
    result = s3_handler.read_file("bucket", "file.pdf", "pdf")
    assert result == "extracted text"


def test_read_file_excel(s3_handler):
    # Create test DataFrame
    df = pd.DataFrame({"A": [1, 2], "B": ["x", "y"]})
    excel_bytes = BytesIO()
    df.to_excel(excel_bytes, index=False)
    excel_bytes.seek(0)

    # Mock S3 response
    mock_body = MagicMock()
    mock_body.read.return_value = excel_bytes.getvalue()
    s3_handler.s3_client.get_object.return_value = {"Body": mock_body}

    result = s3_handler.read_file("bucket", "file.xlsx", "xlsx")
    pd.testing.assert_frame_equal(result, df)


def test_read_file_unsupported_format(s3_handler):
    result = s3_handler.read_file("bucket", "file.txt", "txt")
    assert "Not a supported format: txt" in result
