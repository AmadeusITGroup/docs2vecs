"""Skill that extracts chunk content from Documents and writes it to a JSON file.

Use this skill at any point in a pipeline to capture intermediate state,
e.g. after a splitter, so the output can be checksummed for change detection
without running expensive downstream skills like embedding and indexing.

Only the chunk text content is written as a sorted JSON array of strings —
volatile metadata like filenames, document IDs, and timestamps are excluded
so the checksum remains stable when the underlying text hasn't changed.
"""

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
    through unchanged for downstream skills.

    Config params:
        output_path (str): Path to the output JSON file (default:
                           ``data/pipeline_output.json``). Parent
                           directories are created automatically.
    """

    def __init__(self, skill_config: dict, global_config: Config) -> None:
        super().__init__(skill_config, global_config)
        self._output_path = self._config.get("output_path", "data/pipeline_output.json")

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

        with open(self._output_path, "w", encoding="utf-8") as f:
            json.dump(contents, f, indent=2, ensure_ascii=False)

        self.logger.info(
            "Wrote %d chunk content entries to %s",
            len(contents),
            self._output_path,
        )

        # Pass-through: downstream skills can still consume the documents
        return input
