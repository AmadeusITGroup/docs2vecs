from docs2vecs.subcommands.indexer.document import Chunk


class Document:
    def __init__(self, filename: str, source_url: str = "",  tag = "", text: str = ""):
        self.filename: str = filename
        self.source_url: str = source_url
        self.tag = tag
        self.text: str = text
        self.chunks: set[Chunk] = set()


    def add_chunk(self, chunk: Chunk):
        self.chunks.add(chunk)

    def __str__(self) -> str:
        return f"filename: {self.filename}, source_url: {self.source_url}, text: {self.text}, chunks: {self.chunks}"
