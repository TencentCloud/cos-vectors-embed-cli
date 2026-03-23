# cos-vectors-embed-cli

CLI tool for vectorizing content and storing in Tencent COS Vector Buckets.

Inspired by [oss-vectors-embed-cli](https://github.com/aliyun/oss-vectors-embed-cli) and [s3vectors-embed-cli](https://github.com/aws/s3vectors-embed-cli), this tool provides a consistent developer experience for COS vector operations.

## Features

- **`put` command** — Vectorize text/image content and write to COS vector index
  - Multiple input sources: inline text, local files, glob patterns
  - Custom vector keys and metadata
  - Parallel batch processing with progress bars
- **`query` command** — Similarity search on COS vector index
  - Text and image query support
  - Top-K, metadata filtering, distance scores
  - JSON and table output formats
- **Pluggable embedding** — Provider abstraction with OpenAI-compatible protocol
- **Rich terminal output** — Progress bars, tables, JSON formatting

## Installation

```bash
# From source
git clone <repo-url>
cd cos-vectors-embed-cli
pip install -e .

# Verify installation
cos-vectors-embed-cli --version
```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `COS_SECRET_ID` | Yes | COS SecretId |
| `COS_SECRET_KEY` | Yes | COS SecretKey |
| `COS_TOKEN` | No | Temporary security token |
| `COS_REGION` | No | COS region (e.g. `ap-guangzhou`) |
| `COS_DOMAIN` | No | Vectors service domain |
| `EMBEDDING_API_BASE` | No | Embedding API base URL |
| `EMBEDDING_API_KEY` | No | Embedding API key |

### Embedding Provider

The tool uses the OpenAI-compatible `/v1/embeddings` protocol by default. Configure via:

```bash
export EMBEDDING_API_BASE="https://api.openai.com/v1"
export EMBEDDING_API_KEY="sk-..."
```

Or pass directly:

```bash
cos-vectors-embed-cli put --embedding-api-base https://api.openai.com/v1 --embedding-api-key sk-...
```

## Usage

### Put Vectors

```bash
# Embed a text string
cos-vectors-embed-cli \
  --region ap-guangzhou \
  --domain vectors.ap-guangzhou.coslake.com \
  put \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text-value "Hello world" \
  --embedding-api-base https://api.openai.com/v1 \
  --embedding-api-key sk-xxx

# Embed a local text file
cos-vectors-embed-cli put \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text document.txt \
  --filename-as-key

# Batch embed with glob pattern
cos-vectors-embed-cli put \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text "docs/*.txt" \
  --filename-as-key \
  --max-workers 8 \
  --batch-size 200

# Embed with custom metadata
cos-vectors-embed-cli put \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text-value "Financial report Q4" \
  --metadata '{"category": "finance", "quarter": "Q4"}'

# Embed an image
cos-vectors-embed-cli put \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id clip-vit-base \
  --image photo.jpg
```

### Query Vectors

```bash
# Text query
cos-vectors-embed-cli \
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

# Query with metadata filter
cos-vectors-embed-cli query \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text-value "search query" \
  --filter 'category = "finance"' \
  --top-k 5

# Table output format
cos-vectors-embed-cli query \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text-value "search query" \
  --output table

# Query without distance scores
cos-vectors-embed-cli query \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text-value "search query" \
  --no-return-distance
```

### Global Options

```bash
cos-vectors-embed-cli --help
cos-vectors-embed-cli --version
cos-vectors-embed-cli --debug put ...    # Enable debug logging
```

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

## License

MIT
