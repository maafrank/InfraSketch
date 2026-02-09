# LLM System Design Architecture: Building Production AI Applications

Large Language Models have fundamentally changed how we build software. But shipping an LLM-powered application to production requires far more than wrapping an API call in a web server. You need orchestration layers, retrieval pipelines, guardrails, observability, cost management, and a system design that can handle the unique challenges of nondeterministic, latency-heavy AI workloads.

This guide covers end-to-end LLM system design architecture, from RAG pipelines and vector databases to agent frameworks and production scaling patterns. Whether you are preparing for a system design interview, architecting a new AI product, or trying to understand how tools like [InfraSketch](/) orchestrate LLM workflows behind the scenes, this is the comprehensive reference you need.

## Why LLM Applications Are Different From Traditional ML

Traditional machine learning systems follow a well-understood pattern: collect data, train a model, deploy it behind an inference endpoint, and serve predictions. The model is a black box that takes structured input and returns structured output. Latency is measured in milliseconds. Costs are predictable.

LLM applications break almost every one of those assumptions.

**Nondeterministic outputs.** The same prompt can produce different responses across calls. Your system must handle variability in format, length, and content.

**High latency.** A single LLM call can take 5 to 60+ seconds depending on the model, prompt length, and output length. This rules out synchronous request-response patterns for complex workflows.

**Token-based costs.** You pay per input and output token, not per request. A poorly designed prompt or unnecessary context window can 10x your costs overnight.

**Multi-step reasoning.** Many real-world tasks require the LLM to call tools, retrieve information, reason over results, and iterate. A single API call is rarely sufficient.

**Context window management.** Models have finite context windows (ranging from 8K to 200K+ tokens). You must decide what information to include, how to chunk it, and when to summarize.

These constraints mean that LLM system design architecture demands its own set of patterns, distinct from both traditional web services and conventional ML systems. For a broader look at system design fundamentals, see our [Complete Guide to System Design](/blog/complete-guide-system-design).

## LLM Application Architecture Layers

Every production LLM application can be decomposed into four layers. Understanding these layers is the first step toward designing a robust system.

```
┌─────────────────────────────────────────────────────┐
│                   UI / Client Layer                  │
│         Web app, mobile app, CLI, API consumer       │
├─────────────────────────────────────────────────────┤
│               Orchestration Layer                    │
│     LangGraph, LangChain, custom state machines      │
│     Prompt management, tool routing, guardrails      │
├─────────────────────────────────────────────────────┤
│                  Model Layer                         │
│       Claude, GPT-4, Gemini, open-source models      │
│       Prompt caching, model routing, fallbacks       │
├─────────────────────────────────────────────────────┤
│                   Data Layer                         │
│     Vector DBs, document stores, conversation        │
│     history, knowledge bases, user context            │
└─────────────────────────────────────────────────────┘
```

### UI / Client Layer

This is the user-facing surface. It handles input collection, streaming response display, and interaction patterns (chat, canvas, form-based). The key challenge here is managing the latency inherent in LLM calls. Streaming responses (via Server-Sent Events or WebSockets) is nearly mandatory for any user-facing application.

### Orchestration Layer

This is where the real complexity lives. The orchestration layer decides what to do with a user's input: which model to call, what context to provide, whether tools are needed, how to handle errors, and when to loop back for another LLM call. Frameworks like LangGraph, LangChain, and Semantic Kernel operate at this layer. Many teams also build custom orchestration using simple state machines or directed acyclic graphs.

### Model Layer

The model layer handles the actual LLM API calls. In production, this layer often includes prompt caching (to reduce costs and latency), model routing (sending simple queries to cheaper models), fallback logic (switching providers if one is down), and retry strategies with exponential backoff.

### Data Layer

LLM applications are data-hungry. The data layer encompasses vector databases for semantic search, document stores for raw content, conversation history databases, user preference stores, and any external knowledge bases the LLM needs to access. RAG (Retrieval-Augmented Generation) systems live at the intersection of this layer and the orchestration layer.

## RAG Architecture: End-to-End Design

Retrieval-Augmented Generation is the most common LLM system design pattern in production today. Instead of relying solely on the model's training data, RAG retrieves relevant documents at query time and includes them in the prompt context. This grounds the model's responses in your actual data, reducing hallucinations and keeping answers current.

Here is the full RAG system design architecture:

```
┌──────────────────────────────────────────────────────────────────┐
│                    INGESTION PIPELINE (Offline)                   │
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌───────────┐  │
│  │ Document  │───▶│ Chunking │───▶│ Embedding│───▶│  Vector   │  │
│  │ Sources   │    │ Strategy │    │ Model    │    │  Database  │  │
│  │          │    │          │    │          │    │           │  │
│  │ PDFs     │    │ Fixed    │    │ text-    │    │ Pinecone  │  │
│  │ Docs     │    │ Semantic │    │ embedding│    │ Weaviate  │  │
│  │ Web      │    │ Recursive│    │ -3-large │    │ pgvector  │  │
│  │ APIs     │    │          │    │          │    │           │  │
│  └──────────┘    └──────────┘    └──────────┘    └───────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                    RETRIEVAL + GENERATION (Online)                │
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌───────────┐  │
│  │  User    │───▶│  Query   │───▶│  Vector  │───▶│  Reranker │  │
│  │  Query   │    │ Embedding│    │  Search  │    │ (optional)│  │
│  └──────────┘    └──────────┘    └──────────┘    └─────┬─────┘  │
│                                                        │        │
│                                                        ▼        │
│                                        ┌──────────────────────┐ │
│                                        │   Prompt Assembly    │ │
│                                        │                      │ │
│                                        │ System prompt        │ │
│                                        │ + Retrieved chunks   │ │
│                                        │ + User query         │ │
│                                        │ + Conversation hist. │ │
│                                        └──────────┬───────────┘ │
│                                                   │             │
│                                                   ▼             │
│                                        ┌──────────────────────┐ │
│                                        │      LLM Call        │ │
│                                        │   (Claude, GPT-4)    │ │
│                                        └──────────┬───────────┘ │
│                                                   │             │
│                                                   ▼             │
│                                        ┌──────────────────────┐ │
│                                        │  Response + Sources  │ │
│                                        └──────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### Document Ingestion Pipeline

The ingestion pipeline runs offline (or on a schedule) and prepares your documents for retrieval. It consists of four stages.

**1. Document Loading.** Extract raw text from your sources: PDFs, Markdown files, HTML pages, database records, API responses, Confluence pages, Git repositories. Each document type requires its own parser. Libraries like Unstructured, LangChain document loaders, and LlamaIndex readers handle the most common formats.

**2. Chunking.** Raw documents must be split into chunks small enough to fit in an embedding model's context and specific enough to be useful when retrieved. Chunking strategy has a massive impact on retrieval quality.

**Fixed-size chunking** splits text at a fixed token or character count (e.g., 512 tokens) with overlap (e.g., 50 tokens). Simple to implement, but it can split sentences and paragraphs mid-thought.

```python
# Fixed-size chunking example
def fixed_chunk(text, chunk_size=512, overlap=50):
    tokens = tokenize(text)
    chunks = []
    for i in range(0, len(tokens), chunk_size - overlap):
        chunks.append(tokens[i:i + chunk_size])
    return chunks
```

**Semantic chunking** uses natural boundaries in the text (paragraphs, sections, headers) to create chunks that preserve meaning. This produces variable-sized chunks, but each chunk is more coherent.

**Recursive chunking** combines both approaches. It first splits on major boundaries (sections, paragraphs), then recursively splits any chunks that exceed the size limit. This is the default strategy in LangChain and works well for most use cases.

| Strategy | Pros | Cons | Best For |
|----------|------|------|----------|
| Fixed-size | Simple, predictable | Splits mid-thought | Uniform documents |
| Semantic | Preserves meaning | Variable sizes | Structured documents |
| Recursive | Best of both | More complex | General purpose |

**3. Embedding Generation.** Each chunk is passed through an embedding model to produce a dense vector representation. Popular embedding models include OpenAI's `text-embedding-3-large` (3072 dimensions), Cohere's `embed-v3`, and open-source options like `bge-large-en` and `e5-large-v2`. The choice of embedding model directly affects retrieval quality.

**4. Vector Storage.** The embeddings are stored in a vector database along with the original chunk text and metadata (source document, page number, section title). This metadata is critical for filtering, citation, and debugging.

### Retrieval and Generation

At query time, the system performs the following steps:

1. **Embed the query** using the same embedding model used during ingestion.
2. **Search the vector database** for the top-K most similar chunks (typically K=5 to 20).
3. **(Optional) Rerank** the results using a cross-encoder model for higher precision. Reranking is slower but significantly improves relevance, especially when you retrieve a larger initial set (e.g., top-50) and rerank down to the top-5.
4. **Assemble the prompt** by combining the system prompt, retrieved chunks, conversation history, and user query.
5. **Call the LLM** and return the response with source citations.

### Common RAG Pitfalls

- **Chunk size mismatch.** If chunks are too small, you lose context. If they are too large, you dilute relevance and waste tokens.
- **Embedding model mismatch.** Using different models for ingestion and retrieval produces garbage results.
- **Missing metadata filtering.** Without metadata, you cannot scope searches to specific documents, time ranges, or categories.
- **No reranking.** Vector similarity is a rough proxy for relevance. Reranking with a cross-encoder dramatically improves precision.
- **Stale data.** If your ingestion pipeline does not run frequently, the RAG system serves outdated information.

## Vector Database Integration and Selection

Choosing the right vector database is a critical decision in any RAG system design architecture. The landscape has matured significantly, with options ranging from purpose-built managed services to extensions on databases you may already run.

### Comparison Table

| Database | Type | Hosting | Max Vectors | Filtering | Hybrid Search | Best For |
|----------|------|---------|-------------|-----------|---------------|----------|
| **Pinecone** | Managed SaaS | Cloud only | Billions | Metadata | Yes | Production SaaS, teams wanting zero ops |
| **Weaviate** | Open source | Self-hosted or Cloud | Billions | GraphQL + Metadata | Yes | Complex queries, multi-modal |
| **Milvus** | Open source | Self-hosted or Zilliz Cloud | Billions | Attribute | Yes | Large-scale, high throughput |
| **pgvector** | PostgreSQL extension | Anywhere Postgres runs | Millions | Full SQL | With pg_search | Teams already on Postgres |
| **Qdrant** | Open source | Self-hosted or Cloud | Billions | Payload | Yes | Rust performance, flexible filtering |
| **Chroma** | Open source | Embedded or Server | Millions | Metadata | No | Prototyping, small datasets |

### When to Use Each

**Pinecone** is the default choice for teams that want a fully managed vector database with minimal operational overhead. It handles sharding, replication, and scaling automatically. The tradeoff is vendor lock-in and cost at scale.

**pgvector** is the right choice if you already run PostgreSQL and your dataset is under 10 million vectors. You avoid adding a new database to your stack, and you get the full power of SQL for filtering and joins. For most startups, pgvector is more than sufficient.

**Weaviate** excels when you need complex queries that combine vector search with structured filtering, or when you are working with multi-modal data (text, images, audio).

**Milvus** (and its managed offering, Zilliz) targets high-throughput scenarios with billions of vectors. If you are building a recommendation engine or search system at massive scale, Milvus is worth evaluating.

**Qdrant** offers a strong balance of performance and developer experience. Written in Rust, it is fast and memory-efficient. Its payload filtering is flexible and well-documented.

**Chroma** is the fastest way to prototype. It runs in-process (embedded mode) with no infrastructure required. However, it is not designed for production scale.

For a deeper exploration of vector database patterns, see our upcoming guide on [Vector Database System Design](/blog/vector-database-system-design).

## Chatbot System Design: From Simple to Production-Grade

Chatbot system design architecture follows a progression from trivial to complex. Understanding each stage helps you choose the right level of complexity for your use case.

### Stage 1: Stateless Chatbot

The simplest possible chatbot. Each request is independent. There is no memory of previous messages.

```
┌──────────┐     ┌──────────────┐     ┌───────────┐
│  User    │────▶│  API Server  │────▶│   LLM     │
│  Input   │     │              │     │   API     │
└──────────┘     └──────────────┘     └───────────┘
                        │
                        ▼
                 ┌──────────────┐
                 │   Response   │
                 └──────────────┘
```

This works for single-turn tasks: summarization, translation, code generation. It is not a chatbot in any meaningful sense, but it is where many teams start.

### Stage 2: Conversational Chatbot (With Memory)

Adding conversation history turns a stateless wrapper into an actual chatbot. The key design decisions are where to store history and how to manage the context window.

```
┌──────────┐     ┌──────────────┐     ┌───────────┐
│  User    │────▶│  API Server  │────▶│   LLM     │
│  Input   │     │              │     │   API     │
└──────────┘     └──────┬───────┘     └───────────┘
                        │
                 ┌──────▼───────┐
                 │ Conversation │
                 │   History    │
                 │   Store      │
                 │              │
                 │ (DynamoDB,   │
                 │  Redis,      │
                 │  PostgreSQL) │
                 └──────────────┘
```

**Context window management strategies:**

- **Sliding window.** Keep the last N messages. Simple but loses early context.
- **Summarization.** Periodically summarize older messages into a condensed form. Preserves important context but adds latency and cost.
- **Hybrid.** Keep a rolling summary of the full conversation plus the last N messages verbatim.

### Stage 3: Production Chatbot (Tools, Guardrails, Evaluation)

A production chatbot system design architecture adds several critical layers around the core LLM interaction.

```
┌─────────────────────────────────────────────────────────────┐
│                    Production Chatbot                        │
│                                                             │
│  ┌──────────┐     ┌──────────────┐     ┌────────────────┐  │
│  │  User    │────▶│  Input       │────▶│  Orchestration │  │
│  │  Input   │     │  Guardrails  │     │  Layer         │  │
│  └──────────┘     │              │     │                │  │
│                   │ - PII detect │     │ - Route intent │  │
│                   │ - Toxicity   │     │ - Select model │  │
│                   │ - Injection  │     │ - Build prompt │  │
│                   └──────────────┘     │ - Call tools   │  │
│                                        │ - Loop/finish  │  │
│                                        └───────┬────────┘  │
│                                                │           │
│  ┌──────────────┐    ┌───────────┐    ┌───────▼────────┐  │
│  │ Conversation │    │  Tool     │    │   LLM API      │  │
│  │ History      │◀──▶│  Registry │◀──▶│   (Claude,     │  │
│  │ Store        │    │           │    │    GPT-4)       │  │
│  └──────────────┘    │ - Search  │    └───────┬────────┘  │
│                      │ - DB query│            │           │
│                      │ - API call│    ┌───────▼────────┐  │
│                      │ - Calculate│    │   Output       │  │
│                      └───────────┘    │   Guardrails   │  │
│                                       │                │  │
│  ┌──────────────┐                    │ - Format check │  │
│  │ Observability│                    │ - Safety filter│  │
│  │              │                    │ - Citation     │  │
│  │ - Traces    │                    └───────┬────────┘  │
│  │ - Latency   │                            │           │
│  │ - Cost      │                     ┌──────▼────────┐  │
│  │ - Quality   │                     │   Response    │  │
│  └──────────────┘                     └───────────────┘  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Input guardrails** protect against prompt injection, PII leakage, and toxic inputs. These run before the LLM call and can reject or sanitize inputs.

**Tool calling** allows the chatbot to take actions: search databases, call APIs, execute code, modify documents. This is what transforms a chatbot from a conversational interface into an agent. (More on this in the next section.)

**Output guardrails** validate the LLM's response before returning it to the user. They check for format compliance, safety violations, hallucinated citations, and factual consistency.

**Observability** captures traces, latency metrics, token usage, cost estimates, and quality scores for every interaction. Without observability, you are flying blind.

## Agent Architectures: Tool Calling, ReAct, and Plan-and-Execute

When an LLM needs to interact with external systems, you are building an agent. Agent architectures determine how the LLM decides which tools to use, in what order, and when to stop.

### How Tool Calling Works

Modern LLMs (Claude, GPT-4, Gemini) support native tool calling. Instead of asking the model to output JSON or code, you define tools as structured schemas. The model returns structured tool-call objects that your system executes.

```python
# Define tools as schemas
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
    },
    {
        "name": "get_user_profile",
        "description": "Retrieve a user's profile by ID",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"}
            },
            "required": ["user_id"]
        }
    }
]

# LLM returns structured tool calls
response = client.messages.create(
    model="claude-sonnet-4-5-20250514",
    tools=tools,
    messages=[{"role": "user", "content": "Find laptops under $1000"}]
)

# Execute the tool call
for block in response.content:
    if block.type == "tool_use":
        result = execute_tool(block.name, block.input)
        # Feed result back to the LLM for the next step
```

The key advantage of native tool calling over text-based approaches (like asking the LLM to output JSON) is reliability. The model's output is constrained to valid tool-call structures, eliminating parsing errors.

### The ReAct Pattern

ReAct (Reasoning + Acting) is the most common agent pattern. The LLM alternates between reasoning about what to do and taking actions via tool calls.

```
┌─────────────────────────────────────────────┐
│                ReAct Loop                    │
│                                             │
│  ┌─────────┐    ┌──────────┐    ┌────────┐ │
│  │ Reason  │───▶│ Act      │───▶│Observe │ │
│  │         │    │ (tool    │    │(tool   │ │
│  │ "I need │    │  call)   │    │ result)│ │
│  │  to..." │    │          │    │        │ │
│  └─────────┘    └──────────┘    └───┬────┘ │
│       ▲                             │      │
│       │         ┌──────────┐        │      │
│       └─────────│ Continue │◀───────┘      │
│                 │ or Stop? │               │
│                 └──────────┘               │
└─────────────────────────────────────────────┘
```

Each iteration:
1. The LLM **reasons** about the current state and what it needs to do next.
2. It **acts** by calling a tool.
3. It **observes** the tool's result.
4. It decides whether to continue (loop back to step 1) or stop (return a final response).

ReAct works well for tasks that require 1-5 tool calls. For longer chains, it can lose track of the overall goal or get stuck in loops.

### Plan-and-Execute Pattern

For complex, multi-step tasks, the plan-and-execute pattern separates planning from execution.

```
┌───────────────────────────────────────────────────────┐
│              Plan-and-Execute                          │
│                                                       │
│  ┌──────────┐    ┌─────────────────────────────────┐ │
│  │ Planner  │───▶│ Plan:                           │ │
│  │ (LLM)    │    │  1. Search for relevant docs    │ │
│  └──────────┘    │  2. Extract pricing data        │ │
│                  │  3. Calculate comparison         │ │
│                  │  4. Format report                │ │
│                  └──────────────┬──────────────────┘ │
│                                │                     │
│                  ┌─────────────▼──────────────────┐  │
│                  │ Executor                        │  │
│                  │                                 │  │
│                  │ Step 1: search_docs("pricing")  │  │
│                  │ Step 2: extract_data(results)   │  │
│                  │ Step 3: calculate(data)         │  │
│                  │ Step 4: format_report(results)  │  │
│                  └────────────────────────────────┘  │
│                                                      │
│  ┌──────────┐    ┌────────────────────────────────┐  │
│  │ Replanner│───▶│ Adjust plan if needed          │  │
│  │ (LLM)    │    │ (add steps, skip steps, retry) │  │
│  └──────────┘    └────────────────────────────────┘  │
└───────────────────────────────────────────────────────┘
```

The planner creates a step-by-step plan. The executor runs each step. After each step (or after failures), a replanner can adjust the remaining plan. This pattern handles 10+ step workflows more reliably than ReAct because the LLM does not need to hold the entire plan in its working memory during execution.

## LangGraph Patterns: State Machines for LLM Workflows

LangGraph is a framework for building LLM applications as state machines (or more precisely, as directed graphs with cycles). It sits at the orchestration layer and is particularly well-suited for agent workflows, multi-step generation pipelines, and any LLM application where the control flow is not a simple chain.

### Why State Machines for LLM Apps

LLM workflows are inherently stateful and branching. A chatbot might need to:
- Route between different handling strategies based on intent
- Loop through multiple tool calls
- Retry on failure
- Wait for human approval
- Fork into parallel sub-tasks

Traditional chain-based approaches (like basic LangChain) struggle with these patterns because they assume a linear flow. LangGraph models the workflow as a graph where nodes are processing steps and edges define transitions (which can be conditional).

### Conditional Routing

Conditional routing is the simplest LangGraph pattern. Based on the current state, the graph routes to different nodes.

```python
from langgraph.graph import StateGraph

# Define the graph
graph = StateGraph(AgentState)

# Add nodes
graph.add_node("classify", classify_intent)
graph.add_node("handle_question", answer_question)
graph.add_node("handle_action", execute_action)
graph.add_node("handle_smalltalk", respond_casual)

# Add conditional routing
graph.add_conditional_edges(
    "classify",
    route_by_intent,  # Returns "question", "action", or "smalltalk"
    {
        "question": "handle_question",
        "action": "handle_action",
        "smalltalk": "handle_smalltalk",
    }
)

graph.set_entry_point("classify")
```

This pattern is useful for chatbots that need to handle multiple types of requests differently (questions vs. commands vs. casual conversation).

### Tool Execution Loops

The most common LangGraph pattern is a tool execution loop: the LLM generates a response, and if it contains tool calls, those tools are executed and the results are fed back into the LLM. The loop continues until the LLM produces a response without tool calls.

```
             ┌───────────────┐
             │   Entry       │
             │   Point       │
             └───────┬───────┘
                     │
                     ▼
             ┌───────────────┐
        ┌───▶│   LLM Node    │
        │    │               │
        │    │  Generate     │
        │    │  response     │
        │    └───────┬───────┘
        │            │
        │    ┌───────▼───────┐
        │    │  Has tool     │
        │    │  calls?       │
        │    └───┬───────┬───┘
        │        │       │
        │       Yes      No
        │        │       │
        │  ┌─────▼────┐  │
        │  │ Execute   │  │
        │  │ Tools     │  │
        │  └─────┬─────┘  │
        │        │        │
        └────────┘        │
                          ▼
                  ┌───────────────┐
                  │   Finalize    │
                  │   + Return    │
                  └───────────────┘
```

```python
def route_tool_decision(state):
    """Check if the LLM wants to call tools."""
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

This is the exact pattern that InfraSketch uses internally. When a user asks the AI to modify a system architecture diagram, LangGraph orchestrates the loop: Claude decides which tools to call (add_node, delete_node, update_node, add_edge, etc.), the tools execute against the diagram state, and the results feed back into Claude until it is satisfied with the modifications.

### Human-in-the-Loop

LangGraph supports interrupting a workflow to wait for human input. This is essential for approval workflows, content moderation, and high-stakes actions.

```python
from langgraph.checkpoint.memory import MemorySaver

# Create graph with checkpointing
checkpointer = MemorySaver()
app = graph.compile(
    checkpointer=checkpointer,
    interrupt_before=["execute_dangerous_action"]
)

# Run until interrupt
result = app.invoke(input, config={"configurable": {"thread_id": "1"}})
# Graph pauses before "execute_dangerous_action"

# After human approves, resume
result = app.invoke(None, config={"configurable": {"thread_id": "1"}})
```

The graph state is checkpointed before the interruption point. After human approval, execution resumes from exactly where it left off. This pattern extends naturally to multi-agent systems where different agents handle different parts of a workflow and humans oversee critical decisions.

For more LangGraph system design examples and real-world patterns, see our upcoming guide on [Agentic AI System Architecture](/blog/agentic-ai-system-architecture).

## Scaling LLM Applications

Scaling LLM applications is fundamentally different from scaling traditional web services. The bottleneck is not CPU or memory but rather the LLM API itself: its latency, throughput limits, and per-token costs.

### Prompt Caching

Prompt caching is one of the highest-impact optimizations available. If many requests share the same system prompt or context prefix, caching avoids re-processing those tokens on every call.

**Anthropic's prompt caching** (available for Claude) automatically caches prompt prefixes. If your system prompt is 5,000 tokens and every request includes it, prompt caching reduces that cost by up to 90% after the first request.

```python
# Structure prompts for optimal caching:
# Static prefix (cacheable) + dynamic suffix (varies per request)

messages = [
    {
        "role": "system",
        "content": LONG_SYSTEM_PROMPT  # 5000 tokens, cached after first call
    },
    {
        "role": "user",
        "content": f"Context: {retrieved_documents}\n\nQuestion: {user_query}"
    }
]
```

The key is structuring your prompts so the static portion comes first. System prompts, tool definitions, and few-shot examples should precede the dynamic content (retrieved documents, user query, conversation history).

### Request Batching

For offline or near-real-time workloads (document processing, batch analysis, content generation), batching requests reduces overhead and often qualifies for lower API pricing.

```
┌────────────┐     ┌──────────────┐     ┌────────────┐
│  Request   │────▶│    Batch     │────▶│  LLM API   │
│  Queue     │     │  Aggregator  │     │  (Batch    │
│            │     │              │     │   Mode)    │
│ request 1  │     │ Collect N    │     │            │
│ request 2  │     │ requests or  │     │ Process    │
│ request 3  │     │ wait T secs  │     │ all at     │
│ ...        │     │              │     │ once       │
└────────────┘     └──────────────┘     └────────────┘
```

Anthropic's Message Batches API, for example, offers 50% cost reduction for batch requests that can tolerate up to 24-hour processing times.

### Model Routing

Not every request needs your most expensive model. Model routing sends simple queries to faster, cheaper models and reserves powerful models for complex tasks.

```python
def route_to_model(query, context):
    """Route based on query complexity."""
    # Use a cheap classifier or heuristics
    complexity = assess_complexity(query, context)

    if complexity == "simple":
        return "claude-haiku-4-5"     # $1/M input, fast
    elif complexity == "medium":
        return "claude-sonnet-4-5"    # $3/M input, balanced
    else:
        return "claude-opus-4-5"      # $15/M input, maximum quality
```

Model routing can reduce costs by 50-80% with minimal quality impact, because the majority of requests in most applications are simple enough for a smaller model.

### Cost Management Strategies

| Strategy | Cost Reduction | Implementation Effort | Impact on Quality |
|----------|---------------|----------------------|-------------------|
| Prompt caching | 30-90% on cached tokens | Low | None |
| Model routing | 50-80% | Medium | Minimal if done well |
| Shorter prompts | 20-50% | Medium | Varies |
| Request batching | 50% | Low | Latency increase |
| Output length limits | 10-40% | Low | May truncate |
| Caching responses | 50-90% for repeated queries | Medium | None for exact matches |

**Token budgeting** is essential for production systems. Set per-user, per-session, and per-organization token limits. Track usage in real-time and implement graceful degradation (switch to cheaper models or shorter responses) as limits approach.

## Observability for LLM Systems

LLM applications are difficult to debug without proper observability. The nondeterministic nature of model outputs means you cannot rely on unit tests alone. You need comprehensive tracing, evaluation, and monitoring.

### Tracing

Every LLM interaction should produce a trace that captures:

- The full prompt (system message, context, user query)
- The model's raw response (including tool calls)
- Token counts (input, output, cached)
- Latency (time to first token, total time)
- Cost (calculated from token counts and model pricing)
- Tool execution results
- Any errors or retries

**LangSmith** (from LangChain) is the most popular tracing tool for LLM applications. It integrates directly with LangGraph and LangChain, capturing traces automatically. For custom stacks, OpenTelemetry-based solutions and tools like Weights and Biases Weave and Braintrust also work.

```
┌──────────────────────────────────────────────────┐
│                  Trace Example                    │
│                                                  │
│  Request ID: req-abc-123                         │
│  User: "Update the database node to use Aurora"  │
│  Session: sess-xyz-789                           │
│                                                  │
│  ├── Prompt Assembly         12ms                │
│  │   ├── Tokens: 3,421 input                    │
│  │   └── Context: 5 nodes, 4 edges              │
│  │                                               │
│  ├── LLM Call (Claude)       2,341ms             │
│  │   ├── Model: claude-haiku-4-5                 │
│  │   ├── Output tokens: 287                      │
│  │   ├── Tool calls: 1                           │
│  │   └── Cost: $0.0048                           │
│  │                                               │
│  ├── Tool: update_node       8ms                 │
│  │   ├── Node: "database-1"                      │
│  │   ├── Changes: {technology: "Amazon Aurora"}  │
│  │   └── Result: success                         │
│  │                                               │
│  ├── LLM Call (Claude)       1,892ms             │
│  │   ├── Output tokens: 156                      │
│  │   ├── Tool calls: 0                           │
│  │   └── Cost: $0.0031                           │
│  │                                               │
│  └── Total                   4,253ms             │
│      └── Total cost: $0.0079                     │
└──────────────────────────────────────────────────┘
```

### Evaluation and Quality Metrics

LLM outputs cannot be validated with simple assertions. You need evaluation frameworks that can assess quality along multiple dimensions.

**Automated evaluation metrics:**
- **Relevance.** Does the response answer the user's question? (LLM-as-judge)
- **Faithfulness.** Is the response grounded in the provided context? (For RAG systems)
- **Harmfulness.** Does the response contain unsafe content? (Safety classifier)
- **Format compliance.** Does the response follow the expected structure? (Regex or schema validation)
- **Tool accuracy.** Did the model call the right tools with correct arguments? (Deterministic check)

**Human evaluation** remains the gold standard. Build feedback mechanisms into your application (thumbs up/down, detailed ratings) and use the data to identify failure modes and improve prompts.

**Evaluation datasets** (also called "evals") are curated sets of inputs with expected outputs. Run your system against evals on every prompt change, model upgrade, or system modification. This is the LLM equivalent of a regression test suite.

### Cost Tracking

Track token usage and costs at multiple granularities:

- **Per request.** For debugging and optimization.
- **Per user.** For billing and abuse detection.
- **Per feature.** To understand which features are most expensive.
- **Per model.** To evaluate model routing effectiveness.
- **Per day/week/month.** For budgeting and trend analysis.

### Latency Monitoring

LLM latency has multiple components, and each needs separate monitoring:

- **Time to first token (TTFT).** How long before the user sees the first character. Critical for streaming UX.
- **Tokens per second (TPS).** The rate of output generation. Affects perceived speed.
- **Total latency.** End-to-end time including all tool calls and LLM iterations.
- **Queue time.** Time spent waiting for API rate limits or quota.

Set alerts on P50, P95, and P99 latency. LLM API performance can degrade during peak hours, and you want to know before your users tell you.

## Case Study: How InfraSketch Uses LangGraph and Claude

InfraSketch is an AI-powered system design tool that generates architecture diagrams from natural language descriptions. It is a real-world example of many of the patterns described in this guide, and since it is built on LangGraph and Claude (from Anthropic), we can share some specifics.

### The Architecture

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐
│   React      │────▶│   FastAPI       │────▶│   LangGraph      │
│   Frontend   │     │   Backend       │     │   Agent          │
│              │     │                 │     │                  │
│ - React Flow │     │ - Session mgmt  │     │ - State machine  │
│ - Chat panel │     │ - Auth (Clerk)  │     │ - Tool calling   │
│ - Design doc │     │ - Async tasks   │     │ - Claude API     │
└──────────────┘     └─────────────────┘     └──────────────────┘
                            │                        │
                     ┌──────▼───────┐         ┌──────▼───────┐
                     │  DynamoDB    │         │  Claude      │
                     │  Sessions    │         │  (Anthropic) │
                     └──────────────┘         └──────────────┘
```

When a user describes a system (e.g., "Design a real-time chat application with WebSocket servers, Redis pub/sub, and PostgreSQL"), the request flow is:

1. The frontend sends the prompt to the FastAPI backend.
2. The backend creates a session and triggers an async background task (necessary because complex diagrams can take 30-60+ seconds, exceeding API Gateway timeouts).
3. The frontend polls for status every 2 seconds.
4. The background task runs a LangGraph agent that calls Claude with a structured system prompt and tool definitions.
5. Claude returns tool calls (add_node, add_edge, etc.) that build the diagram incrementally.
6. LangGraph executes the tools, feeds results back to Claude, and loops until Claude is done.
7. The final diagram state is saved and returned to the frontend.

For conversational modifications (when a user clicks a node and says "change this to a managed service"), the same LangGraph tool-calling loop runs, but with the existing diagram as context. Claude can surgically update individual nodes, add or remove edges, and modify the design document, all through structured tool calls rather than regenerating the entire diagram.

This architecture is a direct application of the tool execution loop pattern described in the LangGraph section above. The key design decisions were:

- **Async generation** to handle long-running LLM calls without timeouts.
- **Native tool calling** instead of asking Claude to output JSON, for reliability and type safety.
- **State machine orchestration** via LangGraph, enabling the tool-call loop with clean separation between routing logic, LLM calls, and tool execution.
- **Session-based state** stored in DynamoDB, allowing users to return to previous designs.

If you want to try building system architectures with AI assistance, [give InfraSketch a try](/tools/system-design-tool). It is a practical example of LLM system design architecture in action.

## Putting It All Together: Reference Architecture

Here is a reference architecture for a production-grade LLM application that combines RAG, tool calling, and agent patterns.

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Client Applications                              │
│           Web App    Mobile App    CLI    API Consumers               │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │  API Gateway │
                    │  + Auth      │
                    │  + Rate Limit│
                    └──────┬──────┘
                           │
┌──────────────────────────▼──────────────────────────────────────────┐
│                     Orchestration Service                            │
│                                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  Input      │  │  Intent      │  │  Context     │              │
│  │  Guardrails │─▶│  Router      │─▶│  Assembly    │              │
│  └─────────────┘  └──────────────┘  └──────┬───────┘              │
│                                            │                       │
│                        ┌───────────────────┼───────────────────┐   │
│                        │                   │                   │   │
│                 ┌──────▼──────┐  ┌────────▼────────┐  ┌──────▼──┐│
│                 │  RAG        │  │  Agent           │  │  Direct ││
│                 │  Pipeline   │  │  (Tool calling)  │  │  LLM    ││
│                 │             │  │                  │  │  Call    ││
│                 │ Retrieve    │  │ ReAct loop       │  │         ││
│                 │ Rerank      │  │ Plan-execute     │  │ Simple  ││
│                 │ Generate    │  │ Multi-step       │  │ queries ││
│                 └──────┬──────┘  └────────┬────────┘  └────┬────┘│
│                        │                   │                │     │
│                        └───────────────────┼────────────────┘     │
│                                            │                      │
│                                    ┌───────▼───────┐              │
│                                    │  Output       │              │
│                                    │  Guardrails   │              │
│                                    └───────┬───────┘              │
│                                            │                      │
└────────────────────────────────────────────┼──────────────────────┘
                                             │
          ┌──────────────┬───────────────────┼──────────────────┐
          │              │                   │                  │
   ┌──────▼──────┐ ┌────▼─────┐  ┌─────────▼────────┐  ┌─────▼──────┐
   │  Vector DB  │ │  LLM     │  │  Tool Registry   │  │  Session   │
   │             │ │  APIs    │  │                  │  │  Store     │
   │  Pinecone   │ │          │  │  - DB queries    │  │            │
   │  pgvector   │ │  Claude  │  │  - API calls     │  │  DynamoDB  │
   │  Weaviate   │ │  GPT-4   │  │  - Search        │  │  Redis     │
   │             │ │  Gemini  │  │  - Compute       │  │  Postgres  │
   └─────────────┘ └──────────┘  └──────────────────┘  └────────────┘

          ┌──────────────────────────────────────────────────┐
          │              Observability Layer                  │
          │                                                  │
          │  Traces    Metrics    Evals    Cost    Alerts    │
          │  (LangSmith, OpenTelemetry, CloudWatch)          │
          └──────────────────────────────────────────────────┘
```

This architecture supports all the patterns covered in this guide:

- **RAG** for knowledge-grounded responses
- **Tool calling** for taking actions
- **Model routing** for cost optimization
- **Guardrails** for safety and quality
- **Observability** for debugging and monitoring
- **Session management** for conversational context

## Key Takeaways

Building production LLM applications requires thoughtful system design across every layer of the stack. Here are the core principles to keep in mind:

**Start simple, add complexity as needed.** Begin with a direct LLM call. Add RAG when the model needs external knowledge. Add tool calling when it needs to take actions. Add agent patterns when it needs multi-step reasoning. Each layer adds complexity and potential failure modes.

**Design for latency.** LLM calls are slow. Use async patterns, streaming, and background tasks to keep your application responsive. Never make a user wait synchronously for a complex LLM workflow.

**Invest in observability early.** Tracing, evaluation, and cost tracking are not luxuries. Without them, you cannot debug production issues, optimize costs, or measure quality improvements.

**Choose your vector database based on your existing stack.** If you are already on PostgreSQL, start with pgvector. If you need a managed solution at scale, evaluate Pinecone or Qdrant. Do not over-engineer your data layer before you have validated your RAG pipeline's retrieval quality.

**Use state machines for complex workflows.** LangGraph and similar frameworks provide the control flow primitives you need for agent loops, conditional routing, and human-in-the-loop patterns. They are significantly easier to debug than ad-hoc chain implementations.

**Budget for tokens, not just compute.** LLM costs scale with usage in ways that are fundamentally different from traditional infrastructure. Implement model routing, prompt caching, and token budgets from day one.

For more architectural patterns and guides, explore our series on [Machine Learning System Design Patterns](/blog/ml-system-design-patterns), [Event-Driven Architecture Patterns](/blog/event-driven-architecture-patterns), and the [Complete Guide to System Design](/blog/complete-guide-system-design).

Ready to design your own LLM-powered architecture? [Try InfraSketch](/) to generate system architecture diagrams from natural language descriptions. Describe your system, and the AI will produce a complete architecture diagram with components, connections, and a design document you can iterate on.

---

## Related Resources

- [Machine Learning System Design Patterns](/blog/ml-system-design-patterns)
- [Agentic AI System Architecture](/blog/agentic-ai-system-architecture)
- [Vector Database System Design](/blog/vector-database-system-design)
- [Real-World AI System Architecture](/blog/real-world-ai-system-architecture)
- [Event-Driven Architecture Patterns](/blog/event-driven-architecture-patterns)
- [The Complete Guide to System Design](/blog/complete-guide-system-design)
