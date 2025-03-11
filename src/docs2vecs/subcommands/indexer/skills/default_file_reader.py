from pathlib import Path
from typing import List
from typing import Optional

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders import UnstructuredExcelLoader
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_community.document_loaders import UnstructuredPowerPointLoader
from langchain_community.document_loaders import UnstructuredWordDocumentLoader

from docs2vecs.subcommands.indexer.config.config import Config
from docs2vecs.subcommands.indexer.document.document import Document
from docs2vecs.subcommands.indexer.skills.skill import FileLoaderSkill


class DefaultFileReader(FileLoaderSkill):
    """A skill that reads files based on their extension.

    Supported file extensions:
    - .md: Markdown files using UnstructuredMarkdownLoader
    - .txt: Text files using TextLoader
    - .pdf: PDF files using PyPDFLoader
    - .doc, .docx: Word documents using UnstructuredWordDocumentLoader
    - .ppt, .pptx: PowerPoint files using UnstructuredPowerPointLoader
    - .xls, .xlsx: Excel files using UnstructuredExcelLoader
    """

    def __init__(self, skill_config: dict, global_config: Config) -> None:
        super().__init__(skill_config, global_config)
        self._extension_handlers = {
            ".md": self._load_markdown,
            ".txt": self._load_text,
            ".pdf": self._load_pdf,
            ".doc": self._load_word,
            ".docx": self._load_word,
            ".ppt": self._load_powerpoint,
            ".pptx": self._load_powerpoint,
            ".xls": self._load_excel,
            ".xlsx": self._load_excel,
        }

    def run(self, documents: Optional[List[Document]]) -> List[Document]:
        """Process input documents by reading their content based on file extension.

        Args:
            documents: List of Documents with file_name set

        Returns:
            List of Documents with text content populated
        """
        self.logger.info("Running DefaultFileReader...")

        if not documents:
            self.logger.info("No input documents provided")
            return []

        result = []
        for doc in documents:
            file_path = Path(doc.filename)
            file_tag = doc.tag
            if not file_path.exists():
                self.logger.info(f"File not found: {file_path}")
                continue

            extension = file_path.suffix.lower()
            handler = self._extension_handlers.get(extension)

            if not handler:
                self.logger.info(f"Unsupported file extension: {extension} for file {file_path}")
                continue

            try:
                loaded_docs = handler(file_path, file_tag)
                result.extend(loaded_docs)
                self.logger.info(f"Successfully read file: {file_path}")
            except Exception as e:
                self.logger.info(f"Error reading file {file_path}: {e!s}")
                continue

        self.logger.info(f"Finished reading {len(result)} documents")

        return result

    def _load_markdown(self, file_path: Path, file_tag: str) -> List[Document]:
        """Load markdown files using UnstructuredMarkdownLoader."""
        loader = UnstructuredMarkdownLoader(str(file_path), mode="single")
        docs = loader.load()
        return [Document(filename=str(file_path), source_url=str(file_path), tag=file_tag, text=doc.page_content) for doc in docs]

    def _load_text(self, file_path: Path, file_tag: str) -> List[Document]:
        """Load text files using TextLoader."""
        loader = TextLoader(str(file_path))
        docs = loader.load()
        return [Document(filename=str(file_path), source_url=str(file_path), tag=file_tag, text=doc.page_content) for doc in docs]

    def _load_pdf(self, file_path: Path, file_tag: str) -> List[Document]:
        """Load PDF files using PyPDFLoader."""
        loader = PyPDFLoader(str(file_path))
        docs = loader.load()
        return [Document(filename=str(file_path), source_url=str(file_path), tag=file_tag, text=doc.page_content) for doc in docs]

    def _load_word(self, file_path: Path, file_tag: str) -> List[Document]:
        """Load Word documents using UnstructuredWordDocumentLoader."""
        loader = UnstructuredWordDocumentLoader(str(file_path))
        docs = loader.load()
        return [Document(filename=str(file_path), source_url=str(file_path), tag=file_tag, text=doc.page_content) for doc in docs]

    def _load_powerpoint(self, file_path: Path, file_tag: str) -> List[Document]:
        """Load PowerPoint files using UnstructuredPowerPointLoader."""
        loader = UnstructuredPowerPointLoader(str(file_path))
        docs = loader.load()
        return [Document(filename=str(file_path), source_url=str(file_path), tag=file_tag, text=doc.page_content) for doc in docs]

    def _load_excel(self, file_path: Path, file_tag: str) -> List[Document]:
        """Load Excel files using UnstructuredExcelLoader."""
        loader = UnstructuredExcelLoader(str(file_path))
        docs = loader.load()
        return [Document(filename=str(file_path), source_url=str(file_path), tag=file_tag, text=doc.page_content) for doc in docs]
