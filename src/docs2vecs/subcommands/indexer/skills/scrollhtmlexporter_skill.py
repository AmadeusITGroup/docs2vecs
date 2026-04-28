"""Export Confluence pages as HTML via the Scroll HTML Exporter REST API.

Uses the K15t Scroll HTML Exporter async API to trigger an export, poll for
completion, download the resulting ZIP, and extract it locally.

The async flow is:
    1. POST  ``<api_url>``                → ``{jobId}``
    2. GET   ``<api_url>/<jobId>/status``  → ``{status, downloadUrl, …}``
    3. GET   ``<downloadUrl>``             → ZIP file
    4. Extract ZIP into ``<export_folder>/<page_id>/``

Config params
-------------
api_url : str
    Base URL of the Scroll HTML Exporter async API, e.g.
    ``https://scroll-html.us.exporter.k15t.app/api/public/1/exports``
auth_token : str
    Bearer token for authentication.
poll_interval : int
    Seconds between status polls (recommended: 2).
export_folder : str
    Local directory where exports are extracted.
scope : str, optional
    ``"current"`` (single page) or ``"descendants"`` (page tree).
    Defaults to ``"current"``.
template_id : str, optional
    Scroll HTML template ID.  Defaults to the bundled Help Center template
    (``com.k15t.scroll.html.helpcenter``).
confluence_prefix : str, optional
    Base URL of the Confluence instance (used to build ``source_url``).
tag : str, optional
    Default tag applied to entries without an explicit tag.
page_ids : list[dict], optional
    List of ``{id, tag?}`` dicts.
page_urls : list[dict], optional
    List of ``{url, tag?}`` dicts.
"""

import json
import time
import zipfile
from io import BytesIO
from pathlib import Path
from typing import List, Optional
from urllib.request import Request, urlopen

from docs2vecs.subcommands.indexer.config import Config
from docs2vecs.subcommands.indexer.document import Document
from docs2vecs.subcommands.indexer.skills.skill import IndexerSkill

_DEFAULT_TEMPLATE = "com.k15t.scroll.html.helpcenter"


class ScrollHTMLExporterSkill(IndexerSkill):
    """Export Confluence pages as HTML via Scroll HTML Exporter API.

    Each entry in ``page_urls`` and ``page_ids`` can carry an optional ``tag``
    field.  Entries without a tag fall back to the top-level ``tag`` param
    (default: ``""``).
    """

    def __init__(self, config: dict, global_config: Config) -> None:
        super().__init__(config, global_config)
        self._auth_header = f"Bearer {self._config['auth_token']}"
        self._api_url = self._config["api_url"]
        self._export_folder = Path(self._config["export_folder"]).expanduser().resolve()
        self._confluence_prefix = self._config.get("confluence_prefix", "")
        self._template_id = self._config.get("template_id", _DEFAULT_TEMPLATE)
        self._default_tag: str = self._config.get("tag", "")

    # ------------------------------------------------------------------
    # API helpers
    # ------------------------------------------------------------------
    def _start_export(self, page_id: str) -> str:
        """POST to start an async export job.  Returns the ``jobId``."""
        export_params = {
            "pageId": page_id,
            "templateId": self._template_id,
            "scope": self._config.get("scope", "current"),
        }

        data = json.dumps(export_params).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": self._auth_header,
        }
        if not self._api_url.lower().startswith(("http:", "https:")):
            raise ValueError("API URL must start with http:// or https://")
        response = urlopen(  # noqa: S310
            Request(self._api_url, data, headers, method="POST")
        )
        return json.load(response)["jobId"]

    def _get_status(self, job_id: str) -> dict:
        """GET the status of a running export job."""
        url = f"{self._api_url}/{job_id}/status"
        headers = {"Authorization": self._auth_header}
        if not url.lower().startswith(("http:", "https:")):
            raise ValueError("API URL must start with http:// or https://")
        response = urlopen(  # noqa: S310
            Request(url, None, headers, method="GET")
        )
        return json.load(response)

    def _download_and_extract(self, download_url: str, dest_dir: Path) -> Path:
        """Download the ZIP from *download_url* and extract into *dest_dir*.

        Returns the path to the extracted folder.
        """
        if not download_url.lower().startswith(("http:", "https:")):
            raise ValueError("Download URL must start with http:// or https://")

        response = urlopen(  # noqa: S310
            Request(download_url, None, {}, method="GET")
        )
        zip_bytes = BytesIO(response.read())

        dest_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_bytes) as zf:
            zf.extractall(dest_dir)
            self.logger.info(
                f"Extracted {len(zf.namelist())} files → {dest_dir}"
            )

        return dest_dir

    # ------------------------------------------------------------------
    # Page entry helpers (same pattern as ScrollWordExporter)
    # ------------------------------------------------------------------
    def _extract_page_id_from_url(self, url: str) -> str:
        if "homepageId" in url:
            return url.split("=")[1]
        tokens = url.split("/")
        page_id = tokens[tokens.index("pages") + 1]
        return page_id

    def _extract_confluence_page_entries(self) -> List[dict]:
        """Return a list of dicts with ``page_id``, ``url``, and ``tag``."""
        entries: List[dict] = []

        if self._config.get("page_ids"):
            for entry in self._config["page_ids"]:
                entries.append({
                    "page_id": str(entry["id"]),
                    "url": None,
                    "tag": entry.get("tag", self._default_tag),
                })

        if self._config.get("page_urls"):
            for entry in self._config["page_urls"]:
                entries.append({
                    "page_id": self._extract_page_id_from_url(entry["url"]),
                    "url": entry["url"],
                    "tag": entry.get("tag", self._default_tag),
                })

        if not entries:
            self.logger.warning(
                "No pages to export — both 'page_ids' and 'page_urls' are empty or missing."
            )

        return entries

    # ------------------------------------------------------------------
    # run
    # ------------------------------------------------------------------
    def run(self, input: Optional[List[Document]] = None) -> List[Document]:
        self.logger.info("Running ScrollHTMLExporterSkill")

        doc_list: List[Document] = []
        page_entries = self._extract_confluence_page_entries()

        for entry in page_entries:
            page_id = entry["page_id"]
            tag = entry["tag"]
            self.logger.info(f"Exporting confluence page {page_id} (tag={tag})")

            job_id = self._start_export(page_id)
            self.logger.debug(f"Export job started: {job_id}")

            # Poll until done
            download_url = None
            while True:
                time.sleep(self._config["poll_interval"])
                status = self._get_status(job_id)
                self.logger.debug(
                    f"Step {status['step']:d} of {status['totalSteps']:d} "
                    f"({status['stepProgress']:d}%)"
                )
                print(
                    f"Step {status['step']:d} of {status['totalSteps']:d} "
                    f"({status['stepProgress']:d}%)"
                )

                if status["status"] == "error":
                    self.logger.error(f"Export failed for page {page_id}")
                    break
                if status["status"] == "cancelled":
                    self.logger.warning(f"Export cancelled for page {page_id}")
                    break
                if status["status"] == "complete":
                    download_url = status["downloadUrl"]
                    break

            if not download_url:
                continue

            # Download ZIP and extract
            dest_dir = self._export_folder / page_id
            self._download_and_extract(download_url, dest_dir)

            source_url = ""
            if self._confluence_prefix:
                source_url = (
                    f"{self._confluence_prefix}/pages/viewpage.action?pageId={page_id}"
                )

            doc = Document(
                filename=str(dest_dir), source_url=source_url, tag=tag
            )
            doc_list.append(doc)

        return doc_list
