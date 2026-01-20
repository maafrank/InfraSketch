# InfraSketch User Feedback Analysis

*Analysis date: January 2026*

## Source Feedback

> "I can completely relate to the problem you're trying to solve; creating good design documents is challenging. I would love to have a helpful AI to assist with this task."

The user validated the core problem but identified several UX issues that prevent them from paying for the current implementation.

---

## Feedback Items

### 1. Opus 4.5 Missing from Landing Page

**Status**: DONE

**Issue**: Opus 4.5 was available in InputPanel and ChatPanel but missing from the landing page model selector.

**Fix**: Added Opus option to [LandingPage.jsx:376-378](../frontend/src/components/LandingPage.jsx#L376-L378)

---

### 2. Carousel Can't Be Paused

**Status**: DONE

**Issue**: Users wanted to pause the "See It In Action" carousel to explore screenshots in detail.

**Fix**: Added hover-to-pause functionality in [LandingPage.jsx:184-193](../frontend/src/components/LandingPage.jsx#L184-L193)

---

### 3. No Template/Structure to Start With

**Status**: Future Enhancement

**User Quote**: "I would love to start with some kind of template, TOC, or basic structure of the doc. Not with a chat message 'Design a distributed rate limiter for an API gateway handling millions of requests.'"

**Impact**: High - Users with design doc experience want structure first, not a blank prompt.

**Potential Solutions**:

#### Option A: Template Gallery
- Pre-built templates: Web App, Data Pipeline, Microservices, Event-Driven, etc.
- Each template has predefined sections and placeholder content
- User selects template, then customizes via chat

#### Option B: Guided Wizard
- Step-by-step intake form before generation
- Questions: What type of system? What scale? What are the main features?
- Generates structured doc based on answers

#### Option C: Document Outline First
- AI generates TOC/outline before content
- User approves/modifies structure
- AI fills in sections

**Recommended**: Start with Option A (Template Gallery) - lowest complexity, immediate value.

**Files to Modify**:
- Create `frontend/src/components/TemplateGallery.jsx`
- Add template data: `frontend/src/data/templates.js`
- Modify `App.jsx` to show gallery before generation

---

### 4. Agent Doesn't Ask Clarifying Questions

**Status**: Ready to Implement

**User Quote**: "'Design a distributed rate limiter' is super generic, and it's better for the Agent not to continue before you clarify some details."

**Impact**: High - Generic prompts produce generic diagrams that don't match user needs.

**Solution**: Smart Clarifying Questions Flow

#### How It Works

```
User prompt --> POST /generate
                    |
    +---------------+---------------+
    |                               |
Prompt is SPECIFIC            Prompt is GENERIC
(mentions scale, tech,        (high-level concept
constraints)                   without details)
    |                               |
Generate immediately         Return 2-3 questions
Poll /diagram/status              |
    |                         Show in chat
Render diagram                    |
                             User answers (or skips)
                                  |
                             POST /clarify
                                  |
                             Generate with context
                                  |
                             Render diagram
```

#### What Makes a Prompt Specific vs Generic?

**SPECIFIC** (no questions needed):
- "Design a rate limiter using Redis with 10K req/s capacity"
- "E-commerce checkout with PostgreSQL, Stripe, and eventual consistency"
- "Real-time chat with WebSocket, 1M concurrent users, message persistence"

**GENERIC** (needs clarification):
- "Design a rate limiter"
- "Build a chat application"
- "Create a social media platform"

#### Question Types

Questions should be about factors that **actually change the architecture**:

1. **Scale**: "What request volume do you expect?" → Affects sharding, caching, load balancing
2. **Consistency**: "Do you need real-time or eventual consistency?" → Affects database choices
3. **Latency**: "What's your target response time?" → Affects architecture patterns
4. **Technology preferences**: "Any required technologies or constraints?"

#### User Control

- **Smart opt-out**: AI decides, user can skip
- **User toggle**: Checkbox "Always skip clarifying questions" (stored in localStorage)

#### Implementation Details

**New Backend Files**:
- `backend/app/agent/clarification.py` - Analysis logic
- Add `CLARIFICATION_PROMPT` to `prompts.py`

**Backend Changes**:
- `models.py`: Add `ClarificationQuestion`, `ClarifyRequest` models
- `routes.py`: Modify `/generate` to analyze first, add `/clarify` endpoint
- `manager.py`: Add clarification fields to session state

**Frontend Changes**:
- `client.js`: Add `submitClarificationAnswers()`
- `App.jsx`: Add clarification state and flow
- Create `ClarificationQuestions.jsx` component
- `ChatPanel.jsx`: Render questions inline
- `LandingPage.jsx`: Add skip toggle

**Prompt for Analysis**:
```python
CLARIFICATION_PROMPT = """Analyze this system design request.

User's request: {prompt}

If GENERIC (no scale, tech, constraints), generate 2-3 questions that would
CHANGE the architecture:
- Scale (affects sharding, caching, load balancing)
- Consistency (affects database choices)
- Latency (affects architecture patterns)

If SPECIFIC (mentions scale, technologies, constraints), no clarification needed.

Output JSON only:
{"needs_clarification": bool, "questions": [...], "reason": str}
"""
```

---

### 5. Generic Diagrams, No Diagram Type Variety

**Status**: Future Enhancement

**User Quote**: "When we describe architectural decisions, we usually use various types of diagrams with different purposes (something like 'Domain Model', 'Data Model', 'Components and Structure', 'Information & Data Flow', etc.)"

**Impact**: High - Professional architects use different diagram types for different purposes.

**Potential Solutions**:

#### Option A: Diagram Type Selector
- Let user choose: Component, Data Flow, Sequence, Deployment, etc.
- Each type has different node types and layout rules
- System prompts tailored per diagram type

#### Option B: Multi-View System
- Generate multiple diagram views from same system description
- Component view, data flow view, deployment view
- User switches between views

**Recommended**: Option A first - simpler, lets users pick what they need.

**Complexity**: High - requires new prompts, node types, and possibly layout algorithms per diagram type.

---

### 6. Chat Explanations Don't Persist

**Status**: Future Enhancement

**User Quote**: "For instance, I ask clarifying questions about some component. Does this 'explanation' from the agent go anywhere? It's not clear."

**Impact**: High - Valuable context gets lost in chat, not captured in documentation.

**Solution**: Auto-update design doc when explaining components

#### How It Works

When user asks about a component and bot provides detailed explanation:
1. Bot responds in chat (immediate feedback)
2. Bot also calls `update_design_doc_section` to capture explanation
3. Design doc section for that component gets enriched

#### Implementation

**Prompt Update** (in `prompts.py` CONVERSATION_PROMPT):
```
When you explain a component's purpose, implementation details, or design
rationale in substantial detail (>100 words), also update the corresponding
section of the design document using update_design_doc_section to capture
this explanation permanently.
```

**Files to Modify**:
- `backend/app/agent/prompts.py` - Add instruction to conversation prompt

---

### 7. Design Doc Should Be Source of Truth

**Status**: Future Enhancement (Architectural Change)

**User Quote**: "Diagram is your source of truth, as I understand it. I would suggest making the canvas with the design document your source of truth, and building all activities around it."

**Impact**: High - This is a fundamental architecture shift.

**Current Model**:
```
User Prompt → Diagram (source of truth) → Design Doc (derived)
```

**Proposed Model**:
```
User Prompt → Design Doc (source of truth) → Diagram (visualization)
```

#### Why This Matters

- Design docs capture WHY decisions were made, not just WHAT
- Diagrams are a view of the design, not the design itself
- Professional architects work from documents, reference diagrams

#### Implementation Approach

1. **Phase 1**: Generate outline/structure first (ties into #3)
2. **Phase 2**: Generate design doc content with embedded diagram specs
3. **Phase 3**: Render diagram FROM design doc sections
4. **Phase 4**: Changes to design doc update diagram automatically

**Complexity**: Very High - requires rethinking the entire data flow.

**Recommendation**: Tackle incrementally. Start with #3 (templates) and #4 (clarifying questions) to get user into a structured flow, then evolve toward doc-first model.

---

## Priority Matrix

| Item | User Impact | Implementation Effort | Priority |
|------|-------------|----------------------|----------|
| 1. Opus 4.5 on landing | Low | Low | **DONE** |
| 2. Carousel pause | Medium | Low | **DONE** |
| 4. Clarifying questions | High | Medium | **P1** |
| 3. Templates/structure | High | Medium | **P2** |
| 6. Explanation persistence | High | Low | **P2** |
| 5. Diagram type variety | High | High | **P3** |
| 7. Doc as source of truth | High | Very High | **P4** |

---

## Recommended Implementation Order

### Phase 1: Clarifying Questions (Item #4)
This addresses the most frustrating part of the current experience: generic prompts producing generic results. It's medium effort with high impact.

### Phase 2: Templates + Explanation Persistence (Items #3, #6)
Templates give users structure. Explanation persistence ensures chat value is captured. Both are medium effort.

### Phase 3: Diagram Types (Item #5)
Once users have structure and context, offer different visualization types.

### Phase 4: Doc-First Architecture (Item #7)
Long-term architectural evolution. Consider after validating that users value the doc more than the diagram.

---

## Key Insight

> "At the end of the day, the painpoint is real, but I personally would not pay for the current implementation. I always compare what I can do in my Claude Code setup (with all skills, templates, and plugins already there)."

The competition isn't other design doc tools - it's Claude Code with custom prompts. To win:
1. **Structure**: Provide the templates and structure users would otherwise build themselves
2. **Context**: Ask the right questions before generating
3. **Persistence**: Make sure valuable explanations don't disappear into chat
4. **Professional workflow**: Support how architects actually work (doc-first, multiple diagram types)
