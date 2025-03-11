import fnmatch
import os
from pathlib import Path
from typing import List
from typing import Optional

from docs2vecs.subcommands.indexer.config.config import Config
from docs2vecs.subcommands.indexer.document.document import Document
from docs2vecs.subcommands.indexer.skills.skill import IndexerSkill


class FileScannerSkill(IndexerSkill):
    """A skill that scans a directory for files and returns them as Documents.

    Configuration parameters:
    - path (str): The path to the directory to scan
    - recursive (bool): If true, recursively search the directory
    - filter (List[str]): List of patterns to filter by
    """

    def __init__(self, skill_config: dict, global_config: Config) -> None:
        super().__init__(skill_config, global_config)
        self._path = Path(self._config["path"]).expanduser().resolve()
        self._recursive = self._config.get("recursive", False)
        self._filter = self._config.get("filter", [])
        self._tag = self._config.get("tag", "default")

    def run(self, documents: Optional[List[Document]]) -> List[Document]:
        """Scan directory and return list of Documents with file paths.

        Args:
            documents: Not used by this skill

        Returns:
            List of Documents with file_name set to full file paths
        """
        self.logger.info("Running FileScannerSkill...")

        result = []

        # Get list of files
        if self._recursive:
            files = []
            for root, _, filenames in os.walk(self._path):
                for filename in filenames:
                    files.append(Path(root) / filename)
        else:
            files = [self._path / f for f in os.listdir(self._path) if (self._path / f).is_file()]

        # Filter files based on include/exclude patterns
        for file_path in files:
            # Keep if matches any include pattern
            if not self._filter or any(fnmatch.fnmatch(file_path.name, pattern) for pattern in self._filter):
                # Add file as document
                doc = Document(filename=file_path, tag=self._tag)
                result.append(doc)

        for doc in result:
            self.logger.info(f"Found file: {doc.filename}")

        self.logger.debug(f"Returning {len(result)} documents")

        return result
