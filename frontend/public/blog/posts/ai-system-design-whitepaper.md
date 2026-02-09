# AI System Design: A Comprehensive Reference Architecture

## Executive Summary

Building a production AI system requires far more than training a model. It demands a carefully designed stack of interconnected platforms, each responsible for a critical stage of the machine learning lifecycle: data ingestion, feature engineering, model training, inference serving, and continuous monitoring. When any one of these layers is missing or poorly designed, the entire system becomes fragile, expensive to operate, and difficult to evolve.

This reference architecture provides a comprehensive, layer-by-layer blueprint for designing AI systems at scale. Each section covers the architectural components, design decisions, tradeoffs, and integration patterns for a specific platform layer. Whether you are a platform engineer building ML infrastructure, an architect evaluating technology choices, or an engineer preparing for a [system design interview](/blog/system-design-interview-prep-practice), this document provides the depth and breadth needed to reason about production AI systems end to end.

For pattern-level guidance on individual ML system components, see our companion guides on [ML system design patterns](/blog/ml-system-design-patterns) and [LLM system design architecture](/blog/llm-system-design-architecture).

## The Modern AI System Stack

A production AI system is composed of five interconnected platform layers. Each layer has distinct responsibilities, but they must work together seamlessly for the system to function reliably.

```
┌──────────────────────────────────────────────────────────────────────┐
│                    The Modern AI System Stack                        │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  5. Monitoring Platform                                      │   │
│  │     Data quality | Model performance | Infrastructure health │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              ▲                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  4. Serving Platform                                         │   │
│  │     Online inference | Batch prediction | Edge deployment    │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              ▲                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  3. Training Platform                                        │   │
│  │     Experiment tracking | Distributed training | Registry    │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              ▲                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  2. Feature Platform                                         │   │
│  │     Feature store | Transformation engine | Online/Offline   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              ▲                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  1. Data Platform                                            │   │
│  │     Ingestion | Storage | Quality | Versioning | Catalog     │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

Data flows upward through these layers: raw data enters the data platform, gets transformed into features, feeds training pipelines, produces models that are deployed to serving infrastructure, and is continuously monitored for quality and performance. Feedback loops flow downward: monitoring alerts trigger retraining, serving metrics inform feature engineering, and data quality issues propagate corrections back to the ingestion layer.

The rest of this document examines each layer in detail.

## Data Platform Architecture

The data platform is the foundation of every AI system. Without reliable, high-quality data, nothing else matters. The data platform handles ingestion from diverse sources, stores data at scale, enforces quality standards, and provides versioning and lineage tracking.

### Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        Data Platform Architecture                          │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  Data Sources                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Databases │  │  Event   │  │  APIs    │  │  Files   │  │ Streams  │   │
│  │(CDC)     │  │  Logs    │  │          │  │  (S3)    │  │ (Kafka)  │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │              │              │              │              │         │
│       ▼              ▼              ▼              ▼              ▼         │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  Ingestion Layer                                                    │  │
│  │  ┌──────────────────────┐    ┌──────────────────────────────────┐  │  │
│  │  │  Batch Ingestion     │    │  Stream Ingestion                │  │  │
│  │  │  (Spark / dbt /      │    │  (Kafka Connect / Flink /       │  │  │
│  │  │   Airbyte)           │    │   Kinesis Data Streams)         │  │  │
│  │  └──────────┬───────────┘    └──────────────┬───────────────────┘  │  │
│  └─────────────┼───────────────────────────────┼──────────────────────┘  │
│                │                               │                          │
│                ▼                               ▼                          │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  Storage Layer (Data Lake / Lakehouse)                              │  │
│  │  ┌────────────┐    ┌────────────┐    ┌────────────────────────┐   │  │
│  │  │  Bronze    │───▶│  Silver    │───▶│  Gold (ML-Ready)       │   │  │
│  │  │  (Raw)     │    │  (Cleaned) │    │  (Aggregated, Joined)  │   │  │
│  │  └────────────┘    └────────────┘    └────────────────────────┘   │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │ Data Quality │  │ Data Catalog  │  │   Data      │  │  Schema     │  │
│  │ (Great       │  │ (DataHub /    │  │  Versioning │  │  Registry   │  │
│  │  Expectations│  │  OpenMetadata)│  │  (DVC /     │  │  (Avro /    │  │
│  │  / Soda)     │  │               │  │   lakeFS)   │  │   Protobuf) │  │
│  └──────────────┘  └───────────────┘  └─────────────┘  └─────────────┘  │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

**Batch versus streaming ingestion.** Most AI systems need both. Batch ingestion (hourly or daily) handles historical data loads and large-volume sources like database snapshots and log files. Stream ingestion handles real-time events like user clicks, transactions, and sensor readings. The choice of when to use each depends on feature freshness requirements. If your model needs features computed over the last 30 days, batch is sufficient. If it needs features from the last 5 minutes, streaming is required.

**Medallion architecture.** The bronze-silver-gold pattern (popularized by Databricks) provides a clear data quality progression. Bronze stores raw, unprocessed data exactly as it arrived. Silver applies cleaning, deduplication, and schema normalization. Gold contains ML-ready datasets with features joined, aggregated, and validated. This layered approach means you can always reprocess from raw data if a transformation bug is discovered.

**Data quality gates.** Every transition between medallion layers should pass through automated quality checks. These checks validate schema conformance, value distributions, null rates, referential integrity, and freshness. Great Expectations and Soda are the most widely adopted tools for this purpose. Quality gate failures should block downstream processing and alert the data team.

**Data versioning.** ML models are only reproducible if the data they were trained on is versioned alongside the code. Tools like DVC (Data Version Control) and lakeFS provide Git-like versioning for datasets, making it possible to reproduce any historical training run exactly. This is critical for debugging model regressions and meeting compliance requirements.

**Data catalog and lineage.** As the number of datasets and transformations grows, a data catalog becomes essential for discoverability and governance. DataHub and OpenMetadata provide searchable catalogs with column-level lineage tracking, showing exactly how each gold-layer dataset was derived from raw sources.

For a deeper exploration of data platform patterns, see our guide on [data lake architecture diagrams](/blog/data-lake-architecture-diagram).

## Feature Platform Architecture

The feature platform sits between the data platform and the training platform. Its job is to transform raw data into the numerical features that models consume, and to serve those features consistently in both training and inference contexts. Training-serving skew (where features are computed differently in training versus production) is one of the most common and insidious bugs in ML systems. A well-designed feature platform eliminates this problem entirely.

### Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                     Feature Platform Architecture                          │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │  Transformation Engine                                               │ │
│  │  ┌────────────────────┐    ┌─────────────────────────────────────┐  │ │
│  │  │  Batch Transforms  │    │  Streaming Transforms               │  │ │
│  │  │  (Spark / dbt)     │    │  (Flink / Spark Streaming)          │  │ │
│  │  │  - Aggregations    │    │  - Sliding windows                  │  │ │
│  │  │  - Joins           │    │  - Real-time counts                 │  │ │
│  │  │  - Encodings       │    │  - Session features                 │  │ │
│  │  └────────┬───────────┘    └───────────────┬─────────────────────┘  │ │
│  └───────────┼────────────────────────────────┼─────────────────────────┘ │
│              │                                │                            │
│              ▼                                ▼                            │
│  ┌──────────────────────┐      ┌───────────────────────────────┐         │
│  │  Offline Store       │      │  Online Store                 │         │
│  │  (S3 / BigQuery /    │      │  (Redis / DynamoDB /          │         │
│  │   Snowflake)         │      │   Bigtable)                   │         │
│  │                      │      │                               │         │
│  │  - Training data     │      │  - Latest feature values      │         │
│  │  - Historical values │      │  - Low-latency lookups        │         │
│  │  - Point-in-time     │      │  - < 10ms p99 retrieval       │         │
│  │    correct joins     │      │                               │         │
│  └──────────┬───────────┘      └──────────────┬────────────────┘         │
│             │                                  │                          │
│             ▼                                  ▼                          │
│  ┌──────────────────────┐      ┌───────────────────────────────┐         │
│  │  Training Pipeline   │      │  Inference Service             │         │
│  │  (reads historical   │      │  (reads latest features        │         │
│  │   features)          │      │   at serving time)             │         │
│  └──────────────────────┘      └───────────────────────────────┘         │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │  Feature Registry: definitions, metadata, lineage, freshness SLAs   │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

**Online versus offline stores.** The offline store holds historical feature values for training. It must support point-in-time correct joins (retrieving feature values as they existed at a specific historical timestamp, not the current values). The online store holds the latest feature values for real-time inference. It must deliver sub-10ms lookups under high concurrency. These two stores have fundamentally different access patterns and performance requirements, which is why they are separate.

**Point-in-time correctness.** This is the single most important concept in feature platform design. When constructing a training dataset, you must join labels with features as they existed at the time the label was generated, not as they exist now. Without point-in-time correctness, your training data contains "future information" that will not be available at serving time, leading to models that perform brilliantly in offline evaluation and poorly in production. Every major feature store (Feast, Tecton, Databricks Feature Store) implements this automatically.

**Feature definitions as code.** Features should be defined in version-controlled configuration files, not in ad-hoc SQL queries or notebook cells. This ensures that the same transformation logic is applied in both training and serving, eliminates training-serving skew, and makes features discoverable and reusable across teams.

**Freshness versus cost tradeoff.** Streaming features (computed in real time from event streams) are fresher but significantly more expensive to compute and maintain than batch features (computed on a schedule). Most features do not need sub-minute freshness. A thoughtful approach is to default to batch computation and upgrade individual features to streaming only when latency-sensitive use cases require it.

For a dedicated deep dive into feature store architecture, see our guide on [feature store system design](/blog/feature-store-system-design).

## Training Platform Architecture

The training platform manages the lifecycle of model development: from experimentation and hyperparameter tuning through distributed training to model registration and approval. A well-designed training platform allows data scientists to iterate quickly while maintaining the reproducibility and governance that production systems require.

### Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                    Training Platform Architecture                          │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │  Experiment Management                                               │ │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────┐ │ │
│  │  │  Experiment    │  │  Hyperparameter│  │  Notebook / IDE        │ │ │
│  │  │  Tracker       │  │  Optimization  │  │  Environment           │ │ │
│  │  │  (W&B / MLflow)│  │  (Optuna /     │  │  (JupyterHub /         │ │ │
│  │  │               │  │   Ray Tune)    │  │   SageMaker Studio)    │ │ │
│  │  └───────┬────────┘  └───────┬────────┘  └────────────┬───────────┘ │ │
│  └──────────┼───────────────────┼────────────────────────┼─────────────┘ │
│             │                   │                        │               │
│             ▼                   ▼                        ▼               │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │  Compute Layer                                                       │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │ │
│  │  │  Single GPU      │  │  Multi-GPU       │  │  Multi-Node      │  │ │
│  │  │  Training        │  │  Training (DDP)  │  │  Distributed     │  │ │
│  │  │                  │  │                  │  │  (DeepSpeed /    │  │ │
│  │  │                  │  │                  │  │   FSDP / Horovod)│  │ │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────┘  │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                    │                                      │
│                                    ▼                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │  Model Registry                                                      │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  ┌──────────┐│ │
│  │  │  Versioning  │  │  Metadata    │  │  Staging    │  │ Approval ││ │
│  │  │  (artifacts, │  │  (metrics,   │  │  (dev/      │  │ Gates    ││ │
│  │  │   lineage)   │  │   params,    │  │   staging/  │  │ (human   ││ │
│  │  │              │  │   data hash) │  │   prod)     │  │  review) ││ │
│  │  └──────────────┘  └──────────────┘  └─────────────┘  └──────────┘│ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │  Pipeline Orchestration (Airflow / Kubeflow / Dagster / Prefect)     │ │
│  │  Data Validation ──▶ Feature Eng ──▶ Train ──▶ Evaluate ──▶ Register│ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

**Experiment tracking.** Every training run should automatically log hyperparameters, metrics (loss curves, evaluation scores), artifacts (model checkpoints, confusion matrices), environment details (library versions, hardware), and the exact data version used. This metadata is essential for reproducing results, comparing approaches, and debugging regressions. Weights & Biases and MLflow are the dominant tools, each with different strengths. W&B excels in visualization and collaboration features. MLflow provides a more open, self-hostable alternative.

**Distributed training strategy.** The choice between single-GPU, multi-GPU (data parallel), and multi-node distributed training depends on model size and data volume. Models under 1 billion parameters typically fit on a single GPU. Models between 1 and 10 billion parameters benefit from multi-GPU data parallelism (PyTorch DDP). Models above 10 billion parameters require model parallelism strategies like DeepSpeed ZeRO, FSDP (Fully Sharded Data Parallel), or pipeline parallelism. Each step up in distribution complexity introduces new failure modes and debugging challenges.

**Hyperparameter optimization.** Manual tuning is a poor use of researcher time. Automated HPO tools like Optuna, Ray Tune, and SageMaker Automatic Model Tuning explore the hyperparameter space more efficiently than humans. Bayesian optimization methods find good configurations with fewer trials than grid or random search, which matters when each trial costs GPU hours.

**Model registry and promotion.** The model registry serves as the single source of truth for all trained models. Every model should progress through well-defined stages: development (actively being trained and evaluated), staging (passed automated tests, awaiting human review), and production (approved for serving). Promotion between stages should require both automated quality gates (accuracy above threshold, latency within budget, no bias regressions) and human approval for production deployment.

**Pipeline orchestration.** End-to-end training pipelines should be defined as directed acyclic graphs (DAGs) in an orchestration tool. Each step (data validation, feature engineering, training, evaluation, registration) is a discrete task with defined inputs, outputs, and failure handling. Airflow is the most widely adopted general-purpose orchestrator. Kubeflow Pipelines is purpose-built for ML workflows on Kubernetes. Dagster and Prefect offer modern alternatives with better developer experience.

## Serving Platform Architecture

The serving platform is where models meet users. It must deliver predictions with low latency, high availability, and efficient resource utilization. Serving is often the most operationally demanding layer of the AI stack because it runs 24/7 in the critical path of user-facing applications.

### Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                     Serving Platform Architecture                          │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │  Routing Layer                                                       │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │ │
│  │  │  API Gateway  │  │  Traffic     │  │  Feature Enrichment     │  │ │
│  │  │  (request     │  │  Splitter    │  │  (fetch online features │  │ │
│  │  │   validation, │  │  (A/B test   │  │   from feature store)   │  │ │
│  │  │   auth, rate  │  │   routing)   │  │                         │  │ │
│  │  │   limiting)   │  │              │  │                         │  │ │
│  │  └──────────────┘  └──────────────┘  └──────────────────────────┘  │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                    │                                      │
│                                    ▼                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │  Inference Engines                                                   │ │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────────┐    │ │
│  │  │  Online        │  │  Batch         │  │  Edge              │    │ │
│  │  │  Inference     │  │  Prediction    │  │  Deployment        │    │ │
│  │  │  (Triton /     │  │  (Spark /      │  │  (TFLite /         │    │ │
│  │  │   TorchServe / │  │   SageMaker    │  │   ONNX Runtime /   │    │ │
│  │  │   vLLM)        │  │   Batch)       │  │   CoreML)          │    │ │
│  │  └────────────────┘  └────────────────┘  └────────────────────┘    │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                    │                                      │
│                                    ▼                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │  Optimization Layer                                                  │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  ┌───────────┐ │ │
│  │  │  Model       │  │  Dynamic     │  │  Response │  │  GPU      │ │ │
│  │  │  Optimization│  │  Batching    │  │  Caching  │  │  Sharing  │ │ │
│  │  │  (Quant /    │  │  (aggregate  │  │  (Redis / │  │  (MPS /   │ │ │
│  │  │   Distill /  │  │   requests   │  │   CDN)    │  │   MIG)    │ │ │
│  │  │   Pruning)   │  │   into batch)│  │           │  │           │ │ │
│  │  └──────────────┘  └──────────────┘  └───────────┘  └───────────┘ │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

**Online versus batch versus edge serving.** Online inference (synchronous, request-response) is for latency-sensitive features like search ranking, recommendation carousels, and chatbots. Batch prediction (asynchronous, scheduled) is for high-volume, latency-tolerant workloads like email personalization, risk scoring, and content moderation queues. Edge deployment (on-device) is for scenarios requiring offline capability, extreme low latency, or data privacy (on-device voice recognition, mobile image classification). Most production systems use a combination of these patterns.

**Dynamic batching.** Individual inference requests are often too small to fully utilize a GPU. Dynamic batching aggregates multiple requests into a single batch, dramatically improving throughput and GPU utilization. The tradeoff is added latency: each request waits briefly for the batch to fill. Triton Inference Server implements this natively with configurable maximum batch size and maximum wait time.

**Model optimization techniques.** Reducing model size and computational cost directly translates to lower serving costs and lower latency:
- **Quantization** reduces precision (FP32 to FP16, INT8, or INT4), cutting memory usage and accelerating inference with minimal accuracy loss.
- **Knowledge distillation** trains a smaller model to replicate a larger model's behavior.
- **Pruning** removes unimportant weights or neurons from the model.
- **Compilation** (TorchScript, TensorRT, ONNX) converts models to optimized representations for specific hardware.

**Response caching.** For models with deterministic outputs (classification, embedding generation), caching predictions for repeated inputs eliminates redundant computation. A Redis cache layer in front of the inference service can handle a significant fraction of traffic, especially for popular items or common queries.

**GPU sharing and multi-tenancy.** Running one model per GPU is wasteful when models are small relative to GPU memory. NVIDIA Multi-Instance GPU (MIG) partitions a single GPU into isolated instances, each running a different model. NVIDIA Multi-Process Service (MPS) allows multiple processes to share a GPU with less isolation but more flexibility.

For an in-depth treatment of serving architecture, see our guide on [ML model serving system design](/blog/ml-model-serving-system-design).

## Monitoring and Observability Platform

ML systems degrade silently. Unlike traditional services that crash loudly when something breaks, a model can produce increasingly wrong predictions for weeks before anyone notices. The monitoring platform exists to detect these silent failures and trigger corrective action before they impact business metrics.

### Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                Monitoring and Observability Platform                        │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │  Data Monitoring                                                     │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │ │
│  │  │  Schema Drift   │  │  Distribution   │  │  Freshness /        │ │ │
│  │  │  Detection      │  │  Shift          │  │  Completeness       │ │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │  Model Monitoring                                                    │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │ │
│  │  │  Prediction     │  │  Feature        │  │  Accuracy /         │ │ │
│  │  │  Distribution   │  │  Attribution    │  │  Business Metric    │ │ │
│  │  │  Drift          │  │  Drift          │  │  Correlation        │ │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │  Infrastructure Monitoring                                           │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │ │
│  │  │  Latency (p50,  │  │  GPU / CPU      │  │  Queue Depth /     │ │ │
│  │  │  p95, p99)      │  │  Utilization    │  │  Error Rates       │ │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                    │                                      │
│                                    ▼                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │  Alerting and Response                                               │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │ │
│  │  │  Alert Rules    │  │  Automated      │  │  Dashboards         │ │ │
│  │  │  (thresholds,   │  │  Retraining     │  │  (Grafana /         │ │ │
│  │  │   anomaly det.) │  │  Triggers       │  │   CloudWatch)       │ │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

### Three Layers of ML Monitoring

**Data monitoring** catches problems at the source. Schema drift occurs when upstream data sources add, remove, or change column types. Distribution shift occurs when the statistical properties of input data change (e.g., a new user demographic starts using the product). Freshness monitoring ensures that data pipelines complete on time and that stale data does not silently feed into predictions.

**Model monitoring** detects degradation in the model itself. Prediction distribution drift (the model's output distribution changing over time) is the earliest indicator of trouble. Feature attribution drift (the features driving predictions shifting) reveals which aspects of the input data are changing. When ground truth labels are available (often with a delay), accuracy and precision/recall can be tracked directly. When labels are delayed or unavailable, proxy metrics correlated with business outcomes serve as substitutes.

**Infrastructure monitoring** covers the operational health of the serving system: latency percentiles, throughput, error rates, GPU utilization, memory usage, and queue depths. These are standard DevOps concerns, but ML systems add GPU-specific metrics (GPU memory utilization, GPU compute utilization, tensor core utilization) that traditional monitoring tools may not capture natively.

### Alerting Strategy

ML systems require a tiered alerting strategy:

- **Critical (page immediately):** Serving errors above threshold, complete pipeline failure, model returning constant predictions
- **Warning (notify within hours):** Significant prediction distribution shift, data freshness SLA violation, latency degradation
- **Informational (review daily):** Gradual distribution drift, feature importance changes, resource utilization trends

The key discipline is avoiding alert fatigue. Every alert should be actionable. If the team cannot take a concrete action in response to an alert, the alert should be removed or downgraded.

## LLM and Generative AI Architecture

Large language models and generative AI systems introduce architectural patterns that differ significantly from traditional ML systems. The model is often too large to train from scratch, inference is orders of magnitude more expensive, and the output is non-deterministic free-form text rather than a structured prediction.

### Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                  LLM and Generative AI Architecture                        │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │  RAG (Retrieval-Augmented Generation) Pipeline                       │ │
│  │                                                                      │ │
│  │  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌────────────────────┐ │ │
│  │  │  Query   │─▶│  Embedding│─▶│  Vector  │─▶│  Context Assembly │ │ │
│  │  │          │  │  Model    │  │  Search  │  │  + Reranking      │ │ │
│  │  └──────────┘  └───────────┘  └──────────┘  └────────┬───────────┘ │ │
│  │                                                       │             │ │
│  │                                                       ▼             │ │
│  │  ┌──────────────────────────────────────────────────────────────┐   │ │
│  │  │  LLM Inference (Claude / GPT / Open-Source)                 │   │ │
│  │  │  Prompt Template + Retrieved Context + User Query ──▶ Answer│   │ │
│  │  └──────────────────────────────────────────────────────────────┘   │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │  Agent Architecture                                                  │ │
│  │  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌──────────────────┐  │ │
│  │  │  Router  │─▶│  Planner  │─▶│  Tool    │─▶│  State Machine   │  │ │
│  │  │          │  │           │  │  Executor│  │  (LangGraph)     │  │ │
│  │  └──────────┘  └───────────┘  └──────────┘  └──────────────────┘  │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │  Supporting Infrastructure                                           │ │
│  │  ┌──────────────┐  ┌───────────────┐  ┌───────────┐  ┌───────────┐│ │
│  │  │  Prompt      │  │  Evaluation   │  │  Guard-   │  │  Token    ││ │
│  │  │  Management  │  │  Framework    │  │  rails    │  │  Budget   ││ │
│  │  │  (versioned  │  │  (LLM judge,  │  │  (content │  │  Manager  ││ │
│  │  │   templates) │  │   human eval) │  │   filter) │  │           ││ │
│  │  └──────────────┘  └───────────────┘  └───────────┘  └───────────┘│ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

### Key LLM Architecture Patterns

**Retrieval-Augmented Generation (RAG).** Instead of relying solely on the LLM's parametric knowledge, RAG retrieves relevant documents from an external knowledge base and includes them in the prompt context. This grounds the model's responses in factual, up-to-date information and dramatically reduces hallucination. The architecture involves an embedding model, a [vector database](/blog/vector-database-system-design), a reranking stage, and careful prompt construction.

**Agent architectures.** LLM agents extend beyond simple question-answering by giving the model the ability to use tools, plan multi-step solutions, and maintain state across interactions. Frameworks like LangGraph implement this as a state machine where the LLM decides which tool to call, observes the result, and decides the next action. For a comprehensive treatment of agent architecture patterns, see our guide on [agentic AI system architecture](/blog/agentic-ai-system-architecture).

**Prompt management.** Prompts are the "code" of LLM applications. They should be versioned, tested, and deployed with the same rigor as application code. A prompt management system stores prompt templates, tracks which versions are in production, and supports A/B testing different prompt strategies.

**Evaluation frameworks.** Evaluating LLM outputs is fundamentally harder than evaluating traditional ML predictions. Automated metrics (BLEU, ROUGE) capture surface-level quality but miss semantic correctness. LLM-as-judge evaluation (using a separate LLM to score outputs) provides better signal but introduces its own biases. Human evaluation is the gold standard but does not scale. A robust evaluation framework uses all three approaches in combination.

**Guardrails and safety.** Production LLM systems need input and output guardrails: content filters to block harmful requests and responses, PII detection to prevent data leakage, token budget enforcement to prevent runaway costs, and output validation to ensure responses conform to expected formats.

For deeper coverage, see our guide on [LLM system design architecture](/blog/llm-system-design-architecture).

## Infrastructure Patterns

The underlying compute and networking infrastructure for AI systems can be organized in several ways, each with distinct operational characteristics.

### Kubernetes-Based Infrastructure

Kubernetes is the most common platform for production ML workloads. It provides container orchestration, auto-scaling, resource isolation, and a rich ecosystem of ML-specific tools (KubeFlow, Seldon, KServe). The tradeoff is operational complexity: Kubernetes requires dedicated platform engineering expertise, and GPU scheduling on Kubernetes introduces additional challenges (device plugins, resource quotas, node affinity rules).

### Serverless Infrastructure

Serverless platforms (AWS Lambda, Google Cloud Functions, Azure Functions) eliminate infrastructure management entirely. They are ideal for event-driven ML workloads with variable traffic: preprocessing pipelines, lightweight inference endpoints, and webhook handlers. The limitations are cold start latency, execution time limits, memory constraints, and lack of GPU support (though this is evolving with services like AWS Lambda with GPU and SageMaker Serverless).

### Hybrid Approach

Most production AI systems use a hybrid approach: Kubernetes for steady-state GPU workloads (model serving, training jobs), serverless for event-driven and variable workloads (data ingestion triggers, lightweight preprocessing, API orchestration), and managed services for specialized needs (managed vector databases, hosted experiment tracking).

### Cloud Provider Comparison

| Capability | AWS | GCP | Azure |
|-----------|-----|-----|-------|
| **ML Platform** | SageMaker | Vertex AI | Azure ML |
| **GPU Instances** | p4d/p5 (A100/H100) | A2/A3 (A100/H100) | ND (A100/H100) |
| **Managed Serving** | SageMaker Endpoints | Vertex Prediction | Azure ML Endpoints |
| **Feature Store** | SageMaker Feature Store | Vertex Feature Store | Azure ML Feature Store |
| **Orchestration** | Step Functions, MWAA | Cloud Composer, Vertex Pipelines | Azure Data Factory |
| **Vector DB** | OpenSearch, MemoryDB | AlloyDB, Vertex Vector Search | Azure AI Search |
| **LLM APIs** | Bedrock | Vertex AI (Gemini) | Azure OpenAI |

All three major cloud providers offer comprehensive ML platforms. AWS has the broadest ecosystem and the most third-party integrations. GCP has the strongest integration with open-source ML tools (TensorFlow, JAX) and often offers the best GPU availability. Azure has the tightest integration with the OpenAI ecosystem. The choice often depends on where the rest of your infrastructure already lives.

## Security and Governance

AI systems introduce unique security and governance requirements that go beyond standard application security.

### Model Access Control

Models are valuable intellectual property. Access should be governed by role-based access control (RBAC) at multiple levels: who can train models, who can view experiment results, who can promote models to production, and who can access model artifacts. The model registry should enforce these permissions and maintain an audit trail of all actions.

### Data Privacy

AI systems often process sensitive data. Privacy-preserving techniques include:

- **Data anonymization and pseudonymization** before training
- **Differential privacy** during training (adding calibrated noise to prevent individual records from being extracted)
- **Federated learning** (training on data that never leaves the user's device)
- **Access controls and encryption** for data at rest and in transit

### Audit Trails

Regulatory frameworks (GDPR, CCPA, industry-specific regulations) increasingly require explainability and traceability for automated decisions. A comprehensive audit trail records the model version that made each prediction, the features used, the data the model was trained on, and the approval chain that deployed it to production. This lineage enables root cause analysis when something goes wrong and satisfies compliance requirements.

### Bias Monitoring

ML models can amplify biases present in training data. Bias monitoring tracks model performance across protected demographic groups (gender, race, age) and alerts when disparate impact exceeds acceptable thresholds. Tools like Fairlearn, AI Fairness 360, and What-If Tool provide frameworks for measuring and mitigating bias.

## Reference Architecture: Complete AI Platform

Bringing all layers together, here is the complete reference architecture for a production AI platform:

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                        Complete AI Platform Reference Architecture               │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│    Users / Applications                                                          │
│    ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│    │  Web App │  │ Mobile   │  │ Internal │  │  APIs    │                      │
│    └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘                      │
│         └──────────────┴─────────────┴──────────────┘                            │
│                              │                                                   │
│                              ▼                                                   │
│    ┌────────────────────────────────────────────────────────────────────────┐    │
│    │  API Gateway + Auth + Rate Limiting + A/B Traffic Splitting           │    │
│    └────────────────────────────────────┬───────────────────────────────────┘    │
│                                         │                                        │
│    ┌────────────────────────────────────▼───────────────────────────────────┐    │
│    │  SERVING PLATFORM                                                      │    │
│    │  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  ┌─────────────┐  │    │
│    │  │ Online       │  │ Batch        │  │ LLM       │  │ Edge        │  │    │
│    │  │ Inference    │  │ Prediction   │  │ Serving   │  │ Deployment  │  │    │
│    │  │ (Triton)     │  │ (Spark)      │  │ (vLLM)    │  │ (ONNX)     │  │    │
│    │  └──────┬───────┘  └──────────────┘  └─────┬─────┘  └─────────────┘  │    │
│    └─────────┼──────────────────────────────────┼──────────────────────────┘    │
│              │                                   │                               │
│    ┌─────────▼───────────────────────────────────▼─────────────────────────┐    │
│    │  FEATURE PLATFORM                                                     │    │
│    │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────────┐  │    │
│    │  │ Online Store │  │ Offline Store│  │ Feature Registry           │  │    │
│    │  │ (Redis)      │  │ (S3/BQ)     │  │ (definitions + metadata)   │  │    │
│    │  └──────────────┘  └──────┬───────┘  └────────────────────────────┘  │    │
│    └───────────────────────────┼───────────────────────────────────────────┘    │
│                                │                                                 │
│    ┌───────────────────────────▼───────────────────────────────────────────┐    │
│    │  TRAINING PLATFORM                                                    │    │
│    │  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  ┌────────────┐  │    │
│    │  │ Experiment   │  │ Distributed  │  │ HPO       │  │ Model      │  │    │
│    │  │ Tracker (W&B)│  │ Training     │  │ (Optuna)  │  │ Registry   │  │    │
│    │  └──────────────┘  └──────────────┘  └───────────┘  └────────────┘  │    │
│    └───────────────────────────┬───────────────────────────────────────────┘    │
│                                │                                                 │
│    ┌───────────────────────────▼───────────────────────────────────────────┐    │
│    │  DATA PLATFORM                                                        │    │
│    │  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  ┌────────────┐  │    │
│    │  │ Ingestion    │  │ Lakehouse    │  │ Quality   │  │ Catalog    │  │    │
│    │  │ (Kafka/      │  │ (Bronze/     │  │ (Great    │  │ (DataHub)  │  │    │
│    │  │  Airbyte)    │  │  Silver/Gold)│  │  Expect.) │  │            │  │    │
│    │  └──────────────┘  └──────────────┘  └───────────┘  └────────────┘  │    │
│    └───────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│    ┌───────────────────────────────────────────────────────────────────────┐    │
│    │  MONITORING PLATFORM (Cross-Cutting)                                  │    │
│    │  Data Drift | Model Performance | Infrastructure | Alerting | Dashboards  │
│    └───────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│    ┌───────────────────────────────────────────────────────────────────────┐    │
│    │  GOVERNANCE (Cross-Cutting)                                           │    │
│    │  Access Control | Audit Trail | Bias Monitoring | Privacy | Lineage   │    │
│    └───────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

This architecture is not prescriptive. No organization needs every component from day one. The value of a reference architecture is providing a shared vocabulary and a target state that teams can build toward incrementally.

## Implementation Roadmap

Adopting a full AI platform is a multi-year journey. Here is a phased approach that delivers value at each stage.

### Phase 1: Foundation (Months 1-3)

- Establish a data platform with batch ingestion, basic quality checks, and a bronze/silver/gold structure
- Set up experiment tracking (W&B or MLflow) for all training runs
- Deploy models behind a simple serving layer (FastAPI + Docker)
- Implement basic monitoring (latency, error rates, prediction distribution)

### Phase 2: Automation (Months 3-6)

- Build automated training pipelines with data validation and evaluation gates
- Introduce a model registry with versioning and staging environments
- Add a simple feature store (PostgreSQL for online, S3 for offline)
- Implement A/B testing infrastructure for model rollouts

### Phase 3: Optimization (Months 6-12)

- Deploy a dedicated serving platform (Triton or vLLM) with dynamic batching
- Add data drift detection and automated retraining triggers
- Build comprehensive dashboards for data, model, and infrastructure metrics
- Implement LLM/RAG infrastructure if applicable

### Phase 4: Scale (Months 12+)

- Distribute training across multi-GPU and multi-node clusters
- Add a full-featured feature store with streaming transforms
- Implement governance controls (RBAC, audit trails, bias monitoring)
- Build a self-service platform for data scientists to train, evaluate, and deploy models independently

## Conclusion

Designing a production AI system is a multidisciplinary challenge that spans data engineering, machine learning, distributed systems, DevOps, and security. No single tool or framework covers the entire stack. Success requires understanding the responsibilities of each platform layer, the tradeoffs between approaches, and the integration points where layers connect.

This reference architecture provides a comprehensive blueprint, but every organization's implementation will look different based on their scale, team, and requirements. Start with the layers that address your most pressing bottleneck (usually data quality or serving reliability), build incrementally, and resist the temptation to adopt every tool at once.

To visualize and iterate on your own AI system architecture, [try InfraSketch](https://infrasketch.net). Describe your system in plain English, generate a complete architecture diagram, and refine it through AI-powered conversation.

## Related Resources

- [ML System Design Patterns](/blog/ml-system-design-patterns)
- [LLM System Design Architecture](/blog/llm-system-design-architecture)
- [MLOps System Design](/blog/mlops-system-design)
- [Real-World AI System Architecture](/blog/real-world-ai-system-architecture)
- [AI Pipeline System Design](/blog/ai-pipeline-system-design)
- [Feature Store System Design](/blog/feature-store-system-design)
- [ML Model Serving System Design](/blog/ml-model-serving-system-design)
