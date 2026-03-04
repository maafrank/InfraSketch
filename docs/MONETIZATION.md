# InfraSketch Monetization Strategy

## Business Model Overview

InfraSketch uses a **freemium model** with credit-based premium features. Users can create and edit diagrams for free, but advanced features require an account and credits.

---

## Tier Comparison

### 🆓 Free Tier (No Account Required)

**What's Included:**
- ✅ Create unlimited diagrams
- ✅ Edit diagrams with AI chat
- ✅ Add/delete/modify nodes and edges
- ✅ Auto-layout and visualization
- ✅ Real-time collaboration features
- ✅ Basic model (Claude Haiku 4.5)

**Limitations:**
- ❌ Cannot export diagrams (PNG, PDF, Markdown)
- ❌ Cannot generate boilerplate code
- ❌ Cannot upgrade to better AI models
- ❌ Sessions expire (not persisted)
- ❌ Limited to current session only

**Value Proposition:** Try before you buy. Users can fully experience the core product and validate it solves their problem before paying.

---

### ⭐ Premium Tier (Account + Credits)

**Additional Features:**
- ✅ Export to PNG/PDF/Markdown
- ✅ Generate boilerplate code for nodes
- ✅ Upgrade to Sonnet 4.5 or Opus models
- ✅ Persistent session storage
- ✅ Save/load diagram library
- ✅ Version history (future)
- ✅ Team collaboration (future)

---

## Credit System

### Credit Pricing

| Feature | Credit Cost | Notes |
|---------|-------------|-------|
| **Export PNG** | 1 credit | Single diagram image |
| **Export PDF** | 3 credits | Full design document |
| **Export Markdown** | 3 credits | Markdown doc + diagram PNG |
| **Export Both (PDF + MD)** | 5 credits | Bundle discount |
| **Generate Code (1 node)** | 5 credits | Technology-specific boilerplate |
| **Generate Code (All nodes)** | 3 credits/node | Bulk discount (40% off) |
| **Use Sonnet 4.5** | 3x multiplier | Per AI request (generate or chat) |
| **Use Opus** | 10x multiplier | Per AI request (premium quality) |

### Credit Packages

| Package | Price | Credits | Cost per Credit | Bonus |
|---------|-------|---------|-----------------|-------|
| **Starter** | $5 | 100 | $0.05 | - |
| **Pro** | $20 | 500 | $0.04 | 20% more credits |
| **Business** | $50 | 1,500 | $0.033 | 50% more credits |
| **Enterprise** | $200 | 7,000 | $0.029 | 75% more credits |

**Rationale:**
- Low barrier to entry ($5 minimum)
- Clear value scaling for power users
- Bulk discounts incentivize larger purchases

---

## Premium Features - Detailed Specs

### 1. Export System (Gated)

**Current State:**
- Export button exists in UI
- Generates design docs via `/api/session/{session_id}/export/design-doc`

**Changes Needed:**
- Gate export button behind auth check
- Deduct credits before processing export
- Show "Upgrade to Premium" modal for free users
- Display credit cost preview before export

**User Flow:**
```
User clicks Export → Check if authenticated → Check credit balance →
Preview cost → Confirm → Deduct credits → Generate export → Download
```

---

### 2. Code Generation Feature (New)

**Purpose:** Generate production-ready boilerplate code for diagram nodes.

**Implementation:**
- New endpoint: `POST /api/session/{session_id}/nodes/{node_id}/generate-code`
- New prompt in `prompts.py`: `CODE_GENERATION_PROMPT`
- Uses node type, metadata, and connections to generate code

**Example Outputs by Node Type:**

**API Node → FastAPI Boilerplate**
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class RequestModel(BaseModel):
    # Based on inputs from diagram
    pass

@app.post("/endpoint")
async def handle_request(data: RequestModel):
    # TODO: Implement business logic
    return {"status": "success"}
```

**Database Node → SQLAlchemy Schema**
```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class EntityName(Base):
    __tablename__ = 'entity_name'

    id = Column(Integer, primary_key=True)
    # Based on metadata from diagram
```

**Cache Node → Redis Setup**
```python
import redis
from typing import Optional

redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True
)

def get_cached(key: str) -> Optional[str]:
    return redis_client.get(key)

def set_cached(key: str, value: str, ttl: int = 3600):
    redis_client.setex(key, ttl, value)
```

**UI Components:**
- "Generate Code" button in node context menu
- Code preview modal with syntax highlighting
- Copy to clipboard button
- "Generate All Nodes" bulk action

**Credit Costs:**
- Single node: 5 credits
- All nodes: 3 credits × node_count (bulk discount)

---

### 3. Model Selection (Gated)

**Current State:**
- Hardcoded to Claude Haiku 4.5 in `graph.py`

**Changes Needed:**
- Add `model` parameter to `/api/generate` and `/api/chat` endpoints
- Pass model selection through to `create_llm()` function
- Apply credit multiplier based on model
- Store model preference in user settings (authenticated users only)

**Available Models:**

| Model | Speed | Quality | Cost Multiplier | Use Case |
|-------|-------|---------|-----------------|----------|
| **Haiku 4.5** (default) | ⚡⚡⚡ Fast | ⭐⭐⭐ Good | 1x | Standard diagrams |
| **Sonnet 4.5** | ⚡⚡ Medium | ⭐⭐⭐⭐ Great | 3x | Complex systems |
| **Opus** | ⚡ Slower | ⭐⭐⭐⭐⭐ Best | 10x | Mission-critical architecture |

**UI Components:**
- Model selector dropdown in settings panel
- Real-time credit cost preview ("This request will cost ~15 credits")
- Lock icon on premium models for free users

---

### 4. Persistent Storage (Authenticated Users)

**Database Schema:**

**Users Table:**
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    credit_balance INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);
```

**Saved Diagrams Table:**
```sql
CREATE TABLE diagrams (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    session_id UUID UNIQUE,
    name VARCHAR(255),
    diagram_json JSONB NOT NULL,
    conversation_history JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Transactions Table:**
```sql
CREATE TABLE transactions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    amount INTEGER NOT NULL, -- negative for deductions, positive for purchases
    transaction_type VARCHAR(50), -- 'purchase', 'export_png', 'code_gen', etc.
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**New Endpoints:**
- `POST /api/diagrams/save` - Save current diagram
- `GET /api/diagrams` - List user's saved diagrams
- `GET /api/diagrams/{diagram_id}` - Load specific diagram
- `DELETE /api/diagrams/{diagram_id}` - Delete diagram
- `PATCH /api/diagrams/{diagram_id}` - Update diagram name/data

---

## Authentication System

### Technology Stack
- **JWT Tokens** for stateless authentication
- **bcrypt** for password hashing
- **PostgreSQL** or **SQLite** for user data
- **HTTP-only cookies** for token storage (security)

### Endpoints

**Authentication:**
- `POST /api/auth/signup` - Create account
- `POST /api/auth/login` - Authenticate and get JWT
- `POST /api/auth/logout` - Invalidate token
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/refresh` - Refresh expired token

**Credits:**
- `GET /api/credits/balance` - Get current balance
- `GET /api/credits/history` - Transaction history
- `POST /api/credits/purchase` - Initiate Stripe checkout

### Security Considerations
- Rate limiting on auth endpoints (prevent brute force)
- Email verification (optional, prevents spam)
- Password requirements (min 8 chars, complexity)
- HTTPS only in production
- CORS restricted to frontend domain

---

## Payment Integration

### Stripe Integration

**Flow:**
1. User clicks "Buy Credits" → Select package
2. Frontend calls `POST /api/credits/purchase` with package_id
3. Backend creates Stripe Checkout Session
4. User redirected to Stripe (secure payment form)
5. User completes payment
6. Stripe webhook notifies backend (`/api/webhooks/stripe`)
7. Backend credits user account
8. User redirected back to app with success message

**Webhook Security:**
- Verify Stripe signature on webhook requests
- Idempotent transaction processing (prevent double-credits)
- Log all webhook events for audit trail

**Stripe Products:**
- Create products in Stripe Dashboard for each credit package
- Store mapping in backend config

---

## UI/UX Changes

### New Components Needed

**Authentication:**
- `LoginModal.jsx` - Email/password login form
- `SignupModal.jsx` - Account creation form
- `UserMenu.jsx` - Dropdown with logout, settings, credits
- `CreditBalance.jsx` - Display in header (e.g., "250 credits")

**Monetization:**
- `UpgradePrompt.jsx` - Modal shown when free user clicks premium feature
- `CreditPurchase.jsx` - Modal to buy credit packages
- `ModelSelector.jsx` - Dropdown to choose AI model
- `CodeGeneratorModal.jsx` - Display generated code with syntax highlighting

**User Dashboard:**
- `DiagramLibrary.jsx` - Grid view of saved diagrams
- `TransactionHistory.jsx` - Credit purchase and usage log

### Updated Components

**ExportButton.jsx:**
- Add auth check before allowing export
- Show credit cost and balance
- Disable if insufficient credits
- Show upgrade prompt for free users

**ChatPanel.jsx:**
- Add model selector (premium users only)
- Show credit cost estimate for request

**CustomNode.jsx:**
- Add "Generate Code" option in context menu
- Show lock icon if user is not premium

---

## Migration Strategy

### Phase 1: Authentication (Week 1-2)
- Set up database and user tables
- Implement JWT auth endpoints
- Add login/signup UI
- Test authentication flow

### Phase 2: Credit System (Week 2-3)
- Add credits table and balance tracking
- Implement credit deduction logic
- Gate export features
- Add credit purchase UI (without Stripe initially)

### Phase 3: Stripe Integration (Week 3-4)
- Set up Stripe account and products
- Implement checkout flow
- Set up webhook endpoint
- Test payment flow (sandbox mode)

### Phase 4: Premium Features (Week 4-6)
- Implement code generation
- Add model selection
- Add persistent storage
- Test all premium features

### Phase 5: Launch (Week 7)
- Migration plan for existing free users
- Marketing email announcing premium tier
- Launch pricing page
- Monitor usage and adjust pricing

---

## Metrics to Track

### Business Metrics
- **Conversion Rate:** Free → Paid users
- **Average Revenue Per User (ARPU)**
- **Credit Burn Rate:** Average credits used per session
- **Churn Rate:** Users who don't return after purchase

### Product Metrics
- **Export Usage:** Which formats are most popular?
- **Code Generation Usage:** Which node types?
- **Model Selection:** Do users upgrade to Sonnet/Opus?
- **Session Duration:** Free vs. paid users

### Technical Metrics
- **API Response Time:** With auth overhead
- **Credit Transaction Failures:** Payment issues
- **Export Success Rate:** PDF generation failures

---

## Pricing Experiments

### A/B Test Ideas
1. **Credit Costs:** Test 1 vs. 2 credits for PNG export
2. **Package Pricing:** $5 starter vs. $10 starter
3. **Model Multipliers:** 3x vs. 5x for Sonnet
4. **Free Trial Credits:** Give new users 10 free credits?

### Pricing Adjustments
- Monitor credit usage patterns
- Adjust costs if features are under/over-utilized
- Introduce promotional packages (holidays, launches)

---

## Future Monetization Ideas

### Subscription Model (Alternative to Credits)
- **Pro Plan:** $15/month - Unlimited exports, code gen, Sonnet access
- **Team Plan:** $50/month - 5 users, shared diagram library
- **Enterprise:** Custom pricing - SSO, dedicated support, on-prem

### Enterprise Features
- **Team Collaboration:** Real-time multi-user editing
- **Version Control:** Git-like branching/merging for diagrams
- **Custom Branding:** White-label exports
- **API Access:** Programmatic diagram generation
- **SSO/SAML:** Enterprise authentication
- **Audit Logs:** Track all changes

### Marketplace
- **Template Library:** Pre-built architecture templates ($1-5 each)
- **Custom Nodes:** Community-built node types
- **Plugins:** Extend functionality (Terraform export, CloudFormation, etc.)

---

## Open Questions

1. **Should we offer a free trial?** (e.g., 50 free credits on signup)
2. **Subscription vs. credits?** Which is better long-term?
3. **Team plans?** Do we need multi-user support at launch?
4. **Refund policy?** For unused credits or failed exports?
5. **Credit expiration?** Should credits expire after 1 year?
6. **Educational discounts?** Student/teacher pricing?

---

## Competitive Analysis

### Competitors
- **Lucidchart:** Subscription ($7.95-$9/user/month)
- **Draw.io:** Free with paid hosting
- **Miro:** Freemium ($8-$16/user/month)
- **Figma:** Freemium ($12-$45/user/month)

### Our Differentiator
- **AI-first:** Generate diagrams from natural language
- **Code generation:** Export boilerplate code
- **Pay-as-you-go:** No recurring subscription (initially)
- **Developer-focused:** Built for technical architecture

---

## Technical Debt / Notes

- [ ] Need to add database migrations system (Alembic?)
- [ ] Consider Redis for session caching (performance)
- [ ] Add retry logic for Stripe webhook failures
- [x] Implement email service (Resend) for receipts and announcements
- [ ] Add analytics (PostHog? Mixpanel?)
- [ ] Set up error monitoring (Sentry?)
- [ ] Create admin dashboard to manage users/credits

---

## Next Steps

1. Review and finalize pricing strategy
2. Choose database (PostgreSQL recommended)
3. Design authentication flow
4. Create wireframes for new UI components
5. Set up Stripe test account
6. Implement Phase 1 (Authentication)

---

**Last Updated:** 2025-11-13
**Document Owner:** Product Team
