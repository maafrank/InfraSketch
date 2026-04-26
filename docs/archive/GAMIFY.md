# Gamification System for InfraSketch

Full gamification suite: achievements/badges, streaks, XP/levels. Purely cosmetic (no credit integration). Combination visibility: header widget + toasts + settings page section.

---

## Phase 1: Backend Foundation

### New module: `backend/app/gamification/`

**`models.py`** - Pydantic models:
- `UserGamification`: xp_total, level, level_name, current_streak, longest_streak, last_active_date, streak_grace_used, achievements (list), counters (dict), pending_notifications (list)
- `GamificationCounters`: diagrams_generated, chat_messages_sent, design_docs_generated, exports_completed, nodes_added, edges_added, groups_created, groups_collapsed, models_used (list), node_types_used (list), export_formats_used (list), repos_analyzed, sessions_created
- `UnlockedAchievement`: id, unlocked_at
- `PendingNotification`: id, unlocked_at

**`storage.py`** - DynamoDB CRUD (follow exact pattern from `backend/app/user/storage.py`):
- Table: `infrasketch-user-gamification`, partition key: `user_id`, PAY_PER_REQUEST
- DecimalEncoder, convert_floats_to_decimals, _ensure_table_exists, singleton pattern
- Methods: `get_or_create()`, `save()`, `get()`

**`achievements.py`** - Static registry of 32 achievements in 4 categories:

| Category | Count | Examples |
|----------|-------|---------|
| First-time (common) | 7 | First Blueprint, Conversationalist, Documenter, Publisher, Organizer, Foundation Stone, Code Reader |
| Volume (uncommon-legendary) | 15 | Sketcher (5 diagrams), Master Planner (100), AI Whisperer (250 chats), etc. |
| Feature Discovery (epic) | 5 | Full Spectrum (all node types), Format Master (all exports), Model Connoisseur (2+ models) |
| Streaks (rare-legendary) | 5 | Weekly Warrior (7d), Two-Week Titan (14d), Monthly Master (30d), Centurion (100d) |

Each has: id, name, description, rarity (common/uncommon/rare/epic/legendary), category, check function.

**`xp.py`** - XP values and level system:

| Action | XP |
|--------|----|
| Generate diagram | 25 |
| Chat message | 5 |
| Design doc | 30 |
| Export | 10 |
| Add node | 3 |
| Add edge | 2 |
| Create group | 8 |
| Analyze repo | 35 |
| Daily login bonus | 15 |
| Achievement unlock bonus | 50 |

10 levels: Intern (0 XP) -> Junior Designer (50) -> Designer (150) -> Senior Designer (350) -> Architect (600) -> Senior Architect (1000) -> Lead Architect (1600) -> Principal Architect (2500) -> Distinguished Architect (4000) -> Chief Architect (6000)

**`streaks.py`** - Streak logic:
- Any meaningful action counts (not just login)
- One grace day per streak (miss 1 day, streak survives; miss 2, resets)
- UTC date boundaries
- Updates: last_active_date, current_streak, longest_streak, streak_grace_used

**`engine.py`** - Orchestrator: `process_action(user_id, action, metadata) -> dict`
1. Update counters
2. Update streak (award 15 XP if new day)
3. Award action XP
4. Check level-up
5. Check achievements (adds to pending_notifications)
6. Save to DynamoDB
7. Return: `{xp_gained, level_up, new_level, new_level_name, new_achievements, current_streak}`

Runs synchronously after primary operation. Wrapped in try/except (fail silently with logging).

---

## Phase 2: Backend API Endpoints

Add to `backend/app/api/routes.py`:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/user/gamification` | GET | Full gamification state (level, XP, streak, progress to next level, pending notifications) |
| `/api/user/gamification/achievements` | GET | All 32 achievement defs with unlock status + progress bars for locked ones |
| `/api/user/gamification/notifications/dismiss` | POST | Clear pending notifications after user sees toasts |

---

## Phase 3: Backend Integration Hooks

Add `process_action()` calls in `backend/app/api/routes.py` after existing `log_event`/`log_*` calls:

| Location | Action | Metadata |
|----------|--------|----------|
| Diagram generation (background task) | `diagram_generated` | `{node_count, model}` |
| Chat message endpoint | `chat_message` | `{node_id}` |
| Add node endpoint | `node_added` | `{node_type}` |
| Add edge endpoint | `edge_added` | - |
| Create group endpoint | `group_created` | - |
| Collapse group endpoint | `group_collapsed` | - |
| Design doc generation (background task) | `design_doc_generated` | - |
| Export endpoint | `export_completed` | `{format}` |
| Repo analysis endpoint | `repo_analyzed` | - |
| Create session / generate | `session_created` | `{model}` |

Return gamification result as optional `gamification` field on existing API responses.

---

## Phase 4: Frontend Context & API

**`frontend/src/api/client.js`** - Add 3 new functions:
- `getUserGamification()` - GET `/user/gamification`
- `getUserAchievements()` - GET `/user/gamification/achievements`
- `dismissGamificationNotifications(ids)` - POST `/user/gamification/notifications/dismiss`

**New file: `frontend/src/contexts/GamificationContext.jsx`** (follow `TutorialContext.jsx` pattern):
- Fetch gamification state on mount (when signed in + getToken ready)
- Expose: `gamification`, `loading`, `pendingToasts`, `processGamificationResult()`, `dismissToast()`, `refresh()`
- `processGamificationResult()`: called from App.jsx handlers after API responses, updates local XP/level/streak, queues achievement/level-up toasts

**New file: `frontend/src/contexts/useGamification.js`** - useContext hook

Wire `GamificationProvider` into `frontend/src/App.jsx` (wrap AppContent, alongside TutorialProvider).

---

## Phase 5: Frontend Header Widget

**New files: `GamificationHeader.jsx` + `GamificationHeader.css`**
- Sits next to CreditBalance in the App.jsx header
- Shows: level badge (colored circle with number), streak fire icon + day count (when streak > 0)
- Tooltip on hover: level name, total XP
- Responsive: compact on mobile

---

## Phase 6: Frontend Toast Notifications

**New files: `AchievementToast.jsx` + `AchievementToast.css`**
- Slides in from top-right
- Auto-dismisses after 5 seconds
- Two variants: achievement unlock (badge icon + name + description) and level-up (level number + title)
- Rarity-colored border (common=gray, uncommon=green, rare=blue, epic=purple, legendary=gold)
- Add to App.jsx top-level (near TutorialOverlay)

Process gamification results in App.jsx handlers (handleGenerate, handleSendMessage, handleAddNode, handleExport, etc.) by calling `processGamificationResult(response.gamification)`.

---

## Phase 7: Settings Page Achievements Section

**New files: `AchievementsSection.jsx` + `AchievementsSection.css`**

Add as new `<section>` in `frontend/src/components/SettingsPage.jsx` between "Subscription & Credits" (line 246) and "Tutorial" (line 249):

Contents:
- **Level progress bar**: current level name, XP bar showing progress to next level
- **Streak display**: current streak (fire icon + days), longest streak record
- **Achievement grid**: grouped by category (tabs or accordion), each card shows icon/name/description/rarity border, locked ones are grayed with progress bar (e.g., "12/100 diagrams"), unlocked ones show checkmark + date
- **Stats summary**: "12/32 achievements unlocked"

---

## Verification Plan

1. **Backend unit tests**: Test engine.py with mock storage (counter increments, XP calc, level-up, achievement unlock, streak logic including grace period)
2. **API endpoint tests**: Verify GET/POST gamification endpoints return correct shapes
3. **Integration test**: Generate a diagram, verify gamification response includes xp_gained, counters incremented, achievement unlocked if applicable
4. **Frontend manual test**:
   - Sign in as new user, verify gamification header shows Level 1 / Intern
   - Generate a diagram, verify toast for "First Blueprint" achievement + XP gain
   - Check settings page shows achievements section with progress
   - Return next day, perform action, verify streak increments
5. **DynamoDB**: Verify table auto-creates in Lambda environment
6. **Failure isolation**: Temporarily break gamification storage, verify primary operations (generate, chat) still work normally
