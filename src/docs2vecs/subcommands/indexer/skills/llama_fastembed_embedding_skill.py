import contextlib
import warnings
from typing import List
from typing import Optional

import requests
from llama_index.embeddings.fastembed import FastEmbedEmbedding
from urllib3.exceptions import InsecureRequestWarning

from docs2vecs.subcommands.indexer.config.config import Config
from docs2vecs.subcommands.indexer.document.document import Document
from docs2vecs.subcommands.indexer.skills.skill import IndexerSkill

old_merge_environment_settings = requests.Session.merge_environment_settings


@contextlib.contextmanager
def no_ssl_verification():
    # Based on https://stackoverflow.com/a/15445989
    opened_adapters = set()

    def merge_environment_settings(self, url, proxies, stream, verify, cert):
        # Verification happens only once per connection so we need to close
        # all the opened adapters once we're done. Otherwise, the effects of
        # verify=False persist beyond the end of this context manager.
        opened_adapters.add(self.get_adapter(url))

        settings = old_merge_environment_settings(self, url, proxies, stream, verify, cert)
        settings["verify"] = False

        return settings

    requests.Session.merge_environment_settings = merge_environment_settings

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", InsecureRequestWarning)
            yield
    finally:
        requests.Session.merge_environment_settings = old_merge_environment_settings

        for adapter in opened_adapters:
            try:
                adapter.close()
            except Exception as e:
                print(f"Warning: It was not possible to close the adapter {adapter}: {e}")


class LlamaFastembedEmbeddingSkill(IndexerSkill):
    def __init__(self, config: dict, global_config: Config):
        super().__init__(config, global_config)
        self._set_config_defaults()
        with no_ssl_verification():
            self._embedding_model = FastEmbedEmbedding(model_name=self._config["model_name"])

    def _set_config_defaults(self):
        self._config["model_name"] = self._config.get("model_name", "sentence-transformers/all-MiniLM-L6-v2")

    def _get_embedding(self, content: str):
        return self._embedding_model.get_query_embedding(content)

    def run(self, input: Optional[List[Document]] = None) -> List[Document]:
        self.logger.info("Running LlamaFastembedEmbeddingSkill...\n")

        self.logger.debug(f"Going to process {len(input)} documents")
        for doc in input:
            self.logger.debug(f"Processing document: {doc.filename}")
            for chunk in doc.chunks:
                chunk.embedding = "" if not chunk.content else self._get_embedding(chunk.content)

        return input
