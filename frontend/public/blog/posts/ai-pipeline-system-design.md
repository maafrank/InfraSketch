# AI Pipeline System Design: Data Ingestion, Training, and Serving

Building a production AI system requires far more than training a model in a notebook and calling it done. The real challenge lies in designing the end-to-end ML system design architecture that moves data from raw sources through feature engineering, training, evaluation, and finally into serving infrastructure where predictions reach users. Each phase introduces its own set of engineering problems around reliability, scalability, and correctness.

This guide walks through all three phases of an AI pipeline system design (data ingestion, training, and serving), covering the infrastructure decisions, orchestration patterns, and common pitfalls that separate prototype ML systems from production-grade ones. Whether you are preparing for a system design interview or building a real ML platform, understanding how these components connect is essential.

## The Three Phases of an AI Pipeline

Every production ML system can be decomposed into three major phases:

1. **Data Ingestion and Feature Engineering**: Getting raw data into the system, validating it, and transforming it into features the model can consume.
2. **Training Infrastructure**: Computing model weights from training data, tuning hyperparameters, and managing GPU resources efficiently.
3. **Serving Infrastructure**: Deploying trained models to handle prediction requests in real time, in batch, or at the edge.

These phases are not isolated. They share data contracts, depend on consistent feature transformations, and require coordinated orchestration. A failure in any phase cascades through the entire pipeline.

```
+------------------+     +------------------+     +------------------+
|  Data Ingestion  | --> | Model Training   | --> | Model Serving    |
|  & Feature Eng.  |     | & Evaluation     |     | & Monitoring     |
+------------------+     +------------------+     +------------------+
        |                        |                        |
        v                        v                        v
  Feature Store          Model Registry           Prediction Logs
  Data Catalog           Experiment Tracker       A/B Test Results
```

The rest of this guide examines each phase in detail, then connects them into a unified architecture.

## Data Ingestion Architecture

Data ingestion is the foundation of any AI pipeline. The quality, freshness, and reliability of your data directly determine the upper bound of your model's performance. There are three primary ingestion patterns: batch, streaming, and hybrid.

### Batch Ingestion with ETL

Batch ingestion processes data in scheduled intervals (hourly, daily, or weekly). This is the most common pattern for training pipelines because models are typically retrained on a cadence rather than continuously.

**Common tools:**
- **Apache Spark**: Distributed processing for large-scale ETL
- **AWS Glue / Azure Data Factory**: Managed ETL services
- **dbt**: SQL-based transformation for warehouse-centric pipelines
- **Apache Airflow**: Orchestration of batch ETL DAGs

**Typical batch ingestion flow:**

```
+-----------+     +-----------+     +------------+     +---------------+
| Source DBs| --> | Extract   | --> | Transform  | --> | Load to       |
| APIs      |     | (Pull)    |     | (Clean,    |     | Data Lake /   |
| Files     |     |           |     |  Validate) |     | Feature Store |
+-----------+     +-----------+     +------------+     +---------------+
```

Batch ingestion works well when your data sources update infrequently and your model does not need predictions based on the last few seconds of data. The trade-off is latency: data may be hours or days old by the time it reaches the model.

### Streaming Ingestion with Kafka and Kinesis

Streaming ingestion processes data as it arrives, enabling near-real-time feature computation and model updates. This pattern is necessary for use cases like fraud detection, recommendation engines, and real-time bidding.

**Common tools:**
- **Apache Kafka**: High-throughput distributed event streaming
- **Amazon Kinesis**: Managed streaming on AWS
- **Apache Flink**: Stateful stream processing
- **Apache Pulsar**: Multi-tenant, geo-replicated messaging

**Streaming ingestion architecture:**

```
+-------------+     +----------+     +----------------+     +---------+
| Event       | --> | Kafka /  | --> | Stream         | --> | Feature |
| Producers   |     | Kinesis  |     | Processor      |     | Store   |
| (Apps, IoT, |     | (Buffer) |     | (Flink/Spark   |     | (Online |
|  Sensors)   |     |          |     |  Streaming)    |     |  Store) |
+-------------+     +----------+     +----------------+     +---------+
```

Streaming pipelines are more complex to operate. You need to handle out-of-order events, exactly-once semantics, backpressure, and schema evolution. The operational overhead is significant, so only adopt streaming when the use case truly demands low-latency features.

### Hybrid Approach

Most production ML systems use a hybrid approach, sometimes called the Lambda architecture. Batch pipelines handle historical data and periodic retraining, while streaming pipelines compute real-time features for serving. The [feature store](/blog/feature-store-system-design) bridges the two by providing a unified interface for both batch and real-time features.

### Data Validation and Quality Checks

Raw data is unreliable. Schemas change without notice, upstream services introduce bugs, and data distributions shift over time. Without validation, these issues silently degrade model performance.

**Validation strategies:**

- **Schema validation**: Enforce column types, required fields, and allowed values using tools like Great Expectations, Pandera, or TensorFlow Data Validation (TFDV).
- **Statistical validation**: Monitor distributions, null rates, and value ranges. Alert when metrics deviate beyond thresholds.
- **Referential integrity**: Verify that foreign keys, join keys, and entity identifiers are consistent across datasets.
- **Freshness checks**: Confirm that data partitions arrive on schedule. Missing partitions should block downstream processing.

```python
# Example: Great Expectations validation
import great_expectations as gx

context = gx.get_context()
validator = context.sources.pandas_default.read_csv("training_data.csv")

# Schema checks
validator.expect_column_to_exist("user_id")
validator.expect_column_values_to_be_of_type("user_id", "int64")

# Statistical checks
validator.expect_column_values_to_not_be_null("label", mostly=0.99)
validator.expect_column_mean_to_be_between("feature_a", min_value=0.1, max_value=10.0)

# Distribution checks
validator.expect_column_kl_divergence_to_be_less_than(
    "feature_b", partition_object=reference_distribution, threshold=0.1
)
```

Data validation should be a hard gate in your pipeline. If validation fails, the pipeline should halt and alert rather than silently pushing bad data into training.

## Feature Engineering Pipelines

Feature engineering transforms raw data into the numeric representations that models consume. The challenge is doing this consistently between training and serving, at scale, and with low latency for real-time use cases.

### Batch Feature Computation

Batch features are computed on a schedule over historical data. These include aggregations (average transaction amount over 30 days), window functions (rolling counts), and complex joins across multiple tables.

**Common patterns:**
- **SQL-based transforms**: Run in Spark SQL or warehouse (BigQuery, Redshift, Snowflake)
- **PySpark jobs**: For transforms requiring custom logic
- **dbt models**: For teams that prefer SQL-first feature engineering

Batch features are typically materialized into an offline feature store for training and backfilled into the online store for serving.

### Real-Time Feature Computation

Some features must be computed at request time because they depend on data that is only seconds old. Examples include the number of login attempts in the last five minutes, current session duration, and the most recent item a user viewed.

Real-time features are computed by stream processors (Flink, Spark Structured Streaming) consuming from Kafka or Kinesis. They are written to a low-latency online store (Redis, DynamoDB, Cassandra) for retrieval during inference.

```
+----------+     +---------+     +----------------+     +-------------+
| Kafka    | --> | Flink   | --> | Online Feature | --> | Serving     |
| Events   |     | Window  |     | Store (Redis)  |     | Application |
|          |     | Agg.    |     |                |     |             |
+----------+     +---------+     +----------------+     +-------------+
```

### Feature Stores for Consistency

A feature store is a centralized system that manages the storage, serving, and discovery of ML features. It solves the critical problem of training-serving skew by ensuring that the same transformation logic produces features for both training and inference.

**Key capabilities of a feature store:**

| Capability | Description |
|------------|-------------|
| Dual storage | Offline store for training (S3/warehouse), online store for serving (Redis/DynamoDB) |
| Point-in-time correctness | Retrieves features as they existed at a specific timestamp, preventing data leakage |
| Feature registry | Searchable catalog of all features with metadata, ownership, and lineage |
| Materialization | Automated syncing of features from offline to online stores |
| Monitoring | Tracks feature freshness, coverage, and distribution drift |

**Popular feature store implementations:**
- **Feast**: Open-source, cloud-agnostic
- **Tecton**: Managed platform built on Feast concepts
- **Amazon SageMaker Feature Store**: AWS-native
- **Databricks Feature Store**: Integrated with MLflow
- **Hopsworks**: Open-source with extensive support for real-time features

For a deeper dive into feature store architecture, see our dedicated guide on [Feature Store System Design](/blog/feature-store-system-design).

### Transformation Registries

A transformation registry centralizes the definitions of all feature transformations so they can be reused, versioned, and applied consistently. Without one, teams end up duplicating transformation logic between training scripts and serving code, which is one of the most common sources of training-serving skew.

```python
# Example: Feast feature definition
from feast import Entity, Feature, FeatureView, FileSource, ValueType

user = Entity(name="user_id", value_type=ValueType.INT64)

user_features = FeatureView(
    name="user_features",
    entities=["user_id"],
    ttl=timedelta(days=1),
    features=[
        Feature(name="avg_transaction_30d", dtype=ValueType.FLOAT),
        Feature(name="login_count_7d", dtype=ValueType.INT64),
        Feature(name="account_age_days", dtype=ValueType.INT64),
    ],
    batch_source=FileSource(
        path="s3://features/user_features.parquet",
        timestamp_field="event_timestamp",
    ),
)
```

By defining features declaratively, the feature store can generate the correct retrieval logic for both batch (training) and online (serving) contexts.

## Training Infrastructure

Training infrastructure must balance three competing concerns: speed (time to train), cost (GPU hours are expensive), and reproducibility (every experiment must be traceable). The choices you make here depend on model size, dataset scale, and budget.

### Single-Node Training

For models that fit in the memory of a single GPU (most tabular ML, small to medium deep learning models), single-node training is the simplest and most cost-effective approach. Use a single GPU instance (AWS p3.2xlarge, GCP n1-standard with T4/V100) with frameworks like PyTorch, TensorFlow, or XGBoost.

**When single-node is sufficient:**
- Dataset fits in memory (or can be loaded in chunks)
- Model has fewer than a few hundred million parameters
- Training completes in a reasonable time (under a few hours)
- You do not need to iterate on experiments rapidly

### Distributed Training

When models or datasets exceed what a single machine can handle, you need distributed training. There are two primary strategies.

**Data Parallelism:**
Each worker holds a complete copy of the model and processes a different shard of the training data. Gradients are synchronized across workers after each step (via AllReduce or parameter servers). This is the most common distributed training strategy and scales well for models that fit on a single GPU.

```
+----------+     +----------+     +----------+
| Worker 1 |     | Worker 2 |     | Worker 3 |
| (Full    |     | (Full    |     | (Full    |
|  Model)  |     |  Model)  |     |  Model)  |
| Shard 1  |     | Shard 2  |     | Shard 3  |
+----+-----+     +----+-----+     +----+-----+
     |                |                |
     +-------+--------+--------+------+
             |                 |
        Gradient Sync (AllReduce)
             |
       +-----+-----+
       | Updated   |
       | Model     |
       +-----------+
```

**Model Parallelism:**
The model itself is split across multiple GPUs because it is too large to fit in a single GPU's memory. Different layers or tensor slices reside on different devices. This is necessary for large language models (billions of parameters) and requires careful pipeline scheduling to minimize idle GPU time.

**Frameworks for distributed training:**
- **PyTorch Distributed (DDP)**: Native data parallelism in PyTorch
- **DeepSpeed**: Microsoft's library for large model training (ZeRO optimizer)
- **Horovod**: Framework-agnostic distributed training library
- **Ray Train**: Distributed training with Ray's actor model
- **FSDP (Fully Sharded Data Parallel)**: PyTorch's memory-efficient alternative to DDP

### Hyperparameter Tuning

Hyperparameter tuning searches the space of model configurations to find the best performing set. This is inherently parallelizable and benefits significantly from distributed infrastructure.

**Tuning strategies:**

| Strategy | How It Works | Best For |
|----------|-------------|----------|
| Grid Search | Exhaustive search over defined grid | Small search spaces, few hyperparameters |
| Random Search | Random sampling from distributions | Medium search spaces, faster than grid |
| Bayesian Optimization | Models objective function, picks promising points | Expensive evaluations, continuous parameters |
| Hyperband / ASHA | Early stopping of poor trials | Large search spaces, limited budget |
| Population-Based Training | Evolves hyperparameters during training | Long training runs, RL and GANs |

**Tools:**
- **Optuna**: Pythonic, supports pruning and multiple backends
- **Ray Tune**: Distributed tuning with support for all strategies above
- **W&B Sweeps**: Integrated with Weights & Biases experiment tracking
- **SageMaker Automatic Model Tuning**: Managed Bayesian optimization

### Spot and Preemptible Instances for Cost Reduction

GPU instances are expensive. A single p4d.24xlarge (8x A100 GPUs) costs over $30 per hour on-demand. Spot instances (AWS) or preemptible VMs (GCP) offer 60-90% discounts but can be reclaimed with short notice.

**Making spot instances work for training:**

- **Checkpointing**: Save model state every N steps to durable storage (S3, GCS). On preemption, resume from the last checkpoint.
- **Elastic training**: Use frameworks like PyTorch Elastic or Ray Train that can scale workers up and down dynamically.
- **Mixed fleets**: Combine on-demand base capacity with spot instances for burst capacity.
- **Instance diversification**: Request multiple instance types to reduce the probability of simultaneous preemption across all workers.

```python
# Example: PyTorch checkpointing for spot instance resilience
import torch

def save_checkpoint(model, optimizer, epoch, step, loss, path):
    torch.save({
        "epoch": epoch,
        "step": step,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "loss": loss,
    }, path)

def load_checkpoint(model, optimizer, path):
    checkpoint = torch.load(path)
    model.load_state_dict(checkpoint["model_state_dict"])
    optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
    return checkpoint["epoch"], checkpoint["step"]
```

### GPU Cluster Management

At scale, managing GPU clusters becomes a discipline of its own. Key considerations include:

- **Scheduling**: Use Kubernetes with GPU device plugins or Slurm for HPC-style scheduling. Ensure fair queuing across teams.
- **Multi-tenancy**: Isolate workloads using namespaces, resource quotas, and GPU partitioning (MIG on A100s).
- **Networking**: Distributed training is bottlenecked by inter-node communication. Use high-bandwidth interconnects (NVLink, InfiniBand, EFA on AWS).
- **Storage**: Training data must be accessible at high throughput. Use parallel file systems (Lustre, FSx) or high-performance object storage.
- **Monitoring**: Track GPU utilization, memory usage, and communication overhead. Low GPU utilization indicates a bottleneck elsewhere (data loading, CPU preprocessing, network).

```
+-------------------+     +-------------------+
| GPU Cluster       |     | Shared Storage    |
| +------+ +------+ |     | +---------------+ |
| | Node | | Node | |     | | Training Data | |
| | 8xGPU| | 8xGPU| |<--->| | (Lustre/FSx)  | |
| +------+ +------+ |     | +---------------+ |
| +------+ +------+ |     | +---------------+ |
| | Node | | Node | |     | | Checkpoints   | |
| | 8xGPU| | 8xGPU| |<--->| | (S3/GCS)      | |
| +------+ +------+ |     | +---------------+ |
+-------------------+     +-------------------+
        |
+-------------------+
| Job Scheduler     |
| (K8s / Slurm)     |
+-------------------+
```

## Model Evaluation and Validation

Training a model is only half the battle. Before any model reaches production, it must pass through a rigorous evaluation and validation pipeline that goes beyond checking a single accuracy number.

### Offline Metrics

Offline evaluation computes metrics on held-out test sets. The specific metrics depend on the problem type:

- **Classification**: Precision, recall, F1, AUC-ROC, AUC-PR, calibration curves
- **Regression**: MAE, RMSE, R-squared, quantile errors
- **Ranking**: NDCG, MAP, MRR
- **Generative models**: Perplexity, BLEU, ROUGE, human evaluation scores

Beyond aggregate metrics, evaluate performance across slices of your data. A model that performs well overall but fails for a specific demographic or region is not ready for production. Tools like Fairlearn, Aequitas, and What-If Tool support slice-based evaluation.

### A/B Testing Integration

Offline metrics correlate imperfectly with business outcomes. A/B testing (or online experimentation) measures the actual impact of a new model on users. The evaluation pipeline should integrate with the experimentation platform to:

1. Generate predictions from both the current model and the candidate model
2. Route a percentage of traffic to each model
3. Collect outcome metrics (click-through rate, conversion, revenue)
4. Run statistical tests to determine if the candidate is significantly better

Design your serving infrastructure to support traffic splitting from the start. Retrofitting A/B testing into a monolithic serving system is painful.

### Champion-Challenger Pattern

The champion-challenger pattern (also called shadow mode or canary deployment) provides a safer alternative to full A/B testing. The current production model (champion) serves all real traffic. The new model (challenger) receives the same requests but its predictions are logged rather than returned to users.

**Benefits:**
- No risk to user experience during evaluation
- Collects realistic prediction distributions for comparison
- Can run alongside A/B tests for additional validation

**Flow:**

```
                +---> Champion Model ---> Response to User
User Request ---|
                +---> Challenger Model ---> Log predictions
                                            (compare offline)
```

### Model Registry

A model registry is the central repository for trained model artifacts. It serves as the handoff point between training and serving, storing not just the model weights but also:

- **Metadata**: Training dataset version, hyperparameters, training duration
- **Metrics**: All offline evaluation results
- **Lineage**: Which code commit, feature versions, and data snapshots produced this model
- **Stage**: Development, staging, production, or archived
- **Signatures**: Input/output schema for serving validation

**Popular model registries:**
- **MLflow Model Registry**: Open-source, widely adopted
- **Weights & Biases Model Registry**: Integrated with experiment tracking
- **Amazon SageMaker Model Registry**: AWS-native
- **Vertex AI Model Registry**: GCP-native

A model should not be deployed to production without being registered, evaluated, and explicitly promoted through the registry's stage gates.

## Serving Infrastructure

Serving infrastructure delivers model predictions to end users and downstream systems. The requirements vary dramatically depending on whether you need real-time responses, batch predictions, or edge deployment.

### Online Serving with REST and gRPC

Online serving handles individual prediction requests with low-latency requirements (typically under 100ms). The model runs behind an API endpoint that accepts input features and returns predictions.

**Architecture components:**

```
+--------+     +-----------+     +---------------+     +-----------+
| Client | --> | Load      | --> | Model Server  | --> | Response  |
|        |     | Balancer  |     | (TF Serving / |     |           |
|        |     | (ALB/NLB) |     |  Triton /     |     |           |
|        |     |           |     |  TorchServe)  |     |           |
+--------+     +-----------+     +---------------+     +-----------+
                                       |
                                 +-----+-----+
                                 | Feature   |
                                 | Store     |
                                 | (Online)  |
                                 +-----------+
```

**Model serving frameworks:**

| Framework | Strengths | Best For |
|-----------|-----------|----------|
| TensorFlow Serving | Mature, gRPC native, model versioning | TensorFlow models |
| Triton Inference Server | Multi-framework, dynamic batching, GPU optimization | Mixed model types, GPU serving |
| TorchServe | PyTorch native, easy model packaging | PyTorch models |
| BentoML | Framework-agnostic, simple API, containerized | Rapid prototyping, multi-framework |
| Seldon Core | Kubernetes-native, inference graphs, A/B testing | K8s environments |
| Ray Serve | Python-native, composable, scales horizontally | Complex inference pipelines |

**Key serving concerns:**

- **Autoscaling**: Scale model replicas based on request rate, latency percentiles, or GPU utilization. Use Kubernetes HPA or cloud-specific autoscalers.
- **Batching**: Accumulate multiple requests and process them together to maximize GPU throughput. Triton and TF Serving support dynamic batching natively.
- **Caching**: Cache predictions for repeated inputs. This is especially effective for recommendation systems where the same items are scored frequently.
- **Health checks**: Implement readiness and liveness probes. A model server that loaded a corrupt model should not receive traffic.

### Batch Prediction

Not all predictions need to happen in real time. Batch prediction processes large volumes of inputs on a schedule and writes results to a database or data warehouse for later retrieval.

**When to use batch prediction:**
- Predictions are needed for all entities periodically (daily recommendations, risk scores)
- Latency requirements are relaxed (hours, not milliseconds)
- Input data is only available in bulk
- Cost optimization is important (batch processing is more efficient per prediction)

**Architecture:**

```
+------------+     +-----------+     +---------------+     +----------+
| Input Data | --> | Spark /   | --> | Model         | --> | Results  |
| (S3/       |     | Dataflow  |     | (loaded from  |     | (DB /    |
|  Warehouse)|     |           |     |  registry)    |     |  Cache)  |
+------------+     +-----------+     +---------------+     +----------+
```

Batch prediction jobs run on the same distributed compute infrastructure as training (Spark, Ray, SageMaker Batch Transform) but with read-only model access.

### Edge Deployment

Edge deployment pushes models to devices that are close to the data source: mobile phones, IoT sensors, autonomous vehicles, or on-premise servers. This is necessary when network latency is unacceptable, connectivity is unreliable, or data privacy prevents sending raw data to the cloud.

**Edge deployment considerations:**
- **Model compression**: Quantization (INT8/INT4), pruning, knowledge distillation to reduce model size and inference cost.
- **Runtime**: TensorFlow Lite, ONNX Runtime, Core ML, TensorRT for hardware-specific optimization.
- **Updates**: Over-the-air (OTA) model updates with rollback capability.
- **Monitoring**: Collect inference telemetry from edge devices for aggregate monitoring (you cannot inspect individual requests at scale).

### Model Optimization for Serving

Production models often need optimization to meet latency and cost targets. Common techniques include:

- **Quantization**: Reduce precision from FP32 to FP16 or INT8. Reduces memory footprint and speeds up inference, often with minimal accuracy loss.
- **Pruning**: Remove weights that contribute little to predictions. Structured pruning removes entire neurons or channels.
- **Distillation**: Train a smaller "student" model to mimic a larger "teacher" model. The student is faster to serve while retaining most of the teacher's accuracy.
- **ONNX conversion**: Export models to ONNX format for cross-framework optimization and hardware-specific acceleration.
- **Compilation**: Use tools like TVM, XLA, or TensorRT to compile models into optimized machine code for the target hardware.

## Orchestration

ML pipelines have complex dependencies between data ingestion, feature computation, training, evaluation, and deployment. Orchestration tools manage these dependencies as directed acyclic graphs (DAGs), handling scheduling, retries, monitoring, and alerting.

### Orchestration Tool Comparison

| Tool | Architecture | ML-Specific Features | Strengths | Weaknesses |
|------|-------------|---------------------|-----------|------------|
| **Apache Airflow** | Central scheduler, workers | Limited (needs plugins) | Mature, large community, extensive integrations | UI dated, dynamic DAGs complex, not ML-native |
| **Kubeflow Pipelines** | Kubernetes-native | Full ML lifecycle | Deep K8s integration, containerized steps, experiment tracking | Requires K8s expertise, complex setup |
| **Dagster** | Asset-based, software-defined | Good (IO managers, partitions) | Type safety, testability, asset lineage | Newer community, fewer integrations |
| **Prefect** | Hybrid (cloud + agent) | Moderate | Simple Python API, good observability, easy local dev | Less mature than Airflow for complex workflows |
| **ZenML** | ML-specific abstraction | Full ML lifecycle | Stack-agnostic, pipeline caching, artifact tracking | Newer, smaller community |
| **Metaflow** | Python-native | Full ML lifecycle | Simple API, built-in versioning, Netflix-proven | AWS-centric, limited scheduling |

### DAG-Based Pipeline Management

Each stage of the ML pipeline becomes a node in a DAG. The orchestrator ensures that stages run in the correct order, retries failed stages, and provides visibility into pipeline health.

**Example: Training pipeline DAG**

```
validate_data --> compute_features --> split_data
                                          |
                                    +-----+-----+
                                    |           |
                              train_model   train_baseline
                                    |           |
                                    +-----+-----+
                                          |
                                    evaluate_models
                                          |
                                    register_model
                                          |
                                    deploy_to_staging
                                          |
                                    run_integration_tests
                                          |
                                    promote_to_production
```

### Scheduling and Monitoring

**Scheduling patterns:**
- **Cron-based**: Run pipelines on fixed schedules (e.g., retrain daily at 2 AM UTC)
- **Event-driven**: Trigger pipelines when new data arrives (S3 event, Kafka topic)
- **Data-aware**: Run only when upstream data partitions are available (Dagster sensors, Airflow data-aware scheduling)

**Monitoring essentials:**
- **Pipeline health**: Success/failure rates, duration trends, SLA compliance
- **Data quality**: Validation results at each stage, schema drift detection
- **Model quality**: Prediction distribution shifts, feature drift, accuracy degradation
- **Infrastructure**: GPU utilization, memory pressure, queue depth, cost per pipeline run

Set up alerting for pipeline failures, SLA breaches, and data quality violations. Use PagerDuty, OpsGenie, or Slack integrations so the on-call engineer is notified immediately.

## Connecting the Phases: End-to-End Architecture

Now that we have examined each phase independently, let us connect them into a complete AI pipeline architecture. The following diagram shows how all components interact in a production ML system.

```
+===========================================================================+
|                        END-TO-END AI PIPELINE                             |
+===========================================================================+
|                                                                           |
|  DATA INGESTION                                                           |
|  +----------+  +----------+                                               |
|  | Batch    |  | Streaming|                                               |
|  | Sources  |  | Sources  |                                               |
|  | (DBs,    |  | (Kafka,  |                                               |
|  |  Files)  |  |  Events) |                                               |
|  +----+-----+  +----+-----+                                               |
|       |              |                                                    |
|       v              v                                                    |
|  +----+--------------+----+                                               |
|  |  Data Validation       |                                               |
|  |  (Great Expectations)  |                                               |
|  +----+--------------+----+                                               |
|       |              |                                                    |
|       v              v                                                    |
|  +---------+   +-----------+                                              |
|  | Offline  |   | Online    |                                              |
|  | Feature  |   | Feature   |                                              |
|  | Store    |   | Store     |                                              |
|  | (S3/WH)  |   | (Redis)   |                                              |
|  +----+-----+   +-----+-----+                                              |
|       |               |                                                   |
+-------+---------------+---------------------------------------------------+
|       |               |                                                   |
|  TRAINING             |                                                   |
|       v               |                                                   |
|  +-----------+        |                                                   |
|  | Training  |        |                                                   |
|  | Cluster   |        |                                                   |
|  | (GPUs)    |        |                                                   |
|  +-----+-----+        |                                                   |
|        |               |                                                  |
|        v               |                                                  |
|  +------------+        |                                                  |
|  | Evaluation |        |                                                  |
|  | Pipeline   |        |                                                  |
|  +-----+------+        |                                                  |
|        |               |                                                  |
|        v               |                                                  |
|  +------------+        |                                                  |
|  | Model      |        |                                                  |
|  | Registry   |        |                                                  |
|  +-----+------+        |                                                  |
|        |               |                                                  |
+--------+---------------+--------------------------------------------------+
|        |               |                                                  |
|  SERVING               |                                                  |
|        v               v                                                  |
|  +-----+------+  +-----+-----+                                            |
|  | Model      |  | Feature   |                                            |
|  | Server     |<-| Retrieval |                                            |
|  | (Triton/   |  | (Online   |                                            |
|  |  TF Serve) |  |  Store)   |                                            |
|  +-----+------+  +-----------+                                            |
|        |                                                                  |
|        v                                                                  |
|  +------------+     +---------------+                                     |
|  | Prediction |---->| Monitoring    |                                     |
|  | Response   |     | & Alerting    |                                     |
|  +------------+     +-------+-------+                                     |
|                             |                                             |
|                             v                                             |
|                     +-------+-------+                                     |
|                     | Retrain       |                                     |
|                     | Trigger       |-----> (Back to Training)            |
|                     +---------------+                                     |
|                                                                           |
+===========================================================================+
|  ORCHESTRATION: Airflow / Kubeflow / Dagster                              |
+===========================================================================+
```

**Key integration points:**

1. **Feature Store as the bridge**: The feature store connects ingestion to both training and serving. Training reads from the offline store. Serving reads from the online store. Both use the same feature definitions.

2. **Model Registry as the handoff**: The registry is the single source of truth for model artifacts. Training writes to it. Serving reads from it. No model reaches production without passing through the registry.

3. **Monitoring closes the loop**: Prediction monitoring detects data drift, model degradation, and feature staleness. When metrics breach thresholds, it triggers retraining automatically or alerts the ML team.

4. **Orchestration ties it together**: The orchestration layer manages scheduling, dependencies, and failure handling across all three phases. It ensures that data validation completes before feature computation, features are ready before training starts, and models pass evaluation before deployment.

For more on how these patterns fit into broader MLOps practices, see our guide on [MLOps System Design](/blog/mlops-system-design).

## Common Pitfalls

Even well-designed ML systems fall prey to recurring problems. Here are the most common pitfalls and how to avoid them.

### 1. Training-Serving Skew

Training-serving skew occurs when the features or preprocessing applied during training differ from what happens during serving. This is the single most common source of silent model degradation in production.

**Causes:**
- Different code paths for training and serving feature computation
- Using future data during training that is unavailable at serving time
- Differences in library versions between training and serving environments
- Inconsistent handling of missing values, outliers, or categorical encodings

**Prevention:**
- Use a [feature store](/blog/feature-store-system-design) to enforce consistent transformations
- Containerize both training and serving environments with identical dependencies
- Log serving-time features and periodically compare them against training distributions
- Write integration tests that verify feature parity between training and serving code paths

### 2. Data Leakage

Data leakage means that information from the test set or the future leaks into the training process, producing overly optimistic evaluation metrics that do not generalize to production.

**Common sources:**
- Using features computed from the full dataset (including test rows) during preprocessing
- Temporal leakage: using features derived from events after the prediction timestamp
- Target leakage: using variables that are proxies for the label (e.g., using "loan approved" to predict "creditworthy")

**Prevention:**
- Use point-in-time-correct feature retrieval (feature store with event timestamps)
- Split data temporally, not randomly, for time-series problems
- Review feature definitions with domain experts to identify proxy variables
- Validate that training metrics and serving metrics are in the same range

### 3. Ignoring Monitoring

Many teams invest heavily in model development and then deploy without adequate monitoring. Without monitoring, model degradation is invisible until users complain or business metrics decline weeks later.

**What to monitor:**
- **Prediction distribution**: Compare the distribution of predictions over time. A sudden shift indicates data drift or a broken feature pipeline.
- **Feature distributions**: Monitor each input feature for drift using statistical tests (KS test, PSI, Jensen-Shannon divergence).
- **Latency**: Track p50, p95, and p99 inference latency. Degradation may indicate resource contention or a model that has grown too large.
- **Error rates**: Monitor for increased null predictions, out-of-range values, or serving errors.
- **Business metrics**: Correlate model predictions with downstream outcomes (conversion rates, fraud catch rates, user engagement).

**Tools**: Evidently AI, Arize, WhyLabs, Fiddler, Amazon SageMaker Model Monitor, Seldon Alibi Detect.

### 4. Over-Engineering

Not every ML system needs Kubernetes, a feature store, distributed training, and a full MLOps platform on day one. Over-engineering introduces unnecessary complexity, slows iteration, and consumes engineering bandwidth better spent on model improvement.

**Start simple:**
- Begin with batch predictions and a cron job before building real-time serving
- Use a single GPU before investing in distributed training
- Store features in a database before adopting a feature store
- Deploy with a simple Flask/FastAPI server before adopting Triton or Seldon
- Use MLflow for experiment tracking before building a custom platform

**Scale when you have evidence**: Add infrastructure complexity only when you can point to a specific bottleneck or requirement that justifies it. "Netflix does it this way" is not a valid reason for a 10-person team.

For more patterns on when to introduce complexity, see our guide on [ML System Design Patterns](/blog/ml-system-design-patterns).

## Conclusion

Designing an end-to-end AI pipeline system requires thinking across data ingestion, feature engineering, training, evaluation, serving, and orchestration. Each phase has its own set of infrastructure challenges, and the connections between phases (particularly the feature store and model registry) are where most production ML systems succeed or fail.

The key takeaways from this guide:

1. **Data quality is the foundation.** No amount of model sophistication compensates for bad data. Invest in validation, monitoring, and governance early.

2. **Feature stores prevent training-serving skew.** A centralized feature store that serves both training and inference is the single most impactful infrastructure investment for ML teams.

3. **Start simple, scale deliberately.** Begin with batch ingestion, single-node training, and simple REST serving. Add streaming, distributed training, and GPU-optimized serving only when specific requirements demand it.

4. **Monitoring closes the loop.** Production ML systems degrade over time as data distributions shift. Without monitoring and automated retraining triggers, models silently become stale.

5. **Orchestration is the glue.** DAG-based pipeline management ensures that all phases run reliably, in the correct order, with proper error handling and observability.

Whether you are designing a fraud detection system, a recommendation engine, or a computer vision pipeline, these patterns and components form the backbone of production ML infrastructure. The specific tools may change, but the architectural principles remain consistent.

---

*Want to visualize your AI pipeline architecture? Try [InfraSketch](https://infrasketch.net) to generate end-to-end ML system diagrams from natural language descriptions. Describe your data sources, training requirements, and serving needs, and get a complete architecture diagram in seconds.*

## Related Resources

- [Machine Learning System Design Patterns](/blog/ml-system-design-patterns)
- [MLOps System Design](/blog/mlops-system-design)
- [Feature Store System Design](/blog/feature-store-system-design)
- [Data Lake Architecture](/blog/data-lake-architecture-diagram)
- [Streaming ML System Design](/blog/streaming-ml-system-design)
- [ML System Design Tool](/tools/ml-system-design-tool)
