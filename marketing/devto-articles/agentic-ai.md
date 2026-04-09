---
title: "Building Multi-Agent AI Systems: Architecture Patterns and Best Practices"
published: true
tags: ai, agents, llm, architecture
canonical_url: https://infrasketch.net/blog/agentic-ai-system-architecture
cover_image: https://infrasketch.net/full-app-with-design-doc.png
---

AI agents have moved from research papers to production systems. Unlike simple chatbots that take a prompt and return an answer, agentic AI systems take autonomous actions, use tools, maintain state across interactions, and iteratively refine their outputs.

This article covers the core architectural patterns you need to build reliable agent systems, from single-agent loops to multi-agent orchestration, with practical code examples and production lessons learned. For the full deep dive, check out the [complete article on InfraSketch](https://infrasketch.net/blog/agentic-ai-system-architecture).

## What Makes an Agent Different from a Chatbot?

A chatbot is a function: input in, output out. An agent is a **loop** with branching logic, tool access, and memory. The key differences:

- **Autonomous action:** The agent decides what to do next, including calling external tools, querying databases, or modifying artifacts.
- **Iterative reasoning:** Instead of producing a final answer in one pass, agents loop through cycles of thought, action, and observation.
- **State persistence:** Agents maintain context across multiple steps and multiple user interactions.
- **Goal-directed behavior:** Agents work toward completing a goal, adjusting their approach based on intermediate results.

That loop needs careful design, because every iteration costs tokens, time, and money, and every branch introduces the possibility of compounding errors.

## Single-Agent Patterns: Start Here

Most production agentic systems today use a single agent with tool access. The complexity lives in how the agent reasons, selects tools, and handles failures.

### Tool-Calling Agents (The Dominant Pattern)

Modern LLMs like Claude, GPT-4, and Gemini support native tool calling. Instead of parsing freeform text for tool invocations, the model returns structured, typed tool calls as part of its response. The runtime executes those tools and feeds results back.

This is the pattern used in production for good reason: no brittle regex parsing, typed parameter validation, parallel tool execution, and built-in self-correction when tools return errors.

The core loop is straightforward:

```python
while True:
    response = llm.invoke(messages, tools=tool_definitions)

    if response.has_tool_calls():
        for tool_call in response.tool_calls:
            result = execute_tool(tool_call.name, tool_call.args)
            messages.append(ToolMessage(result, tool_call.id))
        messages.append(response)
    else:
        return response.content  # Final answer
```

This is exactly how [InfraSketch](https://infrasketch.net) works under the hood. When you ask the AI to modify an architecture diagram, Claude decides which tools to call (`add_node`, `delete_node`, `update_node`, `add_edge`), the runtime executes them, and Claude sees the results to decide if more changes are needed.

![InfraSketch: AI-powered architecture diagram generation](https://infrasketch.net/full-app-with-design-doc.png)

### Plan-and-Execute Agents

For complex tasks with many dependencies, separating planning from execution helps the agent stay on track. The planner LLM creates a step-by-step plan, then an executor runs each step with tool access. If a step fails, a replanner adjusts the remaining plan.

**Trade-off:** More token-expensive (the planning step is an extra LLM call), but prevents the agent from losing track of the overall goal during long tasks.

## Multi-Agent Patterns: When One Agent Is Not Enough

When a single agent becomes overloaded with too many tools, too much context, or too many responsibilities, breaking the system into specialized agents can improve reliability.

### Supervisor Pattern

A supervisor agent receives the user's request, delegates to specialist agents, and synthesizes results:

```
                    +------------------+
                    |   Supervisor     |
                    |   Agent          |
                    +--------+---------+
                             |
              +--------------+--------------+
              v              v              v
     +---------------+ +-----------+ +------------+
     |  Research     | |  Coding   | |  Review    |
     |  Agent        | |  Agent    | |  Agent     |
     +---------------+ +-----------+ +------------+
```

Each agent has a focused context window, a smaller tool set, and a more specific system prompt. This reduces confusion and improves tool selection accuracy. The downside: the supervisor becomes a bottleneck, and inter-agent communication adds latency and cost.

### Hierarchical Agent Teams

A generalization where supervisors themselves have supervisors, creating a tree structure. A top-level manager delegates to team leads, who delegate to individual worker agents. For example, a "Platform Architect" manager might delegate to a Backend Lead, Frontend Lead, and DevOps Lead, each of which manages their own specialist agents for databases, APIs, UI components, CI/CD, and monitoring.

This is useful for very large systems, but it introduces significant overhead. Each level of the hierarchy adds latency and token cost. In practice, most production systems use at most two levels.

### Debate and Adversarial Agents

Two or more agents argue for different solutions, and a judge selects the best one. Valuable for architecture decisions (microservices vs. monolith), code review (generator + critic), and verification. Expensive, but significantly improves output quality for high-stakes decisions.

## State Machines: The Secret to Reliable Agents

If you take one thing from this article, let it be this: model your agent as a state machine, not a freeform loop.

Frameworks like [LangGraph](https://langchain-ai.github.io/langgraph/) model agent workflows as directed graphs. Each node is a processing step (LLM call, tool execution, routing decision), and edges define the transitions between steps. This approach gives you explicit control flow (you can see exactly which states the agent can be in), conditional routing based on deterministic logic rather than LLM reasoning, and composability (graphs can be nested, with sub-graphs handling specific concerns).

```python
@dataclass
class AgentState:
    messages: Annotated[Sequence[AnyMessage], add_messages] = field(
        default_factory=list
    )
    diagram: Optional[dict] = None
    design_doc: Optional[str] = None
    session_id: str = ""
    model: str = "claude-haiku-4-5"
```

The key advantage: **routing logic is deterministic Python code, not LLM reasoning.** After an LLM call, a simple function checks whether the model requested tool calls or produced a final response:

```python
def route_tool_decision(state: AgentState) -> str:
    last_message = state.messages[-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"      # Execute tools, then loop back
    return "finalize"       # No tools needed, wrap up
```

This keeps branching logic testable, debuggable, and predictable. You can write unit tests for your routing functions without ever calling an LLM.

LangGraph also supports checkpointing, which saves the agent's state at each step. If a long-running task fails mid-execution (network errors, model API outages), the workflow can resume from the last successful step rather than starting over. For production systems, persistent checkpointing to SQLite, PostgreSQL, or Redis is essential.

Another powerful pattern is human-in-the-loop approval gates. For high-risk actions (deploying code, deleting data, sending emails), you insert a node in the graph that pauses execution and waits for external approval before continuing. This is straightforward with a state machine and nearly impossible with a freeform loop.

![Conversational refinement of architecture diagrams](https://infrasketch.net/followup-questions.png)

## Tool Design: Where Most Agent Failures Happen

A poorly designed tool interface is the most common source of agent failures. Follow these principles:

**1. Descriptive names and documentation.** The model selects tools based on names and descriptions. `add_node` with a detailed docstring outperforms `tool_7`.

**2. Typed parameters with constraints.** Use enums, ranges, and required/optional markers. The more constrained the parameter space, the fewer errors.

**3. Atomic operations.** Prefer `add_node` + `add_edge` over `add_node_and_connect_it`. Atomic tools compose better and fail more gracefully.

**4. Informative return values.** `{"success": false, "error": "Node 'xyz' not found"}` is far more useful than `{"error": true}`.

**5. Inject context automatically.** If a tool needs a session ID, inject it at the runtime level. Do not ask the LLM to provide it.

```python
# Bad: Agent must provide session_id (easy to hallucinate)
def add_node(node_id: str, label: str, session_id: str) -> dict:
    ...

# Good: Runtime injects session_id automatically
def tools_node(state: AgentState) -> dict:
    for tool_call in last_message.tool_calls:
        tool_call.args["session_id"] = state.session_id  # Injected
        result = execute_tool(tool_call)
```

![Chat-based architecture modification in InfraSketch](https://infrasketch.net/url-shortener-chat-add-loadbalancer.png)

## Production Concerns You Cannot Ignore

### Cost Control

Agent loops are expensive. Each iteration is an LLM call, and complex tasks might take 5-15 iterations. Key strategies:

- **Model routing:** Use a fast model (Claude Haiku) for simple tasks, route complex ones to Claude Sonnet or Opus.
- **Token budgets:** Set maximum limits per agent run. Force a final answer when budget is exhausted.
- **Caching:** Cache tool results within a session. Same query twice? Return the cached result.
- **Early termination:** Detect when an agent is looping without progress and terminate.

### Error Handling and Self-Correction

The difference between a demo and a production agent is failure handling. Differentiate between transient errors (retry with backoff), input errors (feed back to the model for self-correction), and logic errors (re-prompt with additional context).

```python
for attempt in range(max_retries):
    response = llm.invoke(messages, tools=tools)
    if response.has_tool_calls():
        results = execute_tools(response.tool_calls)
        for result in results:
            if result.is_error:
                messages.append(ToolMessage(
                    content=f"Error: {result.error}",
                    tool_call_id=result.id
                ))
            else:
                messages.append(ToolMessage(
                    content=result.output,
                    tool_call_id=result.id
                ))
        messages.append(response)
    else:
        break  # Final answer
```

### Async Execution for Long-Running Tasks

Agent tasks often exceed API gateway timeouts (typically 30 seconds). The solution: start the task, return a task ID immediately, and let the client poll for completion. This is the pattern [InfraSketch](https://infrasketch.net) uses for diagram generation. Complex architecture diagrams can take 30-60 seconds, so the backend returns a session ID immediately and the frontend polls every two seconds until generation completes.

### Safety and Guardrails

Agents that can take actions need constraints. Define action allowlists so each agent only has access to the tools it needs. Apply rate limiting to control how many actions an agent can take per turn. Validate outputs to ensure the agent's final response does not contain harmful content or unintended data leaks. And log every tool call, its arguments, and its result. This audit trail is essential for debugging and compliance.

### Observability

Agent systems are notoriously difficult to debug. When an agent produces a wrong answer, you need to trace through every reasoning step, tool call, and state transition to find the root cause. Essential practices:

- **Structured logging:** Log each step as a structured event with session ID, step type, inputs, outputs, and duration.
- **Trace visualization:** Tools like LangSmith provide visual traces of the full graph traversal with timing at each node.
- **State snapshots:** Log the full agent state at each step so you can reproduce issues exactly.
- **Error categorization:** Classify errors by type (model error, tool error, timeout, validation failure) to identify systemic issues across many sessions.

## Key Takeaways

- **Start with a single agent.** Add agents only when a single agent's context, tools, or responsibilities become too large.
- **Use native tool calling.** It is more reliable and self-correcting than text-based tool invocation.
- **Model your agent as a state machine.** Explicit states and transitions make behavior predictable and testable.
- **Design tools as atomic operations** with informative errors and injected context.
- **Plan for failure.** Build retry, fallback, and validation into your architecture from the start.
- **Invest in observability.** You cannot debug what you cannot see.

---

InfraSketch is itself an agentic AI system built with LangGraph and Claude. Try it free to see these patterns in action, and use it to design your own agent architectures at [https://infrasketch.net](https://infrasketch.net).
