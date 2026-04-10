# cos-vectors-embed

![Python](https://img.shields.io/badge/python-%3E%3D3.9-blue)
![License](https://img.shields.io/badge/license-Apache%202.0-blue)

[中文版](README_zh.md)

CLI tool for vectorizing content and storing in Tencent COS Vector Buckets.

## Supported Commands

**cos-vectors-embed put**: Embed text, file content, or COS objects and store them as vectors in a COS vector index.
You can create and ingest vector embeddings into a COS vector index using a single put command. You specify the data input you want to create an embedding for, an embedding model ID, your COS vector bucket name, and COS vector index name. The command supports several input formats including inline text strings, local text files, COS objects via `cos://` URIs, and batch processing via local glob patterns or COS prefix wildcards. The command generates embeddings using the OpenAI-compatible `/v1/embeddings` protocol. If you are ingesting embeddings for multiple files, it automatically uses parallel batch processing with configurable workers and batch sizes to maximize throughput.

**Note**: Each file is processed as a single embedding. Document chunking is not currently supported.

**cos-vectors-embed query**: Embed a query input and search for similar vectors in a COS vector index.
You can perform similarity queries for vector embeddings in your COS vector index using a single query command. You specify your query input, an embedding model ID, the vector bucket name, and vector index name. The command accepts several types of query inputs: a text string or a local text file or a single COS text object. The command generates embeddings for your query using the specified model and then performs a similarity search to find the most relevant matches. You can control the number of results returned, apply metadata filters to narrow your search, and choose whether to include distance scores and metadata in the results.

## Installation and Configuration

### Prerequisites

- Python 3.9 or higher
- Tencent Cloud COS credentials (`COS_SECRET_ID` and `COS_SECRET_KEY`)
- Access to an OpenAI-compatible embedding API (API base URL + API key)
- A COS vector bucket and at least one vector index created in your Tencent Cloud account

### Quick Install (Recommended)

```bash
pip install cos-vectors-embed-cli
```

After installation, use the `cos-vectors-embed` command in your terminal.

### Development Install

```bash
# Clone the repository
git clone https://github.com/TencentCloud/cos-vectors-embed-cli.git
cd cos-vectors-embed-cli

# Install in development mode
pip install -e .
```

**Note**: All dependencies (`cos-python-sdk-v5`, `click`, `rich`) are automatically installed when you install the package via pip.

### Quick Start

#### 1. Configure credentials

```bash
# COS credentials
export COS_SECRET_ID="your-secret-id"
export COS_SECRET_KEY="your-secret-key"

# COS region and vectors service domain
export COS_REGION="ap-guangzhou"
# COS_DOMAIN is optional — auto-generated as vectors.{region}.coslake.com if not set
# export COS_DOMAIN="vectors.ap-guangzhou.coslake.com"

# Embedding API credentials
export EMBEDDING_API_BASE="https://api.openai.com/v1"
export EMBEDDING_API_KEY="sk-..."
```

#### 2. Embed text and store as a vector

```bash
cos-vectors-embed put \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text-value "Hello, world!"
```

#### 3. Query for similar vectors

```bash
cos-vectors-embed query \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text-value "Hello, world!" \
  --top-k 5
```

## Core Concepts

| Concept | Description |
|---------|-------------|
| **Vector Bucket** | A COS bucket enabled for vector storage. Created and managed through Tencent Cloud Console. |
| **Index** | A vector index within a vector bucket. Stores vector embeddings with associated metadata. Each index has a configured dimension size. |
| **Embedding Provider** | The service that converts text into vector embeddings. Currently supports the `openai-compatible` provider using the `/v1/embeddings` protocol. |
| **Vector Key** | A unique identifier for each vector in an index. Can be auto-generated (UUID), derived from filename (`--filename-as-key`), or explicitly set (`--key`). |
| **Metadata** | Key-value pairs associated with each vector. Includes system metadata (source location, content type) and optional user metadata. Used for filtering in queries. |
| **COS URI** | A URI format for referencing COS objects: `cos://bucket-name/object-key`. Supports single objects and prefix patterns with wildcards (`cos://bucket/prefix/*`). |

> For more details about COS Vector Storage, see the [Tencent Cloud COS Vector Storage Documentation](https://cloud.tencent.com/document/product/436/126985).

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `COS_SECRET_ID` | Yes | Tencent Cloud COS SecretId |
| `COS_SECRET_KEY` | Yes | Tencent Cloud COS SecretKey |
| `COS_TOKEN` | No | Temporary security token (for temporary credentials) |
| `COS_REGION` | Yes* | COS region (e.g. `ap-guangzhou`). Can also be set via `--region` CLI option. |
| `COS_DOMAIN` | No | COS Vectors service domain (e.g. `vectors.ap-guangzhou.coslake.com`). Can also be set via `--domain` CLI option. If not set, auto-generated from region as `vectors.{region}.coslake.com`. |
| `EMBEDDING_API_BASE` | Yes* | Embedding API base URL (e.g. `https://api.openai.com/v1`). Can also be set via `--embedding-api-base`. |
| `EMBEDDING_API_KEY` | Yes* | Embedding API key. Can also be set via `--embedding-api-key`. |

\* Can be provided via CLI options instead of environment variables.

### Configuration Priority

Configuration values are resolved in the following priority order (highest to lowest):

1. **Sub-command CLI options** — e.g. `cos-vectors-embed put --region ap-beijing ...` overrides the global `--region`
2. **Global CLI options** — e.g. `cos-vectors-embed --region ap-guangzhou put ...`
3. **Environment variables** — e.g. `COS_REGION=ap-guangzhou`
4. **Auto-generated defaults** — `COS_DOMAIN` is auto-generated from region as `vectors.{region}.coslake.com` if not explicitly set

### Embedding Provider

The tool uses the OpenAI-compatible `/v1/embeddings` protocol. Configure via environment variables or CLI options:

```bash
# Via environment variables
export EMBEDDING_API_BASE="https://api.openai.com/v1"
export EMBEDDING_API_KEY="sk-..."

# Or via CLI options
cos-vectors-embed put --embedding-api-base https://api.openai.com/v1 --embedding-api-key sk-... ...
```

Any API service that implements the OpenAI `/v1/embeddings` endpoint can be used (e.g. OpenAI, Azure OpenAI, local models via vLLM/Ollama, etc.).

## Usage Examples

### Put Vectors

#### 1. Embed inline text

```bash
cos-vectors-embed \
  --region ap-guangzhou \
  --domain vectors.ap-guangzhou.coslake.com \
  put \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text-value "Hello, world!" \
  --embedding-api-base https://api.openai.com/v1 \
  --embedding-api-key sk-xxx
```

#### 2. Embed a local text file

```bash
cos-vectors-embed put \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text document.txt \
  --filename-as-key
```

#### 3. Embed local text files with wildcard pattern

```bash
cos-vectors-embed put \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text "docs/*.txt" \
  --filename-as-key \
  --max-workers 8 \
  --batch-size 200
```

#### 4. Embed a COS object

```bash
cos-vectors-embed put \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text "cos://source-bucket-1250000000/documents/report.txt"
```

#### 5. Embed COS objects with prefix wildcard

```bash
cos-vectors-embed put \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text "cos://source-bucket-1250000000/documents/*" \
  --filename-as-key
```

#### 6. Embed with custom metadata

```bash
cos-vectors-embed put \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text-value "Financial report Q4" \
  --metadata '{"category": "finance", "quarter": "Q4"}'
```

#### 8. Embed with custom vector key

```bash
cos-vectors-embed put \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text-value "Custom key example" \
  --key "my-custom-key-1"
```

#### 9. Embed with key prefix

```bash
cos-vectors-embed put \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text document.txt \
  --filename-as-key \
  --key-prefix "docs/"
```

#### 9. Embed with extra inference parameters

```bash
cos-vectors-embed put \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text-value "Custom parameters" \
  --embedding-inference-params '{"dimensions": 512}'
```

### Query Vectors

#### 1. Direct text query

```bash
cos-vectors-embed \
  --region ap-guangzhou \
  --domain vectors.ap-guangzhou.coslake.com \
  query \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text-value "search query" \
  --top-k 10 \
  --embedding-api-base https://api.openai.com/v1 \
  --embedding-api-key sk-xxx
```

#### 2. Query with metadata filter

```bash
cos-vectors-embed query \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text-value "search query" \
  --filter '{"category": {"$eq": "finance"}}' \
  --top-k 5
```

#### 3. Query with table output format

```bash
cos-vectors-embed query \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text-value "search query" \
  --output table
```

#### 4. Query without distance scores

```bash
cos-vectors-embed query \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text-value "search query" \
  --no-return-distance
```

#### 5. Query without metadata

```bash
cos-vectors-embed query \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text-value "search query" \
  --no-return-metadata
```

#### 6. Query using a local text file

```bash
cos-vectors-embed query \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text "./query.txt" \
  --top-k 10 \
  --output table
```

#### 7. Query using a COS text object

```bash
cos-vectors-embed query \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text "cos://source-bucket-1250000000/queries/query.txt" \
  --top-k 10
```

### Global Options

```bash
cos-vectors-embed --help           # Show help
cos-vectors-embed --version        # Show version
cos-vectors-embed --debug put ...  # Enable debug logging
```

## Command Parameters

### Global Options

| Option | Description |
|--------|-------------|
| `--region` | COS region (e.g. `ap-guangzhou`). Falls back to `COS_REGION` env var. |
| `--domain` | COS Vectors service domain (e.g. `vectors.ap-guangzhou.coslake.com`). Falls back to `COS_DOMAIN` env var. |
| `--debug` | Enable debug output with detailed logging. |
| `--version` | Show version and exit. |

### Put Command Parameters

**Required:**

| Parameter | Description |
|-----------|-------------|
| `--vector-bucket-name` | COS vector bucket name. |
| `--index-name` | Vector index name. |
| `--model-id` | Embedding model identifier. |

**Input Options (one required):**

| Parameter | Description |
|-----------|-------------|
| `--text-value` | Direct text string to embed. |
| `--text` | Text input — supports local file path (`./doc.txt`), glob pattern (`docs/*.txt`), COS URI (`cos://bucket/key`), or COS prefix (`cos://bucket/prefix/*`). |

**Optional:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--key` | Auto UUID | Custom vector key. Only for single-item puts. |
| `--key-prefix` | — | Prefix to prepend to all generated vector keys. |
| `--filename-as-key` | `false` | Use source filename as vector key (mutually exclusive with `--key`). |
| `--metadata` | — | Custom metadata as JSON string, e.g. `'{"category": "finance"}'`. |
| `--provider` | `openai-compatible` | Embedding provider type. |
| `--embedding-api-base` | — | Embedding API base URL. Falls back to `EMBEDDING_API_BASE` env var. |
| `--embedding-api-key` | — | Embedding API key. Falls back to `EMBEDDING_API_KEY` env var. |
| `--embedding-inference-params` | — | Extra inference parameters as JSON string. |
| `--max-workers` | `4` | Number of parallel worker threads for batch processing. |
| `--batch-size` | `100` | Number of items per storage batch. |
| `--output` | `json` | Output format: `json` or `table`. |
| `--region` | — | Override global `--region` for this command. |
| `--domain` | — | Override global `--domain` for this command. |

### Query Command Parameters

**Required:**

| Parameter | Description |
|-----------|-------------|
| `--vector-bucket-name` | COS vector bucket name. |
| `--index-name` | Vector index name. |
| `--model-id` | Embedding model identifier. |

**Query Input (one required):**

| Parameter | Description |
|-----------|-------------|
| `--text-value` | Direct text string to query with. |
| `--text` | Text file path or COS URI (`cos://bucket/key`) containing the query. |

**Optional:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--top-k` | `5` | Number of results to return. |
| `--filter` | — | Metadata filter as JSON string. See [Metadata Filtering](#metadata-filtering) below. |
| `--return-distance` / `--no-return-distance` | `true` | Whether to include distance scores in results. |
| `--return-metadata` / `--no-return-metadata` | `true` | Whether to include metadata in results. |
| `--provider` | `openai-compatible` | Embedding provider type. |
| `--embedding-api-base` | — | Embedding API base URL. Falls back to `EMBEDDING_API_BASE` env var. |
| `--embedding-api-key` | — | Embedding API key. Falls back to `EMBEDDING_API_KEY` env var. |
| `--output` | `json` | Output format: `json` or `table`. |
| `--region` | — | Override global `--region` for this command. |
| `--domain` | — | Override global `--domain` for this command. |

## Metadata

The tool automatically attaches system metadata to every vector. You can also add custom metadata.

### System Metadata Fields

| Field | Description | Example |
|-------|-------------|---------|
| `COSVECTORS-EMBED-SRC-LOCATION` | Source file path or URI of the embedded content. Only set when the source is a file or URI (not set for `--text-value` inline text). | `document.txt`, `cos://bucket/file.txt` |
| `COSVECTORS-EMBED-SRC-TYPE` | Content type of the embedded content. | `text` |

### Custom Metadata

Use `--metadata` to attach custom key-value pairs as a JSON string:

```bash
cos-vectors-embed put \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text-value "Financial report" \
  --metadata '{"category": "finance", "year": "2024"}'
```

**Merge behavior**: Custom metadata is merged with system metadata. If a custom key conflicts with a system metadata key, the **custom value takes priority**.

### Metadata Filtering

When querying vectors, you can use the `--filter` option to narrow results based on metadata fields. The filter must be a **JSON object** following the COS Vectors filter syntax.

> For the full filter syntax specification, see the [COS Vectors Filter Documentation](https://cloud.tencent.com/document/product/436/127723#b6562611-7753-46e8-9d1a-14264adc4165).

#### Supported Operators

| Operator | Type | Description |
|----------|------|-------------|
| `$eq` | Comparison | Equal to |
| `$ne` | Comparison | Not equal to |
| `$gt` | Comparison | Greater than |
| `$gte` | Comparison | Greater than or equal to |
| `$lt` | Comparison | Less than |
| `$lte` | Comparison | Less than or equal to |
| `$in` | Array | Matches any value in the array |
| `$nin` | Array | Does not match any value in the array |
| `$exists` | Existence | Checks if a field exists |
| `$and` | Logical | Logical AND (all conditions must match) |
| `$or` | Logical | Logical OR (any condition matches) |

#### Filter Examples

**Exact match:**

```bash
cos-vectors-embed query \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text-value "search query" \
  --filter '{"category": {"$eq": "finance"}}'
```

**Numeric comparison:**

```bash
# Vectors where year >= 2020
--filter '{"year": {"$gte": 2020}}'

# Vectors where score > 0.8 and score <= 1.0
--filter '{"$and": [{"score": {"$gt": 0.8}}, {"score": {"$lte": 1.0}}]}'
```

**IN / NOT IN:**

```bash
# Vectors where category is one of the listed values
--filter '{"category": {"$in": ["finance", "tech", "health"]}}'

# Vectors where status is NOT "archived" or "deleted"
--filter '{"status": {"$nin": ["archived", "deleted"]}}'
```

**Field existence check:**

```bash
# Only vectors that have a "summary" field
--filter '{"summary": {"$exists": true}}'
```

**Logical AND / OR combinations:**

```bash
# AND: category is "finance" AND year >= 2020
--filter '{"$and": [{"category": {"$eq": "finance"}}, {"year": {"$gte": 2020}}]}'

# OR: category is "finance" OR category is "tech"
--filter '{"$or": [{"category": {"$eq": "finance"}}, {"category": {"$eq": "tech"}}]}'
```

## Batch Processing & Wildcard Patterns

### Local Glob Patterns

Use standard glob wildcards to process multiple local files:

```bash
# Process all .txt files in a directory
cos-vectors-embed put \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text "docs/*.txt" \
  --filename-as-key
```

### COS Prefix Patterns

Use COS URI prefix patterns to process multiple objects from a COS bucket:

```bash
# Process all supported files under a COS prefix
cos-vectors-embed put \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text "cos://source-bucket-1250000000/documents/*" \
  --filename-as-key
```

**Note**: COS prefix patterns filter objects by supported file extensions. Only files with recognized text extensions (`.txt`, `.md`, `.csv`, `.json`, `.xml`, `.html`, `.yaml`, `.yml`, `.log`, `.py`, `.js`, `.ts`, `.java`, `.go`, etc.) are processed.

### Batch Processing Options

| Option | Default | Description |
|--------|---------|-------------|
| `--max-workers` | `4` | Number of parallel worker threads. Increase for higher throughput on large batches. |
| `--batch-size` | `100` | Number of vectors per storage batch sent to COS. |

### Error Resilience

Batch processing is designed to be resilient: if individual files fail (e.g. unreadable or encoding errors), the batch continues processing remaining files. A summary of successes and failures is displayed at the end.

## Architecture

```
cos_vectors/
├── cli.py                     # CLI entry point (Click Group)
├── commands/
│   ├── embed_put.py           # put subcommand
│   └── embed_query.py         # query subcommand
├── core/
│   ├── embedding_provider.py  # EmbeddingProvider ABC + OpenAI implementation
│   ├── cos_vector_service.py  # COS Vectors SDK wrapper
│   ├── unified_processor.py   # Processing pipeline
│   └── streaming_batch_orchestrator.py  # Batch processing
└── utils/
    ├── config.py              # COS configuration management
    ├── models.py              # Data models and utilities
    └── multimodal_helpers.py  # File I/O and encoding helpers
```

### Data Flow

```
CLI Input (text/file/COS URI)
    │
    ▼
Content Preparation (read local file / download COS object / use inline text)
    │
    ▼
Embedding Generation (OpenAI-compatible /v1/embeddings API)
    │
    ▼
Vector Assembly (key + embedding + metadata)
    │
    ▼
COS Vector Storage (put_vectors API → vector bucket/index)
```

For batch inputs (glob patterns or COS prefix wildcards), the **StreamingBatchOrchestrator** manages the flow:
1. **Stream** — Files are discovered and chunked using `iglob` (local) or `list_objects` pagination (COS)
2. **Parallel Embed** — Each chunk is processed with a `ThreadPoolExecutor` (`--max-workers`)
3. **Batch Store** — Assembled vectors are stored in batches (`--batch-size`)

## Troubleshooting

### Common Errors

**COS credentials not found:**
```
ValueError: COS credentials are required. Set COS_SECRET_ID and COS_SECRET_KEY environment variables.
```
→ Ensure `COS_SECRET_ID` and `COS_SECRET_KEY` are set in your environment.

**Region or domain not set:**
```
ValueError: Region is required. Use --region option or set COS_REGION environment variable.
ValueError: Domain is required. Use --domain option, set COS_DOMAIN environment variable, or provide --region to auto-generate domain.
```
→ Set `COS_REGION` environment variable or use `--region` CLI option. The domain will be auto-generated from region if not set explicitly.

**Embedding API not configured:**
```
UsageError: Embedding API base URL is required.
```
→ Set `EMBEDDING_API_BASE` and `EMBEDDING_API_KEY` environment variables, or use `--embedding-api-base` and `--embedding-api-key` CLI options.

**No files matched pattern:**
```
Warning: No files matched pattern 'docs/*.txt'
```
→ Verify that the glob pattern matches existing files. Check the current working directory and file extensions.

**Invalid metadata JSON:**
```
UsageError: Invalid --metadata JSON: ...
```
→ Ensure the `--metadata` value is valid JSON. Use single quotes around the JSON string and double quotes inside.

### Debug Mode

Use `--debug` to enable detailed logging for troubleshooting:

```bash
cos-vectors-embed --debug put \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text-value "debug example"
```

Debug mode shows:
- COS client creation status
- Auto-detected index dimensions
- Embedding generation progress
- Detailed error stack traces

## FAQ

**Q: Which embedding providers are supported?**

A: Currently, the tool supports the `openai-compatible` provider, which uses the standard OpenAI `/v1/embeddings` API protocol. Any service that implements this protocol can be used, including OpenAI, Azure OpenAI, and local model servers like vLLM or Ollama.

**Q: What file types are supported for batch processing?**

A: Text files: `.txt`, `.md`, `.csv`, `.json`, `.xml`, `.html`, `.htm`, `.yaml`, `.yml`, `.log`, `.cfg`, `.ini`, `.conf`, `.py`, `.js`, `.ts`, `.java`, `.c`, `.cpp`, `.h`, `.go`, `.rs`, `.rb`, `.php`, `.sh`, `.bash`.

**Q: How does the COS URI format work?**

A: COS URIs follow the format `cos://bucket-name/object-key`. For single objects, use the full key (e.g. `cos://mybucket/docs/file.txt`). For batch processing, use a prefix with a wildcard (e.g. `cos://mybucket/docs/*`).

**Q: How are vector keys generated?**

A: By default, a UUID is auto-generated for each vector. Use `--key` to set an explicit key (single-item only), `--filename-as-key` to use the source filename, or `--key-prefix` to add a prefix to any generated key.

**Q: Can I use a temporary security token?**

A: Yes. Set the `COS_TOKEN` environment variable with your temporary security token. This is used alongside `COS_SECRET_ID` and `COS_SECRET_KEY` for temporary credential authentication.

## License

This project is licensed under the [Apache License 2.0](LICENSE).
