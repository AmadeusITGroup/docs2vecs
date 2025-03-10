import hashlib
from pathlib import Path
from typing import List
from typing import Optional

from llama_index.core import Document as LlamaDocument
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding

from docs2vecs.subcommands.indexer.config.config import Config
from docs2vecs.subcommands.indexer.document.chunk import Chunk
from docs2vecs.subcommands.indexer.document.document import Document
from docs2vecs.subcommands.indexer.skills.skill import IndexerSkill


class SemanticSplitter(IndexerSkill):
    def __init__(self, config: dict, global_config: Config):
        super().__init__(config, global_config)

    def run(self, input: Optional[List[Document]] = None) -> List[Document]:
        self.logger.info("Running SemanticSplitter...")

        if not input:
            self.logger.error("No documents provided in input")
            return input

        embed_model = AzureOpenAIEmbedding(
            deployment_name=self._config["embedding_model"]["deployment_name"],
            api_key=self._config["embedding_model"]["api_key"],
            azure_endpoint=self._config["embedding_model"]["endpoint"],
            api_version=self._config["embedding_model"]["api_version"],
        )

        splitter = SemanticSplitterNodeParser(
            buffer_size=1,
            breakpoint_percentile_threshold=95,
            embed_model=embed_model,
        )

        for doc in input:
            self.logger.debug(f"Processing document: {doc.filename}")
            try:
                if doc.text is None:
                    raise ValueError(f"Document {doc.filename} text is None")
            except ValueError as e:
                self.logger.error(e)
                continue

            nodes = splitter.get_nodes_from_documents([LlamaDocument(text=doc.text)])

            for node in nodes:
                text = node.get_content()
                chunk = Chunk()
                chunk.document_id = hashlib.sha256(text.encode()).hexdigest()
                chunk.document_name = Path(doc.filename).name
                chunk.tag = doc.tag
                chunk.content = text
                chunk.chunk_id = node.id_
                chunk.source_link = doc.source_url
                doc.add_chunk(chunk)

            self.logger.debug(f"Split {doc.filename} into {len(doc.chunks)} chunks")

        return input
