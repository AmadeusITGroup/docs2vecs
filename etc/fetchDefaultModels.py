import contextlib
import warnings

import requests
from llama_index.embeddings.fastembed import FastEmbedEmbedding
from urllib3.exceptions import InsecureRequestWarning

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


with no_ssl_verification():
    FastEmbedEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2", cache_dir="/.cache")
