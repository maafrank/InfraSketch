# Agentic AI System Architecture: Designing Multi-Agent Systems

The term "AI agent" has quickly moved from research papers to production systems. Unlike simple chatbots that respond to a single prompt and return a single answer, agentic AI systems take autonomous actions, use tools, maintain state across interactions, and iteratively refine their outputs. They reason about what to do, execute a plan, observe the results, and adjust course.

This guide covers the architectural patterns behind agentic AI systems, from single-agent loops to multi-agent orchestration. Whether you are building a code assistant, an autonomous research tool, or (as we did with [InfraSketch](/tools/system-design-tool)) a system design agent that generates and modifies architecture diagrams, these patterns form the foundation you need to understand.

## What Is Agentic AI?

A traditional LLM interaction is stateless and one-shot: you send a prompt, you get a response. An agentic AI system breaks that constraint in several important ways:

- **Autonomous action:** The agent decides what to do next, including calling external tools, querying databases, or modifying artifacts.
- **Iterative reasoning:** Instead of producing a final answer in one pass, agents loop through cycles of thought, action, and observation.
- **State persistence:** Agents maintain context across multiple steps within a task and, often, across multiple user interactions.
- **Goal-directed behavior:** Rather than answering a question, agents work toward completing a goal, adjusting their approach based on intermediate results.

The shift from "chatbot" to "agent" is fundamentally an architectural shift. A chatbot is a function: input goes in, output comes out. An agent is a loop with branching logic, tool access, and memory. That loop needs to be designed carefully, because every iteration costs tokens, time, and money, and every branch introduces the possibility of errors that compound.

## Single-Agent Architectures

Most production agentic systems today use a single agent with tool access. The complexity lives in how the agent reasons, selects tools, and handles failures.

### The ReAct Pattern (Reason + Act)

The ReAct pattern, introduced by Yao et al. in 2022, interleaves reasoning steps with action steps. The agent thinks about what it should do (Reason), takes an action (Act), observes the result, and then reasons again.

```
┌──────────────────────────────────────────────────┐
│                   ReAct Loop                     │
│                                                  │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│   │ Thought  │───>│  Action  │───>│Observation│  │
│   │ (Reason) │    │  (Tool)  │    │ (Result)  │  │
│   └──────────┘    └──────────┘    └──────────┘  │
│        ^                               │         │
│        │          ┌──────────┐         │         │
│        └──────────│  Check:  │<────────┘         │
│                   │  Done?   │                   │
│                   └──────────┘                   │
│                        │                         │
│                   (yes)│                          │
│                        v                         │
│                  ┌───────────┐                   │
│                  │  Answer   │                   │
│                  └───────────┘                   │
└──────────────────────────────────────────────────┘
```

**Strengths:** Interpretable (you can read the agent's reasoning), naturally handles multi-step problems, and self-corrects when an action fails.

**Weaknesses:** Verbose (each reasoning step consumes tokens), can get stuck in loops, and the quality of reasoning depends heavily on the model.

### Tool-Calling Agents (Function Calling API)

Modern LLMs like Claude, GPT-4, and Gemini support native tool calling (also called function calling). Instead of the agent writing freeform text that you parse for tool invocations, the model returns structured tool calls as part of its response. The runtime executes those tools and feeds the results back to the model.

This is the dominant pattern in production systems today for good reason:

- **Reliability:** No regex parsing or brittle JSON extraction. The model returns typed, validated tool calls.
- **Type safety:** Tool parameters have schemas. Invalid arguments are caught before execution.
- **Parallel execution:** The model can request multiple tool calls in a single response.
- **Self-correction:** If a tool returns an error, the model sees that error and can retry with corrected arguments.

```
┌─────────────────────────────────────────────────────┐
│              Tool-Calling Agent Loop                 │
│                                                     │
│   ┌──────────┐    ┌──────────────┐    ┌──────────┐ │
│   │   User   │───>│  LLM with    │───>│  Router  │ │
│   │  Prompt  │    │  Tool Defs   │    │          │ │
│   └──────────┘    └──────────────┘    └──────────┘ │
│                                        /        \   │
│                              (tools)  /    (text) \ │
│                                      v             v│
│                              ┌──────────┐  ┌──────┐│
│                              │ Execute  │  │Return││
│                              │ Tool(s)  │  │Answer││
│                              └──────────┘  └──────┘│
│                                      │              │
│                                      v              │
│                              ┌──────────┐           │
│                              │  Feed    │           │
│                              │  Results │           │
│                              │  to LLM  │──────┐   │
│                              └──────────┘      │   │
│                                                │   │
│                        (back to LLM for        │   │
│                         next decision)─────────┘   │
└─────────────────────────────────────────────────────┘
```

In practice, the tool-calling loop looks like this in pseudocode:

```python
while True:
    response = llm.invoke(messages, tools=tool_definitions)

    if response.has_tool_calls():
        for tool_call in response.tool_calls:
            result = execute_tool(tool_call.name, tool_call.args)
            messages.append(ToolMessage(result, tool_call.id))
        messages.append(response)  # Keep AI message in history
    else:
        return response.content  # Final text answer
```

### Plan-and-Execute Agents

Plan-and-execute agents separate planning from execution. First, the agent creates a step-by-step plan. Then it executes each step, potentially replanning if something goes wrong.

```
┌────────────┐     ┌──────────────────┐     ┌────────────┐
│   Input    │────>│   Planner LLM    │────>│  Plan:     │
│            │     │   (creates plan)  │     │  1. Step A │
└────────────┘     └──────────────────┘     │  2. Step B │
                                            │  3. Step C │
                                            └────────────┘
                                                  │
                                                  v
                                      ┌──────────────────┐
                                      │ Executor (runs   │
                                      │ each step with   │
                                      │ tool access)     │
                                      └──────────────────┘
                                                  │
                                            (if step fails)
                                                  │
                                                  v
                                      ┌──────────────────┐
                                      │  Replanner LLM   │
                                      │  (adjusts plan)  │
                                      └──────────────────┘
```

**When to use:** Complex tasks with many dependencies (research, multi-file code changes, data pipeline construction). The plan provides a roadmap that prevents the agent from losing track of the overall goal.

**Trade-offs:** More token-expensive (planning step is an extra LLM call), and the plan can become stale if the environment changes mid-execution. You need a replanning mechanism to handle this.

## Multi-Agent Patterns

When a single agent becomes overloaded with too many tools, too much context, or too many responsibilities, breaking the system into multiple specialized agents can improve both reliability and performance.

### Supervisor Pattern

A supervisor agent receives the user's request, decides which specialist agent should handle it, delegates the work, and synthesizes the results.

```
                    ┌─────────────────┐
                    │   Supervisor    │
                    │   Agent         │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              v              v              v
     ┌──────────────┐ ┌───────────┐ ┌────────────┐
     │  Research    │ │  Coding   │ │  Review    │
     │  Agent      │ │  Agent    │ │  Agent     │
     └──────────────┘ └───────────┘ └────────────┘
     (web search,    (code gen,    (code review,
      RAG tools)      file tools)   test tools)
```

**How it works:**

1. The supervisor receives a request like "Add authentication to the API."
2. It decides the coding agent should handle implementation and the review agent should verify.
3. The coding agent writes the code using its tools.
4. The review agent examines the output using its tools.
5. The supervisor combines results and responds to the user.

**Advantages:** Each agent has a focused context window, a smaller tool set, and a more specific system prompt. This reduces confusion and improves tool selection accuracy.

**Disadvantages:** The supervisor becomes a bottleneck, and inter-agent communication adds latency and token cost.

### Peer-to-Peer Collaboration

In this pattern, agents communicate directly with each other without a central supervisor. Each agent has its own specialty and can request help from peers.

This pattern works well when agents have clear, non-overlapping responsibilities and need to coordinate (for example, a frontend agent and a backend agent that need to agree on an API contract). However, it is harder to debug and can lead to infinite loops if agents keep deferring to each other.

### Hierarchical Agent Teams

A generalization of the supervisor pattern where supervisors themselves have supervisors, creating a tree structure. A top-level manager delegates to team leads, who delegate to individual worker agents.

```
                       ┌──────────┐
                       │ Manager  │
                       └────┬─────┘
                  ┌─────────┼─────────┐
                  v         v         v
            ┌──────────┐ ┌──────┐ ┌──────────┐
            │ Backend  │ │Front-│ │ DevOps   │
            │ Lead     │ │end   │ │ Lead     │
            └────┬─────┘ │Lead  │ └────┬─────┘
            ┌────┼────┐  └──┬───┘ ┌────┼────┐
            v    v    v     v     v    v    v
           DB  API  Auth  UI   CI/CD  K8s  Mon.
```

This is useful for very large systems but introduces significant overhead. Each level of the hierarchy adds latency and token cost. In practice, most production systems use at most two levels.

### Debate and Adversarial Agents

Two or more agents argue for different solutions, and a judge agent selects the best one (or synthesizes a compromise). This pattern is valuable for:

- **Architecture decisions:** One agent argues for a microservices approach, another for a monolith. A judge evaluates trade-offs.
- **Code review:** A generator agent writes code, a critic agent identifies problems, and the generator revises.
- **Verification:** One agent produces an answer, another tries to find flaws in it.

The adversarial approach is expensive (multiple full LLM calls per decision) but can significantly improve output quality for high-stakes decisions.

## State Management for Agent Systems

Agents need state. They need to know what they have done, what they are doing, and what they should do next. The choice of state management approach has a major impact on reliability, debuggability, and extensibility.

### Why State Machines Work Well

Frameworks like [LangGraph](https://langchain-ai.github.io/langgraph/) model agent workflows as state machines (directed graphs). Each node in the graph is a processing step (an LLM call, a tool execution, a routing decision), and edges define the transitions between steps.

This approach has several advantages over freeform agent loops:

- **Explicit control flow:** You can see exactly which states the agent can be in and which transitions are valid.
- **Conditional routing:** Router functions examine the current state and decide where to go next. This is deterministic logic (not LLM reasoning), so it is fast and predictable.
- **Composability:** Graphs can be nested. A complex agent can be composed of sub-graphs, each handling a specific concern.

A LangGraph state definition might look like this:

```python
from dataclasses import dataclass, field
from typing import Annotated, Sequence, Optional
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages

@dataclass
class AgentState:
    # Messages with automatic history management
    messages: Annotated[Sequence[AnyMessage], add_messages] = field(
        default_factory=list
    )
    # Structured artifacts maintained across turns
    diagram: Optional[dict] = None
    design_doc: Optional[str] = None
    session_id: str = ""
    model: str = "claude-haiku-4-5"
```

The `add_messages` reducer handles message deduplication and ordering automatically. Structured artifacts (like a diagram or document) are stored as direct fields for clarity.

### Conditional Routing Based on Agent Decisions

State machines shine when you need deterministic routing based on agent output. For example, after an LLM call, you might check: did the model request tool calls, or did it produce a final text response?

```python
def route_tool_decision(state: AgentState) -> str:
    last_message = state.messages[-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"      # Execute tools, then loop back
    return "finalize"       # No tools needed, prepare final response
```

This pattern keeps the branching logic out of the LLM prompt and in your application code, where it is testable, debuggable, and deterministic.

### Checkpointing and Resumability

Long-running agent tasks can fail mid-execution (network errors, timeouts, model API outages). Checkpointing saves the agent's state at each step so the workflow can resume from the last successful step rather than starting over.

LangGraph supports this natively with configurable checkpointing backends (in-memory, SQLite, PostgreSQL, Redis). For production systems, persistent checkpointing is essential, especially for tasks that take more than a few seconds.

### Human-in-the-Loop Patterns

Not every agent decision should be autonomous. For high-risk actions (deploying code, deleting data, sending emails), you can insert approval gates into the state machine:

```
LLM Decision ──> Approval Gate ──> Execute Action
                      │
                  (human reviews)
                      │
              ┌───────┴───────┐
              v               v
           Approve         Reject
              │               │
              v               v
         Execute          Return to
         Action           LLM with
                          feedback
```

This is straightforward with a state machine. The "approval gate" is simply a node that pauses execution and waits for external input before transitioning.

## Tool Integration Architecture

Tools are what give agents the ability to act on the world. Designing your tool layer well is critical, because a poorly designed tool interface is the most common source of agent failures.

### Types of Tools

Agents typically interact with several categories of tools:

- **APIs and services:** REST endpoints, GraphQL queries, third-party SaaS APIs
- **Databases:** Read and write operations, schema introspection
- **Code execution sandboxes:** Running generated code safely
- **File systems:** Reading, writing, and searching files
- **Domain-specific tools:** Diagram modification, document editing, infrastructure provisioning

### Tool Design Principles

The quality of your tool definitions directly affects agent performance. Good tool design follows these principles:

1. **Descriptive names and documentation.** The model selects tools based on their names and descriptions. `add_node` with a detailed docstring outperforms `tool_7` with no description.

2. **Typed parameters with constraints.** Use enums, ranges, and required/optional markers. The more constrained the parameter space, the fewer errors the model makes.

3. **Atomic operations.** Each tool should do one thing. Prefer `add_node` plus `add_edge` over `add_node_and_connect_it`, because atomic tools compose better and fail more gracefully.

4. **Informative return values.** Return success/failure, the resulting state, and actionable error messages. `{"success": false, "error": "Node 'xyz' not found"}` is far more useful than `{"error": true}`.

5. **Inject context, do not require agents to provide it.** If a tool needs a session ID or user ID, inject it at the runtime level rather than expecting the LLM to pass it. This eliminates an entire class of errors.

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

### Tool Selection Strategies

When an agent has access to many tools (10+), tool selection accuracy drops. Strategies to mitigate this:

- **Tool grouping:** Only expose relevant tools based on the current state. A "generate" step does not need editing tools.
- **Tool descriptions with examples:** Include usage examples in tool docstrings.
- **Few-shot prompting:** Show the model examples of correct tool usage in the system prompt.
- **Retrieval-based selection:** For very large tool sets (50+), use embedding similarity to retrieve the most relevant tools for each query.

## Error Handling and Self-Correction in Agent Systems

Agents fail. Tools return errors, models hallucinate invalid arguments, and external services go down. The difference between a demo agent and a production agent is how it handles these failures.

### Retry Strategies

Not all errors are the same. Your retry logic should differentiate between:

- **Transient errors** (network timeouts, rate limits): Retry with exponential backoff.
- **Input errors** (invalid tool arguments): Feed the error back to the model and let it correct itself. This is where tool-calling agents excel, because the model can read the error and adjust.
- **Logic errors** (model chose the wrong tool): These require re-prompting or additional context, not simple retries.

```python
# Self-correction loop: model sees its own errors
for attempt in range(max_retries):
    response = llm.invoke(messages, tools=tools)
    if response.has_tool_calls():
        results = execute_tools(response.tool_calls)
        for result in results:
            if result.is_error:
                # Feed error back so model can self-correct
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
        break  # Model gave a final answer
```

### Fallback Behaviors

When an agent repeatedly fails at a task, you need graceful degradation:

- **Model fallback:** If a smaller model fails, retry with a more capable (and more expensive) model.
- **Tool fallback:** If a primary tool is unavailable, switch to an alternative that provides similar functionality.
- **Human escalation:** If the agent cannot complete the task after N attempts, surface the problem to a human.
- **Partial results:** Return what the agent accomplished so far rather than failing entirely.

### Output Validation Loops

For structured outputs (JSON, code, diagrams), validate the output before returning it to the user:

```python
def validated_generation(prompt: str, schema: dict) -> dict:
    for attempt in range(3):
        output = llm.invoke(prompt)
        parsed = try_parse(output, schema)
        if parsed.is_valid:
            return parsed.data
        # Feed validation errors back to model
        prompt += f"\nYour output had errors: {parsed.errors}. Fix them."
    raise GenerationError("Failed after 3 attempts")
```

This pattern is especially valuable for diagram generation, where a malformed JSON response would result in a blank canvas instead of a useful architecture diagram.

## Production Considerations

Moving an agent from a prototype to a production system requires addressing cost, safety, latency, and observability.

### Cost Control

Agent systems can be expensive. Each loop iteration is an LLM call, and complex tasks might require 5 to 15 iterations. Strategies for controlling costs:

- **Model routing:** Use a fast, inexpensive model (like Claude Haiku) for simple tasks, and route complex tasks to a more capable model (like Claude Sonnet or Opus). The routing decision can be made by a lightweight classifier or by simple heuristics (prompt length, task type).
- **Token budgets:** Set maximum token limits per agent run. If the budget is exhausted, force the agent to produce a final answer with whatever progress it has made.
- **Caching:** Cache tool results when possible. If the agent asks for the same database query twice in one session, return the cached result.
- **Early termination:** If the agent is looping without making progress (same tool calls repeated, no state changes), terminate early.

### Safety and Guardrails

Agents that can take actions need constraints:

- **Action allowlists:** Define which tools are available in each context. A chat agent should not have access to a "delete all data" tool.
- **Rate limiting:** Limit how many actions an agent can take per turn and per session.
- **Output filtering:** Validate that the agent's final output does not contain harmful content, PII, or unintended data leaks.
- **Audit logging:** Log every tool call, its arguments, and its result. This is essential for debugging and for compliance.

### Timeout Management

LLM calls and tool executions can take unpredictable amounts of time. In production, you need explicit timeouts at multiple levels:

- **Per-LLM-call timeout:** Prevent a single model call from hanging indefinitely.
- **Per-tool-execution timeout:** External API calls should have aggressive timeouts.
- **Per-task timeout:** The overall agent workflow should have a maximum duration.
- **Async execution:** For tasks that exceed API gateway timeouts (common in cloud deployments), use async patterns. Start the task, return a task ID, and let the client poll for completion. This is the approach used by many production systems, including [InfraSketch](/tools/system-design-tool), where complex diagram generation can take 30 to 60 seconds.

### Observability and Debugging

Agent systems are notoriously difficult to debug. When an agent produces a wrong answer, you need to trace through every reasoning step, tool call, and state transition to find the root cause.

Essential observability practices:

- **Structured logging:** Log each agent step as a structured event with session ID, step type, inputs, outputs, and duration.
- **Trace visualization:** Tools like LangSmith provide visual traces of agent execution, showing the full graph traversal with timing at each node.
- **State snapshots:** Log the full agent state at each step so you can reproduce issues.
- **Error categorization:** Classify errors by type (model error, tool error, timeout, validation failure) to identify systemic issues.

```
Event types for agent observability:
- agent_started        (session_id, model, prompt_length)
- llm_call_completed   (duration_ms, token_count, has_tool_calls)
- tool_executed        (tool_name, args, success, duration_ms)
- route_decision       (from_node, to_node, reason)
- agent_completed      (total_duration_ms, total_tokens, steps)
- agent_error          (error_type, error_message, step)
```

## Case Study: How InfraSketch's Agent Architecture Works

[InfraSketch](/tools/system-design-tool) is an AI-powered system design tool that generates and modifies architecture diagrams through natural language. Its backend is built on LangGraph and Claude (Anthropic's LLM), and it demonstrates many of the patterns discussed in this article in a real production system.

The agent uses a state machine with four nodes: `generate`, `chat`, `tools`, and `finalize`. When a user submits a prompt for a new system design, the `route_intent` function checks whether a diagram already exists. If not, it routes to the `generate` node, which sends the prompt to Claude and parses the returned JSON into a structured diagram (with nodes, edges, and metadata). If a diagram already exists, the request is a conversational modification, and it routes to the `chat` node instead.

The `chat` node is where tool calling happens. Claude receives the current diagram state (including every node ID, label, type, and connection), any focused node context, the design document, and conversation history. It can respond with plain text, or it can invoke tools like `add_node`, `delete_node`, `update_node`, `add_edge`, `delete_edge`, and `update_design_doc_section`. The `route_tool_decision` function then checks: if the response contains tool calls, route to the `tools` node for execution, then loop back to `chat` so Claude can see the results and decide whether more changes are needed. If no tools are called, route to `finalize`. Notably, the runtime injects the `session_id` into every tool call automatically, so Claude never needs to guess or hallucinate session identifiers.

The `finalize` node handles the end of each conversation turn. It syncs the modified diagram and design document state, adds visual indicators to the response (so the frontend knows what changed), and generates follow-up suggestions using a fast Haiku model call. The entire flow, from user message to rendered diagram update, runs asynchronously. For initial diagram generation (which can take 30 to 60 seconds for complex systems), the backend immediately returns a session ID and the frontend polls a status endpoint every two seconds until generation completes. This async pattern avoids API gateway timeouts while keeping the user informed of progress.

This architecture works well in production because it separates concerns cleanly: routing logic is deterministic Python code (not LLM reasoning), tool execution is atomic and type-safe, and the state machine makes the agent's behavior predictable and debuggable. For a deeper look at system design fundamentals, see our [Complete Guide to System Design](/blog/complete-guide-system-design).

## Conclusion

Agentic AI architecture is not a single pattern but a toolkit of composable patterns. Single-agent loops with tool calling cover most production use cases today. Multi-agent systems add value when tasks are complex enough to benefit from specialization. State machines (like those built with LangGraph) provide the control flow, checkpointing, and debuggability that production systems require.

The key principles to keep in mind:

- **Start with a single agent.** Add agents only when a single agent's context window, tool set, or responsibilities become too large.
- **Use native tool calling.** It is more reliable, type-safe, and self-correcting than text-based tool invocation.
- **Model your agent as a state machine.** Explicit states and transitions make agent behavior predictable and testable.
- **Design tools as atomic operations** with informative error messages and injected context.
- **Plan for failure.** Every LLM call can fail, every tool can error, every network request can time out. Build retry, fallback, and validation into your architecture from the start.
- **Invest in observability.** You cannot debug what you cannot see. Structured logging and trace visualization are not optional for production agents.

If you want to see these patterns in action, [try InfraSketch](/tools/system-design-tool) to generate a system architecture diagram from a natural language description. You will be interacting with a LangGraph-powered agent that uses Claude's tool calling to build and iteratively refine your design.

---

## Related Resources

- [The Complete Guide to System Design](/blog/complete-guide-system-design)
- [LLM System Design Architecture](/blog/llm-system-design-architecture)
- [Machine Learning System Design Patterns](/blog/ml-system-design-patterns)
- [Event-Driven Architecture Patterns](/blog/event-driven-architecture-patterns)
