"""Skill that extracts chunk content from Documents and writes it to a JSON file.

Use this skill at any point in a pipeline to capture intermediate state,
e.g. after a splitter, so the output can be checksummed for change detection
without running expensive downstream skills like embedding and indexing.

Only the chunk text content is written as a sorted JSON array of strings —
volatile metadata like filenames, document IDs, and timestamps are excluded
so the checksum remains stable when the underlying text hasn't changed.

When ``checksum_path`` is configured, the skill compares the current content
hash against a previously stored one. If unchanged and
``skip_downstream_if_unchanged`` is true, all chunks are removed from the
documents so downstream skills (embedding, indexing) naturally skip
processing — enabling a single-config pipeline with a built-in change gate.
"""

import hashlib
import json
import os
from typing import List, Optional

from docs2vecs.subcommands.indexer.config.config import Config
from docs2vecs.subcommands.indexer.document import Document
from docs2vecs.subcommands.indexer.skills.skill import IndexerSkill


class JSONWriterSkill(IndexerSkill):
    """Extract text content from all chunks and write it as a sorted JSON array.

    The output is a flat list of strings (one per non-empty chunk), sorted
    alphabetically for deterministic checksumming. Documents are passed
    through unchanged for downstream skills — unless ``checksum_path`` is
    set and the content hasn't changed, in which case chunks are stripped
    so downstream embedding/indexing skills skip processing.

    Config params:
        output_path (str): Path to the output JSON file (default:
                           ``data/pipeline_output.json``). Parent
                           directories are created automatically.
        checksum_path (str, optional): Path to store/read a SHA-256
                           checksum of the JSON output. When set, the
                           skill compares the current checksum against the
                           stored one to detect content changes.
        skip_downstream_if_unchanged (bool, optional): If true (default)
                           and ``checksum_path`` is set, remove all chunks
                           from documents when content is unchanged. This
                           causes downstream skills (embedding, indexing)
                           to skip processing. Set to false to always pass
                           chunks through regardless of change detection.
    """

    def __init__(self, skill_config: dict, global_config: Config) -> None:
        super().__init__(skill_config, global_config)
        self._output_path = self._config.get("output_path", "data/pipeline_output.json")
        self._checksum_path = self._config.get("checksum_path", None)
        self._skip_if_unchanged = self._config.get("skip_downstream_if_unchanged", True)

    def _compute_checksum(self, content_bytes: bytes) -> str:
        return hashlib.sha256(content_bytes).hexdigest()

    def _read_stored_checksum(self) -> Optional[str]:
        if self._checksum_path and os.path.isfile(self._checksum_path):
            try:
                with open(self._checksum_path, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except Exception as e:
                self.logger.warning(f"Failed to read stored checksum: {e}")
        return None

    def _write_checksum(self, checksum: str) -> None:
        if self._checksum_path:
            os.makedirs(os.path.dirname(self._checksum_path) or ".", exist_ok=True)
            with open(self._checksum_path, "w", encoding="utf-8") as f:
                f.write(checksum)

    def run(self, input: Optional[List[Document]] = None) -> List[Document]:
        if not input:
            self.logger.warning("JSONWriterSkill received no input — nothing to write.")
            return input or []

        # Collect only the content from every chunk across all documents
        contents = []
        for doc in input:
            for chunk in doc.chunks:
                if chunk.content:
                    contents.append(chunk.content)

        # Sort for deterministic output (stable checksums)
        contents.sort()

        os.makedirs(os.path.dirname(self._output_path) or ".", exist_ok=True)

        json_bytes = json.dumps(contents, indent=2, ensure_ascii=False).encode("utf-8")

        with open(self._output_path, "wb") as f:
            f.write(json_bytes)

        self.logger.info(
            "Wrote %d chunk content entries to %s",
            len(contents),
            self._output_path,
        )

        # ── Checksum-based change gate ──────────────────────────
        if self._checksum_path:
            new_checksum = self._compute_checksum(json_bytes)
            old_checksum = self._read_stored_checksum()

            if old_checksum and new_checksum == old_checksum and self._skip_if_unchanged:
                self.logger.info(
                    "Content unchanged (checksum: %s) — stripping chunks to skip downstream processing.",
                    new_checksum[:12],
                )
                for doc in input:
                    doc.chunks = set()
            else:
                if old_checksum:
                    self.logger.info(
                        "Content changed (old: %s, new: %s) — passing chunks to downstream skills.",
                        old_checksum[:12],
                        new_checksum[:12],
                    )
                else:
                    self.logger.info(
                        "No previous checksum found — passing chunks to downstream skills (first run).",
                    )

            # Always save the new checksum
            self._write_checksum(new_checksum)

        # Pass-through: downstream skills can still consume the documents
        return input
