import json
from pathlib import Path
from typing import List
from typing import Optional

from docs2vecs.subcommands.indexer.config.config import Config
from docs2vecs.subcommands.indexer.document import Chunk
from docs2vecs.subcommands.indexer.document.document import Document
from docs2vecs.subcommands.indexer.skills.skill import IndexerSkill


class TeamsQnALoaderSkill(IndexerSkill):
    """A skill that loads enriched Q&A pairs from the FAQ pipeline JSON output.
    
    The JSON file should be an array of enriched Q&A objects with:
    - thread_id: Unique identifier for the conversation thread
    - question: Original question text
    - rephrased_question: AI-polished question (used for embedding)
    - rephrased_answer: AI-summarized answer (used as content)
    - topic: Clustered topic category
    - key_phrases: Extracted key phrases
    - question_sender: Original question author
    - timestamp: Message timestamp
    - answers: Array of original answers
    
    Configuration parameters:
    - file_path (str): Path to the enriched Q&A JSON file
    """

    def __init__(self, skill_config: dict, global_config: Config) -> None:
        super().__init__(skill_config, global_config)
        self._file_path = Path(self._config["file_path"]).expanduser().resolve()
        self.tag = self._config.get("tag", "enriched-qna")

    def run(self, documents: Optional[List[Document]]) -> List[Document]:
        """Load enriched Q&A pairs from JSON file and create Document objects with chunks.

        Args:
            documents: Not used by this skill (loader skill)

        Returns:
            List of Documents with chunks populated from enriched Q&A JSON
        """
        self.logger.info(f"Running TeamsQnALoaderSkill on {self._file_path}...")

        if not self._file_path.exists():
            raise FileNotFoundError(f"Enriched Q&A JSON file not found: {self._file_path}")

        # Load JSON file
        with self._file_path.open('r', encoding='utf-8') as f:
            qna_list = json.load(f)

        if not qna_list:
            self.logger.warning(f"No Q&A pairs found in JSON file: {self._file_path}")
            return []

        if not isinstance(qna_list, list):
            raise ValueError(f"Expected JSON array of Q&A objects, got {type(qna_list).__name__}")

        result = []
        
        # Process each enriched Q&A pair
        for idx, qna in enumerate(qna_list):
            # Extract rephrased question and answer, falling back to originals
            question = qna.get("rephrased_question") or qna.get("question", "")
            answer = qna.get("rephrased_answer") or self._get_best_answer(qna)
            
            # Skip if no meaningful content
            if not question.strip() or not answer.strip():
                self.logger.debug(f"Skipping Q&A pair {idx} - missing question or answer")
                continue
            
            # Build content with both question and answer
            topic = qna.get("topic", "General")
            content = f"Q: {question}\n\nA: {answer}"
            
            # Generate document ID from thread_id or index
            thread_id = qna.get("thread_id") or f"qna_{idx}"
            document_id = self._sanitize_id(thread_id)
            
            # Use source_link from the Q&A pair (Teams message deep link) if available
            source_url = qna.get("source_link", "").strip()
            
            # Create a Document object
            doc = Document(filename=str(self._file_path))
            
            # Create a Chunk object from the Q&A pair
            chunk = Chunk()
            chunk.document_id = document_id
            chunk.document_name = f"{topic} - FAQ"
            chunk.tag = self.tag
            chunk.content = content
            chunk.chunk_id = f"{document_id}_chunk_0"
            chunk.source_link = source_url
            
            # Add chunk to document
            doc.add_chunk(chunk)
            result.append(doc)
            
            self.logger.debug(f"Loaded Q&A: {document_id} | Topic: {topic}")

        self.logger.info(f"Successfully loaded {len(result)} enriched Q&A pairs from JSON")

        return result

    def _get_best_answer(self, qna: dict) -> str:
        """Get the best answer from the answers array, preferring expert answers."""
        answers = qna.get("answers", [])
        if not answers:
            return ""
        
        # Prefer expert answers
        expert_answers = [a for a in answers if a.get("is_expert", False)]
        if expert_answers:
            return expert_answers[0].get("answer", "")
        
        # Fall back to first answer
        return answers[0].get("answer", "")

    def _sanitize_id(self, thread_id: str) -> str:
        """Sanitize thread_id to be a valid document ID."""
        # Remove any characters that might cause issues in Azure Search
        import re
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', str(thread_id))
        return sanitized[:128]  # Limit length
