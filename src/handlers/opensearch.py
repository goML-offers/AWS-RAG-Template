import time
from typing import Dict, List

import boto3
from dotenv import load_dotenv
from llama_index.core import Document
from llama_index.core.node_parser import SimpleNodeParser
from opensearchpy import AWSV4SignerAuth, OpenSearch, RequestsHttpConnection

from src.handlers.bedrock import BedrockServiceHandler

load_dotenv()


class OpenSearchHandler:
    def __init__(self, host, port, service, region="us-west-2"):
        session = boto3.Session()
        credentials = session.get_credentials()
        auth = AWSV4SignerAuth(credentials, region, service)

        self.opensearch_handler = OpenSearch(
            hosts=[{"host": host, "port": port}],
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=120,
        )
        self.bedrock_handler = BedrockServiceHandler()
        self.node_parser = SimpleNodeParser(chunk_size=512, chunk_overlap=64)

    def create_index(self, index_name, vector_dimension):
        """Create an index with KNN vector search enabled."""
        index_body = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "index": {"knn": True},
            },
            "mappings": {
                "properties": {
                    "vector": {"type": "knn_vector", "dimension": vector_dimension},
                    "metadata": {"type": "object"},
                    "content": {"type": "text"},
                    "doc_id": {"type": "keyword"},
                }
            },
        }
        response = self.opensearch_handler.indices.create(
            index=index_name, body=index_body
        )
        print("Index created:", response)
        return response

    def index_text_document(self, index_name: str, text: str, metadata: Dict = None):
        """Index a text document using LlamaIndex for processing."""
        document = Document(text=text, metadata=metadata or {})
        nodes = self.node_parser.get_nodes_from_documents([document])

        responses = []
        for i, node in enumerate(nodes):
            vector = self.bedrock_handler.get_bedrock_embedding(node.text)
            if vector is None or not isinstance(vector, list):
                print(f"Warning: Invalid embedding generated for chunk {i}")
                continue

            if metadata:
                document = {
                    "vector": vector,
                    "content": node.text,
                    "metadata": {
                        **node.metadata,
                        "chunk_id": i,
                    },
                    "doc_id": node.node_id,
                    "lb_metadata": metadata,
                }
            else:
                document = {
                    "vector": vector,
                    "content": node.text,
                    "metadata": {
                        **node.metadata,
                        "chunk_id": i,
                    },
                    "doc_id": node.node_id,
                }
            response = self.opensearch_handler.index(index=index_name, body=document)
            responses.append(response)

        return responses

    def search_vectors(
        self,
        index_name: str,  # updated from tenant_id
        query: str,
        k: int = 5,
    ) -> List[Dict]:
        """Search for similar vectors in the specified index."""
        try:
            time_start = time.time()
            query_embedding = self.bedrock_handler.get_bedrock_embedding(query)
            # knn_query = {"vector": {"vector": query_embedding, "k": k}}
            # must_conditions = [{"knn": knn_query}]

            # query_body = {"size": k, "query": {"bool": {"must": must_conditions}}}

            query_body = {
                "size": k,
                "query": {"knn": {"vector": {"vector": query_embedding, "k": k}}},
            }

            response = self.opensearch_handler.search(index=index_name, body=query_body)

            results = []
            for hit in response["hits"]["hits"]:
                results.append(
                    {
                        "content": hit["_source"]["content"],
                        "metadata": hit["_source"]["metadata"],
                        "doc_id": hit["_source"]["doc_id"],
                        "score": hit["_score"],
                        "lb_metadata": hit["_source"].get("lb_metadata", {}),
                    }
                )
            time_end = time.time()
            print("TIME TAKEN: ", time_end - time_start)
            return results
        except Exception as e:
            print(f"Error during search: {e}")
            return []

    def delete_index(self, index_name):
        """Delete an index."""
        response = self.opensearch_handler.indices.delete(index=index_name)
        print("Index deleted:", response)
        return response
