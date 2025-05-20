import time
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError, ConnectionError


class DynamoDBHandler:
    def __init__(
        self,
        region_name: str,
        endpoint_url: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: int = 1,
    ):
        self.region_name = region_name
        self.endpoint_url = endpoint_url
        self.client = None
        self.resource = None
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def check_connection(self) -> bool:
        """
        Checks if the connection is alive and reconnects if necessary.
        :return: Boolean indicating if the connection is healthy after check.
        """
        try:
            # First check if we have client and resource objects
            if self.client is None or self.resource is None:
                print("No connection exists. Attempting to connect...")
                self.connect()
                return self.client is not None and self.resource is not None

            # Test the connection with a simple operation
            self.client.list_tables(Limit=1)
            return True

        except (ClientError, BotoCoreError, ConnectionError) as e:
            print(f"Connection lost: {e}")
            try:
                # Attempt to reconnect
                print("Attempting to reconnect...")
                self.connect()
                return self.client is not None and self.resource is not None
            except (ClientError, BotoCoreError, ConnectionError) as e:
                print(f"Failed to reconnect: {e}")
                return False

    def connect(self) -> None:
        """Establishes a connection to the DynamoDB service."""
        try:
            kwargs = {"region_name": self.region_name}

            # Add endpoint URL if it exists
            if self.endpoint_url:
                kwargs["endpoint_url"] = self.endpoint_url

            # Create both client and resource for different operation types
            self.client = boto3.client("dynamodb", **kwargs)
            self.resource = boto3.resource("dynamodb", **kwargs)

            print("Connection to DynamoDB successful")
        except (ClientError, BotoCoreError, ConnectionError) as e:
            print(f"Could not connect to DynamoDB: {e}")
            self.client = None
            self.resource = None

    def execute_operation(self, operation_type: str, **kwargs) -> Dict[str, Any]:
        """
        Executes a DynamoDB operation with retry logic.
        :param operation_type: Type of DynamoDB operation (e.g., 'get_item', 'put_item', etc.)
        :param kwargs: Parameters for the specified operation
        :return: Dictionary containing operation results
        """
        retries = 0
        while retries < self.max_retries:
            try:
                # Check connection before executing
                if not self.check_connection():
                    print(
                        f"Connection check failed. Attempt {retries + 1} of {self.max_retries}"
                    )
                    retries += 1
                    time.sleep(self.retry_delay)
                    continue

                # Different operations may use client or resource
                if operation_type in [
                    "scan",
                    "query",
                    "get_item",
                    "put_item",
                    "update_item",
                    "delete_item",
                    "batch_write_item",
                    "batch_get_item",
                ]:
                    if not hasattr(self.client, operation_type):
                        print(
                            f"Operation {operation_type} not supported by DynamoDB client"
                        )
                        return {}

                    result = getattr(self.client, operation_type)(**kwargs)
                    print(f"{operation_type} operation executed successfully")
                    return result
                else:
                    print(f"Unsupported operation type: {operation_type}")
                    return {}

            except (ClientError, BotoCoreError, ConnectionError) as e:
                print(
                    f"Connection error during operation execution (attempt {retries + 1}): {e}"
                )
                self.client = None
                self.resource = None

                retries += 1
                if retries < self.max_retries:
                    print(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                continue

            except Exception as e:
                print(f"Error during operation execution: {e}")
                return {}

        print(f"Failed to execute operation after {self.max_retries} attempts")
        return {}

    def get_item(
        self, table_name: str, key: Dict[str, Dict[str, Any]], **kwargs
    ) -> Dict[str, Any]:
        """
        Get an item from a table.
        :param table_name: Name of the table
        :param key: Primary key of the item to get
        :param kwargs: Additional parameters for the operation
        :return: Dictionary containing the requested item
        """
        operation_params = {"TableName": table_name, "Key": key, **kwargs}
        result = self.execute_operation("get_item", **operation_params)
        return result

    def put_item(
        self, table_name: str, item: Dict[str, Dict[str, Any]], **kwargs
    ) -> Dict[str, Any]:
        """
        Put an item into a table.
        :param table_name: Name of the table
        :param item: Item to put
        :param kwargs: Additional parameters for the operation
        :return: Dictionary containing the response
        """
        operation_params = {"TableName": table_name, "Item": item, **kwargs}
        result = self.execute_operation("put_item", **operation_params)
        return result

    def update_item(
        self,
        table_name: str,
        key: Dict[str, Dict[str, Any]],
        update_expression: str,
        expression_attribute_values: Dict[str, Dict[str, Any]],
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Update an item in a table.
        :param table_name: Name of the table
        :param key: Primary key of the item to update
        :param update_expression: Update expression
        :param expression_attribute_values: Expression attribute values
        :param kwargs: Additional parameters for the operation
        :return: Dictionary containing the response
        """
        operation_params = {
            "TableName": table_name,
            "Key": key,
            "UpdateExpression": update_expression,
            "ExpressionAttributeValues": expression_attribute_values,
            **kwargs,
        }
        result = self.execute_operation("update_item", **operation_params)
        return result

    def delete_item(
        self, table_name: str, key: Dict[str, Dict[str, Any]], **kwargs
    ) -> Dict[str, Any]:
        """
        Delete an item from a table.
        :param table_name: Name of the table
        :param key: Primary key of the item to delete
        :param kwargs: Additional parameters for the operation
        :return: Dictionary containing the response
        """
        operation_params = {"TableName": table_name, "Key": key, **kwargs}
        result = self.execute_operation("delete_item", **operation_params)
        return result

    def query(self, table_name: str, **kwargs) -> Dict[str, Any]:
        """
        Query a table.
        :param table_name: Name of the table
        :param kwargs: Query parameters
        :return: Dictionary containing the query results
        """
        operation_params = {"TableName": table_name, **kwargs}
        result = self.execute_operation("query", **operation_params)
        return result

    def scan(self, table_name: str, **kwargs) -> Dict[str, Any]:
        """
        Scan a table.
        :param table_name: Name of the table
        :param kwargs: Scan parameters
        :return: Dictionary containing the scan results
        """
        operation_params = {"TableName": table_name, **kwargs}
        result = self.execute_operation("scan", **operation_params)
        return result

    def batch_write(
        self, request_items: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Perform a batch write operation.
        :param request_items: Dictionary containing tables and lists of write requests
        :return: Dictionary containing the response
        """
        operation_params = {"RequestItems": request_items}
        result = self.execute_operation("batch_write_item", **operation_params)
        return result

    def batch_get(self, request_items: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Perform a batch get operation.
        :param request_items: Dictionary containing tables and keys to get
        :return: Dictionary containing the response
        """
        operation_params = {"RequestItems": request_items}
        result = self.execute_operation("batch_get_item", **operation_params)
        return result

    def close(self) -> None:
        """Closes the DynamoDB connection."""
        # No actual connection to close with boto3, but we'll reset the client and resource
        self.client = None
        self.resource = None
        print("DynamoDB connection resources released")
