# ML Model Serving System Design: From Prototype to Production

Getting a machine learning model to work in a Jupyter notebook is one thing. Serving that model reliably at scale, with low latency, high availability, and continuous updates, is an entirely different challenge. ML model serving system design sits at the intersection of machine learning engineering, distributed systems, and DevOps. It requires you to think carefully about inference latency, throughput, resource utilization, model versioning, and graceful degradation.

This guide walks through the complete landscape of ML model serving, from choosing the right serving architecture to scaling inference, managing deployment pipelines, running A/B tests, optimizing latency, and monitoring production models. Whether you are preparing for a system design interview or building a real-time ML system design for your organization, this article provides the depth and practical detail you need.

## Why Model Serving Is Hard

The gap between a working prototype and a production inference system is enormous. In a notebook, you load a model, feed it data, and get predictions. In production, you must handle:

- **Concurrent requests:** Thousands of users hitting your model at once, each expecting sub-100ms responses
- **Model versioning:** Rolling out new model versions without downtime or degrading the user experience
- **Resource management:** GPUs are expensive. You need to maximize utilization without starving any single request
- **Fault tolerance:** What happens when a model server crashes mid-inference? When a GPU runs out of memory?
- **Data consistency:** Ensuring the same preprocessing pipeline runs in training and serving (training-serving skew)
- **Cost optimization:** Balancing performance requirements against cloud compute bills that can spiral quickly

Most ML teams discover these challenges the hard way. A model that takes 2 seconds per prediction in a notebook becomes a bottleneck when 500 requests arrive simultaneously. A model that works perfectly on the training distribution starts producing nonsensical outputs when real-world data shifts. These are the problems that ML model serving system design must solve.

## Serving Architecture Patterns

The first decision in any AI inference system design is how to expose your model to consumers. There are several well-established patterns, each with distinct tradeoffs.

### REST API Serving

The most straightforward approach is wrapping your model behind a REST API using frameworks like FastAPI or Flask.

```python
# FastAPI model serving example
from fastapi import FastAPI
import torch

app = FastAPI()
model = None

@app.on_event("startup")
async def load_model():
    global model
    model = torch.jit.load("model.pt")
    model.eval()

@app.post("/predict")
async def predict(request: PredictionRequest):
    with torch.no_grad():
        inputs = preprocess(request.data)
        output = model(inputs)
        return {"prediction": postprocess(output)}
```

**Strengths:** Simple to build and debug. Works with any ML framework. Easy to add authentication, logging, and middleware. Familiar to most developers.

**Weaknesses:** HTTP overhead adds latency. Not ideal for very high throughput. No built-in model management or batching.

**Best for:** Internal tools, low-to-medium traffic APIs, rapid prototyping, teams without dedicated ML infrastructure.

### gRPC Serving

For higher performance, gRPC provides binary serialization (Protocol Buffers) and HTTP/2 multiplexing. Purpose-built serving frameworks like TensorFlow Serving and NVIDIA Triton Inference Server use gRPC natively.

```protobuf
// Inference service definition
service InferenceService {
  rpc Predict(PredictRequest) returns (PredictResponse);
  rpc StreamPredict(stream PredictRequest) returns (stream PredictResponse);
}

message PredictRequest {
  string model_name = 1;
  int64 model_version = 2;
  repeated float input_tensor = 3;
  repeated int64 input_shape = 4;
}
```

**Strengths:** 2-10x lower latency than REST for large payloads. Built-in streaming support. Strong typing via protobuf. Efficient binary serialization reduces bandwidth.

**Weaknesses:** Harder to debug (binary protocol). Requires protobuf schema management. Less tooling for browser clients (though gRPC-Web exists).

**Best for:** High-throughput internal services, inter-service communication, large tensor inputs/outputs, real-time ML system design use cases.

### Serverless Inference

AWS Lambda, SageMaker Serverless Inference, and Google Cloud Functions allow you to serve models without managing infrastructure.

```python
# AWS Lambda handler for model inference
import json
import boto3
import numpy as np

# Model loaded during cold start
model = load_model_from_s3("s3://models/production/v12/model.tar.gz")

def handler(event, context):
    body = json.loads(event["body"])
    inputs = preprocess(body["features"])
    prediction = model.predict(inputs)
    return {
        "statusCode": 200,
        "body": json.dumps({"prediction": prediction.tolist()})
    }
```

**Strengths:** Zero infrastructure management. Automatic scaling to zero (no cost when idle). Pay-per-request pricing works well for bursty traffic.

**Weaknesses:** Cold start latency (seconds for large models). Memory and package size limits. No GPU support on basic Lambda (SageMaker Serverless does support GPU). Not suitable for large models.

**Best for:** Lightweight models (under 500MB), sporadic traffic, cost-sensitive workloads, preprocessing/postprocessing steps.

### Streaming Inference

For real-time use cases like large language model generation, live video analysis, or continuous sensor data processing, streaming inference delivers results incrementally.

```python
# Server-Sent Events for streaming inference
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

@app.post("/generate")
async def generate_stream(request: GenerateRequest):
    async def token_generator():
        for token in model.generate_stream(request.prompt):
            yield f"data: {json.dumps({'token': token})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        token_generator(),
        media_type="text/event-stream"
    )
```

**Strengths:** Lower time-to-first-token. Better user experience for generative models. Enables real-time processing pipelines.

**Weaknesses:** More complex client-side handling. Harder to load balance. Connection management overhead.

**Best for:** LLM serving, real-time video/audio processing, live recommendation updates, chat applications.

### Comparison of Serving Approaches

| Approach | Latency | Throughput | Scalability | Complexity | Cost Model |
|----------|---------|------------|-------------|------------|------------|
| REST API | Medium | Medium | Manual/Auto | Low | Always-on |
| gRPC | Low | High | Manual/Auto | Medium | Always-on |
| Serverless | High (cold) | Variable | Automatic | Low | Pay-per-use |
| Streaming | Low (first token) | Medium | Manual/Auto | High | Always-on |
| Triton/TF Serving | Low | Very High | Manual/Auto | Medium | Always-on |

## Real-Time vs Batch vs Near-Real-Time

Not every prediction needs to happen in milliseconds. Choosing the right inference pattern can dramatically reduce costs and complexity.

### Real-Time Inference

Predictions are generated on-demand for each request, typically within 10-200ms.

**When to use:**
- User-facing features requiring immediate response (search ranking, content recommendations, fraud detection at checkout)
- Interactive applications where latency directly impacts user experience
- Decisions that depend on the most current data available

**Tradeoffs:** Requires always-on infrastructure. Must handle peak traffic. Most expensive per-prediction.

### Batch Inference

Predictions are computed for large datasets on a schedule (hourly, daily, weekly).

**When to use:**
- Generating recommendations for all users overnight
- Scoring entire customer databases for marketing campaigns
- Periodic report generation or risk assessments
- Any scenario where predictions can be pre-computed and cached

**Tradeoffs:** Results may be stale. Requires storage for pre-computed predictions. Much cheaper per-prediction.

### Near-Real-Time (Micro-Batch)

A middle ground where predictions are generated in small batches every few seconds or minutes.

**When to use:**
- Streaming data pipelines (Kafka consumers processing events)
- Systems that can tolerate seconds of delay but not hours
- Aggregation-dependent features (e.g., "purchases in last 5 minutes")

**Tradeoffs:** More complex pipeline architecture. Must tune batch size and window duration.

### Hybrid Architectures

Most production systems combine multiple patterns. A common approach:

```
+------------------------------------------------------------------+
|                     HYBRID INFERENCE ARCHITECTURE                 |
+------------------------------------------------------------------+
|                                                                    |
|   REAL-TIME PATH                                                   |
|   +---------+     +----------------+     +------------------+      |
|   | API     | --> | Feature Store  | --> | Real-Time Model  |      |
|   | Request |     | (Online)       |     | Server (GPU)     |      |
|   +---------+     +----------------+     +------------------+      |
|                                                 |                  |
|                                                 v                  |
|                                          +-------------+           |
|                                          |  Response   |           |
|                                          |  Cache      |           |
|                                          +-------------+           |
|                                                                    |
|   NEAR-REAL-TIME PATH                                              |
|   +---------+     +----------------+     +------------------+      |
|   | Kafka   | --> | Stream         | --> | Micro-Batch      |      |
|   | Events  |     | Processor      |     | Inference        |      |
|   +---------+     +----------------+     +------------------+      |
|                                                 |                  |
|                                                 v                  |
|                                          +-------------+           |
|                                          | Feature     |           |
|                                          | Store Update|           |
|                                          +-------------+           |
|                                                                    |
|   BATCH PATH                                                       |
|   +---------+     +----------------+     +------------------+      |
|   | Cron /  | --> | Data Warehouse | --> | Batch Inference  |      |
|   | Airflow |     | (Full Dataset) |     | Cluster (Spark)  |      |
|   +---------+     +----------------+     +------------------+      |
|                                                 |                  |
|                                                 v                  |
|                                          +-------------+           |
|                                          | Results DB  |           |
|                                          | (Pre-comp.) |           |
|                                          +-------------+           |
+------------------------------------------------------------------+
```

In this pattern, the batch path pre-computes predictions for most users. The real-time path handles cases where fresh predictions are critical (new users, recently changed data). The near-real-time path continuously updates features used by the real-time model.

## Scaling Inference

Once your serving architecture is in place, the next challenge is scaling it to handle production traffic. Scalable AI inference system design requires thinking about compute, memory, and network at every layer.

### Horizontal Scaling and Load Balancing

The most straightforward scaling approach is running multiple model server replicas behind a load balancer.

```yaml
# Kubernetes deployment for model serving
apiVersion: apps/v1
kind: Deployment
metadata:
  name: model-server
spec:
  replicas: 8
  selector:
    matchLabels:
      app: model-server
  template:
    spec:
      containers:
      - name: inference
        image: model-server:v2.1
        resources:
          limits:
            nvidia.com/gpu: 1
            memory: "16Gi"
          requests:
            cpu: "4"
            memory: "8Gi"
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: model-server-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: model-server
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Pods
    pods:
      metric:
        name: inference_queue_depth
      target:
        type: AverageValue
        averageValue: "5"
```

**Key considerations:**
- **Health checks:** Model loading can take 30-60 seconds. Use readiness probes to prevent traffic before the model is ready.
- **Autoscaling metrics:** Scale on custom metrics like queue depth or GPU utilization, not just CPU. Standard CPU metrics miss GPU-bound workloads entirely.
- **Session affinity:** Generally unnecessary for stateless inference, but critical for streaming or multi-turn interactions.

### GPU Sharing and Scheduling

GPUs are expensive. Running one model per GPU is wasteful if the model does not fully utilize the hardware.

**Multi-Process Service (MPS):** NVIDIA MPS allows multiple processes to share a single GPU. Each process gets a portion of GPU compute. Useful when individual inference requests do not saturate the GPU.

**Multi-Instance GPU (MIG):** Available on A100 and H100 GPUs. Physically partitions a GPU into up to 7 isolated instances. Each instance has dedicated memory and compute. Provides hardware-level isolation, preventing noisy-neighbor effects.

**Time-Slicing:** The simplest approach. Multiple pods share a GPU by taking turns. Kubernetes enables this with `nvidia.com/gpu` fractional requests. Works for lightweight models but adds latency due to context switching.

```
+--------------------------------------------------+
|              NVIDIA A100 GPU (80GB)               |
+--------------------------------------------------+
|  MIG Instance 1   |  MIG Instance 2  | MIG Inst 3|
|  (40GB, 4 SMs)    |  (20GB, 2 SMs)   | (20GB)    |
|                    |                   |           |
|  Large Language    |  Embedding        | Ranking   |
|  Model             |  Model            | Model     |
|  (latency-critical)|  (high-throughput)| (batch)   |
+--------------------------------------------------+
```

### Model Optimization

Before scaling horizontally, optimize the model itself. Smaller, faster models reduce infrastructure costs.

**Quantization:** Reduces model precision from FP32 to FP16, INT8, or even INT4. Often achieves 2-4x speedup with minimal accuracy loss.

```python
# Post-training quantization with PyTorch
import torch

model_fp32 = load_model()
model_int8 = torch.quantization.quantize_dynamic(
    model_fp32,
    {torch.nn.Linear},
    dtype=torch.qint8
)
# Model size: 400MB -> 100MB
# Latency: 45ms -> 18ms
```

**Knowledge Distillation:** Train a smaller "student" model to mimic a larger "teacher" model. The student can be 3-10x smaller while retaining 95-99% of the teacher's performance.

**Pruning:** Remove redundant weights or neurons. Structured pruning removes entire channels or layers, making the model physically smaller. Unstructured pruning zeros out individual weights, requiring sparse computation support.

**ONNX Conversion:** Convert models to ONNX (Open Neural Network Exchange) format for cross-framework optimization. ONNX Runtime provides optimized execution across CPUs, GPUs, and specialized hardware.

### Request Batching

Processing multiple requests together exploits GPU parallelism. A single prediction might use 5% of GPU capacity, but a batch of 32 uses 80%.

**Dynamic batching** collects incoming requests and groups them into batches based on configurable time windows and maximum batch sizes.

```
  Requests arrive:  t=0ms  t=2ms  t=3ms  t=5ms  t=8ms
                      |      |      |      |      |
                      v      v      v      v      v
                  +-----------------------------------+
                  |      Dynamic Batcher              |
                  |  max_batch_size: 32                |
                  |  max_delay_ms: 10                  |
                  +-----------------------------------+
                              |
              Batch formed at t=10ms (4 requests)
                              |
                              v
                  +-----------------------------------+
                  |      GPU Inference                |
                  |  Batch of 4: 12ms total           |
                  |  vs. 4 x 8ms = 32ms sequential   |
                  +-----------------------------------+
                              |
                  Results dispatched to each client
```

NVIDIA Triton Inference Server provides dynamic batching out of the box. You configure `max_batch_size` and `batching_delay_ms`, and Triton handles the rest. TensorFlow Serving also supports batching via its `--enable_batching` flag and a batching parameters file.

### Scaled Serving Infrastructure

Putting it all together, here is what a production-grade scaled inference system looks like:

```
+-----------------------------------------------------------------------+
|                  SCALED MODEL SERVING INFRASTRUCTURE                   |
+-----------------------------------------------------------------------+
|                                                                         |
|  +----------+     +-----------+     +-----------------------------+     |
|  | Clients  | --> | CDN /     | --> | API Gateway                 |     |
|  | (Web,    |     | Edge      |     | (Auth, Rate Limit, Route)   |     |
|  |  Mobile) |     | Cache     |     +-----------------------------+     |
|  +----------+     +-----------+                  |                      |
|                                                  v                      |
|                                    +---------------------------+        |
|                                    |     Load Balancer         |        |
|                                    | (Round-Robin / Least-Conn)|        |
|                                    +---------------------------+        |
|                                       |        |        |               |
|                                       v        v        v               |
|                                  +--------+--------+--------+           |
|                                  | Model  | Model  | Model  |           |
|                                  | Server | Server | Server |           |
|                                  | Pod 1  | Pod 2  | Pod N  |           |
|                                  |        |        |        |           |
|                                  | GPU    | GPU    | GPU    |           |
|                                  | +Batch | +Batch | +Batch |           |
|                                  +--------+--------+--------+           |
|                                       |        |        |               |
|                                       v        v        v               |
|                                  +----------------------------+         |
|                                  |     Prediction Cache       |         |
|                                  |     (Redis Cluster)        |         |
|                                  +----------------------------+         |
|                                              |                          |
|                            +-----------------+-----------------+        |
|                            |                                   |        |
|                            v                                   v        |
|                   +-----------------+              +----------------+   |
|                   | Feature Store   |              | Model Registry |   |
|                   | (Feast/Tecton)  |              | (MLflow)       |   |
|                   +-----------------+              +----------------+   |
|                                                                         |
|  +---------------------------+    +-----------------------------+       |
|  | Autoscaler               |    | Monitoring                  |       |
|  | (HPA on queue depth,     |    | (Prometheus, Grafana,       |       |
|  |  GPU util, latency)      |    |  custom ML metrics)         |       |
|  +---------------------------+    +-----------------------------+       |
+-----------------------------------------------------------------------+
```

## Model Registry and Deployment Pipelines

A model registry is the single source of truth for all trained models. It tracks model artifacts, metadata, performance metrics, lineage, and deployment status.

### Model Registry Options

**MLflow Model Registry:** Open-source, widely adopted. Supports model stages (Staging, Production, Archived). Integrates with most ML frameworks. Can be self-hosted or used via Databricks.

**Weights and Biases (W&B):** Strong experiment tracking and artifact versioning. Model Registry links artifacts to training runs. Good collaboration features for team-based ML development.

**SageMaker Model Registry:** Deep AWS integration. Approval workflows built in. Connects directly to SageMaker endpoints for deployment. Best choice for AWS-native ML pipelines.

### CI/CD for Models

ML models need the same deployment rigor as application code. A model CI/CD pipeline typically includes:

```
+---------------------------------------------------------------+
|                    MODEL CI/CD PIPELINE                        |
+---------------------------------------------------------------+
|                                                                 |
|  1. TRIGGER                                                     |
|     - New model registered in registry                          |
|     - Scheduled retraining completes                            |
|     - Manual promotion request                                  |
|                                                                 |
|  2. VALIDATION GATE                                             |
|     - Run model on holdout test set                             |
|     - Compare metrics against production baseline               |
|     - Check for regression on critical slices                   |
|     - Verify input/output schema compatibility                  |
|     - Run bias and fairness checks                              |
|                                                                 |
|  3. INTEGRATION TESTING                                         |
|     - Deploy to staging environment                             |
|     - Run end-to-end inference tests                            |
|     - Verify latency meets SLA (p99 < 100ms)                   |
|     - Load test at 2x expected peak traffic                     |
|                                                                 |
|  4. DEPLOYMENT                                                  |
|     - Blue-green or canary rollout                              |
|     - Gradual traffic shift (1% -> 10% -> 50% -> 100%)         |
|     - Automated rollback on metric degradation                  |
|                                                                 |
|  5. POST-DEPLOYMENT                                             |
|     - Monitor prediction distributions                          |
|     - Compare against shadow model predictions                  |
|     - Alert on drift or anomalies                               |
+---------------------------------------------------------------+
```

### Blue-Green and Canary Deployments

**Blue-green deployment** for ML models maintains two identical environments. The "blue" environment serves production traffic while "green" runs the new model version. After validation, traffic switches entirely to green. This approach provides instant rollback by switching back to blue if issues arise.

**Canary deployment** gradually shifts traffic to the new model version. Start with 1-5% of traffic, monitor metrics, then incrementally increase. This limits the blast radius of a bad model.

```python
# Canary routing logic
def route_request(request, canary_percentage=5):
    # Deterministic routing based on user ID
    # ensures same user always hits same model version
    bucket = hash(request.user_id) % 100

    if bucket < canary_percentage:
        return call_model("v2-canary")
    else:
        return call_model("v1-production")
```

For ML models specifically, canary deployments should monitor not just standard health metrics but also prediction distribution shifts, confidence score distributions, and downstream business metrics (click-through rate, conversion rate, user engagement).

## A/B Testing for ML Models

A/B testing is fundamental to measuring whether a new model actually improves outcomes. It goes beyond canary deployment by applying statistical rigor to the comparison.

### Traffic Splitting Strategies

**Random splitting:** Each request is randomly assigned to model A or model B. Simple but can introduce noise if user behavior varies across sessions.

**User-level splitting:** Each user is consistently assigned to one model variant for the duration of the experiment. Reduces noise from within-user variability. Implemented via hashing the user ID.

**Stratified splitting:** Users are divided into strata (e.g., by geography, device type, engagement level), and splitting happens within each stratum. Ensures balanced representation across segments.

**Multi-armed bandit:** Dynamically shifts traffic toward the better-performing model during the experiment. Reduces the cost of running an inferior model on half your traffic. Thompson Sampling and Upper Confidence Bound (UCB) are common algorithms.

### Statistical Significance in ML Experiments

ML A/B tests require careful statistical methodology:

- **Sample size calculation:** Before the experiment, calculate the required sample size to detect a meaningful effect. For a 1% improvement in click-through rate with 80% power and 95% confidence, you may need millions of observations.
- **Multiple testing correction:** If you are evaluating 10 metrics simultaneously, apply Bonferroni correction or control false discovery rate (FDR) to avoid false positives.
- **Sequential testing:** Rather than waiting for a fixed sample size, sequential testing frameworks (like always-valid confidence intervals) allow you to check results continuously without inflating false positive rates.
- **Novelty and primacy effects:** Users may initially engage more with a new model simply because it is different. Run experiments long enough (typically 2-4 weeks) to let these effects dissipate.

### Shadow Mode Deployment

Before exposing users to a new model, run it in shadow mode. The production model serves all live traffic while the new model receives a copy of each request and generates predictions that are logged but not returned to users.

```
+----------------------------------------------------------------+
|                    SHADOW MODE DEPLOYMENT                       |
+----------------------------------------------------------------+
|                                                                  |
|   +----------+     +------------------+     +----------------+   |
|   | Incoming | --> | Production Model | --> | Response to    |   |
|   | Request  |     | (v1, live)       |     | User           |   |
|   +----------+     +------------------+     +----------------+   |
|        |                                                         |
|        | (async copy)                                            |
|        v                                                         |
|   +------------------+     +------------------+                  |
|   | Shadow Model     | --> | Log Predictions  |                  |
|   | (v2, not live)   |     | (compare later)  |                  |
|   +------------------+     +------------------+                  |
|                                                                  |
|   Analysis: Compare v1 vs v2 predictions offline                 |
|   - Prediction agreement rate                                    |
|   - Confidence distribution differences                          |
|   - Latency comparison                                           |
|   - Error case analysis                                          |
+----------------------------------------------------------------+
```

Shadow mode is especially valuable for high-stakes applications (fraud detection, medical diagnosis, autonomous systems) where the cost of a bad prediction is severe. It lets you measure how the new model would have performed without any risk to users.

## Latency Optimization Techniques

In a real-time ML system design, every millisecond counts. Latency optimization operates at multiple levels.

### Model Compilation

Converting models from eager-mode frameworks to optimized runtimes dramatically reduces inference latency.

**TorchScript (PyTorch):** Traces or scripts your PyTorch model into an intermediate representation that can be optimized and run without a Python runtime.

```python
# TorchScript compilation
import torch

model = MyModel()
model.eval()

# Tracing (works for models without control flow)
example_input = torch.randn(1, 3, 224, 224)
traced_model = torch.jit.trace(model, example_input)
traced_model.save("model_traced.pt")

# Scripting (works for models with control flow)
scripted_model = torch.jit.script(model)
```

**TensorRT (NVIDIA):** Optimizes models specifically for NVIDIA GPUs. Applies layer fusion, kernel auto-tuning, precision calibration, and memory optimization. Can deliver 2-6x speedup over native PyTorch.

**ONNX Runtime:** Framework-agnostic optimization. Supports CPU, GPU, and specialized accelerators. Graph optimizations include constant folding, redundant node elimination, and operator fusion.

| Optimization | Typical Speedup | Accuracy Impact | Complexity |
|-------------|----------------|-----------------|------------|
| TorchScript | 1.2-2x | None | Low |
| ONNX Runtime | 1.5-3x | None | Low |
| TensorRT FP16 | 2-4x | Minimal | Medium |
| TensorRT INT8 | 3-6x | Small (calibration needed) | High |
| Quantization + Pruning | 4-8x | Moderate | High |

### Caching Strategies

Not every request needs a fresh inference call. Strategic caching can eliminate redundant computation.

**Prediction cache:** For deterministic models, cache the mapping from input features to output predictions. A Redis cluster with TTL-based expiration works well. Hash the input features to create cache keys.

```python
import hashlib
import redis
import json

cache = redis.Redis(host="redis-cluster", port=6379)

def predict_with_cache(features, ttl_seconds=300):
    # Create deterministic cache key from features
    key = hashlib.sha256(
        json.dumps(features, sort_keys=True).encode()
    ).hexdigest()

    cached = cache.get(key)
    if cached:
        return json.loads(cached)

    prediction = model.predict(features)
    cache.setex(key, ttl_seconds, json.dumps(prediction))
    return prediction
```

**Embedding cache:** For models that compute embeddings (search, recommendations), cache the embeddings rather than recomputing them. User embeddings change infrequently and can be cached for hours or days.

**Feature cache:** Cache expensive feature computations in a feature store. Features like "user's average session duration over 30 days" do not change with each request and can be pre-computed.

### Edge Deployment

For ultra-low latency requirements (under 10ms), deploy models directly to edge locations close to users.

- **CDN-based inference:** Services like Cloudflare Workers AI and AWS CloudFront Functions run lightweight models at edge locations worldwide.
- **On-device inference:** TensorFlow Lite, Core ML, and ONNX Runtime Mobile run models directly on user devices. Zero network latency, but limited model size and compute.
- **Edge servers:** Deploy model servers in regional data centers or at the network edge. Useful for applications like real-time game AI, autonomous vehicles, or industrial IoT.

The tradeoff with edge deployment is always model size versus latency. Larger, more accurate models must run in centralized data centers. Smaller, distilled models can run at the edge.

## Monitoring Model Serving

Production ML systems require monitoring at both the infrastructure level and the model performance level. A model can be "up" from a systems perspective while producing degraded predictions due to data drift.

### Latency Percentiles

Track latency at multiple percentiles, not just the average.

- **p50 (median):** The typical user experience. Target depends on use case, but under 50ms is common for real-time serving.
- **p95:** The experience for 1 in 20 users. Should still be acceptable. Often 2-3x the p50.
- **p99:** The worst-case experience (excluding extreme outliers). If your p99 is 500ms but your SLA is 200ms, you have a tail latency problem.
- **p99.9:** Critical for high-traffic services where even 0.1% of slow requests affects thousands of users.

```
  Latency Distribution Example:

  p50:  23ms  |========
  p75:  35ms  |============
  p90:  58ms  |====================
  p95:  89ms  |==============================
  p99: 245ms  |=================================================================================
  p99.9: 890ms|[off chart - investigate these]
```

Tail latency spikes often indicate garbage collection pauses, GPU memory contention, model loading, or batch size variability. Investigate p99 anomalies aggressively.

### Throughput and Error Rates

- **Requests per second (RPS):** Track per model version and per endpoint. Set alerts for both traffic drops (possible upstream issue) and spikes (possible attack or upstream bug).
- **Error rate:** Categorize errors: model errors (NaN outputs, shape mismatches), infrastructure errors (OOM, timeouts), and client errors (bad input). Each category requires different remediation.
- **Queue depth:** For systems with request batching, monitor how many requests are waiting. Growing queues indicate the system is falling behind.

### Model Performance Drift

This is where ML monitoring diverges from traditional application monitoring. Models degrade over time as the real world changes.

**Data drift:** The distribution of input features shifts from what the model was trained on. For example, a fraud detection model trained on pre-pandemic transaction data will see very different patterns post-pandemic.

**Concept drift:** The relationship between inputs and outputs changes. A recommendation model trained when users preferred long-form content may become stale as short-form video becomes dominant.

**Prediction drift:** The distribution of model outputs changes, even if accuracy has not been measured. A sudden shift in prediction confidence or class distribution warrants investigation.

**Monitoring approach:**
- Compare incoming feature distributions against training data using statistical tests (KS test, PSI, Jensen-Shannon divergence)
- Track prediction distributions over time with rolling windows
- Log ground truth labels when available and compute accuracy metrics on a delay
- Set alerts on distribution shift magnitude and accuracy degradation thresholds

### Resource Utilization

- **GPU utilization:** Target 70-85%. Below 50% means you are overpaying. Above 90% risks latency spikes from contention.
- **GPU memory:** Monitor peak usage. OOM kills are the most common cause of inference server crashes.
- **CPU utilization:** Preprocessing and postprocessing often happen on CPU. A CPU bottleneck can starve the GPU.
- **Network I/O:** Large model inputs (images, audio) can saturate network bandwidth, especially with high request concurrency.

## Architecture Diagram: Complete Production Model Serving Stack

Here is a comprehensive view of a production ML model serving system, showing all the components discussed in this guide working together:

```
+===========================================================================+
||                 COMPLETE PRODUCTION MODEL SERVING STACK                  ||
+===========================================================================+
|                                                                             |
|   CLIENTS                                                                   |
|   +-------+  +--------+  +---------+                                        |
|   | Web   |  | Mobile |  | Internal|                                        |
|   | App   |  | App    |  | Service |                                        |
|   +---+---+  +---+----+  +----+----+                                        |
|       |          |             |                                             |
|       +----------+-------------+                                            |
|                  |                                                           |
|                  v                                                           |
|   EDGE / GATEWAY LAYER                                                      |
|   +------------------------------------------------------------------+      |
|   |  CDN + Edge Cache (CloudFront / Cloudflare)                      |      |
|   +------------------------------------------------------------------+      |
|   |  API Gateway (Kong / AWS API GW)                                 |      |
|   |  - Authentication    - Rate Limiting    - Request Routing        |      |
|   +------------------------------------------------------------------+      |
|                  |                                                           |
|                  v                                                           |
|   ROUTING LAYER                                                             |
|   +------------------------------------------------------------------+      |
|   |  Traffic Router / A/B Test Controller                            |      |
|   |  - Model version routing    - Canary % control                   |      |
|   |  - Shadow mode forking      - User-level assignment              |      |
|   +------------------------------------------------------------------+      |
|           |              |                |                                  |
|           v              v                v                                  |
|   SERVING LAYER                                                             |
|   +-----------------+ +-----------------+ +-----------------+               |
|   | Model v2        | | Model v1        | | Shadow Model v3 |               |
|   | (Canary - 5%)   | | (Prod - 95%)    | | (Logging Only)  |               |
|   |                 | |                 | |                 |               |
|   | Triton Server   | | Triton Server   | | Triton Server   |               |
|   | - Dynamic Batch | | - Dynamic Batch | | - Async Logging |               |
|   | - GPU (MIG)     | | - GPU (MIG)     | | - GPU (shared)  |               |
|   +-----------------+ +-----------------+ +-----------------+               |
|           |              |                |                                  |
|           v              v                v                                  |
|   DATA LAYER                                                                |
|   +------------------------------------------------------------------+      |
|   | Prediction Cache (Redis)    | Feature Store (Feast / Tecton)     |      |
|   +------------------------------------------------------------------+      |
|   | Embedding Store (Pinecone / pgvector)  | Ground Truth Logger     |      |
|   +------------------------------------------------------------------+      |
|                                                                             |
|   ML PLATFORM LAYER                                                         |
|   +------------------------------------------------------------------+      |
|   | Model Registry (MLflow)                                          |      |
|   |  - Model artifacts    - Metadata    - Lineage    - Approvals     |      |
|   +------------------------------------------------------------------+      |
|   | CI/CD Pipeline (GitHub Actions / Argo)                           |      |
|   |  - Validation gates   - Integration tests   - Auto-rollout      |      |
|   +------------------------------------------------------------------+      |
|   | Training Pipeline (Kubeflow / SageMaker)                         |      |
|   |  - Scheduled retraining    - Hyperparameter tuning               |      |
|   +------------------------------------------------------------------+      |
|                                                                             |
|   MONITORING LAYER                                                          |
|   +------------------------------------------------------------------+      |
|   | Infrastructure (Prometheus + Grafana)                            |      |
|   |  - Latency (p50/p95/p99)   - GPU util   - Error rates           |      |
|   +------------------------------------------------------------------+      |
|   | Model Performance (Evidently / Arize / WhyLabs)                  |      |
|   |  - Data drift    - Prediction drift    - Accuracy tracking       |      |
|   +------------------------------------------------------------------+      |
|   | Business Metrics (Datadog / internal dashboards)                 |      |
|   |  - CTR    - Conversion    - Revenue impact                       |      |
|   +------------------------------------------------------------------+      |
|   | Alerting (PagerDuty / OpsGenie)                                  |      |
|   |  - Latency SLA breach   - Drift threshold   - Error spike        |      |
|   +------------------------------------------------------------------+      |
|                                                                             |
+=============================================================================+
```

This architecture handles the full lifecycle: requests flow through the gateway and traffic router, hit the appropriate model version, leverage caching and feature stores, and feed into a comprehensive monitoring stack. The ML platform layer manages model artifacts, automated pipelines, and deployment orchestration.

## Key Takeaways

Designing an ML model serving system for production requires thinking far beyond the model itself. Here are the principles that matter most:

1. **Match the serving pattern to your use case.** Not every prediction needs real-time inference. Batch and near-real-time patterns can reduce costs by 10-100x for the right workloads.

2. **Optimize the model before scaling the infrastructure.** Quantization, distillation, and compilation often deliver more speedup per dollar than adding more GPUs.

3. **Dynamic batching is nearly free performance.** If you are serving on GPUs, enable dynamic batching. The throughput gains are substantial with minimal latency impact.

4. **Treat model deployment like application deployment.** Blue-green deployments, canary rollouts, and automated rollback are not optional for production ML systems.

5. **Shadow mode before A/B test before full rollout.** This progression, from zero-risk validation to controlled experiment to full deployment, prevents costly mistakes.

6. **Monitor predictions, not just infrastructure.** A model server can report 100% uptime and 20ms latency while the model itself produces increasingly wrong predictions due to data drift.

7. **Cache aggressively.** Many ML applications see significant input repetition. A prediction cache with a 5-minute TTL can eliminate 30-60% of inference calls.

8. **Plan for GPU efficiency from the start.** MIG partitioning, time-slicing, and workload-aware scheduling prevent the common pattern of paying for 8 GPUs while only using 2 at capacity.

## Design Your ML Serving Architecture

Visualizing these complex serving architectures helps teams align on design decisions before writing code. [InfraSketch's AI-powered system design tool](/tools/system-design-tool) lets you generate production ML serving diagrams from natural language descriptions, complete with inference servers, feature stores, model registries, and monitoring stacks.

Describe your ML serving requirements in plain English and get a complete architecture diagram in seconds, along with a detailed design document covering scaling strategies, deployment patterns, and monitoring approaches.

---

## Related Resources

- [Machine Learning System Design Patterns](/blog/ml-system-design-patterns)
- [Real-World AI System Architecture](/blog/real-world-ai-system-architecture)
- [Streaming ML System Design](/blog/streaming-ml-system-design)
- [MLOps System Design](/blog/mlops-system-design)
- [Microservices Architecture Diagram Guide](/blog/microservices-architecture-diagram-guide)
