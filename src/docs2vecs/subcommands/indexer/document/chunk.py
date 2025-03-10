class Chunk:
    @classmethod
    def FromDict(dict):
        chunk = Chunk()
        chunk.document_id = dict["document_id"]
        chunk.document_name = dict["document_name"]
        chunk.tag = dict["document_tag"]
        chunk.content = dict["content"]
        chunk.chunk_id = dict["chunk_id"]
        chunk.source_link = dict["source_link"]
        chunk.embedding = dict["embedding"]
        return chunk

    def __init__(self):
        self.document_id = None
        self.document_name = None
        self.tag = None
        self.content = None
        self.chunk_id = None
        self.source_link = None
        self.embedding = []
        self._hash = None

    def __hash__(self):
        if self._hash is None:
            self._hash = hash(self.chunk_id)
        return self._hash

    def __eq__(self, other):
        if not isinstance(other, Chunk):
            return NotImplemented
        return self.chunk_id == other.chunk_id

    def to_dict(self):
        return {
            "document_id": self.document_id,
            "document_name": self.document_name,
            "tag": self.tag,
            "content": self.content,
            "chunk_id": self.chunk_id,
            "source_link": self.source_link,
            "embedding": self.embedding,
        }

    def __str__(self) -> str:
        return str(self.to_dict())
