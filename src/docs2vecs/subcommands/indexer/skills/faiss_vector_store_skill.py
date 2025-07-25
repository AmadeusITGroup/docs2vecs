from pathlib import Path
from typing import List
from typing import Dict
from typing import Optional
from typing import Any

import faiss
import os
from docs2vecs.subcommands.indexer.config.config import Config
from docs2vecs.subcommands.indexer.document.document import Document
from docs2vecs.subcommands.indexer.skills.skill import IndexerSkill
from docs2vecs.subcommands.indexer.skills.tracker import VectorStoreTracker
from langchain_community.vectorstores import FAISS
from langchain_community.docstore.in_memory import InMemoryDocstore


class FaissVectorStoreSkill(IndexerSkill):
    """
    Faiss vector store skill for storing and retrieving document embeddings.
    Supports flat L2 indexing
    """

    def __init__(
        self,
        config: Dict[str, Any],
        global_config: Config,
        vector_store_tracker: Optional[VectorStoreTracker] = None,
    ) -> None:
        super().__init__(config, global_config)
        self._vector_store_tracker = vector_store_tracker
        self._overwrite_index = self._config.get("overwrite_index", False)
        self._VECTOR_DIMENSION = self._config.get("dimension")
        self.faiss_index = faiss.IndexFlatL2(self._VECTOR_DIMENSION)

    def run(self, input: Optional[List[Document]] = None) -> List[Document]:
        self.logger.info("Running FaissVectorStoreSkill...")
        db_path = Path(self._config.get("db_path")).expanduser().resolve().as_posix()

        for doc in input:
            self.logger.info(f"Processing document: {doc.filename}")
            ids = [chunk.chunk_id for chunk in doc.chunks]
            embeddings = [chunk.embedding for chunk in doc.chunks]
            documents = [chunk.content for chunk in doc.chunks]
            metadatas = [
                {"source": chunk.source_link, "tags": doc.tag} for chunk in doc.chunks
            ]

            embeddings_to_add = []
            metadatas_to_add = []
            documents_to_add = []
            ids_to_add = []
            self.logger.debug(f"ids in the processed file are : {ids}")
            self.logger.debug(
                f"the value of overwrite_index is : {self._overwrite_index}"
            )
        # load or create the vector store
        vector_store = self._get_vector_store(db_path, input)
        # Get existing IDs as a set
        existing_ids = list(vector_store.index_to_docstore_id.values())

        if self._overwrite_index:
            ids_to_add = ids
            embeddings_to_add = embeddings
            metadatas_to_add = metadatas
            documents_to_add = documents
            if existing_ids:
                self.logger.info("Deleting existing index.")
                vector_store.delete(ids=existing_ids)
                self.logger.debug(f"ids to add are : {ids_to_add}")

        elif ids:
            for id in ids:
                if id not in existing_ids:
                    self.logger.debug(
                        f"ID {id} does not exist in the index, adding it."
                    )
                    self.logger.debug(
                        f"the list of ids {ids}, list of embeddings {embeddings}, list of metadatas {metadatas}, list of documents {documents}"
                    )
                    embeddings_to_add.append(embeddings[ids.index(id)])
                    metadatas_to_add.append(metadatas[ids.index(id)])
                    documents_to_add.append(documents[ids.index(id)])
                    ids_to_add.append(id)

        if ids_to_add:
            self.logger.info(
                f"Adding {len(ids_to_add)} new embeddings to the vector store."
            )
            vector_store.add_embeddings(
                text_embeddings=zip(documents, embeddings),
                metadatas=metadatas,
                ids=ids_to_add,
            )
        else:
            self.logger.info("No new embeddings to add (all ids already exist).")

        vector_store.save_local(db_path)

        return input

    def _get_embeddings(self, input: Optional[List[Document]] = None) -> List[float]:
        data = []
        for doc in input:
            self.logger.debug(f"Processing document: {doc.filename}")
            for chunk in doc.chunks:
                data.append(chunk.embedding)
        return data

    def _get_vector_store(
        self, db_path: Path, input: Optional[List[Document]] = None
    ) -> FAISS:
        index_path = os.path.join(db_path, "index.faiss")

        if os.path.exists(index_path):
            self.logger.info(f"FAISS index found at {index_path}.")
            vector_store = FAISS.load_local(
                db_path,
                embeddings=self._get_embeddings(input),
                allow_dangerous_deserialization=True,
            )

        else:
            self.logger.info(f"FAISS index not found at {index_path}.")
            vector_store = FAISS(
                index=self.faiss_index,
                embedding_function=self._get_embeddings(input),
                docstore=InMemoryDocstore(),
                index_to_docstore_id={},
            )
        return vector_store
