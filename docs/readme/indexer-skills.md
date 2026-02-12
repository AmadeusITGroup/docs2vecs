# Indexer Skills Documentation

This document describes all available skills that can be used in the indexer pipeline. Each skill serves a specific purpose in the data processing pipeline, from data collection to vectorization and storage.

# Typical use cases
1. You have a bunch of files locally, and you would like to vectorize them? You'll typically need the following type of skills in your config file:

   1. A `file-scanner` to scan your local folder for documents to be indexed.
   2. A `file-reader` to read the content of the files.
   3. A `splitter` to split the documents into chunks.
   4. A `embedding` to generate embeddings from the chunks.
   5. A `vector-store` to store the embeddings.


2. You have a list of Confluence pages that you'd like to vectorize? You'll typically need the following type of skills in your config file:

   1. An `exporter` to export the Confluence pages to word documents.
   2. A `file-reader` to read the content of the word documents.
   3. A `splitter` to split the word documents into chunks.
   4. An `embedding` to generate embeddings from the chunks.
   5. A `vector-store` to store the embeddings.

3. You have a list of jira tickets that you'd like to vectorize? You'll typically need the following type of skills in your config file:

   1. A `jira-loader` to extract the data from the jira tickets
   2. A `splitter` to split the data into chunks.
   3. An `embedding` to generate embeddings from the chunks.
   4. A `vector-store` to store the embeddings.

4. You have FAQ documents exported from Confluence (`.docx` files) and want to extract Q&A pairs for vectorization? You'll typically need:

   1. An `exporter` (Scroll Word) or `file-scanner` to get the `.docx` files.
   2. A `confluence-faq-splitter` to extract Q&A pairs directly from the `.docx` headings.
   3. An `embedding` to generate embeddings from the Q&A chunks.
   4. A `vector-store` to store the embeddings.

5. You have enriched Q&A JSON output from a Teams FAQ pipeline and want to index it? You'll typically need:

   1. A `teams-qna-loader` to load the enriched Q&A pairs from the JSON file.
   2. An `embedding` to generate embeddings from the Q&A content.
   3. A `vector-store` to store the embeddings.


# Available Skills

<details><summary>Exporter Skills</summary>
Export data from one source to another. For example export a confluence page to a markdown file.

### Scroll Word Exporter
Exports a confluence page to Microsoft Word document

```yaml
- skill: &Exporter
    type: exporter
    name: scrollword-exporter
    params:
        api_url: https://scroll-word.us.exporter.k15t.app/api/public/1/exports
        auth_token: env.SWE_AUTH_TOKEN  # Scroll Word API token - can be obtained in Confluence
        poll_interval: 20   # Interval in seconds to check the status of the export
        export_folder: ~/Downloads/sw_export_temp   # Path where the exported file(s) should be saved
        scope: current  # Possible values: [current | descendants]. `current` exports just the current page, where `descendants` include all the descendants of the current page
        page_ids:   # List all page IDs that you'd like to export
          - 1774209540
        page_urls:  # List all page URLs that you'd like to export
          - https://your/corporate/confluence/prefix/wiki/spaces/your/confluence/space
        confluence_prefix: https://your/corporate/confluence/prefix # Your corporate Confluence URL
```
</details>

<details><summary>File Scanner Skills</summary>
Scans local folder for documents to be indexed.

### Multi-File Scanner
Scans local disk for documents to be indexed.

```yaml
- skill: &FileScanner
    type: file-scanner
    name: multi-file-scanner
    params:
        path: /path/to/your/documents
        filter: ["*.md"]    # Optional. If missing or empty - all the files will be considered. Use filter to narrow down the scope. Example: ["*.md", "*.txt"], ["globaldns*.md"]
        recursive: false    # false - scans only the folder indicated by `path`, true - scans the folder indicated by `path` and all its subfolders
```
</details>

<details><summary>File Reader Skills</summary>
Read the content of files.

### Azure Document Intelligence
Uses Azure Document Intelligence to extract the textual content from the input file.

```yaml
- skill: &DocumentIntelligence
    type: file-reader
    name: azure-document-intelligence
    params:
      endpoint: "https://your-form-recognizer-endpoint"
      api_key: env.AZURE_FORM_RECOGNIZER_KEY
```

### Multi File Reader
Supported file extensions:
- .md: Markdown files using UnstructuredMarkdownLoader
- .txt: Text files using TextLoader
- .pdf: PDF files using PyPDFLoader
- .doc, .docx: Word documents using UnstructuredWordDocumentLoader
- .ppt, .pptx: PowerPoint files using UnstructuredPowerPointLoader
- .xls, .xlsx: Excel files using UnstructuredExcelLoader

```yaml
- skill: &FileReader
    type: file-reader   # fixed parameter, do not change
    name: multi-file-reader # fixed parameter, do not change
```
</details>

<details><summary>Web loaders</summary>
Load data from web or structured files.

### Jira Loader
Loads data from Jira issues

```yaml
- skill: &JiraLoader
    type: loader
    name: jira-loader
    params:
        server_url: https://your/corporate/jira/url
        api_token: env.JIRA_PAT # Jira Personal Authentication Token. Can be obtained from Jira.
        issues: # You need to list jira issues one by one. This is intentional and allows you to control exactly what data goes in.
            - JSTAD-XYZ
            - JIRA-1234
```

### Teams Q&A Loader
Loads enriched Q&A pairs from a JSON file produced by the FAQ enrichment pipeline. Each Q&A pair becomes a single document with one chunk. The skill prefers rephrased questions/answers when available, falling back to originals.

```yaml
- skill: &TeamsQnALoader
    type: loader
    name: teams-qna-loader
    params:
      file_path: data/processed_output/enriched_qna.json   # Required: path to enriched Q&A JSON file
      tag: teams-faq                                        # Optional: tag for chunks (default: "enriched-qna")
```
</details>


<details><summary>Text Splitters</summary>
Split large text data into smaller chunks.

### Recursive Character Splitter
Splits text into chunks of a certain size, with overlap. Ideal to get you started.

```yaml
- skill: &TextSplitter
    type: splitter  # fixed parameter, do not change
    name: recursive-character-splitter # fixed parameter, do not change
    params:
      chunk_size: 1200  # you can experiment with this value. Don't go too big or too small
      overlap: 180  # you can experiment with this value. Don't go too big or too small
```

### Semantic Splitter
Splits text by grouping semantically equivalent chunks together. A bit more advanced than the Recursive Character Splitter.

```yaml
- skill: &SemanticSplitter
    type: splitter  # fixed parameter, do not change
    name: semantic-splitter # fixed parameter, do not change
    params:
        embedding_model: # Currently only Azure embedding models are supported
            endpoint: https://your-embedding-endpoint
            api_key: env.AZURE_EMBEDDING_KEY
            api_version: your-api-version
            deployment_name: your-deployment-name
```

### Confluence FAQ Splitter
Extracts Q&A pairs directly from FAQ `.docx` files exported from Confluence. Each heading that contains a `?` or starts with a problem/question pattern (e.g. "How do I", "I cannot") is treated as a question, and the body content below it becomes the answer. Each Q&A pair is produced as a single atomic chunk. No `file-reader` is needed — this skill reads `.docx` files directly via `python-docx`.

All parameters are optional with sensible defaults.

```yaml
- skill: &ConfluenceFAQSplitter
    type: splitter
    name: confluence-faq-splitter
    params:
      min_heading_level: 2          # Minimum heading level for questions (default: 2)
      max_heading_level: 6          # Maximum heading level for questions (default: 6)
      skip_headings:                # Heading titles to skip (default: ['summary'])
        - summary
      skip_patterns:                # Text patterns to skip in answer content (default: ['CONFIDENTIAL', 'Search the FAQ', 'Search Artifactory FAQ'])
        - CONFIDENTIAL
      question_patterns:            # Prefixes that indicate a question (default: ['i am ', 'i cannot ', 'how do i ', 'what is ', ...])
        - "how do i "
        - "i cannot "
      stop_sections:                # Regex patterns for sections that end Q&A extraction (default: ['related articles', 'see also'])
        - "^\\s*related\\s*articles?\\s*$"
```
</details>

<details><summary>Embedding</summary>
Generate embeddings from text. Embeddings is a vector representation of your text data.

### Azure Embeddings
Generates embeddings from text using embedding models deployed in Azure portal.

```yaml
- skill: &Ada002Embedding
    type: embedding
    name: azure-ada002-embedding
    params:     # Configuration can be retrieved from your Azure Portal
      endpoint: https://your-embedding-endpoint
      api_key: env.AZURE_EMBEDDING_API_KEY
      api_version: your-api-version
      deployment_name: your-deployment-name
```

### Fast Embed
Generates embeddings from text using `llama_index` library.

```yaml
- skill: &FastEmbed
    type: embedding
    name: llama-fastembed
```
</details>


<details><summary>Vector Store</summary>
Store embedding in a vector store.

### Azure AI Search
Stores embeddings in an Azure AI Search index.

```yaml
- skill: &AzureAISearch
    type: vector-store
    name: azure-ai-search
    params:
      endpoint: http://your-endpoint
      index_name: your-index-name
      api_key: env.AZURE_AI_SEARCH_API_KEY  # This parameter is optional. If missing, it will attempt an RBAC-based authentication. You might need to login to azure beforehand in your terminal using `azd` tool.
      field_mapping:    # on the left hand side is the internal representation. On the right hand side is your schema. You need to provide a mapping between our internal representation and your schema. If there's a field you don't need, just remove the line
        document_id: document_id
        content: content
        source_link: source_link
        document_name: document_name
        embedding: embedding
      overwrite_index: true  # true - before storing data, it will remove all the documents from your index. false - will append documents to your index
```

### Chroma
Stores embeddings in a Chroma vector store. Ideal for prototyping.

```yaml
- skill: &ChromaDbVectorStore
    type: vector-store
    name: chromadb
    params:
        db_path: path/to/where/your/chroma/db/is    # if you don't have any yet, a new one will be created at the specified path
        collection_name: replace-this-with-your-collection-name # if you don't have a collection yet, a new one will be created when documents are inserted
```

### FAISS
Stores embeddings in a faiss vector store. 

```yaml
- skill: &FaissDbVectorStore
    type: vector-store
    name: faissdb
    params:
        db_path: path/to/where/your/faiss/db/is    # if you don't have any yet, a new one will be created at the specified path
        dimension : replace-with-your-embeddings-dimension # Ensure that the correct dimension is provided. The expected dimension must match the embedding model you have selected
        overwrite_index: true  # true - before storing data, it will remove all the documents from your index. false - will append documents to your index

```     





</details>


# Contributors
All contributions are welcome!

The above list of skills and functionality covers the typical use cases identified so far.

If you have any cool ideas to extend the existing skills, or to create new ones, please contribute! Your contributions and feedback are the key to make this project a success!

## Thank you so much! <3
