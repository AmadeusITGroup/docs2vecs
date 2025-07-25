from pathlib import Path
from typing import List
from typing import Optional

import chromadb

from docs2vecs.subcommands.indexer.config.config import Config
from docs2vecs.subcommands.indexer.document.document import Document
from docs2vecs.subcommands.indexer.skills.skill import IndexerSkill
from docs2vecs.subcommands.indexer.skills.tracker import VectorStoreTracker


class ChromaDBVectorStoreSkill(IndexerSkill):
    def __init__(self, config: dict, global_config: Config, vector_store_tracker: Optional[VectorStoreTracker] = None) -> None:
        super().__init__(config, global_config)
        self._vector_store_tracker = vector_store_tracker

    def run(self, input: Optional[List[Document]] = None) -> List[Document]:
        self.logger.info("Running ChromaDBVectorStoreSkill...")

        db_path = Path(self._config["db_path"]).expanduser().resolve().as_posix()
        chroma_client: chromadb.Client = self._get_client(db_path)
        chroma_collection = chroma_client.get_or_create_collection(self._config["collection_name"])

        self.logger.debug(f"Going to process {len(input)} documents")
        for doc in input:
            self.logger.debug(f"Processing document: {doc.filename}")
            chroma_collection.upsert(
                ids=[chunk.chunk_id for chunk in doc.chunks],
                embeddings=[chunk.embedding for chunk in doc.chunks],
                documents=[chunk.content for chunk in doc.chunks],
                metadatas=[{"source": chunk.source_link, "tags": doc.tag} for chunk in doc.chunks],
            )

        return input

    def _get_client(self, db_path: str) -> chromadb.Client:
        return chromadb.PersistentClient(path=db_path)