# Vector Database System Design: Architecture for AI Applications

Vector databases have become a critical piece of infrastructure for AI-powered applications. As large language models (LLMs), recommendation engines, and semantic search systems have exploded in adoption, the need for specialized storage that handles high-dimensional vector data has grown alongside them. Traditional relational databases and even NoSQL stores were never built to answer the question "what data is most similar to this query?" at scale. Vector databases fill that gap.

This guide covers the core architecture of vector databases, compares the leading solutions, and walks through a complete system design for building a Retrieval-Augmented Generation (RAG) pipeline. Whether you are preparing for a [system design interview](/blog/complete-guide-system-design) or building production AI infrastructure, understanding vector database internals is now an essential skill.

## Why Traditional Databases Fall Short

Relational databases excel at exact lookups: find the row where `id = 42`, join on foreign keys, filter by indexed columns. They are optimized for structured data with well-defined schemas and precise queries.

But AI applications work with embeddings, which are dense numerical vectors (often 768 to 1536 dimensions) that capture semantic meaning. A sentence, an image, or a product listing can all be represented as a vector in a high-dimensional space where similar items cluster together.

The fundamental operation you need is **similarity search**: given a query vector, find the K nearest vectors in the database. Traditional B-tree and hash indexes are useless here. A SQL query like `ORDER BY euclidean_distance(embedding, query_vector) LIMIT 10` would require a full table scan across millions of rows, computing distance for every single one. At scale, this is prohibitively slow.

Vector databases solve this with specialized indexing algorithms that make similarity search fast, even across billions of vectors.

## Core Concepts

### Embeddings and Vector Representations

An embedding is a fixed-length numerical array that represents an object in a continuous vector space. Embedding models (such as OpenAI's `text-embedding-3-small`, Cohere's `embed-v3`, or open-source models like `e5-large`) transform raw data into these representations.

Key properties of embeddings:

- **Dimensionality**: Typically 256 to 3072 dimensions, depending on the model
- **Semantic proximity**: Items with similar meaning have vectors that are close together
- **Dense representation**: Unlike sparse bag-of-words vectors, embeddings pack meaning into every dimension
- **Model-dependent**: Vectors from different models are not comparable; you must use the same model for indexing and querying

### Similarity Metrics

Three distance functions dominate vector search:

- **Cosine similarity**: Measures the angle between two vectors. Values range from -1 (opposite) to 1 (identical). Most common for text embeddings because it is insensitive to vector magnitude.
- **Euclidean distance (L2)**: Measures straight-line distance in the vector space. Lower values mean more similar. Works well when vector magnitudes carry meaning.
- **Dot product (inner product)**: Measures both direction and magnitude. Fastest to compute. Often used when vectors are already normalized (in which case it equals cosine similarity).

### Approximate Nearest Neighbors (ANN) vs Exact Search

Exact nearest neighbor search (brute force) computes the distance between the query vector and every vector in the database. It guarantees perfect results but has O(n) complexity, making it impractical for large datasets.

Approximate Nearest Neighbor (ANN) algorithms trade a small amount of accuracy for dramatic speed improvements. A well-tuned ANN index can search billions of vectors in milliseconds, returning results that are 95-99% as accurate as brute force. This tradeoff is called the **recall-latency tradeoff**, and it is the central engineering challenge in vector database design.

## Architecture of a Vector Database

A vector database is more than just an ANN index. It is a complete data management system with multiple layers working together:

```
+------------------------------------------------------------------+
|                        CLIENT LAYER                               |
|  SDK / REST API / gRPC                                           |
+------------------------------------------------------------------+
         |                    |                     |
         v                    v                     v
+------------------+  +------------------+  +------------------+
|  QUERY PLANNER   |  |  WRITE PATH      |  |  METADATA INDEX  |
|                  |  |                  |  |                  |
|  Parse query     |  |  Validate data   |  |  B-tree / hash   |
|  Apply filters   |  |  Generate ID     |  |  indexes on      |
|  Select index    |  |  Encode vector   |  |  scalar fields   |
+------------------+  +------------------+  +------------------+
         |                    |                     |
         v                    v                     v
+------------------------------------------------------------------+
|                      INDEXING LAYER                                |
|                                                                  |
|  +------------+  +------------+  +-----------+  +------------+   |
|  |   HNSW     |  |    IVF     |  |    PQ     |  |   ScaNN    |   |
|  |  (graph)   |  | (clusters) |  | (compress)|  |  (hybrid)  |   |
|  +------------+  +------------+  +-----------+  +------------+   |
|                                                                  |
+------------------------------------------------------------------+
         |                    |
         v                    v
+------------------------------------------------------------------+
|                      STORAGE LAYER                                |
|                                                                  |
|  +------------------+  +------------------+  +----------------+  |
|  |   In-Memory      |  |   Memory-Mapped  |  |   Disk-Based   |  |
|  |   (fastest,      |  |   (balanced,     |  |   (cheapest,   |  |
|  |    expensive)     |  |    flexible)     |  |    slower)     |  |
|  +------------------+  +------------------+  +----------------+  |
|                                                                  |
+------------------------------------------------------------------+
         |
         v
+------------------------------------------------------------------+
|                  DISTRIBUTED LAYER                                |
|  Sharding  |  Replication  |  Consensus  |  Load Balancing       |
+------------------------------------------------------------------+
```

### Indexing Layer

The indexing layer is the heart of a vector database. The four major index types each make different tradeoffs:

**HNSW (Hierarchical Navigable Small World)** builds a multi-layer graph where each node is a vector. The top layers contain a sparse subset for coarse navigation, while lower layers add more vectors for fine-grained search. Queries start at the top and greedily navigate toward the nearest neighbors, then drop down to refine.

- **Pros**: Excellent recall, sub-millisecond query times at millions of vectors, no training step
- **Cons**: High memory usage, slow index build time
- **Used by**: Qdrant, Weaviate, pgvector, most production deployments

**IVF (Inverted File Index)** partitions the vector space into clusters using k-means. At query time, it only searches the closest clusters. The `nprobe` parameter controls how many clusters to search.

- **Pros**: Lower memory footprint, good for very large datasets
- **Cons**: Requires a training step, recall degrades if clusters are unbalanced
- **Used by**: Milvus, FAISS-based systems

**PQ (Product Quantization)** compresses vectors by splitting each into sub-vectors and encoding each with a learned codebook. This reduces memory usage by 10-50x.

- **Pros**: Dramatic memory savings, enables disk-based search
- **Cons**: Lossy compression reduces recall
- **Used by**: Often combined with IVF (IVF-PQ) or HNSW for memory efficiency

**ScaNN (Scalable Nearest Neighbors)**, developed by Google, combines anisotropic vector quantization with efficient scoring. It optimizes specifically for maximum inner product search (MIPS) using hardware-level SIMD instructions.

- **Pros**: State-of-the-art recall-latency tradeoff
- **Cons**: Primarily research-oriented, less ecosystem support

### Storage Layer

**In-Memory**: All vectors and indexes reside in RAM. Lowest latency (microseconds) but limits dataset size and drives up cost.

**Memory-Mapped (mmap)**: Vectors are stored on disk but accessed through virtual memory. Frequently accessed vectors stay in the page cache, while cold data lives on disk. Balances performance and cost.

**Disk-Based**: Vectors reside on SSD with only lightweight metadata in memory. Systems like DiskANN (Microsoft) build graph indexes optimized for disk access patterns. Higher latency (low milliseconds) but dramatically lower cost per vector.

Most production vector databases use a hybrid approach, keeping hot data and graph structures in memory while offloading raw vectors to disk.

### Query Processing Pipeline

When a query arrives, the database executes:

1. **Parse and validate**: Extract the query vector, filter conditions, top-K parameter, and similarity metric
2. **Metadata pre-filtering** (optional): Narrow the candidate set based on scalar filters before vector search
3. **ANN search**: Traverse the index to find candidate nearest neighbors
4. **Re-scoring** (optional): Compute exact distances on the candidate set for improved accuracy
5. **Metadata post-filtering** (optional): Apply remaining filters after vector search
6. **Return results**: Ranked list of IDs, distances, and associated metadata

### Metadata Filtering

Real applications rarely perform pure vector search. You almost always need to combine similarity search with metadata constraints: "find similar products, but only in the Electronics category, priced under $50."

**Pre-filtering** applies metadata filters first, then runs vector search on the filtered subset. Precise but can be slow when the filter is very selective. **Post-filtering** runs vector search first, then removes non-matching results. Fast but can return fewer than K results. **Integrated filtering** interleaves metadata checks during ANN traversal itself. Best performance but hardest to implement. Qdrant and Weaviate both support this strategy.

## Vector Database Comparison

| Feature | Pinecone | Weaviate | Milvus | pgvector | Qdrant | Chroma |
|---------|----------|----------|--------|----------|--------|--------|
| **Hosting** | Managed only | Self-hosted + Cloud | Self-hosted + Cloud | Self-hosted (any Postgres) | Self-hosted + Cloud | Self-hosted |
| **Max Scale** | Billions | Hundreds of millions | Billions | Tens of millions | Hundreds of millions | Millions |
| **Primary Index** | Proprietary | HNSW | IVF, HNSW, DiskANN | HNSW, IVFFlat | HNSW | HNSW |
| **Hybrid Search** | No | Yes (BM25 + vector) | Yes (sparse + dense) | Yes (with tsvector) | Yes (sparse + dense) | No |
| **Filtering** | Integrated | Integrated | Pre/Post | Post | Integrated | Post |
| **ACID** | No | No | No | Yes | No | No |
| **Language** | Proprietary | Go | Go + C++ | C (Postgres ext.) | Rust | Python |
| **GPU Support** | N/A | No | Yes | No | No | No |

**Pinecone** is fully managed and serverless. Zero operations, strong consistency, good documentation. Best for teams that want production vector search without infrastructure management. Tradeoff: vendor lock-in and cost at scale.

**Weaviate** is open-source with built-in hybrid search (BM25 + vector) and native vectorization modules. Best for applications requiring both semantic and keyword search.

**Milvus** is built for scale with a distributed architecture (etcd, Pulsar, object storage) supporting billions of vectors. Best for large-scale production workloads. Tradeoff: complex multi-component deployment.

**pgvector** is a PostgreSQL extension that adds vector search to your existing database. Best for teams already on Postgres who want vector search without adding infrastructure. Tradeoff: single-node performance limits.

**Qdrant** is written in Rust with excellent filtered search and low memory overhead. Best for performance-critical applications with complex filtering requirements.

**Chroma** is lightweight and developer-friendly, embedding directly into Python applications. Best for prototyping and small-scale workloads. Not designed for billions-scale production use.

## System Design: Building a RAG System with a Vector Database

Retrieval-Augmented Generation (RAG) is the most common architecture pattern using vector databases. Instead of fine-tuning an LLM on proprietary data, RAG retrieves relevant context at query time and feeds it into the LLM prompt. This keeps knowledge current, reduces hallucinations, and gives you control over what the model can access.

Here is the complete RAG system design architecture:

```
+------------------------------------------------------------------+
|                     DOCUMENT INGESTION PIPELINE                   |
|                                                                  |
|  +----------+    +-----------+    +------------+    +----------+ |
|  |  Source   | -> | Document  | -> |  Chunking  | -> | Embedding| |
|  |  Files    |    | Parser    |    |  Strategy  |    | Model    | |
|  | (PDF,     |    | (extract  |    | (size,     |    | (OpenAI, | |
|  |  HTML,    |    |  text,    |    |  overlap,  |    |  Cohere, | |
|  |  Notion)  |    |  tables)  |    |  semantic) |    |  local)  | |
|  +----------+    +-----------+    +------------+    +----------+ |
|                                          |                |      |
|                                          v                v      |
|                                   +------+-------+  +----+----+ |
|                                   |   Metadata   |  | Vector  | |
|                                   |   Store      |  | Database| |
|                                   +--------------+  +---------+ |
+------------------------------------------------------------------+

+------------------------------------------------------------------+
|                     RETRIEVAL + GENERATION                        |
|                                                                  |
|  +----------+    +-----------+    +------------+    +----------+ |
|  |  User    | -> | Query     | -> |  Vector    | -> | Re-rank  | |
|  |  Query   |    | Embedding |    |  Search    |    | Model    | |
|  |          |    |           |    |  (top-K    |    | (cross-  | |
|  |          |    |           |    |   + filter)|    |  encoder) | |
|  +----------+    +-----------+    +------------+    +----------+ |
|                                                          |       |
|                                                          v       |
|  +----------+    +-----------+    +---------------------------+  |
|  | Response | <- |    LLM    | <- | Prompt = Instructions    |  |
|  | to User  |    | (Claude,  |    |   + Retrieved Context    |  |
|  |          |    |  GPT-4)   |    |   + User Query           |  |
|  +----------+    +-----------+    +---------------------------+  |
+------------------------------------------------------------------+
```

### Step 1: Document Ingestion Pipeline

The ingestion pipeline transforms raw documents into indexed vectors.

**Document parsing** extracts clean text from source formats. PDFs need OCR for scanned content. HTML needs tag stripping while preserving structure. Tables need special handling to maintain row-column relationships.

**Chunking** splits documents into retrieval units. This is one of the most impactful design decisions in a RAG system:

- **Fixed-size chunking**: Split every N tokens (e.g., 512) with M tokens of overlap (e.g., 50). Simple but can split mid-concept.
- **Recursive chunking**: Split on paragraph boundaries, then sentence boundaries as a fallback. Preserves semantic coherence.
- **Semantic chunking**: Use embedding similarity to detect topic shifts and split accordingly. Most coherent chunks but slower.

Most production systems use 512 tokens with 50-100 tokens of overlap as a starting point, then tune based on evaluation.

### Step 2: Storage and Indexing

Each chunk is stored as a record containing the embedding vector, the original chunk text, and metadata (source document, page number, section title, creation date, access level).

For a RAG system, HNSW is typically the best index choice. Configure parameters based on your dataset size:

```python
# Example: Qdrant collection creation
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient(host="localhost", port=6333)

client.create_collection(
    collection_name="documents",
    vectors_config=VectorParams(
        size=1536,           # Embedding dimension
        distance=Distance.COSINE,
    ),
    hnsw_config={
        "m": 16,             # Edges per node (higher = better recall, more memory)
        "ef_construct": 128, # Build-time search width
    },
)
```

### Step 3: Retrieval and Re-ranking

When a user submits a query, the retrieval pipeline runs:

1. **Embed the query** using the same embedding model used for indexing
2. **Vector search** for the top-K candidates (typically K = 20-50)
3. **Apply metadata filters** (e.g., only documents the user has access to)
4. **Re-rank** the candidates using a cross-encoder model

Re-ranking significantly improves result quality. Bi-encoder models (used for initial retrieval) are fast but less accurate for fine-grained relevance. Cross-encoder models (Cohere Rerank, `bge-reranker`) take a query-document pair as input and produce a precise relevance score. They are too slow for the full corpus but work well on 20-50 candidates.

```python
# Retrieve and re-rank
query_vector = embed(user_query)

candidates = vector_db.search(
    collection="documents",
    query_vector=query_vector,
    limit=30,
    filter={"access_level": {"$in": user_roles}},
)

reranked = reranker.rank(
    query=user_query,
    documents=[c.text for c in candidates],
    top_n=5,
)
```

### Step 4: Generation with Retrieved Context

The final step constructs a prompt containing the retrieved context and sends it to the LLM:

```
System: You are a helpful assistant. Answer the user's question based
only on the provided context. If the context does not contain enough
information, say so.

Context:
[Chunk 1 text]
[Chunk 2 text]
[Chunk 3 text]

User: {user_query}
```

With 5 chunks of 512 tokens each, you use roughly 2,500 tokens of context, leaving ample room for the system prompt, user query, and response. For more on designing [LLM-powered systems](/blog/llm-system-design-architecture), see our dedicated guide.

## Scaling Considerations

### Sharding Strategies

Sharding distributes vectors across multiple nodes:

- **Hash-based sharding**: Vectors are assigned to shards by ID hash. Distributes data evenly but requires querying all shards (scatter-gather).
- **Partition-based sharding**: Vectors are assigned by clustering (e.g., IVF centroids). Queries only search relevant shards, but rebalancing is complex.

Most production systems use hash-based sharding because it is simpler to operate. The overhead of querying all shards is offset by parallelism.

### Replication for Availability

Each shard should have at least one replica. **Synchronous replication** guarantees consistency but adds write latency. **Asynchronous replication** prioritizes speed but risks brief data loss during failover. **Read replicas** scale read throughput linearly without affecting writes.

### Consistency Trade-offs

Vector search is inherently approximate, which relaxes consistency requirements. A briefly stale replica missing the last few seconds of writes will still return useful similarity results. This makes eventual consistency a natural fit, and most vector databases prioritize availability (AP in CAP theorem terms).

### Index Rebuild and Update Strategies

HNSW indexes are efficient for reads but complex to update. Deleting a vector requires a soft delete (marking, not removing) since removing a graph node would break connectivity. Production systems handle accumulated deletes through **segment compaction** (periodic merge and rebuild), **incremental indexing** (new vectors go into a small appendable segment), or scheduled **full rebuilds**.

These patterns connect directly to broader [system design principles](/blog/complete-guide-system-design) around distributed storage and data management.

## When NOT to Use a Vector Database

### Small Datasets (Under 100K Vectors)

Brute-force exact nearest neighbor search handles 100K vectors in under 10 milliseconds on a single CPU core. A dedicated vector database adds operational complexity without meaningful benefit.

```python
import numpy as np

# Brute-force search for small datasets
def search(query_vector, all_vectors, top_k=10):
    similarities = np.dot(all_vectors, query_vector)
    top_indices = np.argpartition(similarities, -top_k)[-top_k:]
    return top_indices[np.argsort(similarities[top_indices])[::-1]]
```

### Exact Match Queries

If your queries are exact lookups ("find document with ID X") or precise filters ("all products in category Y under $50"), a relational database or Elasticsearch is the right choice. Vector databases are optimized for fuzzy, similarity-based retrieval.

### Structured Data Without Semantic Search

If your data is purely structured (transactions, inventory records) and your queries are analytical or transactional, you do not need embeddings. A well-designed relational schema with proper indexes will outperform a vector database.

### When pgvector is Enough

If you already run PostgreSQL and your dataset is under 10 million vectors, pgvector avoids the operational burden of a separate database. Graduate to a dedicated solution when you hit scaling limits or need distributed search, advanced filtering, or GPU acceleration.

For guidance on choosing data infrastructure, see our guides on [data architecture patterns](/blog/data-lake-architecture-diagram) and [ML system design patterns](/blog/ml-system-design-patterns).

## Conclusion

Vector databases are a foundational component of modern AI infrastructure. They solve a problem that traditional databases cannot: finding semantically similar items across millions or billions of high-dimensional vectors in milliseconds. Understanding their architecture, from HNSW graph traversal to sharding strategies to metadata filtering, is essential for anyone designing AI-powered systems.

The RAG pattern has made vector databases indispensable. By combining a vector database for retrieval with an LLM for generation, you can build applications that reason over proprietary data without expensive fine-tuning.

Whether you choose a managed solution like Pinecone, an open-source system like Milvus or Qdrant, or a simple extension like pgvector depends on your scale, operational capacity, and feature requirements. Start with the simplest solution that meets your needs and scale up as your data grows.

**Ready to design your own vector database architecture or RAG pipeline?** [Try InfraSketch](/tools/system-design-tool) to generate architecture diagrams from natural language descriptions. Describe your system in plain English and get a complete, editable diagram in seconds.

---

## Related Resources

- [LLM System Design Architecture](/blog/llm-system-design-architecture)
- [Machine Learning System Design Patterns](/blog/ml-system-design-patterns)
- [Data Lake Architecture Diagram](/blog/data-lake-architecture-diagram)
- [The Complete Guide to System Design](/blog/complete-guide-system-design)
