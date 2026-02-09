# Machine Learning System Design Patterns: The Complete Guide

Machine learning system design patterns have become one of the most critical areas of knowledge for software engineers building production AI applications. While traditional system design focuses on serving requests, storing data, and scaling compute, ML system design introduces entirely new dimensions: data pipelines, feature engineering, model training, inference serving, experiment tracking, and continuous monitoring for data drift. If you have worked on [traditional system design](/blog/complete-guide-system-design), you already have a strong foundation. But production machine learning system design requires a fundamentally different mental model.

This guide covers the six most important machine learning system design patterns used in large scale machine learning system design at companies like Google, Meta, Netflix, and Uber. Whether you are preparing for an AI system design interview, building your first end to end ML system design architecture, or scaling an existing ML platform, these patterns will give you a practical framework for making the right architectural decisions.

## Why ML System Design is Different from Traditional System Design

Before diving into patterns, it is worth understanding what makes ML systems unique. In a [standard system design](/blog/complete-guide-system-design), you reason about request routing, database queries, caching layers, and horizontal scaling. The inputs and outputs are well-defined, the behavior is deterministic, and failures are typically binary (the system works or it does not).

ML systems break these assumptions in several important ways:

- **Data is a first-class citizen.** The quality of your data directly determines the quality of your model. Bad data produces bad predictions, regardless of how elegant your architecture is.
- **Behavior is probabilistic.** Models produce confidence scores, not definitive answers. You must design systems that handle uncertainty gracefully.
- **The system degrades silently.** A traditional service crashes loudly when something breaks. An ML model can quietly produce increasingly wrong predictions as data distribution shifts over time.
- **Training and serving are separate systems.** You need infrastructure for both offline training (batch compute, GPU clusters) and online serving (low-latency inference), and these systems have very different requirements.
- **Experimentation is continuous.** You are constantly training new model versions, running A/B tests, and rolling back to previous versions. Version control applies not just to code but also to data, features, and model artifacts.

Understanding these differences is the foundation for approaching any distributed ML system design problem effectively.

## The End-to-End ML System

Before exploring individual patterns, let us look at the full picture. Every production machine learning system design has these core stages:

```
┌─────────────────────────────────────────────────────────────────────┐
│                   End-to-End ML System Architecture                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐    │
│  │  Data     │──▶│ Feature  │──▶│  Model   │──▶│   Model      │    │
│  │ Ingestion │   │ Engineer │   │ Training │   │   Registry   │    │
│  └──────────┘   └──────────┘   └──────────┘   └──────┬───────┘    │
│       │              │                                │            │
│       ▼              ▼                                ▼            │
│  ┌──────────┐   ┌──────────┐                   ┌──────────────┐   │
│  │  Data    │   │ Feature  │                   │   Model      │   │
│  │  Lake    │   │  Store   │──────────────────▶│   Serving    │   │
│  └──────────┘   └──────────┘                   └──────┬───────┘   │
│                                                       │            │
│                                                       ▼            │
│                                                ┌──────────────┐   │
│                                                │  Monitoring  │   │
│                                                │  & Feedback  │   │
│                                                └──────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Stage 1: Data Ingestion.** Raw data flows in from databases, event streams, APIs, and third-party sources. This is where you decide between batch and streaming ingestion, apply schema validation, and handle data quality checks.

**Stage 2: Feature Engineering.** Raw data is transformed into features that the model can consume. This includes normalization, encoding categorical variables, computing aggregations, and joining data from multiple sources. For a deeper look at data pipeline architecture, see our guide on [data lake architecture diagrams](/blog/data-lake-architecture-diagram).

**Stage 3: Model Training.** Features are fed into training pipelines that produce model artifacts. Training can be offline (batch), online (incremental), or a hybrid. This stage also includes hyperparameter tuning, cross-validation, and experiment tracking.

**Stage 4: Model Registry.** Trained models are versioned, evaluated, and stored in a central registry. The registry tracks metadata like training data, performance metrics, and lineage.

**Stage 5: Model Serving.** The selected model is deployed for inference. This is where the production ML system meets the user, and latency, throughput, and reliability all matter.

**Stage 6: Monitoring and Feedback.** Predictions are logged, model performance is tracked, data drift is detected, and feedback loops send ground truth labels back to improve future models.

Each of the following patterns addresses how to implement one or more of these stages for a specific use case. If you want to visualize and iterate on these architectures interactively, [try InfraSketch](https://infrasketch.net) to generate ML system diagrams from natural language.

## Pattern 1: Batch Prediction Pipeline

The batch prediction pipeline is the simplest and most common pattern for production machine learning system design. It generates predictions for large datasets on a fixed schedule (hourly, daily, or weekly) and stores them for later retrieval.

### Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Scheduled   │────▶│   Feature    │────▶│   Batch      │
│  Trigger     │     │   Retrieval  │     │   Inference  │
│  (Airflow)   │     │   (Spark)    │     │   (Spark)    │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                                                  ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Application │◀────│  Prediction  │◀────│  Prediction  │
│  Server      │     │  Cache       │     │  Store       │
│  (API)       │     │  (Redis)     │     │  (S3/DB)     │
└──────────────┘     └──────────────┘     └──────────────┘
```

### How It Works

1. A scheduler (Airflow, Prefect, or a cron job) triggers the pipeline on a fixed cadence.
2. The pipeline reads the latest features from the feature store or data warehouse.
3. A batch inference job loads the model and generates predictions for all entities (users, products, transactions).
4. Predictions are written to a prediction store (S3, a database, or a key-value store).
5. An optional caching layer (Redis, Memcached) serves predictions with low latency.
6. The application server looks up precomputed predictions when a user makes a request.

### When to Use

- **Recommendation systems** where you can precompute recommendations for all users daily.
- **Risk scoring** for loan applications or fraud detection at the account level.
- **Content ranking** where you re-rank a catalog of items periodically.
- **Email campaigns** that score users for likelihood to convert.
- Any scenario where predictions do not need to reflect real-time state.

### Trade-offs

| Advantage | Disadvantage |
|-----------|-------------|
| Simple to implement and debug | Predictions become stale between runs |
| High throughput (process millions of records) | Cannot personalize based on real-time context |
| Easy to validate before serving | Cold-start problem for new entities |
| Cost-efficient (use spot instances) | Storage costs for all precomputed results |
| No latency constraints on inference | Wasted compute for entities that are never queried |

### Production Considerations

- **Validation gates:** Run automated quality checks on predictions before promoting them to the serving store. Compare prediction distributions against historical baselines.
- **Fallback strategy:** Keep the previous batch of predictions available so the application can fall back if the latest pipeline fails.
- **Incremental processing:** For large datasets, consider processing only the delta (changed entities) rather than recomputing everything.
- **Monitoring:** Track pipeline latency, prediction coverage (what percentage of entities received predictions), and distribution statistics.

## Pattern 2: Real-Time Inference Service

When predictions must reflect the most current data or respond to user actions in milliseconds, you need a real-time inference service. This is the second most common ML system design pattern and the one that appears most frequently in AI system design interview examples.

### Architecture

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────┐
│  Client  │────▶│   API        │────▶│   Feature    │────▶│  Model   │
│  Request │     │   Gateway    │     │   Assembly   │     │  Server  │
└──────────┘     └──────────────┘     └──────────────┘     └────┬─────┘
                                            │                    │
                                            ▼                    ▼
                                      ┌──────────────┐   ┌──────────┐
                                      │   Feature    │   │ Prediction│
                                      │   Store      │   │ Response  │
                                      │   (Online)   │   └──────────┘
                                      └──────────────┘
                                            ▲
                                      ┌──────────────┐
                                      │   Streaming  │
                                      │   Pipeline   │
                                      │   (Kafka)    │
                                      └──────────────┘
```

### How It Works

1. A client sends a request (for example, "should we approve this transaction?").
2. The API gateway routes the request to the inference service.
3. The feature assembly layer pulls real-time features from the online feature store and combines them with request-time features.
4. The assembled feature vector is sent to the model server (TensorFlow Serving, Triton, TorchServe, or a custom server).
5. The model returns a prediction, which is sent back to the client.
6. In parallel, a streaming pipeline continuously updates the online feature store with the latest events.

### When to Use

- **Fraud detection** where transactions must be scored in real time before approval.
- **Search ranking** where results must reflect the user's current query and context.
- **Dynamic pricing** that adjusts based on demand, inventory, and user behavior.
- **Content moderation** that must evaluate posts before they go live.
- **Conversational AI** where response latency directly affects user experience.

### Trade-offs

| Advantage | Disadvantage |
|-----------|-------------|
| Predictions reflect current state | Higher infrastructure complexity |
| Handles unseen entities (no cold start) | Strict latency requirements (p99 < 100ms) |
| Contextual personalization | Feature assembly adds latency |
| Immediate feedback loop | Requires high-availability model serving |
| Scales with request volume | Cost scales linearly with traffic |

### Latency Budget Breakdown

One of the most important exercises in designing a real-time inference service is understanding where latency comes from:

```
Total latency budget: 100ms (p99)

┌─────────────────────────────────────────────────┐
│ Network (client to gateway)       │    10ms     │
│ Feature retrieval (online store)  │    15ms     │
│ Feature assembly & transforms     │     5ms     │
│ Model inference                   │    40ms     │
│ Post-processing                   │     5ms     │
│ Network (response to client)      │    10ms     │
│ Buffer                            │    15ms     │
└─────────────────────────────────────────────────┘
```

For model inference specifically, GPU-based serving (NVIDIA Triton) can batch multiple requests together, improving throughput while staying within latency targets. The key optimization levers are model quantization (INT8, FP16), request batching, caching frequently requested features, and pre-materializing expensive feature computations.

### Key Design Decisions

- **Model format:** ONNX for cross-framework compatibility, TensorRT for NVIDIA GPU optimization, or framework-native (SavedModel, TorchScript).
- **Scaling strategy:** Horizontal (more replicas) versus vertical (bigger GPUs). Use autoscaling based on request queue depth, not just CPU.
- **Fallback behavior:** What happens when the model is unavailable? Options include returning a default prediction, using a simpler rule-based system, or gracefully degrading the feature.

For more on API gateway patterns and service architecture, see our [microservices architecture diagram guide](/blog/microservices-architecture-diagram-guide).

## Pattern 3: Online Learning Pipeline

Online learning (also called incremental learning or continual learning) updates the model continuously as new data arrives, rather than retraining from scratch on a schedule. This pattern is essential for large scale machine learning system design in domains where data distribution changes rapidly.

### Architecture

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Event   │────▶│   Stream     │────▶│   Online     │────▶│   Model      │
│  Stream  │     │   Processor  │     │   Trainer    │     │   Server     │
│  (Kafka) │     │   (Flink)    │     │   (Vowpal)   │     │   (Live)     │
└──────────┘     └──────────────┘     └──────┬───────┘     └──────────────┘
                                              │
                                              ▼
                                       ┌──────────────┐
                                       │  Model       │
                                       │  Checkpoint  │
                                       │  Store       │
                                       └──────────────┘
                                              │
                                       ┌──────────────┐
                                       │  Periodic    │
                                       │  Validation  │
                                       │  Pipeline    │
                                       └──────────────┘
```

### How It Works

1. Events (clicks, purchases, sensor readings) flow into a streaming platform like Kafka or Kinesis.
2. A stream processor (Flink, Spark Streaming) transforms raw events into training examples with features and labels.
3. An online trainer ingests these examples and updates model weights incrementally. Frameworks like Vowpal Wabbit, River, or custom SGD implementations support this.
4. Updated model weights are pushed to the serving layer, either continuously or in micro-batches (every few minutes).
5. A checkpoint store persists model snapshots for rollback and recovery.
6. A periodic validation pipeline evaluates the model against a held-out dataset to detect degradation.

### When to Use

- **Ad click prediction** where user behavior and ad inventory change minute to minute.
- **Stock trading signals** where market conditions evolve rapidly.
- **Anomaly detection** on IoT sensor data where "normal" drifts over time.
- **Personalization** for news feeds or content where trends shift within hours.
- **Cybersecurity** where attack patterns evolve faster than batch retraining cycles.

### Trade-offs

| Advantage | Disadvantage |
|-----------|-------------|
| Adapts to distribution shift in real time | Risk of catastrophic forgetting |
| No retraining downtime | Harder to debug and reproduce |
| Lower latency from data to model | Vulnerable to adversarial/corrupted data |
| Efficient use of compute (incremental) | Limited to models that support online updates |
| Always reflects the latest patterns | Requires robust validation guardrails |

### Guardrails for Safety

Online learning introduces unique risks. If a burst of corrupted data arrives, the model can degrade rapidly. Essential guardrails include:

- **Data validation:** Reject training examples that fall outside expected distributions.
- **Learning rate decay:** Use a decreasing learning rate to prevent recent examples from dominating.
- **Periodic reset:** Retrain from scratch on a schedule (weekly or monthly) to prevent drift accumulation.
- **Shadow validation:** Run every model update against a validation set before promoting to production.
- **Rollback triggers:** Automatically revert to the last checkpoint if performance drops below a threshold.

For more on event-driven data pipelines that feed online learning systems, see our [event-driven architecture patterns guide](/blog/event-driven-architecture-patterns).

## Pattern 4: A/B Testing and Shadow Mode Deployment

No ML model should go directly from training to full production traffic. A/B testing and shadow mode are deployment patterns that reduce risk by comparing new models against existing ones using real-world traffic.

### Architecture

```
                         ┌──────────────────────────────────────┐
                         │         Traffic Router               │
                         │    (Feature Flags / Load Balancer)    │
                         └────┬─────────────┬──────────────┬────┘
                              │             │              │
                         90% traffic   5% traffic    5% traffic
                              │             │              │
                              ▼             ▼              ▼
                       ┌──────────┐  ┌──────────┐  ┌──────────┐
                       │ Model A  │  │ Model B  │  │ Model C  │
                       │ (Control)│  │(Variant 1)│ │(Variant 2)│
                       └────┬─────┘  └────┬─────┘  └────┬─────┘
                            │             │              │
                            ▼             ▼              ▼
                       ┌──────────────────────────────────────┐
                       │       Experiment Tracking Service     │
                       │    (Predictions, Outcomes, Metrics)   │
                       └──────────────────────────────────────┘
                                          │
                                          ▼
                       ┌──────────────────────────────────────┐
                       │       Statistical Analysis Engine     │
                       │   (Significance, Confidence, Power)   │
                       └──────────────────────────────────────┘
```

### A/B Testing

In A/B testing, a percentage of live traffic is routed to the new model, and outcomes are measured against the control model.

**Key components:**
- **Traffic router:** Assigns users to experiment groups deterministically (hash of user ID) to ensure consistency across sessions.
- **Experiment tracking:** Logs predictions and outcomes for both groups.
- **Statistical analysis:** Calculates significance, confidence intervals, and effect size.
- **Guardrails:** Automatic rollback if the variant degrades a critical metric beyond a threshold.

**Metrics to track:**
- Primary metric (click-through rate, conversion rate, revenue per user)
- Guardrail metrics (latency, error rate, user complaints)
- Sample ratio mismatch (verifies the split is actually correct)

### Shadow Mode (Dark Launch)

Shadow mode runs the new model in parallel with the production model on 100% of traffic, but only the production model's predictions are served. The shadow model's predictions are logged for offline comparison.

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐
│  Request │────▶│  Production  │────▶│  Response     │
│          │     │  Model       │     │  (served)     │
└──────────┘     └──────────────┘     └──────────────┘
      │
      └─────────▶┌──────────────┐     ┌──────────────┐
                 │  Shadow      │────▶│  Log Only     │
                 │  Model       │     │  (not served) │
                 └──────────────┘     └──────────────┘
```

**When to use shadow mode:**
- Before running an A/B test, to validate that the new model behaves as expected.
- When you cannot easily measure outcomes (for example, a safety classifier where "nothing bad happened" is the desired outcome).
- When the cost of a bad prediction is very high (medical, financial).

### Deployment Progression

The safest path from training to full deployment follows this progression:

1. **Offline evaluation:** Test on held-out data and historical traffic.
2. **Shadow mode:** Run on live traffic without serving predictions.
3. **A/B test with small traffic:** Route 1-5% of traffic to the new model.
4. **Gradual ramp:** Increase to 10%, 25%, 50%, monitoring metrics at each step.
5. **Full rollout:** Promote to 100% traffic.
6. **Continued monitoring:** Watch for long-term drift or seasonal effects.

## Pattern 5: Feature Store Architecture

A feature store is a centralized system for managing, storing, and serving ML features. It solves one of the most common problems in large scale machine learning system design: ensuring that training features and serving features are consistent.

### The Training-Serving Skew Problem

Without a feature store, feature engineering code is often duplicated between training pipelines (Python, Spark) and serving pipelines (Java, Go). This duplication leads to subtle inconsistencies, known as training-serving skew, which silently degrade model performance.

```
Without Feature Store (skew risk):

  Training Pipeline                    Serving Pipeline
  (Python/Spark)                       (Java/Go)
  ┌──────────────┐                     ┌──────────────┐
  │ Feature code │  ← Different        │ Feature code │
  │ version A    │     implementations │ version B    │
  └──────────────┘                     └──────────────┘
        │                                    │
        ▼                                    ▼
  Different feature values = Training-Serving Skew
```

### Feature Store Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                       Feature Store                            │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │  Feature     │    │  Feature     │    │  Feature     │     │
│  │  Registry    │    │  Transform   │    │  Monitoring  │     │
│  │  (metadata)  │    │  Engine      │    │  (quality)   │     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
│                                                                │
│  ┌─────────────────────────┐  ┌─────────────────────────┐     │
│  │   Offline Store         │  │   Online Store           │    │
│  │   (S3/BigQuery/Hive)    │  │   (Redis/DynamoDB)       │    │
│  │                         │  │                           │    │
│  │   - Historical values   │  │   - Latest values         │   │
│  │   - Point-in-time joins │  │   - Low-latency lookups   │   │
│  │   - Training datasets   │  │   - Serving features      │   │
│  └─────────────────────────┘  └─────────────────────────┘     │
│                                                                │
└────────────────────────────────────────────────────────────────┘
        ▲                  ▲                    │
        │                  │                    │
  ┌──────────┐      ┌──────────┐         ┌──────────┐
  │ Batch    │      │ Stream   │         │  Model   │
  │ Pipeline │      │ Pipeline │         │  Server  │
  └──────────┘      └──────────┘         └──────────┘
```

### Core Components

**Feature Registry:** A metadata catalog that tracks feature definitions, owners, data types, descriptions, lineage (where the feature comes from), and statistics. Think of it as a data dictionary specifically for ML features.

**Feature Transform Engine:** Executes feature transformations consistently across both training and serving. Transformations are defined once and applied everywhere.

**Offline Store:** Stores historical feature values for training. Supports point-in-time queries so that training data does not include future information (preventing data leakage). Typically backed by a data warehouse (BigQuery, Redshift) or object storage (S3 with Parquet files).

**Online Store:** Stores the latest feature values for real-time serving. Optimized for low-latency lookups by entity key. Typically backed by a key-value store (Redis, DynamoDB, Cassandra).

**Feature Monitoring:** Tracks feature distributions over time, alerting on drift, missing values, and data quality issues.

### Popular Feature Store Technologies

| Technology | Type | Strengths |
|-----------|------|-----------|
| Feast | Open source | Simple, pluggable backends, growing community |
| Tecton | Managed | Real-time transforms, Databricks integration |
| Hopsworks | Open source | Full MLOps platform, Spark-native |
| Vertex AI Feature Store | Managed (GCP) | Deep GCP integration, BigQuery native |
| SageMaker Feature Store | Managed (AWS) | AWS ecosystem, SageMaker integration |

### When to Invest in a Feature Store

A feature store adds complexity and is not always justified. Consider building one when:

- Multiple teams share features across different models.
- You have both batch and real-time serving requirements.
- Training-serving skew has caused production issues.
- Feature computation is expensive and should not be duplicated.
- You need point-in-time correctness for training data.

If you have a single model with simple features, a feature store is overkill. Start with a shared library of feature transforms and evolve to a feature store when the pain of managing features manually becomes greater than the cost of the infrastructure.

## Pattern 6: ML Model Registry and Versioning

A model registry is the source of truth for trained models in a production ML system. It tracks model versions, their training provenance, evaluation metrics, and deployment status. This pattern is essential for any end to end ML system design architecture that goes beyond a single prototype.

### Architecture

```
┌──────────────┐     ┌──────────────────────────────────────────┐
│  Training    │────▶│            Model Registry                │
│  Pipeline    │     ├──────────────────────────────────────────┤
└──────────────┘     │                                          │
                     │  Model: fraud-detector                   │
                     │  ┌────────────────────────────────┐      │
                     │  │ v3.2 [Production]  AUC: 0.94   │      │
                     │  │ v3.1 [Staging]     AUC: 0.93   │      │
                     │  │ v3.0 [Archived]    AUC: 0.91   │      │
                     │  │ v2.9 [Archived]    AUC: 0.90   │      │
                     │  └────────────────────────────────┘      │
                     │                                          │
                     │  Metadata per version:                   │
                     │  - Training data hash                    │
                     │  - Feature schema                        │
                     │  - Hyperparameters                       │
                     │  - Evaluation metrics                    │
                     │  - Training duration                     │
                     │  - Model size                            │
                     │  - Git commit hash                       │
                     │  - Author                                │
                     │  - Deployment history                    │
                     └────────────────┬─────────────────────────┘
                                      │
                          ┌───────────┴───────────┐
                          ▼                       ▼
                   ┌──────────────┐        ┌──────────────┐
                   │  Staging     │        │  Production  │
                   │  Environment │        │  Environment │
                   └──────────────┘        └──────────────┘
```

### Model Lifecycle Stages

1. **Registered:** A new model version is uploaded to the registry after training completes.
2. **Validated:** Automated tests pass (unit tests on prediction format, integration tests with the serving stack, performance benchmarks).
3. **Staging:** The model is deployed to a staging environment for shadow mode testing or canary deployment.
4. **Production:** The model is promoted to serve live traffic.
5. **Archived:** Previous production models are retained for rollback and audit.

### What to Version

Versioning just the model weights is insufficient. A complete model version should include:

- **Model artifact:** The serialized model file (weights, graph).
- **Feature schema:** The exact set of features the model expects, including types and acceptable ranges.
- **Preprocessing code:** Any transformations applied before inference.
- **Training data reference:** A pointer to the exact dataset (or a hash) used for training, not the data itself.
- **Training configuration:** Hyperparameters, random seeds, hardware used.
- **Evaluation results:** Metrics on validation and test sets.
- **Dependencies:** Library versions (TensorFlow 2.15, scikit-learn 1.4, etc.).

### Popular Model Registry Technologies

| Technology | Type | Strengths |
|-----------|------|-----------|
| MLflow Model Registry | Open source | Widely adopted, language-agnostic |
| Weights & Biases | Managed | Excellent experiment tracking, team features |
| Vertex AI Model Registry | Managed (GCP) | GCP-native, integrated deployment |
| SageMaker Model Registry | Managed (AWS) | AWS ecosystem, approval workflows |
| Neptune.ai | Managed | Lightweight, flexible metadata |

## Scaling Patterns: Data Parallelism, Model Parallelism, and Distributed Training

As models and datasets grow, single-machine training becomes impractical. Distributed ML system design patterns address this by spreading computation across multiple machines.

### Data Parallelism

Each worker holds a complete copy of the model but trains on a different subset (shard) of the data. Gradients are synchronized across workers after each step.

```
┌──────────────────────────────────────────────────────┐
│                  Parameter Server                     │
│            (Aggregates Gradients)                     │
└───────┬──────────────┬──────────────┬────────────────┘
        │              │              │
        ▼              ▼              ▼
  ┌──────────┐   ┌──────────┐   ┌──────────┐
  │ Worker 1 │   │ Worker 2 │   │ Worker 3 │
  │ GPU 0    │   │ GPU 1    │   │ GPU 2    │
  │          │   │          │   │          │
  │ Full     │   │ Full     │   │ Full     │
  │ Model    │   │ Model    │   │ Model    │
  │          │   │          │   │          │
  │ Data     │   │ Data     │   │ Data     │
  │ Shard 1  │   │ Shard 2  │   │ Shard 3  │
  └──────────┘   └──────────┘   └──────────┘
```

**When to use:** The model fits in a single GPU's memory, but training data is large. This is the most common distributed training strategy.

**Synchronization strategies:**
- **Synchronous SGD:** All workers compute gradients on their shard, gradients are averaged, and all workers update simultaneously. Consistent but slow (limited by the slowest worker).
- **Asynchronous SGD:** Workers update the parameter server independently. Faster but can produce stale gradients.
- **Ring AllReduce:** Workers pass gradients around a ring, eliminating the parameter server bottleneck. Used by Horovod and PyTorch DDP.

### Model Parallelism

The model is split across multiple devices, with each device holding a different part of the model. Data flows through devices sequentially.

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  GPU 0   │────▶│  GPU 1   │────▶│  GPU 2   │────▶│  GPU 3   │
│          │     │          │     │          │     │          │
│ Layers   │     │ Layers   │     │ Layers   │     │ Layers   │
│  1-10    │     │  11-20   │     │  21-30   │     │  31-40   │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
```

**When to use:** The model is too large to fit in a single GPU's memory. This is common for large language models and large vision transformers.

**Challenge:** Naive model parallelism creates a pipeline bubble where only one GPU is active at a time. Solutions include pipeline parallelism (GPipe, PipeDream) that overlap forward and backward passes across micro-batches.

### Hybrid Parallelism (For Very Large Models)

Modern large-scale training combines data parallelism, model parallelism (tensor parallelism), and pipeline parallelism. For example, training a 175B parameter model might use:

- **Tensor parallelism** within a single node (split matrix operations across 8 GPUs)
- **Pipeline parallelism** across nodes in a rack (split layers across 4 nodes)
- **Data parallelism** across racks (replicate the full pipeline across 16 groups)

This is the strategy used by frameworks like DeepSpeed and Megatron-LM for training models at the scale of GPT-4 and beyond.

### Distributed Training Infrastructure Considerations

- **Network bandwidth:** Gradient synchronization requires high-bandwidth, low-latency interconnects. InfiniBand or NVLink for intra-node, RDMA for inter-node.
- **Fault tolerance:** With hundreds of GPUs, hardware failures are inevitable. Checkpointing every N steps and elastic training (adding/removing workers) are essential.
- **Efficient data loading:** The data pipeline must keep GPUs fed. Use prefetching, parallel data loading, and optimized data formats (TFRecord, WebDataset).
- **Mixed precision training:** Use FP16 or BF16 for forward/backward passes and FP32 for gradient accumulation. This halves memory usage and doubles throughput on modern GPUs.

## Production Considerations: Monitoring, Drift Detection, and Rollback

Deploying a model is not the finish line. Production machine learning system design requires continuous monitoring to detect degradation and mechanisms to roll back quickly.

### What to Monitor

```
┌──────────────────────────────────────────────────────────────┐
│                    ML Monitoring Dashboard                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Model Performance        Data Quality        System Health  │
│  ┌────────────────┐      ┌──────────────┐    ┌────────────┐ │
│  │ Accuracy: 0.94 │      │ Missing: 0.1%│    │ p99: 45ms  │ │
│  │ AUC:     0.97  │      │ Outliers: 2% │    │ QPS: 1.2k  │ │
│  │ F1:      0.91  │      │ Schema: OK   │    │ Errors: 0% │ │
│  │ Drift:   LOW   │      │ Volume: OK   │    │ GPU: 72%   │ │
│  └────────────────┘      └──────────────┘    └────────────┘ │
│                                                              │
│  Feature Drift            Prediction Drift                   │
│  ┌────────────────┐      ┌──────────────────┐               │
│  │ age:     0.02  │      │ Mean pred: 0.34  │               │
│  │ income:  0.15▲ │      │ Std dev:   0.21  │               │
│  │ score:   0.03  │      │ Dist shift: 0.08 │               │
│  │ tenure:  0.01  │      │ Coverage:  99.2% │               │
│  └────────────────┘      └──────────────────┘               │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Model performance metrics:**
- Accuracy, precision, recall, F1 score (classification)
- MAE, RMSE, R-squared (regression)
- Business metrics (revenue per prediction, conversion lift)

**Data quality metrics:**
- Missing values, null rates, cardinality changes
- Schema violations (unexpected types, new categories)
- Volume anomalies (sudden drops or spikes in input data)

**Data drift metrics:**
- Population Stability Index (PSI) for feature distributions
- Kolmogorov-Smirnov test for distribution comparison
- Jensen-Shannon divergence for prediction distributions

**System health metrics:**
- Inference latency (p50, p95, p99)
- Throughput (queries per second)
- Error rates and timeout rates
- GPU/CPU utilization and memory

### Drift Detection Strategies

Data drift occurs when the distribution of input data changes over time. Concept drift occurs when the relationship between inputs and outputs changes.

**Detecting drift:**
1. **Reference window:** Establish a baseline distribution from the training data or a recent production window.
2. **Sliding window:** Continuously compute feature distributions over the most recent N hours or days.
3. **Statistical tests:** Compare the sliding window to the reference window using PSI, KS test, or chi-squared test.
4. **Alert thresholds:** Set thresholds for each feature and trigger alerts when drift exceeds them.

**Responding to drift:**
- **Mild drift (PSI < 0.1):** Monitor closely, no action needed.
- **Moderate drift (PSI 0.1-0.25):** Investigate the cause, consider retraining.
- **Severe drift (PSI > 0.25):** Retrain immediately, consider rolling back.

### Rollback Strategy

Every production ML system needs a rollback plan:

1. **Keep previous model versions deployed** behind a feature flag or traffic router. Rollback is a configuration change, not a deployment.
2. **Automate rollback triggers.** If a guardrail metric (latency, error rate, or a business metric) crosses a threshold, automatically revert.
3. **Maintain prediction logs.** Store predictions with timestamps and model versions so you can audit what happened.
4. **Test rollback regularly.** Just like disaster recovery drills, periodically verify that your rollback mechanism works.

## Interview Tips: How to Approach ML System Design Questions

ML system design questions are increasingly common in interviews at companies building AI products. These questions test your ability to think about the full machine learning lifecycle, not just model architecture. Here is a structured approach and a set of AI system design interview examples to practice with.

### The FRAME Framework for ML System Design

Use this five-step framework to structure your answer:

1. **F - Formulate the problem.** Clarify the ML task (classification, regression, ranking, recommendation). Define the input, output, and success metric. Ask clarifying questions about scale, latency requirements, and constraints.

2. **R - Review the data.** Discuss what data is available, how it is collected, and what features can be derived. Address data quality, labeling strategies, and privacy constraints.

3. **A - Architect the system.** Choose the right pattern (batch, real-time, online learning). Design the data pipeline, feature engineering, training pipeline, and serving infrastructure. Draw a clear architecture diagram.

4. **M - Model selection and training.** Discuss candidate models, training strategy, evaluation methodology, and offline metrics. Address training infrastructure (single machine vs. distributed).

5. **E - Evaluate and evolve.** Cover deployment strategy (shadow mode, A/B testing, gradual rollout), monitoring (drift detection, performance tracking), and iteration (retraining cadence, feedback loops).

### Example ML System Design Interview Questions

Here are seven common questions with brief notes on the key considerations for each:

**1. Design a recommendation system for a streaming platform (like Netflix).**
- Two-stage architecture: candidate generation (retrieve hundreds from millions) then ranking (score and order candidates).
- Feature store for user history, item metadata, and interaction features.
- Batch predictions for the homepage, real-time re-ranking when the user interacts.
- A/B testing on engagement metrics (watch time, completion rate).
- Cold-start strategies for new users and new content.

**2. Design a fraud detection system for a payment processor.**
- Real-time inference with strict latency constraints (< 100ms per transaction).
- Features: transaction velocity, merchant risk, device fingerprint, geographic anomalies.
- Extreme class imbalance (fraud is < 0.1% of transactions), so precision-recall tradeoff matters more than accuracy.
- Online learning to adapt to evolving fraud patterns.
- Human-in-the-loop review for borderline cases.

**3. Design a search ranking system for an e-commerce platform.**
- Multi-stage: query understanding, retrieval (inverted index + approximate nearest neighbor), ranking (LTR model), re-ranking (business rules).
- Feature engineering: query-document relevance, user personalization, item popularity, recency.
- Online A/B testing with interleaved experiments.
- Position bias in training data (users click higher-ranked items regardless of relevance).

**4. Design an image moderation system for a social media platform.**
- Real-time classification pipeline (upload, classify, serve or block).
- Multi-label classification (violence, nudity, hate symbols, spam).
- Model cascade: fast, cheap model filters 95% of content, expensive model handles borderline cases.
- Human review queue for low-confidence predictions.
- Feedback loop from human reviewers to improve the model.

**5. Design a demand forecasting system for a ride-sharing platform.**
- Time-series forecasting at the city-zone level with 15-minute granularity.
- Features: historical demand, weather, events, holidays, time of day, day of week.
- Batch prediction with frequent updates (every 15-30 minutes).
- Hierarchical forecasting (city, zone, sub-zone) with reconciliation.
- Direct business impact: drives surge pricing and driver positioning.

**6. Design a conversational AI system (chatbot) for customer support.**
- Intent classification + entity extraction + dialogue management.
- Retrieval-augmented generation (RAG) for knowledge-grounded responses.
- Conversation state tracking across multi-turn dialogues.
- Escalation to human agents based on confidence thresholds.
- Evaluation: task completion rate, user satisfaction, handle time reduction.

**7. Design an anomaly detection system for cloud infrastructure monitoring.**
- Streaming pipeline processing millions of metrics per second.
- Unsupervised or semi-supervised approaches (autoencoders, isolation forests) since labeled anomalies are rare.
- Multi-scale detection (point anomalies, contextual anomalies, collective anomalies).
- Alert routing and deduplication to prevent alert fatigue.
- Seasonal decomposition to handle daily and weekly patterns.

For additional system design interview strategies and a structured study plan, check out our [system design interview prep guide](/blog/system-design-interview-prep-practice).

### Common Mistakes in ML System Design Interviews

- **Jumping to model architecture.** Interviewers care more about the system than the model. Spend 70% of your time on data, features, serving, and monitoring.
- **Ignoring scale.** Always discuss how the system handles 10x and 100x growth.
- **Forgetting feedback loops.** Every ML system needs a plan for incorporating new labeled data.
- **Overlooking failure modes.** What happens when the model returns garbage? What happens when the feature store is down?
- **Not drawing diagrams.** A clear architecture diagram communicates more than ten minutes of verbal explanation. Practice sketching system diagrams, or use a tool like [InfraSketch](/tools/system-design-tool) to prototype architectures quickly.

## Putting It All Together: Choosing the Right Pattern

There is no single "best" pattern. The right choice depends on your latency requirements, data velocity, team maturity, and business constraints. Here is a decision framework:

```
Is prediction latency critical (< 100ms)?
├── YES: Do you need to adapt to distribution shift in real-time?
│   ├── YES → Pattern 3: Online Learning Pipeline
│   └── NO  → Pattern 2: Real-Time Inference Service
└── NO:  Can you precompute predictions for all entities?
    ├── YES → Pattern 1: Batch Prediction Pipeline
    └── NO  → Pattern 2: Real-Time Inference (with caching)

Always combine with:
├── Pattern 4: A/B Testing (for safe deployment)
├── Pattern 5: Feature Store (when sharing features across models)
└── Pattern 6: Model Registry (when managing multiple models)
```

Most mature ML platforms use a combination of these patterns. For example, Netflix uses batch predictions for homepage recommendations, real-time inference for search ranking, a centralized feature store, a model registry, and A/B testing for every model change.

## Conclusion

Machine learning system design patterns provide the architectural building blocks for deploying ML in production. The six patterns covered in this guide (batch prediction, real-time inference, online learning, A/B testing and shadow mode, feature stores, and model registries) address the core challenges of building reliable, scalable, and maintainable ML systems. Combined with sound practices around distributed training, monitoring, drift detection, and rollback, these patterns form the foundation for any production machine learning system design.

The key insight is that ML system design is fundamentally about the infrastructure around the model, not the model itself. The best model in the world is useless without reliable data pipelines, consistent feature engineering, safe deployment mechanisms, and continuous monitoring. When approaching any ML system design problem (whether in an interview or in production), start with the end-to-end picture and then drill into the patterns that fit your specific requirements.

Ready to design your own ML system architecture? [Try InfraSketch](https://infrasketch.net) to generate professional architecture diagrams from natural language descriptions. Describe your ML pipeline, and get an interactive diagram with a complete design document in seconds.

---

## Related Resources

- [LLM System Design Architecture](/blog/llm-system-design-architecture)
- [Real-World AI System Architecture](/blog/real-world-ai-system-architecture)
- [The Complete Guide to System Design](/blog/complete-guide-system-design)
- [System Design Interview Prep](/blog/system-design-interview-prep-practice)
- [Data Lake Architecture Diagram](/blog/data-lake-architecture-diagram)
- [Event-Driven Architecture Patterns](/blog/event-driven-architecture-patterns)
- [Microservices Architecture Diagram Guide](/blog/microservices-architecture-diagram-guide)
