# cos-vectors-embed

![Python](https://img.shields.io/badge/python-%3E%3D3.9-blue)
![License](https://img.shields.io/badge/license-Apache%202.0-blue)

用于向量化内容并存储到腾讯云 COS 向量存储桶的命令行工具。

## 支持的命令

**cos-vectors-embed put**：将文本、文件内容或 COS 对象进行向量化（Embedding），并存储到 COS 向量索引中。
你可以通过一条 put 命令创建向量嵌入并写入 COS 向量索引。只需指定要嵌入的数据输入、Embedding 模型 ID、COS 向量存储桶名称和向量索引名称即可。该命令支持多种输入格式，包括内联文本字符串、本地文本文件、通过 `cos://` URI 引用的 COS 对象，以及通过本地 glob 模式或 COS 前缀通配符进行的批量处理。命令使用 OpenAI 兼容的 `/v1/embeddings` 协议生成向量嵌入。如果需要处理多个文件，工具会自动使用可配置的并行 worker 和批量大小进行并行批量处理，以最大化吞吐量。

**注意**：每个文件作为一个整体生成单个向量嵌入，暂不支持文档分块。

**cos-vectors-embed query**：将查询输入进行向量化，并在 COS 向量索引中搜索相似向量。
你可以通过一条 query 命令对向量索引执行相似性查询。只需指定查询输入、Embedding 模型 ID、向量存储桶名称和向量索引名称。该命令支持多种查询输入类型：文本字符串、本地文本文件，或单个 COS 文本对象。命令会使用指定模型为查询输入生成向量嵌入，然后执行相似性搜索以找到最相关的匹配结果。你可以控制返回结果的数量、应用元数据过滤器缩小搜索范围，以及选择是否在结果中包含距离分数和元数据。

## 安装与配置

### 前置条件

- Python 3.9 或更高版本
- 腾讯云 COS 凭证（`COS_SECRET_ID` 和 `COS_SECRET_KEY`）
- 可用的 OpenAI 兼容 Embedding API（API 基础 URL + API 密钥）
- 在腾讯云账号中已创建 COS 向量存储桶和至少一个向量索引

### 快速安装（推荐）

```bash
pip install cos-vectors-embed-cli
```

安装完成后，在终端中使用 `cos-vectors-embed` 命令。

### 开发安装

```bash
# 克隆仓库
git clone https://github.com/TencentCloud/cos-vectors-embed-cli.git
cd cos-vectors-embed-cli

# 以开发模式安装
pip install -e .
```

**注意**：通过 pip 安装时，所有依赖项（`cos-python-sdk-v5`、`click`、`rich`）会自动安装。

### 快速开始

#### 1. 配置凭证

```bash
# COS 凭证
export COS_SECRET_ID="your-secret-id"
export COS_SECRET_KEY="your-secret-key"

# COS 地域和向量服务域名
export COS_REGION="ap-guangzhou"
# COS_DOMAIN 为可选项 — 未设置时将根据 region 自动生成为 vectors.{region}.coslake.com
# export COS_DOMAIN="vectors.ap-guangzhou.coslake.com"

# Embedding API 凭证
export EMBEDDING_API_BASE="https://api.openai.com/v1"
export EMBEDDING_API_KEY="sk-..."
```

#### 2. 向量化文本并存储

```bash
cos-vectors-embed put \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text-value "Hello, world!"
```

#### 3. 查询相似向量

```bash
cos-vectors-embed query \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text-value "Hello, world!" \
  --top-k 5
```

## 核心概念

| 概念 | 说明 |
|------|------|
| **向量存储桶（Vector Bucket）** | 启用了向量存储功能的 COS 存储桶。通过腾讯云控制台创建和管理。 |
| **索引（Index）** | 向量存储桶中的向量索引。存储向量嵌入及其关联的元数据。每个索引有配置的维度大小。 |
| **Embedding 提供者（Embedding Provider）** | 将文本转换为向量嵌入的服务。目前支持使用 `/v1/embeddings` 协议的 `openai-compatible` 提供者。 |
| **向量键（Vector Key）** | 索引中每个向量的唯一标识符。可以自动生成（UUID）、从文件名派生（`--filename-as-key`）或显式设置（`--key`）。 |
| **元数据（Metadata）** | 与每个向量关联的键值对。包括系统元数据（来源位置、内容类型）和可选的用户元数据。用于查询时的过滤。 |
| **COS URI** | 引用 COS 对象的 URI 格式：`cos://bucket-name/object-key`。支持单个对象和带通配符的前缀模式（`cos://bucket/prefix/*`）。 |

> 更多关于 COS 向量存储的详细说明，请参阅[腾讯云 COS 向量存储官方文档](https://cloud.tencent.com/document/product/436/126985)。

## 配置

### 环境变量

| 变量 | 是否必需 | 说明 |
|------|----------|------|
| `COS_SECRET_ID` | 是 | 腾讯云 COS SecretId |
| `COS_SECRET_KEY` | 是 | 腾讯云 COS SecretKey |
| `COS_TOKEN` | 否 | 临时安全令牌（用于临时凭证） |
| `COS_REGION` | 是* | COS 地域（如 `ap-guangzhou`）。也可通过 `--region` CLI 选项设置。 |
| `COS_DOMAIN` | 否 | COS 向量服务域名（如 `vectors.ap-guangzhou.coslake.com`）。也可通过 `--domain` CLI 选项设置。若未设置，将根据 region 自动生成为 `vectors.{region}.coslake.com`。 |
| `EMBEDDING_API_BASE` | 是* | Embedding API 基础 URL（如 `https://api.openai.com/v1`）。也可通过 `--embedding-api-base` 设置。 |
| `EMBEDDING_API_KEY` | 是* | Embedding API 密钥。也可通过 `--embedding-api-key` 设置。 |

\* 可以通过 CLI 选项替代环境变量提供。

### 配置优先级

配置值按以下优先级顺序解析（从高到低）：

1. **子命令 CLI 选项** — 例如 `cos-vectors-embed put --region ap-beijing ...` 会覆盖全局 `--region`
2. **全局 CLI 选项** — 例如 `cos-vectors-embed --region ap-guangzhou put ...`
3. **环境变量** — 例如 `COS_REGION=ap-guangzhou`
4. **自动生成的默认值** — `COS_DOMAIN` 未显式设置时，将根据 region 自动生成为 `vectors.{region}.coslake.com`

### Embedding 提供者

本工具使用 OpenAI 兼容的 `/v1/embeddings` 协议。通过环境变量或 CLI 选项配置：

```bash
# 通过环境变量
export EMBEDDING_API_BASE="https://api.openai.com/v1"
export EMBEDDING_API_KEY="sk-..."

# 或通过 CLI 选项
cos-vectors-embed put --embedding-api-base https://api.openai.com/v1 --embedding-api-key sk-... ...
```

任何实现了 OpenAI `/v1/embeddings` 端点的 API 服务都可以使用（如 OpenAI、Azure OpenAI、通过 vLLM/Ollama 运行的本地模型等）。

## 使用示例

### 存储向量（Put）

#### 1. 嵌入内联文本

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

#### 2. 嵌入本地文本文件

```bash
cos-vectors-embed put \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text document.txt \
  --filename-as-key
```

#### 3. 使用通配符模式嵌入本地文本文件

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

#### 4. 嵌入 COS 对象

```bash
cos-vectors-embed put \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text "cos://source-bucket-1250000000/documents/report.txt"
```

#### 5. 使用前缀通配符嵌入 COS 对象

```bash
cos-vectors-embed put \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text "cos://source-bucket-1250000000/documents/*" \
  --filename-as-key
```

#### 6. 使用自定义元数据嵌入

```bash
cos-vectors-embed put \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text-value "Financial report Q4" \
  --metadata '{"category": "finance", "quarter": "Q4"}'
```

#### 8. 使用自定义向量键嵌入

```bash
cos-vectors-embed put \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text-value "Custom key example" \
  --key "my-custom-key-1"
```

#### 9. 使用键前缀嵌入

```bash
cos-vectors-embed put \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text document.txt \
  --filename-as-key \
  --key-prefix "docs/"
```

#### 10. 使用额外推理参数嵌入

```bash
cos-vectors-embed put \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text-value "Custom parameters" \
  --embedding-inference-params '{"dimensions": 512}'
```

### 查询向量（Query）

#### 1. 直接文本查询

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

#### 2. 使用元数据过滤查询

```bash
cos-vectors-embed query \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text-value "search query" \
  --filter '{"category": {"$eq": "finance"}}' \
  --top-k 5
```

#### 3. 使用表格输出格式查询

```bash
cos-vectors-embed query \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text-value "search query" \
  --output table
```

#### 4. 查询（不返回距离分数）

```bash
cos-vectors-embed query \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text-value "search query" \
  --no-return-distance
```

#### 5. 查询（不返回元数据）

```bash
cos-vectors-embed query \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text-value "search query" \
  --no-return-metadata
```

#### 6. 使用本地文本文件查询

```bash
cos-vectors-embed query \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text "./query.txt" \
  --top-k 10 \
  --output table
```

#### 7. 使用 COS 文本对象查询

```bash
cos-vectors-embed query \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text "cos://source-bucket-1250000000/queries/query.txt" \
  --top-k 10
```

### 全局选项

```bash
cos-vectors-embed --help           # 显示帮助
cos-vectors-embed --version        # 显示版本
cos-vectors-embed --debug put ...  # 启用调试日志
```

## 命令参数

### 全局选项

| 选项 | 说明 |
|------|------|
| `--region` | COS 地域（如 `ap-guangzhou`）。回退到 `COS_REGION` 环境变量。 |
| `--domain` | COS 向量服务域名（如 `vectors.ap-guangzhou.coslake.com`）。回退到 `COS_DOMAIN` 环境变量。 |
| `--debug` | 启用详细调试日志输出。 |
| `--version` | 显示版本并退出。 |

### Put 命令参数

**必需参数：**

| 参数 | 说明 |
|------|------|
| `--vector-bucket-name` | COS 向量存储桶名称。 |
| `--index-name` | 向量索引名称。 |
| `--model-id` | Embedding 模型标识符。 |

**输入选项（至少需要一个）：**

| 参数 | 说明 |
|------|------|
| `--text-value` | 直接输入的文本字符串。 |
| `--text` | 文本输入 — 支持本地文件路径（`./doc.txt`）、glob 模式（`docs/*.txt`）、COS URI（`cos://bucket/key`）或 COS 前缀（`cos://bucket/prefix/*`）。 |

**可选参数：**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--key` | 自动 UUID | 自定义向量键。仅用于单项写入。 |
| `--key-prefix` | — | 添加到所有生成的向量键前面的前缀。 |
| `--filename-as-key` | `false` | 使用源文件名作为向量键（与 `--key` 互斥）。 |
| `--metadata` | — | 自定义元数据 JSON 字符串，如 `'{"category": "finance"}'`。 |
| `--provider` | `openai-compatible` | Embedding 提供者类型。 |
| `--embedding-api-base` | — | Embedding API 基础 URL。回退到 `EMBEDDING_API_BASE` 环境变量。 |
| `--embedding-api-key` | — | Embedding API 密钥。回退到 `EMBEDDING_API_KEY` 环境变量。 |
| `--embedding-inference-params` | — | 额外推理参数 JSON 字符串。 |
| `--max-workers` | `4` | 批量处理的并行 worker 线程数。 |
| `--batch-size` | `100` | 每批存储的向量数量。 |
| `--output` | `json` | 输出格式：`json` 或 `table`。 |
| `--region` | — | 覆盖全局 `--region`（仅对本命令生效）。 |
| `--domain` | — | 覆盖全局 `--domain`（仅对本命令生效）。 |

### Query 命令参数

**必需参数：**

| 参数 | 说明 |
|------|------|
| `--vector-bucket-name` | COS 向量存储桶名称。 |
| `--index-name` | 向量索引名称。 |
| `--model-id` | Embedding 模型标识符。 |

**查询输入（至少需要一个）：**

| 参数 | 说明 |
|------|------|
| `--text-value` | 直接输入的查询文本字符串。 |
| `--text` | 文本文件路径或 COS URI（`cos://bucket/key`），包含查询内容。 |

**可选参数：**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--top-k` | `5` | 返回结果数量。 |
| `--filter` | — | 元数据过滤 JSON 字符串。参见下方[元数据过滤](#元数据过滤)。 |
| `--return-distance` / `--no-return-distance` | `true` | 是否在结果中包含距离分数。 |
| `--return-metadata` / `--no-return-metadata` | `true` | 是否在结果中包含元数据。 |
| `--provider` | `openai-compatible` | Embedding 提供者类型。 |
| `--embedding-api-base` | — | Embedding API 基础 URL。回退到 `EMBEDDING_API_BASE` 环境变量。 |
| `--embedding-api-key` | — | Embedding API 密钥。回退到 `EMBEDDING_API_KEY` 环境变量。 |
| `--output` | `json` | 输出格式：`json` 或 `table`。 |
| `--region` | — | 覆盖全局 `--region`（仅对本命令生效）。 |
| `--domain` | — | 覆盖全局 `--domain`（仅对本命令生效）。 |

## 元数据

本工具会自动为每个向量附加系统元数据。你也可以添加自定义元数据。

### 系统元数据字段

| 字段 | 说明 | 示例 |
|------|------|------|
| `COSVECTORS-EMBED-SRC-LOCATION` | 嵌入内容的来源文件路径或 URI。仅在来源为文件或 URI 时设置（`--text-value` 内联文本不设置）。 | `document.txt`、`cos://bucket/file.txt` |
| `COSVECTORS-EMBED-SRC-TYPE` | 嵌入内容的内容类型。 | `text` |

### 自定义元数据

使用 `--metadata` 以 JSON 字符串形式附加自定义键值对：

```bash
cos-vectors-embed put \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text-value "Financial report" \
  --metadata '{"category": "finance", "year": "2024"}'
```

**合并行为**：自定义元数据会与系统元数据合并。如果自定义键与系统元数据键冲突，**自定义值优先**。

### 元数据过滤

查询向量时，可以使用 `--filter` 选项根据元数据字段筛选结果。过滤条件必须是 **JSON 对象**，遵循 COS 向量存储的过滤语法。

> 完整的过滤语法规范，请参阅 [COS 向量存储过滤文档](https://cloud.tencent.com/document/product/436/127723#b6562611-7753-46e8-9d1a-14264adc4165)。

#### 支持的操作符

| 操作符 | 类型 | 说明 |
|--------|------|------|
| `$eq` | 比较 | 等于 |
| `$ne` | 比较 | 不等于 |
| `$gt` | 比较 | 大于 |
| `$gte` | 比较 | 大于等于 |
| `$lt` | 比较 | 小于 |
| `$lte` | 比较 | 小于等于 |
| `$in` | 数组 | 匹配数组中任一值 |
| `$nin` | 数组 | 不匹配数组中任何值 |
| `$exists` | 存在性 | 检查字段是否存在 |
| `$and` | 逻辑 | 逻辑与（所有条件都必须匹配） |
| `$or` | 逻辑 | 逻辑或（任一条件匹配即可） |

#### 过滤示例

**精确匹配：**

```bash
cos-vectors-embed query \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text-value "搜索查询" \
  --filter '{"category": {"$eq": "finance"}}'
```

**数值比较：**

```bash
# year >= 2020 的向量
--filter '{"year": {"$gte": 2020}}'

# score > 0.8 且 score <= 1.0 的向量
--filter '{"$and": [{"score": {"$gt": 0.8}}, {"score": {"$lte": 1.0}}]}'
```

**IN / NOT IN：**

```bash
# category 是列出值之一的向量
--filter '{"category": {"$in": ["finance", "tech", "health"]}}'

# status 不是 "archived" 或 "deleted" 的向量
--filter '{"status": {"$nin": ["archived", "deleted"]}}'
```

**字段存在性检查：**

```bash
# 仅返回包含 "summary" 字段的向量
--filter '{"summary": {"$exists": true}}'
```

**逻辑 AND / OR 组合：**

```bash
# AND：category 是 "finance" 且 year >= 2020
--filter '{"$and": [{"category": {"$eq": "finance"}}, {"year": {"$gte": 2020}}]}'

# OR：category 是 "finance" 或 category 是 "tech"
--filter '{"$or": [{"category": {"$eq": "finance"}}, {"category": {"$eq": "tech"}}]}'
```

## 批量处理与通配符模式

### 本地 Glob 模式

使用标准 glob 通配符处理多个本地文件：

```bash
# 处理目录中所有 .txt 文件
cos-vectors-embed put \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text "docs/*.txt" \
  --filename-as-key
```

### COS 前缀模式

使用 COS URI 前缀模式处理 COS 存储桶中的多个对象：

```bash
# 处理 COS 前缀下所有支持的文件
cos-vectors-embed put \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text "cos://source-bucket-1250000000/documents/*" \
  --filename-as-key
```

**注意**：COS 前缀模式按支持的文件扩展名过滤对象。仅处理已识别的文本扩展名（`.txt`、`.md`、`.csv`、`.json`、`.xml`、`.html`、`.yaml`、`.yml`、`.log`、`.py`、`.js`、`.ts`、`.java`、`.go` 等）的文件。

### 批量处理选项

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `--max-workers` | `4` | 并行 worker 线程数。增大此值可提高大批量处理的吞吐量。 |
| `--batch-size` | `100` | 每批发送到 COS 的向量数量。 |

### 错误容忍

批量处理具有错误容忍能力：如果个别文件处理失败（如不可读或编码错误），批量处理会继续处理剩余文件。处理结束后会显示成功和失败的汇总信息。

## 架构

```
cos_vectors/
├── cli.py                     # CLI 入口（Click Group）
├── commands/
│   ├── embed_put.py           # put 子命令
│   └── embed_query.py         # query 子命令
├── core/
│   ├── embedding_provider.py  # EmbeddingProvider 抽象基类 + OpenAI 实现
│   ├── cos_vector_service.py  # COS 向量 SDK 封装
│   ├── unified_processor.py   # 处理管线
│   └── streaming_batch_orchestrator.py  # 批量处理
└── utils/
    ├── config.py              # COS 配置管理
    ├── models.py              # 数据模型与工具函数
    └── multimodal_helpers.py  # 文件 I/O 与编码辅助函数
```

### 数据流

```
CLI 输入 (文本/文件/COS URI)
    │
    ▼
内容准备 (读取本地文件 / 下载 COS 对象 / 使用内联文本)
    │
    ▼
向量嵌入生成 (OpenAI 兼容 /v1/embeddings API)
    │
    ▼
向量组装 (键 + 嵌入向量 + 元数据)
    │
    ▼
COS 向量存储 (put_vectors API → 向量存储桶/索引)
```

对于批量输入（glob 模式或 COS 前缀通配符），**StreamingBatchOrchestrator** 管理整个流程：
1. **流式发现** — 使用 `iglob`（本地）或 `list_objects` 分页（COS）发现并分块文件
2. **并行嵌入** — 每个分块通过 `ThreadPoolExecutor`（`--max-workers`）并行处理
3. **批量存储** — 组装好的向量按批次（`--batch-size`）存储

## 故障排查

### 常见错误

**COS 凭证未找到：**
```
ValueError: COS credentials are required. Set COS_SECRET_ID and COS_SECRET_KEY environment variables.
```
→ 确保环境中已设置 `COS_SECRET_ID` 和 `COS_SECRET_KEY`。

**地域或域名未设置：**
```
ValueError: Region is required. Use --region option or set COS_REGION environment variable.
ValueError: Domain is required. Use --domain option, set COS_DOMAIN environment variable, or provide --region to auto-generate domain.
```
→ 设置 `COS_REGION` 环境变量或使用 `--region` CLI 选项。域名将根据 region 自动生成（如未显式设置）。

**Embedding API 未配置：**
```
UsageError: Embedding API base URL is required.
```
→ 设置 `EMBEDDING_API_BASE` 和 `EMBEDDING_API_KEY` 环境变量，或使用 `--embedding-api-base` 和 `--embedding-api-key` CLI 选项。

**没有文件匹配模式：**
```
Warning: No files matched pattern 'docs/*.txt'
```
→ 验证 glob 模式是否匹配现有文件。检查当前工作目录和文件扩展名。

**无效的元数据 JSON：**
```
UsageError: Invalid --metadata JSON: ...
```
→ 确保 `--metadata` 的值是有效的 JSON。在 JSON 字符串外使用单引号，内部使用双引号。

### 调试模式

使用 `--debug` 启用详细日志以辅助排查问题：

```bash
cos-vectors-embed --debug put \
  --vector-bucket-name mybucket-1250000000 \
  --index-name myindex \
  --model-id text-embedding-3-small \
  --text-value "debug example"
```

调试模式显示：
- COS 客户端创建状态
- 自动检测的索引维度
- 向量嵌入生成进度
- 详细的错误堆栈信息

## 常见问题

**Q：支持哪些 Embedding 提供者？**

A：目前工具支持 `openai-compatible` 提供者，使用标准的 OpenAI `/v1/embeddings` API 协议。任何实现了此协议的服务都可以使用，包括 OpenAI、Azure OpenAI 以及 vLLM 或 Ollama 等本地模型服务。

**Q：批量处理支持哪些文件类型？**

A：文本文件：`.txt`、`.md`、`.csv`、`.json`、`.xml`、`.html`、`.htm`、`.yaml`、`.yml`、`.log`、`.cfg`、`.ini`、`.conf`、`.py`、`.js`、`.ts`、`.java`、`.c`、`.cpp`、`.h`、`.go`、`.rs`、`.rb`、`.php`、`.sh`、`.bash`。

**Q：COS URI 格式是什么样的？**

A：COS URI 遵循 `cos://bucket-name/object-key` 格式。对于单个对象，使用完整的键（如 `cos://mybucket/docs/file.txt`）。对于批量处理，使用带通配符的前缀（如 `cos://mybucket/docs/*`）。

**Q：向量键是怎么生成的？**

A：默认情况下，为每个向量自动生成 UUID。使用 `--key` 设置显式键（仅限单项），使用 `--filename-as-key` 使用源文件名，或使用 `--key-prefix` 为任何生成的键添加前缀。

**Q：可以使用临时安全令牌吗？**

A：可以。设置 `COS_TOKEN` 环境变量为你的临时安全令牌。它与 `COS_SECRET_ID` 和 `COS_SECRET_KEY` 配合使用，用于临时凭证认证。

## 许可协议

本项目基于 [Apache License 2.0](LICENSE) 协议开源。
