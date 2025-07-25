import hashlib
from pathlib import Path
from typing import List
from typing import Optional

from langchain.text_splitter import RecursiveCharacterTextSplitter as LCRecursiveCharacterTextSplitter

from docs2vecs.subcommands.indexer.config.config import Config
from docs2vecs.subcommands.indexer.document.chunk import Chunk
from docs2vecs.subcommands.indexer.document.document import Document
from docs2vecs.subcommands.indexer.skills.skill import IndexerSkill


class RecursiveCharacterTextSplitter(IndexerSkill):
    DEFAULT_CHUNK_SIZE = 1000
    DEFAULT_CHUNK_OVERLAP = 100
    
    def __init__(self, config: dict, global_config: Config):
        super().__init__(config, global_config)
        self._set_config_defaults()

    def _set_config_defaults(self):
        if "chunk_size" not in self._config:
            self._config["chunk_size"] = RecursiveCharacterTextSplitter.DEFAULT_CHUNK_SIZE

        if "chunk_overlap" not in self._config:
            self._config["chunk_overlap"] = RecursiveCharacterTextSplitter.DEFAULT_CHUNK_OVERLAP

    def run(self, input: Optional[List[Document]] = None) -> List[Document]:
        self.logger.info("Running RecursiveCharacterTextSplitter...")

        splitter = LCRecursiveCharacterTextSplitter(chunk_size=self._config["chunk_size"], chunk_overlap=self._config["chunk_overlap"])

        for doc in input:
            self.logger.debug(f"Splitting {doc.filename}...")
            try:
                if doc.text is None:
                    raise ValueError(f"Document {doc.filename} text is None")
            except ValueError as e:
                self.logger.info(e)
                continue
            nodes = splitter.split_text(doc.text)
            for node in nodes:
                text = node
                chunk = Chunk()
                chunk.document_id = hashlib.sha256(text.encode()).hexdigest()
                chunk.document_name = Path(doc.filename).name
                chunk.tag = doc.tag
                chunk.content = text
                chunk.chunk_id = chunk.document_id
                chunk.source_link = doc.source_url
                doc.add_chunk(chunk)

            self.logger.debug(f"Split {doc.filename} into {len(doc.chunks)} chunks")

        return input
