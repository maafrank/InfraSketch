---
title: "Vector Databases Explained: Architecture and System Design for AI Apps"
published: true
tags: vectordatabase, ai, rag, systemdesign
canonical_url: https://infrasketch.net/blog/vector-database-system-design
cover_image: https://infrasketch.net/full-app-with-design-doc.png
---

If you are building anything with LLMs, recommendation engines, or semantic search, you will eventually need a vector database. Traditional databases answer "find the row where id = 42." Vector databases answer a fundamentally different question: "what data is most *similar* to this?"

This guide covers how vector databases work under the hood, compares the leading solutions, and walks through a RAG (Retrieval-Augmented Generation) system design. For the full deep dive with additional code examples and scaling strategies, check out the [complete article on InfraSketch](https://infrasketch.net/blog/vector-database-system-design).

## Why Traditional Databases Fall Short

Relational databases are built for exact lookups and structured queries. But AI applications work with **embeddings**, which are dense numerical vectors (typically 768 to 1536 dimensions) that capture semantic meaning. A sentence, an image, or a product listing can all be represented as a point in high-dimensional space where similar items cluster together.

The operation you need is **similarity search**: given a query vector, find the K nearest vectors. Traditional B-tree and hash indexes are useless here. A brute-force `ORDER BY distance(embedding, query) LIMIT 10` requires computing distance against every single row. At millions of vectors, that is prohibitively slow.

Vector databases solve this with specialized indexing algorithms that make similarity search fast, even across billions of vectors.

## Core Concepts You Need to Know

### Embeddings

An embedding is a fixed-length numerical array that represents an object in a continuous vector space. Models like OpenAI's `text-embedding-3-small` or open-source alternatives like `e5-large` produce these vectors. The key properties:

- **Dimensionality**: Typically 256 to 3072 dimensions
- **Semantic proximity**: Similar items have vectors that are close together
- **Model-dependent**: Vectors from different models are not comparable. You must use the same model for indexing and querying.

### Similarity Metrics

Three distance functions dominate:

- **Cosine similarity**: Measures the angle between vectors. Most common for text because it ignores magnitude.
- **Euclidean distance (L2)**: Straight-line distance. Lower means more similar.
- **Dot product**: Measures direction and magnitude. Fastest to compute.

### Approximate Nearest Neighbors (ANN)

Exact nearest neighbor search has O(n) complexity. ANN algorithms trade a small amount of accuracy for dramatic speedups. A well-tuned ANN index searches billions of vectors in milliseconds with 95-99% accuracy compared to brute force. This **recall-latency tradeoff** is the central engineering challenge in vector database design.

## Architecture Internals

A vector database is more than just an ANN index. It is a full data management system with four layers:

**1. Client Layer**: SDK, REST API, or gRPC interface for queries and writes.

**2. Indexing Layer**: The core. Four major index types:

- **HNSW (Hierarchical Navigable Small World)**: A multi-layer graph. Queries navigate from coarse to fine layers. Excellent recall and sub-millisecond queries. High memory usage. Used by Qdrant, Weaviate, and pgvector.
- **IVF (Inverted File Index)**: Partitions vectors into clusters via k-means. Only searches the closest clusters. Lower memory, but requires training and can degrade if clusters are unbalanced. Used by Milvus.
- **PQ (Product Quantization)**: Compresses vectors 10-50x by encoding sub-vectors with learned codebooks. Lossy but dramatically reduces memory. Often paired with IVF or HNSW.
- **ScaNN**: Google's research system combining anisotropic quantization with hardware-level SIMD. State-of-the-art recall-latency, but limited ecosystem.

**3. Storage Layer**: In-memory (fastest, most expensive), memory-mapped (balanced), or disk-based (cheapest, higher latency). Most production systems use a hybrid approach.

**4. Distributed Layer**: Sharding, replication, consensus, and load balancing for scaling beyond a single node.

![Designing RAG architectures with InfraSketch](https://infrasketch.net/full-app-with-design-doc.png)
*Designing RAG architectures with [InfraSketch](https://infrasketch.net)*

### Query Processing Pipeline

When a query arrives:

1. Parse the query vector, filters, top-K, and similarity metric
2. (Optional) Pre-filter by metadata to narrow candidates
3. ANN search through the index
4. (Optional) Re-score candidates with exact distances
5. (Optional) Post-filter remaining results
6. Return ranked IDs, distances, and metadata

Real applications almost always combine vector similarity with metadata constraints, like "find similar products, but only in Electronics, priced under $50." The best databases (Qdrant, Weaviate) support **integrated filtering** that interleaves metadata checks during ANN traversal itself.

## Vector Database Comparison

| Feature | Pinecone | Weaviate | Milvus | pgvector | Qdrant | Chroma |
|---------|----------|----------|--------|----------|--------|--------|
| **Hosting** | Managed only | Self-hosted + Cloud | Self-hosted + Cloud | Any Postgres | Self-hosted + Cloud | Self-hosted |
| **Max Scale** | Billions | Hundreds of millions | Billions | Tens of millions | Hundreds of millions | Millions |
| **Primary Index** | Proprietary | HNSW | IVF, HNSW, DiskANN | HNSW, IVFFlat | HNSW | HNSW |
| **Hybrid Search** | No | Yes (BM25 + vector) | Yes (sparse + dense) | Yes (with tsvector) | Yes (sparse + dense) | No |
| **Filtering** | Integrated | Integrated | Pre/Post | Post | Integrated | Post |
| **ACID** | No | No | No | Yes | No | No |
| **Language** | Proprietary | Go | Go + C++ | C (Postgres ext.) | Rust | Python |

### Quick Recommendations

- **Pinecone**: Best for teams that want zero-ops managed vector search. Tradeoff: vendor lock-in and cost at scale.
- **Weaviate**: Best for apps needing both semantic and keyword search (built-in BM25 + vector hybrid).
- **Milvus**: Best for large-scale workloads (billions of vectors). Tradeoff: complex multi-component deployment.
- **pgvector**: Best for teams already on Postgres who want to avoid a new database. Tradeoff: single-node limits.
- **Qdrant**: Best for performance-critical apps with complex filtering. Written in Rust with low memory overhead.
- **Chroma**: Best for prototyping. Not built for billions-scale production.

## Scaling Considerations

Before diving into RAG, it is worth understanding how vector databases scale. **Hash-based sharding** distributes vectors across nodes by ID hash. It spreads data evenly but requires querying all shards (scatter-gather). **Partition-based sharding** assigns vectors by cluster, so queries only hit relevant shards, but rebalancing is more complex.

For replication, most teams choose **asynchronous replication** because vector search is inherently approximate. A replica that is a few seconds stale still returns useful similarity results. This makes eventual consistency a natural fit, and most vector databases lean toward availability over strict consistency in CAP theorem terms.

HNSW indexes also need maintenance. Deleted vectors are soft-deleted (marked, not removed) to preserve graph connectivity. Production systems run periodic **segment compaction** to merge and rebuild, keeping performance stable over time.

## Designing a RAG System with Vector Search

RAG is the most common architecture pattern for vector databases. Instead of fine-tuning an LLM, you retrieve relevant context at query time and inject it into the prompt. This keeps knowledge current, reduces hallucinations, and lets you control what the model accesses.

![Auto-generated design documentation in InfraSketch](https://infrasketch.net/url-shortener-design-doc-panel.png)
*Auto-generated design documentation in [InfraSketch](https://infrasketch.net)*

### The Four-Step Pipeline

**Step 1: Document Ingestion.** Parse source documents (PDF, HTML, Notion), chunk them into retrieval units, and embed each chunk. Chunking strategy matters a lot: start with 512 tokens and 50-100 token overlap, then tune from there. Recursive chunking (split on paragraphs, then sentences) tends to preserve semantic coherence better than fixed-size splits.

**Step 2: Storage and Indexing.** Store each chunk with its embedding vector, raw text, and metadata (source, page number, section title, access level). HNSW is typically the best index choice for RAG.

```python
# Qdrant collection setup
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient(host="localhost", port=6333)
client.create_collection(
    collection_name="documents",
    vectors_config=VectorParams(
        size=1536,
        distance=Distance.COSINE,
    ),
    hnsw_config={"m": 16, "ef_construct": 128},
)
```

**Step 3: Retrieval and Re-ranking.** Embed the user query with the same model, search for top-K candidates (20-50), apply metadata filters, then re-rank with a cross-encoder model (like Cohere Rerank or `bge-reranker`). Re-ranking is crucial: bi-encoders are fast but less precise, while cross-encoders evaluate query-document pairs together for much better relevance scores.

**Step 4: Generation.** Construct a prompt with the retrieved chunks as context, send it to the LLM, and return the response. With 5 chunks of 512 tokens, you use roughly 2,500 tokens of context, leaving plenty of room for instructions and the response.

![AI model selection for architecture generation](https://infrasketch.net/email-platform-model-selector.png)
*AI model selection for architecture generation in [InfraSketch](https://infrasketch.net)*

## When NOT to Use a Vector Database

Not every project needs one:

- **Under 100K vectors**: Brute-force numpy search handles this in under 10ms. A dedicated vector database adds complexity without meaningful benefit.
- **Exact match queries**: If you need "find document with ID X," use a relational database or Elasticsearch.
- **Purely structured data**: Transactions, inventory, analytics. A proper relational schema with indexes will outperform vector search.
- **When pgvector is enough**: If you already run Postgres and have under 10M vectors, pgvector avoids the overhead of another database. Graduate to a dedicated solution when you hit scaling limits.

## Key Takeaways

1. Vector databases solve a problem traditional databases cannot: finding semantically similar items across billions of high-dimensional vectors in milliseconds.
2. HNSW is the dominant index for most production workloads, offering excellent recall with sub-millisecond latency.
3. The RAG pattern (vector retrieval + LLM generation) is now the standard approach for building apps that reason over proprietary data.
4. Start simple. For small datasets, brute-force search or pgvector may be all you need. Add a dedicated vector database when you hit scale or feature limits.
5. Metadata filtering strategy (pre, post, or integrated) has a huge impact on both performance and result quality.

---

Design your vector database and RAG architecture visually with InfraSketch. Describe your system in plain English and get a complete architecture diagram with design documentation. Try it free at [https://infrasketch.net](https://infrasketch.net).
