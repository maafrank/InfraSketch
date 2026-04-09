---
title: 6 Machine Learning System Design Patterns Every Engineer Should Know
published: true
tags: machinelearning, systemdesign, ai, architecture
canonical_url: https://infrasketch.net/blog/ml-system-design-patterns
cover_image: https://infrasketch.net/full-app-with-design-doc.png
---

Production ML is not about the model. It is about everything around it: data pipelines, feature engineering, safe deployment, monitoring, and rollback. The model itself is often the easiest part.

After working on and studying ML systems at scale, I have distilled the most important architectural patterns into six categories. Whether you are building your first ML pipeline or preparing for a system design interview, these patterns will give you a practical framework for making the right decisions.

For the full deep-dive (with interview tips, distributed training strategies, and a decision framework), check out the [complete guide on InfraSketch](https://infrasketch.net/blog/ml-system-design-patterns).

## What Makes ML Systems Different

Before we jump in, it is worth understanding why ML system design is its own discipline:

- **Data is a first-class citizen.** Bad data produces bad predictions, no matter how elegant your architecture is.
- **Behavior is probabilistic.** Models produce confidence scores, not definitive answers.
- **The system degrades silently.** A traditional service crashes loudly. An ML model can quietly produce increasingly wrong predictions as data drifts.
- **Training and serving are separate systems** with very different infrastructure requirements.
- **Experimentation is continuous.** You version not just code, but data, features, and model artifacts.

With that context, let us look at the six patterns.

![InfraSketch generating an ML system design](https://infrasketch.net/full-app-with-design-doc.png)

## Pattern 1: Batch Prediction Pipeline

The simplest and most common pattern. Generate predictions for large datasets on a schedule, store the results, and look them up at serving time.

```
Scheduler (Airflow)
    -> Feature Retrieval (Spark)
    -> Batch Inference (Spark)
    -> Prediction Store (S3/DB)
    -> Cache (Redis)
    -> Application Server
```

**How it works:** A scheduler triggers a pipeline that reads features, runs inference across all entities (users, products, transactions), and writes predictions to a store. Your application server simply looks up precomputed results.

**Use it for:** Recommendation systems, risk scoring, content ranking, email campaign targeting. Anything where predictions do not need to reflect real-time state.

**Trade-offs:**

| Advantage | Disadvantage |
|-----------|-------------|
| Simple to implement and debug | Predictions go stale between runs |
| High throughput (millions of records) | No real-time personalization |
| Easy to validate before serving | Cold-start problem for new entities |
| Cost-efficient (spot instances) | Wasted compute for unqueried entities |

**Production tip:** Always keep the previous batch available as a fallback. Run automated quality checks (distribution comparisons against historical baselines) before promoting new predictions to serving.

## Pattern 2: Real-Time Inference Service

When predictions must reflect current data or respond in milliseconds, you need real-time inference.

```
Client Request
    -> API Gateway
    -> Feature Assembly (online feature store + request features)
    -> Model Server (TF Serving / Triton / TorchServe)
    -> Prediction Response
```

The critical design exercise here is your **latency budget**:

```
Total budget: 100ms (p99)

Network (client to gateway):       10ms
Feature retrieval (online store):  15ms
Feature assembly & transforms:     5ms
Model inference:                   40ms
Post-processing:                   5ms
Network (response to client):      10ms
Buffer:                            15ms
```

**Use it for:** Fraud detection, search ranking, dynamic pricing, content moderation, conversational AI.

**Key decisions:**
- **Model format:** ONNX for portability, TensorRT for GPU optimization, or framework-native (SavedModel, TorchScript).
- **Scaling:** Autoscale on request queue depth, not just CPU.
- **Fallback:** When the model is unavailable, return a default prediction or fall back to a rule-based system.

## Pattern 3: Online Learning Pipeline

Online learning updates the model continuously as new data arrives, rather than retraining from scratch on a schedule.

```
Event Stream (Kafka)
    -> Stream Processor (Flink)
    -> Online Trainer (Vowpal Wabbit / River)
    -> Model Server (live updates)
    -> Checkpoint Store (for rollback)
    -> Periodic Validation Pipeline
```

**Use it for:** Ad click prediction, trading signals, IoT anomaly detection, news feed personalization, cybersecurity.

This pattern introduces unique risks. A burst of corrupted data can degrade the model rapidly. Essential guardrails:

- **Data validation:** Reject training examples outside expected distributions.
- **Learning rate decay:** Prevent recent examples from dominating.
- **Periodic reset:** Retrain from scratch weekly or monthly to prevent drift accumulation.
- **Rollback triggers:** Automatically revert to the last checkpoint if performance drops.

![AI-generated architecture diagram in InfraSketch](https://infrasketch.net/url-shortener-diagram-generated.png)

## Pattern 4: A/B Testing and Shadow Mode

No ML model should go directly from training to full production traffic. These deployment patterns reduce risk by comparing models against each other using real traffic.

### A/B Testing

Route a percentage of traffic to the new model and measure outcomes against the control:

```
Traffic Router (feature flags)
    |-- 90% --> Model A (Control)
    |-- 5%  --> Model B (Variant 1)
    |-- 5%  --> Model C (Variant 2)
    |
    v
Experiment Tracking (predictions + outcomes)
    -> Statistical Analysis (significance, confidence, power)
```

Assign users deterministically (hash of user ID) for consistency across sessions. Track your primary metric (CTR, conversion, revenue) alongside guardrail metrics (latency, error rate).

### Shadow Mode (Dark Launch)

Run the new model on 100% of traffic in parallel with production, but only serve the production model's predictions. Log the shadow model's output for offline comparison.

**Use shadow mode when:**
- You want to validate behavior before committing to an A/B test.
- The cost of a bad prediction is very high (medical, financial).
- You cannot easily measure outcomes directly.

### The Safe Deployment Progression

1. Offline evaluation on held-out data
2. Shadow mode on live traffic
3. A/B test with 1-5% traffic
4. Gradual ramp: 10%, 25%, 50%
5. Full rollout
6. Continued monitoring for drift

## Pattern 5: Feature Store

A feature store is a centralized system for managing, storing, and serving ML features. It solves the **training-serving skew problem**, where feature engineering code is duplicated between training (Python/Spark) and serving (Java/Go), leading to subtle inconsistencies.

A feature store has two key storage layers:

- **Offline Store** (S3/BigQuery): Historical values, point-in-time joins, training datasets.
- **Online Store** (Redis/DynamoDB): Latest values, low-latency lookups for serving.

Plus shared infrastructure: a feature registry (metadata catalog), a transform engine (define once, apply everywhere), and monitoring (drift, quality, missing values).

**When to invest in one:**
- Multiple teams share features across models.
- You have both batch and real-time serving needs.
- Training-serving skew has caused production issues.
- Feature computation is expensive and should not be duplicated.

**When to skip it:** If you have a single model with simple features, start with a shared library of feature transforms. Evolve to a feature store when the pain of manual management exceeds the cost of the infrastructure.

**Popular options:** Feast (open source), Tecton (managed), Hopsworks (open source), Vertex AI Feature Store (GCP), SageMaker Feature Store (AWS).

## Pattern 6: Model Registry and Versioning

A model registry is the source of truth for trained models. It tracks versions, training provenance, evaluation metrics, and deployment status.

**Model lifecycle stages:**

1. **Registered** - Uploaded after training
2. **Validated** - Automated tests pass (prediction format, integration, benchmarks)
3. **Staging** - Deployed for shadow mode or canary testing
4. **Production** - Serving live traffic
5. **Archived** - Retained for rollback and audit

**What to version** (model weights alone are not enough):
- Model artifact (serialized weights/graph)
- Feature schema (exact features, types, ranges)
- Preprocessing code
- Training data reference (pointer or hash, not the data itself)
- Training configuration (hyperparameters, seeds, hardware)
- Evaluation results
- Dependency versions

**Popular options:** MLflow (open source, widely adopted), Weights and Biases (excellent experiment tracking), Vertex AI / SageMaker (cloud-native).

![Complex system architecture with InfraSketch](https://infrasketch.net/analytics-diagram-generated.png)

## Choosing the Right Pattern

There is no single best pattern. Here is a quick decision framework:

```
Is prediction latency critical (< 100ms)?
|-- YES: Need to adapt to distribution shift in real-time?
|   |-- YES -> Pattern 3: Online Learning
|   |-- NO  -> Pattern 2: Real-Time Inference
|-- NO: Can you precompute predictions for all entities?
    |-- YES -> Pattern 1: Batch Prediction
    |-- NO  -> Pattern 2: Real-Time Inference (with caching)

Always combine with:
  - Pattern 4: A/B Testing (for safe deployment)
  - Pattern 5: Feature Store (when sharing features across models)
  - Pattern 6: Model Registry (when managing multiple models)
```

Most mature ML platforms use a combination. Netflix, for example, uses batch predictions for homepage recommendations, real-time inference for search ranking, a centralized feature store, a model registry, and A/B testing for every model change.

## The Key Takeaway

ML system design is fundamentally about the infrastructure around the model, not the model itself. The best model in the world is useless without reliable data pipelines, consistent feature engineering, safe deployment mechanisms, and continuous monitoring.

When approaching any ML system design problem, start with the end-to-end picture. Then drill into the patterns that fit your specific requirements. For the full version of this guide (including distributed training patterns, monitoring dashboards, drift detection strategies, and seven interview practice questions), read the [complete article on InfraSketch](https://infrasketch.net/blog/ml-system-design-patterns).

---

Practice designing ML systems with [InfraSketch](https://infrasketch.net). Describe your ML pipeline in plain English and get a complete architecture diagram in seconds. Try it free at [https://infrasketch.net](https://infrasketch.net).
