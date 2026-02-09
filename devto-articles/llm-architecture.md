---
title: How to Design LLM Applications for Production: A System Design Guide
published: true
tags: llm, ai, systemdesign, architecture
canonical_url: https://infrasketch.net/blog/llm-system-design-architecture
cover_image: https://infrasketch.net/full-app-with-design-doc.png
---

Shipping an LLM-powered application to production requires far more than wrapping an API call in a web server. You need orchestration layers, retrieval pipelines, guardrails, observability, and cost management, all designed around the unique constraints of nondeterministic, latency-heavy AI workloads.

This guide covers the core patterns you need: RAG pipelines, vector databases, chatbot design, agent architectures, and production scaling. For the full deep-dive with additional diagrams and code, check out the [complete article on InfraSketch](https://infrasketch.net/blog/llm-system-design-architecture).

## Why LLM Apps Are Architecturally Different

Traditional ML systems return structured predictions in milliseconds with predictable costs. LLM applications break those assumptions:

- **Nondeterministic outputs.** The same prompt can produce different responses. Your system must handle variability.
- **High latency.** A single LLM call can take 5 to 60+ seconds. Synchronous request-response patterns fall apart for complex workflows.
- **Token-based costs.** You pay per token, not per request. A poorly designed prompt can 10x your costs overnight.
- **Multi-step reasoning.** Real-world tasks often require multiple tool calls, retrieval steps, and LLM iterations.
- **Context window management.** Models have finite context (8K to 200K+ tokens). You must decide what to include and when to summarize.

These constraints demand their own set of architectural patterns.

## The Four Layers of Every LLM Application

```
+-----------------------------------------------------+
|                   UI / Client Layer                   |
|         Web app, mobile app, CLI, API consumer        |
+-----------------------------------------------------+
|               Orchestration Layer                     |
|     LangGraph, LangChain, custom state machines       |
|     Prompt management, tool routing, guardrails       |
+-----------------------------------------------------+
|                  Model Layer                          |
|       Claude, GPT-4, Gemini, open-source models       |
|       Prompt caching, model routing, fallbacks        |
+-----------------------------------------------------+
|                   Data Layer                          |
|     Vector DBs, document stores, conversation         |
|     history, knowledge bases, user context             |
+-----------------------------------------------------+
```

The **orchestration layer** is where the real complexity lives. It decides which model to call, what context to provide, whether tools are needed, how to handle errors, and when to loop back for another LLM call. Frameworks like LangGraph operate at this layer.

The **data layer** encompasses vector databases for semantic search, conversation history, and any external knowledge the LLM needs. RAG systems sit at the intersection of data and orchestration.

![InfraSketch: AI-generated architecture diagrams with design docs](https://infrasketch.net/full-app-with-design-doc.png)

## RAG Architecture: The Essential Pattern

Retrieval-Augmented Generation is the most common LLM pattern in production. Instead of relying solely on training data, RAG retrieves relevant documents at query time and includes them in the prompt, grounding responses in your actual data.

### The Ingestion Pipeline (Offline)

```
Documents --> Chunking --> Embedding Model --> Vector Database
(PDFs,       (Fixed,      (text-embedding-   (Pinecone,
 Docs,        Semantic,    3-large)            pgvector,
 APIs)        Recursive)                       Weaviate)
```

**Chunking strategy matters.** Fixed-size chunking (512 tokens with overlap) is simple but splits mid-thought. Semantic chunking uses natural boundaries (paragraphs, headers) for more coherent chunks. Recursive chunking combines both and is the best default.

### The Retrieval Pipeline (Online)

1. **Embed the query** using the same model as ingestion.
2. **Vector search** for the top-K most similar chunks.
3. **(Optional) Rerank** with a cross-encoder for higher precision.
4. **Assemble the prompt** with system instructions, retrieved chunks, history, and query.
5. **Call the LLM** and return the response with citations.

### Common RAG Pitfalls

These are the mistakes I see most often in RAG implementations:

- **Chunk size mismatch.** Chunks too small lose context; too large dilute relevance and waste tokens. Start with 512 tokens and 50-token overlap, then tune based on retrieval quality.
- **Embedding model mismatch.** Using different models for ingestion and retrieval produces garbage results. This sounds obvious, but it happens frequently during model upgrades.
- **Skipping reranking.** Vector similarity is a rough proxy for relevance. Adding a cross-encoder reranker (retrieve top-50, rerank to top-5) dramatically improves precision.
- **No metadata filtering.** Without metadata, you cannot scope searches to specific documents, time ranges, or categories. Always store source, date, and section metadata alongside your chunks.
- **Stale data.** If your ingestion pipeline does not run frequently, the RAG system serves outdated information. Automate your ingestion on a schedule.

## Choosing a Vector Database

| Database | Best For |
|----------|----------|
| **Pinecone** | Production SaaS, zero-ops teams |
| **pgvector** | Teams already on PostgreSQL (under 10M vectors) |
| **Weaviate** | Complex queries, multi-modal data |
| **Qdrant** | High performance, flexible filtering |
| **Milvus** | Massive scale, billions of vectors |
| **Chroma** | Prototyping, small datasets |

The practical advice: if you already run PostgreSQL, start with pgvector. If you need managed scale, evaluate Pinecone or Qdrant. Do not over-engineer your data layer before validating retrieval quality.

## Agent Architectures: Tool Calling and LangGraph

When an LLM needs to interact with external systems, you are building an agent. Modern LLMs (Claude, GPT-4, Gemini) support native tool calling, where you define tools as structured schemas and the model returns structured tool-call objects.

```python
tools = [
    {
        "name": "search_database",
        "description": "Search the product database",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 10}
            },
            "required": ["query"]
        }
    }
]

response = client.messages.create(
    model="claude-sonnet-4-5-20250514",
    tools=tools,
    messages=[{"role": "user", "content": "Find laptops under $1000"}]
)
```

### The ReAct Pattern

The most common agent pattern alternates between reasoning and acting:

1. The LLM **reasons** about what it needs to do.
2. It **acts** by calling a tool.
3. It **observes** the result.
4. It decides whether to **continue** (loop) or **stop** (return a response).

ReAct works well for 1-5 tool calls. For longer chains, consider the **plan-and-execute** pattern, which separates planning from execution and handles 10+ step workflows more reliably.

### LangGraph: State Machines for LLM Workflows

LangGraph models workflows as directed graphs with cycles, which is perfect for agent loops. The most common pattern is the tool execution loop:

```python
def route_tool_decision(state):
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "finalize"

graph.add_conditional_edges(
    "llm_node",
    route_tool_decision,
    {"tools": "tool_executor", "finalize": "finalize_node"}
)
graph.add_edge("tool_executor", "llm_node")  # Loop back
```

This is the exact pattern that [InfraSketch](https://infrasketch.net) uses internally. When a user asks the AI to modify a system architecture diagram, LangGraph orchestrates the loop: Claude decides which tools to call (`add_node`, `delete_node`, `update_node`, `add_edge`), the tools execute against the diagram state, and results feed back into Claude until the modifications are complete.

![Complex system architecture visualization in InfraSketch](https://infrasketch.net/ecommerce-expanded.png)

## Scaling LLM Applications

The bottleneck is not CPU or memory but the LLM API itself: its latency, throughput limits, and per-token costs.

### Prompt Caching

If many requests share the same system prompt, caching avoids re-processing those tokens. Anthropic's prompt caching for Claude can reduce costs by up to 90% on cached tokens. Structure prompts so the static portion (system prompt, tool definitions, few-shot examples) comes first, followed by dynamic content.

### Model Routing

Not every request needs your most expensive model:

```python
def route_to_model(query, context):
    complexity = assess_complexity(query, context)
    if complexity == "simple":
        return "claude-haiku-4-5"      # Fast, cheap
    elif complexity == "medium":
        return "claude-sonnet-4-5"     # Balanced
    else:
        return "claude-opus-4-5"       # Maximum quality
```

Model routing can reduce costs by 50-80% with minimal quality impact, because most requests are simple enough for a smaller model.

### Cost Management at a Glance

| Strategy | Cost Reduction | Effort |
|----------|---------------|--------|
| Prompt caching | 30-90% | Low |
| Model routing | 50-80% | Medium |
| Request batching | 50% | Low |
| Shorter prompts | 20-50% | Medium |
| Response caching | 50-90% (repeated queries) | Medium |

## Observability: Non-Negotiable for Production

LLM applications are difficult to debug without proper observability. The nondeterministic nature of model outputs means you cannot rely on unit tests alone. Every interaction should produce a trace capturing: the full prompt, raw response (including tool calls), token counts, latency, cost, and any errors.

Key metrics to monitor:

- **Time to first token (TTFT)** for streaming UX quality.
- **Tokens per second** for perceived speed during generation.
- **Total latency** including all tool calls and LLM iterations.
- **Cost per request, per user, per feature** for budgeting and optimization.
- **Tool call accuracy** to catch when models call wrong tools or pass bad arguments.

Tools like LangSmith, OpenTelemetry, and CloudWatch handle this. Set alerts on P50, P95, and P99 latency. LLM API performance can degrade during peak hours, and you want to know before your users tell you.

Beyond tracing, build **evaluation datasets** (curated inputs with expected outputs) and run them on every prompt change, model upgrade, or system modification. This is the LLM equivalent of a regression test suite. Also build feedback mechanisms into your application (thumbs up/down) and use that data to identify failure modes.

![Full application view with diagram and chat in InfraSketch](https://infrasketch.net/url-shortener-full-app-view.png)

## Key Takeaways

1. **Start simple, add complexity as needed.** Begin with a direct LLM call. Add RAG when you need external knowledge. Add tool calling for actions. Add agent patterns for multi-step reasoning.

2. **Design for latency.** Use async patterns, streaming, and background tasks. Never make a user wait synchronously for a complex LLM workflow.

3. **Invest in observability early.** Tracing, evaluation, and cost tracking are not luxuries.

4. **Choose your vector database based on your existing stack.** pgvector for PostgreSQL users, Pinecone or Qdrant for managed scale.

5. **Use state machines for complex workflows.** LangGraph provides the control flow primitives for agent loops, conditional routing, and human-in-the-loop patterns.

6. **Budget for tokens, not just compute.** Implement model routing, prompt caching, and token budgets from day one.

For the full version of this guide with complete architecture diagrams, additional code samples, and the InfraSketch case study, read the [complete article](https://infrasketch.net/blog/llm-system-design-architecture).

---

Visualize your LLM architecture with [InfraSketch](https://infrasketch.net). Describe your RAG pipeline, chatbot, or agent system in plain English and get a complete architecture diagram. Try it free at [https://infrasketch.net](https://infrasketch.net).
