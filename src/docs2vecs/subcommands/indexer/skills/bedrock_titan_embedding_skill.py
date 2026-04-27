import json
import time
from typing import List, Optional

import boto3

from docs2vecs.subcommands.indexer.config.config import Config
from docs2vecs.subcommands.indexer.document.document import Document
from docs2vecs.subcommands.indexer.skills.skill import IndexerSkill


class BedrockTitanEmbeddingSkill(IndexerSkill):
    DEFAULT_MODEL_ID = "amazon.titan-embed-text-v2:0"
    DEFAULT_DIMENSIONS = 1024
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_BACKOFF = 2

    def __init__(self, config: dict, global_config: Config):
        super().__init__(config, global_config)
        self._model_id = self._config.get("model_id", self.DEFAULT_MODEL_ID)
        self._dimensions = self._config.get("dimensions", self.DEFAULT_DIMENSIONS)
        self._normalize = self._config.get("normalize", True)
        self._max_retries = self._config.get("max_retries", self.DEFAULT_MAX_RETRIES)
        self._retry_backoff = self._config.get("retry_backoff", self.DEFAULT_RETRY_BACKOFF)
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=self._config.get("region"),
        )

    def _embed_text(self, content: str, chunk_id=None):
        self.logger.debug(
            f"Requesting Bedrock embedding for chunk_id={chunk_id}, content_length={len(content)}"
        )
        body = json.dumps(
            {
                "inputText": content,
                "dimensions": self._dimensions,
                "normalize": self._normalize,
            }
        )
        for attempt in range(self._max_retries):
            try:
                resp = self._client.invoke_model(
                    modelId=self._model_id,
                    body=body,
                    contentType="application/json",
                    accept="application/json",
                )
                embedding = json.loads(resp["body"].read())["embedding"]
                self.logger.debug(
                    f"Successfully received embedding for chunk_id={chunk_id}, embedding_dim={len(embedding) if embedding else 0}"
                )
                return embedding
            except Exception as exc:
                if attempt == self._max_retries - 1:
                    raise
                wait = self._retry_backoff * (attempt + 1)
                self.logger.warning(
                    f"Bedrock call failed (attempt {attempt + 1}/{self._max_retries}): {exc} - retrying in {wait}s"
                )
                time.sleep(wait)

    def run(self, input: Optional[List[Document]] = None) -> Optional[List[Document]]:
        self.logger.info(
            f"Running Bedrock Titan Embedding Skill with model_id: {self._model_id}..."
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
                chunk.embedding = "" if not chunk.content else self._embed_text(
                    chunk.content, chunk_id=chunk.chunk_id
                )

        return input
