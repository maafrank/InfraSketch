---
title: "How Netflix, Uber, and Google Build AI Systems: Architecture Deep Dive"
published: true
tags: ai, systemdesign, machinelearning, architecture
canonical_url: https://infrasketch.net/blog/real-world-ai-system-architecture
cover_image: https://infrasketch.net/full-app-with-design-doc.png
---

Here is a fact that surprises most engineers: at Google, the actual ML model code makes up less than 5% of a production AI system. The other 95% is data pipelines, feature stores, serving infrastructure, monitoring, and testing.

That insight, from Google's famous "Hidden Technical Debt in Machine Learning Systems" paper, explains why studying real-world AI architectures is so valuable. The model is the easy part. The system around it is where the real engineering happens.

I spent weeks studying the production AI architectures at Netflix, Uber, Google, and Spotify. Here are the patterns that keep appearing, and why they matter for every engineer building AI-powered products. Whether you are building your first recommendation system, preparing for a system design interview, or scaling an existing ML pipeline, these are the blueprints worth understanding.

## Netflix: Personalization at Planetary Scale

80% of what people watch on Netflix comes from recommendations, not search. That makes the recommendation engine the core product distribution mechanism for 200+ million subscribers.

Netflix's architecture follows a **three-stage pipeline** that progressively narrows the candidate set:

**Stage 1: Candidate Generation** narrows tens of thousands of titles to roughly 10,000 per user. Multiple generators run in parallel (collaborative filtering, content-based filtering, trending signals, new release injection), and their results are merged.

**Stage 2: Ranking** scores those 10,000 candidates using deep neural networks fed by a centralized feature store. The features include user history, item metadata, context (time of day, device), and interaction data (has the user seen the trailer?).

**Stage 3: Re-Ranking** applies diversity injection (no genre domination), explore-vs-exploit balancing (prevent filter bubbles), freshness boosting, and business constraints like regional licensing.

The secret weapon is the **feature store**, which ensures the exact same feature computation logic runs during training and serving. Without this, "training-serving skew" silently degrades model performance. Netflix also runs thousands of concurrent A/B experiments. Every pipeline component, from candidate generation to artwork selection, can be tested independently.

**Key takeaway:** Multi-stage pipelines let you balance cost (cheap early filtering) with quality (expensive final ranking). The feature store and A/B testing framework are as architecturally important as the models themselves.

![Visualizing system architectures with InfraSketch](https://infrasketch.net/full-app-with-design-doc.png)
*Mapping out a multi-stage recommendation pipeline in [InfraSketch](https://infrasketch.net), with an auto-generated design document alongside the architecture diagram*

## Google Search: 8.5 Billion Queries Per Day, Under 500ms

Google Search faces a unique constraint: every query must return results in under 500 milliseconds from an index of hundreds of billions of pages.

The architecture uses **multi-stage retrieval**, where each stage applies progressively more expensive models:

1. **Retrieval** uses inverted indexes and BM25 scoring to pull ~10,000 candidates from billions of documents in sub-millisecond time
2. **Initial Ranking** scores those candidates with lightweight gradient-boosted trees using hundreds of features (PageRank, freshness, mobile-friendliness, query-document match)
3. **Deep Ranking** applies transformer-based models (descendants of BERT) to the top ~1,000 results for semantic understanding

Before any of this happens, a **query understanding layer** classifies intent (navigational vs. informational vs. transactional), recognizes entities, and expands the query with synonyms.

The transformer stage is the most expensive by far. Google makes it viable through model distillation (compressing large models into smaller ones), quantization (8-bit instead of 32-bit precision), custom TPU hardware, and caching embeddings for popular queries.

**Key takeaway:** When your corpus is too large for expensive models to score everything, staged retrieval is mandatory. Hardware optimization and model compression are what make deep learning feasible at search scale. Also note how similar this is to Netflix's pipeline: cheap retrieval first, expensive ranking last. The pattern is universal.

## Uber Michelangelo: ML as Infrastructure

Uber runs dozens of ML models simultaneously: surge pricing, ETA estimation, fraud detection, driver-rider matching, and delivery time prediction. Rather than building custom infrastructure for each, they built **Michelangelo**, an internal ML platform that standardizes the entire lifecycle.

The architecture has four layers:

**Data and Feature Layer** handles both batch features (computed via Spark on historical data, like a driver's 30-day average rating) and real-time features (computed via Kafka/Flink on streaming data, like current GPS coordinates). Both feed into a unified feature store.

**Training Layer** supports multiple frameworks (XGBoost, TensorFlow, PyTorch) through a single interface, with distributed GPU training and hyperparameter tuning.

**Serving Layer** provides online serving (p99 under 10ms for pricing and ETA) with pre-loaded models in memory, plus batch prediction for less latency-sensitive tasks like fraud review.

**Monitoring Layer** continuously tracks prediction drift, feature drift, model performance, and data quality. This is critical because in production, models degrade silently unless you actively watch for it.

![AI-generated analytics architecture in InfraSketch](https://infrasketch.net/analytics-diagram-generated.png)
*An AI-generated analytics architecture in [InfraSketch](https://infrasketch.net), showing data pipelines, processing layers, and serving infrastructure similar to Uber's platform approach*

**Key takeaway:** Once you have multiple ML use cases, building a shared platform pays for itself. The monitoring layer (prediction drift, feature drift, data quality) is not optional. It is how you catch problems before users do.

## Spotify Discover Weekly: Music You Didn't Know You Wanted

Discover Weekly generates a personalized 30-song playlist for 500+ million users every Monday. The architectural challenge is combining three different signal types into a coherent recommendation.

**Collaborative filtering** builds a massive user-item interaction matrix from billions of streaming events, then uses implicit matrix factorization (alternating least squares on Spark clusters) to find users with similar taste.

**Audio analysis** processes raw audio waveforms through convolutional neural networks to extract features like tempo, energy, danceability, and mood. This solves the cold start problem: new tracks with few listeners can still be recommended based on how they sound.

**NLP-based analysis** scrapes music blogs, reviews, and social media to capture cultural context that neither listening data nor audio analysis can see.

The hybrid ranking model combines all three signal types, then curates each playlist to balance familiarity with novelty (roughly 50/50), enforce genre and artist diversity, and create a natural listening arc. The entire thing runs as a weekend batch job on Spark, generating playlists for every user before Monday morning.

**Key takeaway:** Hybrid approaches (behavioral + content + text signals) outperform any single method. Audio analysis is particularly clever because it breaks the cold start problem that plagues pure collaborative filtering systems. For weekly delivery cadences, massive batch jobs are both practical and cost-effective.

## Five Patterns That Keep Appearing

After studying these systems, five architectural patterns show up everywhere:

### 1. Feature Stores

Netflix, Uber, and Spotify all maintain centralized feature stores. They solve training-serving skew (where features computed differently during training and serving cause silent model degradation), enable feature sharing across teams, and support point-in-time correctness for training data. If you take away one thing from this article, let it be this: get your feature computation right, and half your production ML problems disappear.

### 2. Multi-Stage Ranking Pipelines

Every system uses cheap, fast models to reduce candidates before expensive models score the finalists. Netflix goes 10K to 1K to final. Google goes 10K to 1K to final. The pattern is universal because the best models are too expensive to run on everything.

### 3. Offline-Online Architecture Split

All systems separate batch processing (training, index building, feature pre-computation) from online serving (real-time inference, feature lookup). Each path gets independently optimized for its constraints.

### 4. A/B Testing as Core Infrastructure

This is not an afterthought. Netflix, Google, Uber, and Spotify all treat experimentation infrastructure as a first-class architectural component. Consistent user assignment, metric collection, statistical significance testing, and interaction detection between concurrent experiments are all built in.

### 5. Monitoring Beyond Accuracy

Production monitoring tracks prediction distributions, feature drift, data quality, and business metrics. User interactions (clicks, skips, purchases) feed back into training pipelines for continuous learning. Traditional software monitoring asks "is the server up?" ML monitoring asks "is the model still giving good answers?" These are fundamentally different questions that require different tooling.

![Complex architecture with collapsible component groups](https://infrasketch.net/ecommerce-collapsed-groups.png)
*Organizing a complex AI system architecture with collapsible component groups in [InfraSketch](https://infrasketch.net), making it easier to communicate multi-layer designs to your team*

## How to Apply These Patterns at Any Scale

You do not need Netflix's scale to use these patterns. Here is how to start:

**Multi-stage pipeline:** Your first stage can be a database query with filters. Your second stage can be a lightweight scoring function. Swap in more sophisticated components as you grow.

**Feature store:** Start simple. A well-organized set of SQL views and a Redis cache can serve as a feature store. The key is consistency between training and serving, not infrastructure complexity.

**A/B testing:** Use feature flags to control model variants per user. Log predictions alongside the features used. Define your primary metric and track it from day one.

**Monitoring:** Track prediction distribution statistics, feature coverage, serving latency, and the business metrics your model is supposed to influence.

**Architecture visualization:** Creating a clear diagram of data flow, component boundaries, and the offline-online split forces you to make implicit assumptions explicit. It is one of the highest-value exercises in system design. Before writing any code, sketch out your pipeline stages, data stores, and serving layer. You will catch design flaws that would have taken weeks to discover otherwise.

For a deeper dive into each case study with full architecture diagrams and additional analysis of Pinterest's visual search system, read the [complete article on the InfraSketch blog](https://infrasketch.net/blog/real-world-ai-system-architecture).

---

Want to design AI architectures like the ones used at Netflix, Uber, and Google? Try [InfraSketch](https://infrasketch.net) -- describe your system in plain English and get a complete architecture diagram in seconds. Free at [https://infrasketch.net](https://infrasketch.net).
