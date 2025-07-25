from docs2vecs.subcommands.indexer.skills import FaissVectorStoreSkill
from docs2vecs.subcommands.indexer.document.document import Document
from docs2vecs.subcommands.indexer.document import Chunk
from langchain_community.vectorstores import FAISS
from pathlib import Path
import shutil


def test_faiss_vector_store_skill() -> None:
    db_path = Path("tests\\test_index\\my_index_test.faiss")
    files_path = "tests\\test_index\\test_file.txt"
    number_of_chunks = 1

    vec_store = FaissVectorStoreSkill(
        config={
            "type": "vector-store",
            "name": "faissdb",
            "params": {
                "collection_name": "test_collection",
                "db_path": db_path,
                "dimension": 384,  # Example dimension, adjust as needed
                "overwrite_index": False,
            },
        },
        global_config=None,
        vector_store_tracker=None,
    )

    chunk_dict = {
        "document_id": "doc_1",
        "document_name": "test_doc",
        "tag": "test_tag",
        "content": "This is a test chunk.",
        "chunk_id": "chunk_1",
        "source_link": files_path,
        "embedding": [0.1] * 384,  # Example embedding
    }
    chunk = Chunk()
    chunk.document_id = chunk_dict["document_id"]
    chunk.document_name = chunk_dict["document_name"]
    chunk.tag = chunk_dict["tag"]
    chunk.content = chunk_dict["content"]
    chunk.chunk_id = chunk_dict["chunk_id"]
    chunk.source_link = chunk_dict["source_link"]
    chunk.embedding = chunk_dict["embedding"]

    doc = Document(
        filename="test_doc",
        source_url=files_path,
        tag="test_tag",
        text="This is a test document.",
    )
    doc.add_chunk(chunk)

    # Run the skill with the document
    vec_store.run(input=[doc])
    # load the database to verify the document was added
    loaded_faiss = FAISS.load_local(
        db_path,
        embeddings=_dummy_embedding_function(doc),
        allow_dangerous_deserialization=True,
    )
    docstore = loaded_faiss.docstore
    docstore_dict = docstore._dict
    assert len(list(docstore_dict)) == number_of_chunks
    for doc_id, doc in docstore_dict.items():
        id = doc_id
        content = doc.page_content
        metadata = doc.metadata

    assert id == chunk.chunk_id
    assert content == chunk.content
    assert metadata == {"source": chunk.source_link, "tags": chunk.tag}
    shutil.rmtree(db_path)  # Clean up the test database file


def _dummy_embedding_function(text: str) -> list[float]:
    # This is a dummy implementation.
    return [0.1] * 384
