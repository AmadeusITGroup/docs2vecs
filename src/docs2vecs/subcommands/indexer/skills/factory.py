from enum import StrEnum

from docs2vecs.subcommands.indexer.config import Config
from docs2vecs.subcommands.indexer.db.mongodb import MongoDbConnection
from docs2vecs.subcommands.indexer.skills import AzureAda002EmbeddingSkill
from docs2vecs.subcommands.indexer.skills import AzureBlobStoreUploaderSkill
from docs2vecs.subcommands.indexer.skills import AzureVectorStoreSkill
from docs2vecs.subcommands.indexer.skills import ChromaDBVectorStoreSkill
from docs2vecs.subcommands.indexer.skills import DefaultFileReader
from docs2vecs.subcommands.indexer.skills import AzureDocumentIntelligenceSkill
from docs2vecs.subcommands.indexer.skills import FileScannerSkill
from docs2vecs.subcommands.indexer.skills import JiraLoaderSkill
from docs2vecs.subcommands.indexer.skills import LlamaFastembedEmbeddingSkill
from docs2vecs.subcommands.indexer.skills import RecursiveCharacterTextSplitter
from docs2vecs.subcommands.indexer.skills import ScrollWorldExporterSkill
from docs2vecs.subcommands.indexer.skills import SemanticSplitter
from docs2vecs.subcommands.indexer.skills import VectorStoreTracker
from docs2vecs.subcommands.indexer.skills import FaissVectorStoreSkill


class SkillType(StrEnum):
    EXPORTER = "exporter"
    FILE_SCANNER = "file-scanner"
    FILE_READER = "file-reader"
    EMBEDDING = "embedding"
    VECTOR_STORE = "vector-store"
    UPLOADER = "uploader"
    SPLITTER = "splitter"
    LOADER = "loader"


class AvailableSkillName(StrEnum):
    # exporters
    SCROLLWORD_EXPORTER = "scrollword-exporter"

    # file readers
    AZ_DOCUMENT_INTELLIGENCE = "azure-document-intelligence"
    MULTI_FILE_READER = "multi-file-reader"

    # file scanners
    MULTI_FILE_SCANNER = "multi-file-scanner"

    # vector stores
    AZ_AISearch = "azure-ai-search"
    CHROMADB = "chromadb"
    FAISSDB = "faissdb"

    # uplaoders
    AZ_BLOB_STORE = "azure-blob-store"

    # splitters
    SEMANTIC_SPLITTER = "semantic-splitter"
    RECURSIVE_CHARACTER_SPLITTER = "recursive-character-splitter"

    # embeddings
    AZ_ADA002_EMBEDDING = "azure-ada002-embedding"
    LLAMA_FASTEMBED = "llama-fastembed"

    # web loaders
    JIRA_LOADER = "jira-loader"


AVAILABLE_SKILLS = {
    SkillType.EXPORTER: {
        AvailableSkillName.SCROLLWORD_EXPORTER: ScrollWorldExporterSkill,
    },
    SkillType.FILE_SCANNER: {AvailableSkillName.MULTI_FILE_SCANNER: FileScannerSkill},
    SkillType.FILE_READER: {
        AvailableSkillName.AZ_DOCUMENT_INTELLIGENCE: AzureDocumentIntelligenceSkill,
        AvailableSkillName.MULTI_FILE_READER: DefaultFileReader,
    },
    SkillType.EMBEDDING: {
        AvailableSkillName.AZ_ADA002_EMBEDDING: AzureAda002EmbeddingSkill,
        AvailableSkillName.LLAMA_FASTEMBED: LlamaFastembedEmbeddingSkill,
    },
    SkillType.VECTOR_STORE: {
        AvailableSkillName.AZ_AISearch: AzureVectorStoreSkill,
        AvailableSkillName.CHROMADB: ChromaDBVectorStoreSkill,
        AvailableSkillName.FAISSDB: FaissVectorStoreSkill,
    },
    SkillType.UPLOADER: {AvailableSkillName.AZ_BLOB_STORE: AzureBlobStoreUploaderSkill},
    SkillType.SPLITTER: {
        AvailableSkillName.SEMANTIC_SPLITTER: SemanticSplitter,
        AvailableSkillName.RECURSIVE_CHARACTER_SPLITTER: RecursiveCharacterTextSplitter,
    },
    SkillType.LOADER: {AvailableSkillName.JIRA_LOADER: JiraLoaderSkill},
}


class SkillFactory:
    @classmethod
    def get_skill(cls, skill_config_dict: dict, global_config: Config):
        try:
            skill_type = SkillType(skill_config_dict["type"])
            avail_skill_name = AvailableSkillName(skill_config_dict["name"])
            return AVAILABLE_SKILLS[skill_type][avail_skill_name](skill_config_dict, global_config)
        except ValueError as error:
            raise ValueError(f"Unknown skill of type: {skill_config_dict['type']}, and name: {skill_config_dict['name']}") from error


class TrackerFactory:
    def get_tracker(global_config: Config):
        tracker_config_dict = global_config.get_tracker_config_dict()
        if tracker_config_dict:
            db_config = tracker_config_dict["params"]["database"]
            db_connection = DBFactory.get_db(db_config, global_config)

            return VectorStoreTracker(db_connection=db_connection)
        return None


class DBFactory:
    def get_db(db_config_dict: dict, global_config: Config = None):
        if db_config_dict["type"] == "mongodb":
            return MongoDbConnection(
                connection_string=db_config_dict["connection_string"],
                db_name=db_config_dict["db_name"],
                col_name=db_config_dict["collection_name"],
            )
        raise ValueError(f"Unknown db type: {db_config_dict['type']}")