# Streaming ML System Design: Real-Time Machine Learning Architecture

Streaming ML system design addresses one of the most demanding challenges in modern machine learning engineering: delivering predictions and model updates in real time as data flows continuously through your system. While batch ML pipelines dominate most production environments, an increasing number of use cases require millisecond-level response times, features computed on live event streams, and models that adapt to shifting patterns within minutes rather than days. Fraud detection, real-time recommendations, dynamic pricing, and autonomous systems all depend on streaming ML architectures.

If you are already familiar with [batch ML system design patterns](/blog/ml-system-design-patterns), streaming ML builds on those foundations but introduces new constraints around latency, ordering, state management, and fault tolerance. This guide covers the core streaming ML architecture patterns, stream processing frameworks, real-time feature engineering, and two detailed case studies. Whether you are preparing for an ML system design interview or building a real-time ML system design from scratch, this guide provides the practical knowledge you need.

## Batch vs Streaming ML: When Do You Need Real-Time?

Batch systems are simpler, cheaper, and easier to debug. They compute predictions on a schedule and store results for later retrieval. Streaming ML becomes necessary when:

- **Low-latency decisions.** The system must respond within milliseconds. A fraud detection system cannot wait for a nightly batch job to flag a suspicious transaction.
- **Rapidly changing features.** A user's click stream in the last 30 seconds is far more predictive than their behavior from yesterday.
- **High event velocity.** Millions of events per second flow through the system, and each may trigger a prediction.
- **Adaptive requirements.** The underlying patterns shift continuously (adversarial environments, trending topics, volatile markets).
- **Regulatory or safety constraints.** Anti-money laundering, autonomous driving, and real-time bidding all demand streaming architectures.

If none of these apply, a [batch prediction pipeline](/blog/ml-system-design-patterns) is likely the right choice. Streaming ML adds significant operational complexity that must be justified by business requirements.

## Streaming ML Architecture Patterns

### Pattern 1: Real-Time Feature Computation with Batch Model

The most common streaming ML pattern. The model is trained offline, but the features it consumes are computed in real time from event streams.

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Event       │────▶│  Stream      │────▶│  Feature     │
│  Stream      │     │  Processor   │     │  Store       │
│  (Kafka)     │     │  (Flink)     │     │  (Redis)     │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                                                  ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Response    │◀────│  Model       │◀────│  Feature     │
│              │     │  Server      │     │  Retrieval   │
└──────────────┘     └──────────────┘     └──────────────┘
```

**How it works:**
1. Events arrive on a message stream (Kafka, Kinesis).
2. A stream processor computes real-time features: windowed aggregations, running counts, velocity metrics.
3. Computed features are written to a low-latency feature store (Redis, DynamoDB).
4. When inference is triggered, the model server retrieves the latest features and runs prediction.
5. The model itself is updated periodically through offline retraining.

**Strengths:** Simpler model lifecycle (standard batch training), fresh features, battle-tested pattern at companies like Uber, Netflix, and Stripe.

**Weaknesses:** Feature computation adds latency. The model cannot adapt to distribution shifts between retraining cycles.

### Pattern 2: Online Inference with Streaming Input

Both feature computation and model inference happen inline with the event stream. Every event triggers a prediction emitted downstream.

```
┌──────────────┐     ┌────────────────────────────────┐     ┌──────────────┐
│  Event       │────▶│       Stream Processor          │────▶│  Decision    │
│  Stream      │     │  ┌────────┐    ┌─────────────┐ │     │  Engine /    │
│  (Kafka)     │     │  │Compute │───▶│  Embedded   │ │     │  Output      │
└──────────────┘     │  │Features│    │  Model      │ │     │  Stream      │
                     │  └────────┘    └─────────────┘ │     └──────────────┘
                     └────────────────────────────────┘
```

Each event enters the stream processor, features are computed on the fly using windowed aggregations and lookups against state stores, and a pre-trained model loaded into the processor runs inference immediately. The prediction is emitted to a downstream topic or triggers an action directly.

**Strengths:** Lowest possible end-to-end latency since there is no network hop to a separate model server. Features and predictions are computed in a single topology.

**Weaknesses:** Model updates require redeploying the stream processor. Limited to models small enough to run within the processor's memory and compute constraints.

### Pattern 3: Online Learning (Model Updates with Each Event)

The model parameters are updated incrementally with each new data point, allowing near-real-time adaptation to distribution shifts. Used in adversarial environments (fraud, spam) and rapidly changing domains (ad bidding, trending content).

```
┌──────────────┐     ┌──────────────────────────────────────┐
│  Event       │────▶│         Online Learning Loop          │
│  Stream      │     │  ┌────────┐   ┌──────┐   ┌────────┐ │
│  (Kafka)     │     │  │Compute │──▶│Predict│──▶│ Update │ │
└──────────────┘     │  │Features│   │      │   │ Model  │ │
                     │  └────────┘   └──────┘   └───┬────┘ │
                     │                    ▲         │      │
                     │                    └─────────┘      │
                     │              (feedback loop)         │
                     └──────────────────────────────────────┘
```

This provides the fastest adaptation but carries risks: catastrophic forgetting, harder debugging, and not all model architectures support incremental updates.

| Criterion | Pattern 1 (RT Features) | Pattern 2 (Inline Inference) | Pattern 3 (Online Learning) |
|-----------|------------------------|-----------------------------|-----------------------------|
| Model freshness | Hours to days | Hours to days | Seconds to minutes |
| Feature freshness | Seconds | Seconds | Seconds |
| End-to-end latency | 10-100ms | 1-10ms | 1-10ms |
| Operational complexity | Medium | Medium-High | High |

## Stream Processing Frameworks

Choosing the right framework has long-term implications for latency, state management, and operational overhead. For a broader look at event-driven systems, see our guide on [event-driven architecture patterns](/blog/event-driven-architecture-patterns).

**Apache Kafka + Kafka Streams** runs as a library within your application (no separate cluster). It supports stateful processing with RocksDB, exactly-once semantics, and windowed aggregations. Best for teams already in the Kafka ecosystem needing moderate-complexity processing.

**Apache Flink** is the most powerful general-purpose stream processor, providing true event-time processing with watermarks, exactly-once state consistency, and massive-scale stateful processing. The framework of choice at Alibaba, Uber, and Netflix for their most demanding workloads.

**Apache Spark Structured Streaming** extends Spark SQL for streaming using micro-batch processing. Best for teams already using Spark for batch training that want a unified API, though latency is higher (100ms+).

**AWS Kinesis** provides a fully managed streaming platform integrating natively with SageMaker, Lambda, and S3. Best for AWS-native architectures prioritizing operational simplicity.

| Framework | Latency | Throughput | Exactly-Once | Complexity |
|-----------|---------|-----------|--------------|-----------|
| Kafka Streams | Low (ms) | High | Yes | Low |
| Apache Flink | Very Low (ms) | Very High | Yes | High |
| Spark Structured Streaming | Medium (100ms+) | Very High | Yes | Medium |
| AWS Kinesis | Low-Medium | High | Yes (with Flink) | Low |

## Real-Time Feature Engineering

Feature engineering for streaming ML differs fundamentally from batch. You see one event at a time and must maintain running state to compute features over windows. For a comprehensive look at feature management, see our [feature store system design](/blog/feature-store-system-design) guide.

### Windowed Aggregations

Windowed aggregations are the most common real-time feature type. They compute metrics (count, sum, average, min, max, percentile) over a defined window of events.

**Tumbling windows** divide time into fixed, non-overlapping intervals. Every event belongs to exactly one window.

```
Time:    |----W1----|----W2----|----W3----|
Events:  e1 e2 e3   e4 e5     e6 e7 e8
```

Example feature: "Number of transactions in the last 5 minutes" (tumbling, 5-min window).

**Sliding windows** overlap. A new window starts at every slide interval, and events can belong to multiple windows. A 10-minute window with a 5-minute slide lets you compute "average transaction amount over the last 10 minutes, updated every 5 minutes."

**Session windows** are dynamic. A session starts when the first event arrives and closes after a configurable gap of inactivity. Session windows are ideal for user behavior features like "number of pages viewed in the current session."

### Stream-Table Joins

Many real-time features require enriching stream events with static or slowly changing reference data. A stream-table join combines a live event stream with a lookup table to produce enriched events. Common examples include joining transaction events with merchant risk scores, joining user activity events with user profile data, and joining IoT sensor readings with device metadata. The reference table is typically kept up to date using change data capture (CDC) from the source database or by periodically refreshing a local cache.

### Late-Arriving Data

In distributed systems, events do not always arrive in order. Network delays, retries, and clock skew can cause events to arrive after their logical time window has closed. Handling late data correctly is critical for feature accuracy.

The stream processor tracks a watermark, which represents the point in event time up to which the system believes all data has arrived. Events arriving after the watermark are considered late. Strategies for handling late data include:

- **Grace periods.** Keep windows open for an additional buffer (e.g., 5 minutes past the watermark). Late events within the grace period are included.
- **Side outputs.** Route late events to a separate stream for offline reprocessing.
- **Retraction and correction.** Emit updated aggregation results when late data arrives. This is the most accurate but also the most complex approach.
- **Drop late events.** Simplest, but you lose data. Acceptable only when approximate features are sufficient.

### Feature Freshness Requirements

A common mistake in streaming ML design is streaming everything when many features are perfectly fine computed in batch. Classify your features by freshness requirement:

| Freshness | Example Features | Compute Method |
|-----------|-------------------|----------------|
| Real-time (seconds) | Transaction velocity, session activity | Stream processing |
| Near-real-time (minutes) | Rolling 1-hour aggregations | Stream processing |
| Hourly/Daily | Spending patterns, lifetime value | Batch pipeline |
| Static | Demographics, product categories | Database lookup |

Designing your feature pipeline with mixed freshness levels reduces infrastructure cost and operational complexity. Use a [feature store](/blog/feature-store-system-design) to serve both batch and streaming features through a unified API, ensuring consistency between training and serving.

## Online Learning vs Real-Time Inference

**Real-time inference** means a pre-trained model serves predictions on streaming data. The model is static between deployments, retrained on a schedule. Debugging is straightforward since you can reproduce any prediction by replaying inputs through the same model version.

**Online learning** means model parameters update incrementally with each new data point. It adapts quickly to shifts but is harder to debug, version, and reproduce. It requires algorithms supporting incremental updates: stochastic gradient descent, Hoeffding trees, bandit algorithms.

**Use real-time inference** when distributions are stable, reproducibility matters (finance, healthcare), or the model does not support incremental updates. **Use online learning** when the environment is adversarial, labeled data arrives continuously, or cold-start adaptation is critical.

Many production systems use a **hybrid approach**: a batch-trained baseline model with an online learning layer for recent adjustments. For more on serving strategies, see our guide on [ML model serving system design](/blog/ml-model-serving-system-design).

## Case Study: Fraud Detection System

Fraud detection is the canonical streaming ML use case: transactions scored under 100ms, features reflecting activity from the last 5 minutes to 30 days, and fraud patterns evolving continuously.

```
┌─────────────────────────────────────────────────────────────────────┐
│                 Fraud Detection System Architecture                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────┐     │
│  │  Transaction │────▶│  Kafka       │────▶│  Flink Stream    │     │
│  │  API         │     │  Topic       │     │  Processor       │     │
│  └──────────────┘     └──────────────┘     └────────┬─────────┘     │
│                                                      │               │
│                          ┌───────────────────────────┤               │
│                          ▼                           ▼               │
│                   ┌──────────────┐           ┌──────────────┐        │
│                   │  RT Features │           │  Batch       │        │
│                   │  (Redis)     │           │  Features    │        │
│                   │  - velocity  │           │  (DynamoDB)  │        │
│                   │  - session   │           │  - 30d avg   │        │
│                   │  - geo dist  │           │  - lifetime  │        │
│                   └──────┬───────┘           └──────┬───────┘        │
│                          └────────┬─────────────────┘                │
│                                   ▼                                  │
│                            ┌──────────────┐                          │
│                            │  Model Server│                          │
│                            │  (< 20ms)    │                          │
│                            └──────┬───────┘                          │
│                                   ▼                                  │
│                            ┌──────────────┐     ┌──────────────┐     │
│                            │  Decision    │────▶│  Alert /     │     │
│                            │  Engine      │     │  Human Review│     │
│                            └──────────────┘     └──────────────┘     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

The Flink stream processor computes several categories of real-time features:

- **Velocity checks** (tumbling and sliding windows): Number of transactions in the last 1, 5, and 60 minutes. Number of distinct merchants in the last 30 minutes. Number of card-not-present transactions in the last hour.
- **Amount pattern detection** (sliding windows): Average transaction amount over the last 24 hours. Ratio of current transaction to historical average. Sudden spending spike detection using rolling standard deviation.
- **Geographic anomaly detection:** Distance between the current and last known transaction locations. Velocity check for physically impossible travel. Country mismatch between billing address and transaction origin.
- **Device and session scoring:** Device fingerprint match against known devices. New device flag. Session age and activity pattern.

The model server runs a gradient-boosted decision tree (XGBoost or LightGBM) that takes approximately 50 features as input and produces a fraud probability score. Inference latency is under 20ms. The feature vector combines real-time features from Redis (computed by Flink), historical features from DynamoDB (computed by a nightly batch pipeline), and static features from the user profile database.

The decision engine translates the fraud score into an action: approve immediately (< 0.3), apply additional verification like 3D Secure or SMS challenge (0.3-0.7), or decline and flag for human review (> 0.7). Thresholds are configurable per merchant category and risk tolerance.

| Stage | Target Latency |
|-------|---------------|
| Event ingestion (Kafka) | < 5ms |
| Feature computation (Flink) | < 15ms |
| Feature retrieval (Redis + DynamoDB) | < 10ms |
| Model inference | < 20ms |
| Decision engine | < 5ms |
| **Total end-to-end** | **< 55ms** |

## Case Study: Real-Time Recommendations

Real-time recommendation systems combine batch-computed embeddings with session-level signals to reflect the user's current intent.

```
┌──────────────────────────────────────────────────────────────────┐
│              Real-Time Recommendation System                      │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐      │
│  │  User        │────▶│  Kafka       │────▶│  Session     │      │
│  │  Activity    │     │  Events      │     │  Feature     │      │
│  └──────────────┘     └──────────────┘     │  Processor   │      │
│                                             └──────┬───────┘      │
│                                                    ▼               │
│  ┌──────────────┐                          ┌──────────────┐       │
│  │  Candidate   │◀─── Embeddings ─────────│  Feature     │       │
│  │  Generation  │                          │  Store       │       │
│  │  (ANN Index) │                          └──────────────┘       │
│  └──────┬───────┘                                                  │
│         │  Top 200 candidates                                      │
│         ▼                                                          │
│  ┌──────────────┐                                                  │
│  │  Re-Ranking  │◀─── Session + batch + item features             │
│  │  Model       │                                                  │
│  └──────┬───────┘                                                  │
│         │  Top 20 ranked items                                     │
│         ▼                                                          │
│  ┌──────────────┐                                                  │
│  │  Business    │  (diversity, freshness, sponsorship)             │
│  │  Rules       │                                                  │
│  └──────────────┘                                                  │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

The Flink session processor computes features that capture the user's current intent:

- **Session-level item interactions:** Categories viewed, items clicked, items added to cart in the current session.
- **Search queries:** Keywords and categories from the last N search queries.
- **Dwell time patterns:** Which item categories the user spent the most time on.
- **Recency-weighted engagement:** More recent interactions in the session are weighted higher.
- **Session context:** Time of day, day of week, device type, referral source.

These session features are stored in Redis with a session-keyed TTL. The re-ranking model scores the top 200 ANN candidates using a combination of batch embeddings and real-time session features, enabling in-session intent shifts. If a user who typically browses electronics starts searching for hiking gear, the session features pick up on this shift and the re-ranker promotes outdoor items. This two-stage approach (batch candidate generation plus real-time re-ranking) is used at virtually every large-scale recommendation platform.

For more on AI-powered system architectures, see our guide on [real-world AI system architecture](/blog/real-world-ai-system-architecture).

## Scaling Streaming ML Systems

Scaling a streaming ML system introduces challenges that do not exist in batch systems. The data never stops flowing, so you cannot simply "run it again" if something goes wrong.

**Partitioning strategies.** Partition by entity key (user ID, account ID) so all events for a given entity go to the same processor instance, enabling stateful per-entity feature computation. The key challenge is hot keys: some entities generate far more events than others, creating processing skew. Solutions include salted keys (appending a random suffix and aggregating downstream), two-phase aggregation, or dynamic repartitioning.

**Backpressure handling.** Backpressure occurs when downstream consumers cannot keep up with the event rate. Without proper handling, this leads to unbounded memory growth or cascading failures. Strategies include bounded buffers with blocking (propagates backpressure upstream naturally), dynamic auto-scaling based on consumer lag, load shedding for non-critical events, and priority queues for high-value traffic.

**Exactly-once semantics.** Essential for financial features where duplicates or missing events produce incorrect results. In Kafka + Flink, this works through atomic checkpointing of both state snapshots and consumer offsets. If a failure occurs, Flink restores from the last checkpoint and resumes from the saved offsets. For approximate features (trending scores, popularity counts), at-least-once with idempotent writes is a reasonable tradeoff that reduces latency overhead.

**State management at scale.** Streaming features require maintaining state: running counters, sliding window buffers, session data, and aggregation accumulators. Use local state (RocksDB) for moderate sizes, external state stores (Redis, DynamoDB) for very large or shared state. Set TTLs to prevent unbounded growth, and periodically compact state to reduce checkpoint sizes.

## Monitoring Streaming ML Systems

Monitoring requires tracking three dimensions: stream health, feature quality, and model performance.

**Stream lag monitoring.** Track consumer lag per partition, processing throughput versus ingestion rate, checkpoint duration, and restart recovery time. Alert when lag exceeds thresholds (e.g., 10,000 messages or 30 seconds of event time).

**Feature freshness SLAs.** Attach timestamps to every computed feature value. Monitor feature age in the feature store and alert when any feature exceeds its freshness SLA. Track freshness percentiles (p50, p95, p99) over time.

**Model performance on streaming data.** Compute accuracy, precision, recall, and AUC over rolling windows. Match predictions to delayed labels using event IDs. Compare current-window metrics against previous windows to detect sudden drops.

**Drift detection in real-time.** Maintain exponentially weighted moving averages of feature statistics in the stream processor. Periodically compare against reference distributions using Population Stability Index (PSI) or Wasserstein distance. Monitor individual feature distributions, feature correlation changes, prediction distribution shifts, and input volume anomalies.

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Feature     │────▶│  Running     │────▶│  Drift       │
│  Stream      │     │  Statistics  │     │  Detector    │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                            ┌─────────────────────┤
                            ▼                     ▼
                     ┌──────────────┐     ┌──────────────┐
                     │  Dashboard   │     │  Alert       │
                     └──────────────┘     └──────────────┘
```

## Conclusion

Streaming ML system design brings together distributed stream processing, real-time feature engineering, low-latency model serving, and continuous monitoring into a single architecture. The three core patterns (real-time feature computation with batch models, inline streaming inference, and online learning) each address different points on the latency-adaptability spectrum.

Key takeaways for building production streaming ML systems:

- **Start with Pattern 1** (real-time features, batch model) unless you have a compelling reason for online learning.
- **Invest in your stream processing layer.** The choice of framework has long-term implications for latency, state management, and operations.
- **Design features with mixed freshness.** Use streaming for features that genuinely benefit from freshness, and batch for everything else.
- **Plan for failure from day one.** Exactly-once semantics, checkpointing, and backpressure handling are not optional.
- **Monitor three dimensions.** Stream health, feature quality, and model performance must all be tracked continuously.

Ready to design your own streaming ML architecture? [Try InfraSketch](/tools/ml-system-design-tool) to generate professional architecture diagrams from natural language descriptions. Describe your streaming pipeline, and get an interactive diagram with a complete design document in seconds.

---

## Related Resources

- [ML System Design Patterns](/blog/ml-system-design-patterns)
- [Feature Store System Design](/blog/feature-store-system-design)
- [Event-Driven Architecture Patterns](/blog/event-driven-architecture-patterns)
- [ML Model Serving System Design](/blog/ml-model-serving-system-design)
- [Real-World AI System Architecture](/blog/real-world-ai-system-architecture)
