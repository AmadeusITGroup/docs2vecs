"""Writes chunk content to a JSON file with optional per-document change detection.

Outputs a sorted JSON array of chunk text strings (metadata excluded).
When ``checksum_path`` is set, per-chunk SHA-256 checksums (keyed by
``document_id``) gate downstream processing — only changed or new chunks
are kept; unchanged chunks are stripped from their documents.
"""

import hashlib
import json
import os
from typing import List, Optional

from docs2vecs.subcommands.indexer.config.config import Config
from docs2vecs.subcommands.indexer.document import Document
from docs2vecs.subcommands.indexer.skills.skill import IndexerSkill


class JSONWriterSkill(IndexerSkill):
    """Write chunk text as a sorted JSON array with per-chunk change gating.

    Config params:
        output_path (str): Output JSON path (default: ``data/pipeline_output.json``).
        checksum_path (str, optional): JSON file for per-chunk SHA-256 checksums
            keyed by ``document_id``.
        skip_downstream_if_unchanged (bool, optional): Strip unchanged chunks
            so downstream skills skip them (default: true).
    """

    def __init__(self, skill_config: dict, global_config: Config) -> None:
        super().__init__(skill_config, global_config)
        self._output_path = self._config.get("output_path", "data/pipeline_output.json")
        self._checksum_path = self._config.get("checksum_path", None)
        self._skip_if_unchanged = self._config.get("skip_downstream_if_unchanged", True)

    def _compute_checksum(self, content_bytes: bytes) -> str:
        return hashlib.sha256(content_bytes).hexdigest()

    def _read_stored_checksums(self) -> dict:
        """Return stored {document_id: checksum} map, or empty dict."""
        if self._checksum_path and os.path.isfile(self._checksum_path):
            try:
                with open(self._checksum_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
                    # Legacy format — cannot migrate, start fresh.
                    self.logger.warning(
                        "Checksum file contains legacy format — starting fresh."
                    )
            except Exception as e:
                self.logger.warning(f"Failed to read stored checksums: {e}")
        return {}

    def _write_checksums(self, checksums: dict) -> None:
        """Save per-document checksums to disk."""
        if self._checksum_path:
            os.makedirs(os.path.dirname(self._checksum_path) or ".", exist_ok=True)
            with open(self._checksum_path, "w", encoding="utf-8") as f:
                json.dump(checksums, f, indent=2, ensure_ascii=False)

    def _compute_chunk_checksum(self, chunk) -> str:
        """SHA-256 checksum of a single chunk's content."""
        payload = (chunk.content or "").encode("utf-8")
        return self._compute_checksum(payload)

    def run(self, input: Optional[List[Document]] = None) -> List[Document]:
        if not input:
            self.logger.warning("JSONWriterSkill received no input — nothing to write.")
            return input or []

        # Collect chunk content across all documents
        contents = []
        for doc in input:
            for chunk in doc.chunks:
                if chunk.content:
                    contents.append(chunk.content)

        contents.sort()  # deterministic order for stable checksums

        os.makedirs(os.path.dirname(self._output_path) or ".", exist_ok=True)

        json_bytes = json.dumps(contents, indent=2, ensure_ascii=False).encode("utf-8")

        with open(self._output_path, "wb") as f:
            f.write(json_bytes)

        self.logger.info(
            "Wrote %d chunk content entries to %s",
            len(contents),
            self._output_path,
        )

        # ── Per-chunk checksum-based change gate ────────────────
        # Each chunk is keyed by its document_id (e.g. question hash).
        # Only chunks whose content has changed (or are new) are kept;
        # unchanged chunks are removed so downstream skills skip them.
        if self._checksum_path:
            old_checksums = self._read_stored_checksums()
            new_checksums: dict = {}

            changed_count = 0
            unchanged_count = 0

            for doc in input:
                unchanged_chunks = set()

                for chunk in doc.chunks:
                    doc_id = chunk.document_id or chunk.chunk_id or "unknown"
                    chunk_checksum = self._compute_chunk_checksum(chunk)
                    new_checksums[doc_id] = chunk_checksum

                    old_checksum = old_checksums.get(doc_id)

                    if old_checksum and chunk_checksum == old_checksum and self._skip_if_unchanged:
                        unchanged_chunks.add(chunk)
                        unchanged_count += 1
                        self.logger.debug(
                            "Chunk %s unchanged — will be stripped.",
                            doc_id[:12],
                        )
                    else:
                        changed_count += 1
                        if old_checksum:
                            self.logger.debug(
                                "Chunk %s changed (old: %s, new: %s).",
                                doc_id[:12],
                                old_checksum[:12],
                                chunk_checksum[:12],
                            )
                        else:
                            self.logger.debug("Chunk %s is new.", doc_id[:12])

                # Remove unchanged chunks from this document
                if unchanged_chunks:
                    doc.chunks -= unchanged_chunks

            self.logger.info(
                "Change detection: %d changed/new, %d unchanged out of %d chunks.",
                changed_count,
                unchanged_count,
                changed_count + unchanged_count,
            )

            self._write_checksums(new_checksums)

        return input
