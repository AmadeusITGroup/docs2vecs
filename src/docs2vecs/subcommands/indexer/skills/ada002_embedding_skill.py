from typing import List, Optional

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding

from docs2vecs.subcommands.indexer.config import Config
from docs2vecs.subcommands.indexer.document import Document
from docs2vecs.subcommands.indexer.skills.skill import IndexerSkill


class AzureAda002EmbeddingSkill(IndexerSkill):
    def __init__(self, config: dict, global_config: Config):
        super().__init__(config, global_config)

    def az_ada002_embeddings(self, content: str, chunk_id=None):
        self.logger.debug(
            f"Requesting embedding for chunk_id={chunk_id}, content_length={len(content)} chars"
        )

        api_key = self._config.get("api_key")
        if api_key:
            self.logger.debug("Using API key authentication")
            embed_model = AzureOpenAIEmbedding(
                deployment_name=self._config["deployment_name"],
                api_key=api_key,
                azure_endpoint=self._config["endpoint"],
                api_version=self._config["api_version"],
            )
        else:
            self.logger.debug(
                "No api_key provided, using Azure AD token authentication (DefaultAzureCredential)"
            )
            credential = DefaultAzureCredential()
            token_provider = get_bearer_token_provider(
                credential, "https://cognitiveservices.azure.com/.default"
            )
            embed_model = AzureOpenAIEmbedding(
                deployment_name=self._config["deployment_name"],
                azure_ad_token_provider=token_provider,
                azure_endpoint=self._config["endpoint"],
                api_version=self._config["api_version"],
                use_azure_ad=True,
            )

        embedding = embed_model.get_query_embedding(content)
        self.logger.debug(
            f"Successfully received embedding for chunk_id={chunk_id}, embedding_dim={len(embedding) if embedding else 0}"
        )
        return embedding

    def run(self, input: Optional[List[Document]] = None) -> Optional[List[Document]]:
        self.logger.info(
            f"Running Azure Embedding Skill with deployment name: {self._config['deployment_name']}..."
        )

        docs_count = len(input)
        chunks_count = sum(len(doc.chunks) for doc in input)

        self.logger.info(
            f"Processing a total of documents: {docs_count}. Total number of chunks: {chunks_count}"
        )

        for doc in input:
            self.logger.debug(f"Processing document: {doc.filename}")
            for chunk in doc.chunks:
                self.logger.debug(f"Creating embedding for chunk: {chunk.chunk_id}")
                chunk.embedding = "" if not chunk.content else self.az_ada002_embeddings(
                    chunk.content, chunk_id=chunk.chunk_id
                )

        return input
