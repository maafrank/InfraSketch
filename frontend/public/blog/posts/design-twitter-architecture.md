# How to Design Twitter/X Architecture: System Design Case Study

"Design Twitter" is one of the most common system design interview questions. This case study walks through designing a Twitter-like social media platform, covering the key components, trade-offs, and scaling considerations.

## Requirements Analysis

Before diving into architecture, clarify the requirements:

### Functional Requirements

**Core Features:**
- Post tweets (280 characters, with optional images/videos)
- Follow/unfollow users
- View home timeline (tweets from followed users)
- View user profile and their tweets
- Like and retweet
- Search tweets and users

**Secondary Features:**
- Direct messages
- Notifications
- Trending topics
- Hashtags

### Non-Functional Requirements

- **Scale:** 500M users, 200M daily active users
- **Tweets per day:** 500M new tweets
- **Timeline reads per day:** 28B (average user checks timeline 10+ times)
- **Read-heavy:** ~100:1 read to write ratio
- **Latency:** Timeline should load in <200ms
- **Availability:** 99.99% uptime

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          Clients                                │
│              (iOS, Android, Web, Third-party Apps)              │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         CDN (CloudFront)                        │
│                    (Static assets, media)                       │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Load Balancer (L7)                          │
└─────────────────────────────┬───────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ API Gateway   │    │ API Gateway   │    │ API Gateway   │
│ (Auth, Rate)  │    │ (Auth, Rate)  │    │ (Auth, Rate)  │
└───────┬───────┘    └───────┬───────┘    └───────┬───────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
            ┌─────────────┐   ┌─────────────┐
            │   Tweet     │   │  Timeline   │
            │  Service    │   │  Service    │
            └─────────────┘   └─────────────┘
```

## Core Services

### 1. Tweet Service

Handles tweet creation, storage, and retrieval.

**Responsibilities:**
- Create tweets
- Store tweet content and metadata
- Serve individual tweets
- Handle media attachments

**Data Model:**
```
Tweet {
  tweet_id: UUID (snowflake ID)
  user_id: UUID
  content: VARCHAR(280)
  media_urls: ARRAY[VARCHAR]
  created_at: TIMESTAMP
  like_count: INT
  retweet_count: INT
  reply_count: INT
  reply_to: UUID (nullable)
}
```

**Storage:**
- Primary: Sharded MySQL/PostgreSQL (tweet_id based sharding)
- Cache: Redis cluster for hot tweets
- Media: S3 + CDN

### 2. Timeline Service

The most critical service. Generates home timelines for users.

**Two approaches:**

**Pull Model (Fan-out on read):**
```
When user requests timeline:
1. Get list of followed users
2. Query recent tweets from each user
3. Merge and sort by timestamp
4. Return top N tweets
```

Pros: Simple, no storage overhead
Cons: Slow for users following many accounts, high read latency

**Push Model (Fan-out on write):**
```
When user posts tweet:
1. Get list of followers
2. Insert tweet reference into each follower's timeline cache
3. Timeline read = single cache lookup
```

Pros: Fast reads, predictable latency
Cons: Celebrity problem (millions of followers = millions of writes)

**Hybrid Approach (Twitter's actual solution):**
- Push to timelines for users with < 10K followers
- Pull for celebrities (verified accounts, > 10K followers)
- Merge at read time

**Timeline Cache Structure:**
```
Key: timeline:{user_id}
Value: List of tweet_ids (most recent first)
Size: ~800 tweets per user
TTL: 24 hours (rebuild from DB if missing)
```

### 3. User Service

Manages user accounts and social graph.

**Responsibilities:**
- User registration and authentication
- Profile management
- Follow/unfollow relationships

**Social Graph Storage:**
```
Follows {
  follower_id: UUID
  following_id: UUID
  created_at: TIMESTAMP
}
```

**Challenges:**
- Bi-directional queries: "Who do I follow?" and "Who follows me?"
- Hot users with millions of followers
- Graph database or adjacency list in memory

**Storage options:**
- Graph database (Neo4j) for complex queries
- Redis for follower/following lists
- MySQL with proper indexes

### 4. Search Service

Full-text search for tweets and users.

**Components:**
- Elasticsearch cluster for indexing
- Real-time indexing pipeline (Kafka -> Elasticsearch)
- Ranking algorithms (relevance, recency, engagement)

**Index structure:**
```
Tweet Index:
- content (analyzed text)
- hashtags
- mentions
- user_id
- created_at
- engagement_score
```

### 5. Notification Service

Push notifications and in-app notifications.

**Events that trigger notifications:**
- New follower
- Like on your tweet
- Reply to your tweet
- Retweet
- Direct message
- Mention

**Architecture:**
- Event-driven with Kafka
- Notification preferences per user
- Push notification gateway (APNs, FCM)
- In-app notification storage

## Data Flow: Posting a Tweet

```
1. Client posts tweet
   └─▶ API Gateway (auth, rate limit)
       └─▶ Tweet Service
           ├─▶ Validate content
           ├─▶ Store in Tweet DB
           ├─▶ Upload media to S3
           ├─▶ Publish TweetCreated event
           └─▶ Return success

2. Timeline Service (async consumer)
   ├─▶ Get followers list
   ├─▶ For non-celebrity: fan-out to timeline caches
   └─▶ For celebrity: skip (pull at read time)

3. Search Service (async consumer)
   └─▶ Index tweet in Elasticsearch

4. Notification Service (async consumer)
   └─▶ Notify mentioned users
```

## Data Flow: Reading Timeline

```
1. Client requests timeline
   └─▶ API Gateway
       └─▶ Timeline Service
           ├─▶ Get cached timeline (tweet_ids)
           ├─▶ Pull celebrity tweets for merge
           ├─▶ Hydrate tweet_ids -> full tweets
           │   └─▶ Batch query to Tweet Service
           │       └─▶ Check Redis cache first
           │           └─▶ Fall back to DB
           └─▶ Return sorted, hydrated timeline
```

## Scaling Considerations

### Database Sharding

**Tweet Table:**
- Shard by tweet_id (time-based snowflake ID)
- Auto-increment within shard
- Cross-shard queries rare (timeline uses cache)

**User Table:**
- Shard by user_id
- Keep social graph on same shard as user

### Caching Strategy

**Multi-layer caching:**
1. CDN: Static assets, profile images
2. Application cache: Hot tweets, user profiles
3. Timeline cache: Pre-computed timelines
4. Database cache: Query result cache

**Cache invalidation:**
- Tweet update: Invalidate tweet cache
- Follow/unfollow: Rebuild timeline cache async
- Profile update: Invalidate profile cache

### Handling Celebrities

The "celebrity problem": A user with 50M followers creates massive fan-out.

**Solutions:**
1. Don't fan-out for celebrities (pull at read time)
2. Prioritize active followers
3. Batch fan-out over time
4. Separate infrastructure for high-follower accounts

### Media Storage

- Upload to S3 with pre-signed URLs
- Process asynchronously (resize, encode)
- Serve via CDN with long cache TTL
- Different qualities for different clients

## Trade-offs and Decisions

| Decision | Trade-off |
|----------|-----------|
| Push vs Pull timeline | Push: fast reads, expensive writes. Hybrid is best. |
| SQL vs NoSQL | SQL for consistency (user data). NoSQL for scale (tweets). |
| Strong vs Eventual consistency | Eventual for timeline (acceptable), strong for DMs. |
| Monolith vs Microservices | Microservices for independent scaling and deployment. |

## Designing with InfraSketch

Instead of whiteboarding manually, describe the system:

**Example prompt:**
> "Design a Twitter-like social media platform with user service, tweet service, timeline service with fan-out, search with Elasticsearch, and notification service. Include caching with Redis, message queue with Kafka, and CDN for media. Show the hybrid push/pull timeline approach."

InfraSketch generates a complete diagram showing all services, data flows, and infrastructure components. Then refine through chat:
- "Add database sharding for the tweet service"
- "Show the celebrity fan-out optimization"
- "Include rate limiting at the API gateway"

Click "Create Design Doc" to generate comprehensive documentation covering system overview, component details, data flows, and scalability considerations.

## Interview Tips

### Structure Your Answer

1. **Clarify requirements** (5 min)
2. **High-level design** (10 min)
3. **Deep dive on core components** (20 min)
4. **Scaling and trade-offs** (10 min)

### Common Follow-up Questions

- "How would you handle a viral tweet?"
- "What happens when the timeline cache is empty?"
- "How do you ensure no duplicate tweets in timeline?"
- "How would you implement trending topics?"

### Key Points to Hit

- Explain the hybrid push/pull approach
- Discuss the celebrity problem
- Mention caching at every layer
- Talk about eventual consistency trade-offs
- Show awareness of real-world scale

## Conclusion

Designing Twitter involves balancing read-heavy access patterns with write fan-out challenges. The hybrid approach (push for regular users, pull for celebrities) is the key insight that makes the system scalable.

Practice with InfraSketch: describe the system, generate the diagram, refine through conversation, and export a design document you can reference for interviews.

---

**Practice designing Twitter and other systems** with [InfraSketch](https://infrasketch.net). Generate diagrams and design docs in minutes.

## Related Resources

- [System Design Interview Prep Guide](/blog/system-design-interview-prep-practice)
- [Microservices Architecture Diagram Guide](/blog/microservices-architecture-diagram-guide)
- [The Complete Guide to System Design](/blog/complete-guide-system-design)
- [Real-World AI System Architecture: Netflix, Uber, and More](/blog/real-world-ai-system-architecture)
- [Machine Learning System Design Patterns](/blog/ml-system-design-patterns)
