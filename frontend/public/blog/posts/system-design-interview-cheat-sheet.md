System design interviews can make or break your chances at top tech companies. Unlike coding interviews with clear right answers, system design requires you to navigate ambiguity, make trade-offs, and communicate complex ideas clearly.

This cheat sheet gives you a structured approach and quick references for your next system design interview at Google, Meta, Amazon, Netflix, or any top company. For a deeper dive into system design concepts, see our [Complete Guide to System Design](/blog/complete-guide-system-design).

## The 5-Step Framework

Use this framework for every system design interview:

### Step 1: Clarify Requirements (3-5 minutes)

Never start designing without asking questions first.

**Functional Requirements:**
- What are the core features?
- Who are the users?
- What should users be able to do?

**Non-Functional Requirements:**
- What's the expected scale? (users, requests/second)
- What latency is acceptable?
- What availability is required? (99.9%? 99.99%?)
- Any compliance requirements? (GDPR, HIPAA)

**Example Questions:**
- "How many daily active users should we design for?"
- "What's the read-to-write ratio?"
- "Should we prioritize consistency or availability?"
- "Is this a global service or regional?"

### Step 2: Estimate Scale (2-3 minutes)

Do back-of-envelope calculations to inform your design.

**Traffic Estimates:**
```
DAU = 100M users
Avg requests per user = 10/day
Total daily requests = 1B
Requests per second = 1B / 86400 ≈ 12K RPS
```

**Storage Estimates:**
```
New records per day = 10M
Record size = 1KB
Daily storage = 10GB
Annual storage = 3.6TB
5-year storage = 18TB
```

**Memory Estimates (for caching):**
```
Hot data = 20% of total
Cache size = 3.6TB * 0.2 = 720GB
```

### Step 3: High-Level Design (10-15 minutes)

Draw the major components and their interactions.

**Standard Components:**
- Clients (web, mobile, API consumers)
- Load Balancer
- API Gateway
- Application Servers
- Cache Layer (Redis/Memcached)
- Database (primary + replicas)
- Message Queue
- Background Workers
- CDN (for static content)
- Monitoring/Logging

**Draw the Flow:**
1. Start with the client
2. Show request path through load balancer
3. Show application tier
4. Show data layer
5. Show async processing (if applicable)

### Step 4: Deep Dive (15-20 minutes)

Pick 2-3 critical components and explain them in detail.

**For Each Component:**
- Why this technology choice?
- How does it handle scale?
- What are the failure modes?
- How do you monitor it?

**Common Deep Dives:**
- Database schema and query patterns
- Caching strategy and invalidation
- API design and authentication
- Data partitioning strategy

### Step 5: Wrap Up (3-5 minutes)

Address remaining concerns.

**Discuss:**
- Bottlenecks and how to address them
- Single points of failure
- Future scaling considerations
- Monitoring and alerting strategy
- Security considerations

## Quick Reference: Components

### Load Balancers

**When to Use:** Always, when you have multiple servers

**Options:**
| Type | Example | Use Case |
|------|---------|----------|
| L4 (Transport) | AWS NLB | High throughput, TCP/UDP |
| L7 (Application) | AWS ALB, NGINX | HTTP routing, SSL termination |

**Algorithms:**
- Round Robin: Simple, equal distribution
- Least Connections: Route to least busy server
- IP Hash: Session affinity

### Databases

**Relational (SQL):**
- PostgreSQL, MySQL
- ACID transactions
- Complex queries, JOINs
- Vertical scaling primarily

**Document (NoSQL):**
- MongoDB, DynamoDB
- Flexible schemas
- Horizontal scaling
- Eventual consistency

**Key-Value:**
- Redis, Memcached
- Ultra-fast reads
- Simple data model
- Great for caching

**When to Choose:**
- Need transactions? → SQL
- Need flexibility? → Document
- Need speed? → Key-Value
- Need relationships? → SQL or Graph

### Caching

**Cache-Aside Pattern:**
```
1. Check cache
2. If miss, read from DB
3. Write to cache
4. Return data
```

**Cache Invalidation:**
- TTL: Simplest, eventual staleness
- Write-through: Update cache on every write
- Event-based: Invalidate on data change

**What to Cache:**
- Database query results
- API responses
- Session data
- Computed values

### Message Queues

**When to Use:**
- Async processing needed
- Decouple services
- Handle traffic spikes
- Ensure delivery

**Options:**
| Queue | Best For |
|-------|----------|
| Kafka | High throughput, event streaming |
| RabbitMQ | Task queues, routing logic |
| SQS | AWS integration, simplicity |
| Redis Streams | Low latency, real-time |

### CDN

**What to Cache:**
- Static assets (images, CSS, JS)
- API responses (with appropriate TTL)
- HTML pages

**Benefits:**
- Reduce latency (edge locations)
- Offload origin traffic
- DDoS protection

## Quick Reference: Patterns

### Database Scaling

**Read Replicas:**
- Create read-only copies
- Route reads to replicas
- Master handles writes
- Eventually consistent

**Sharding:**
- Split data across databases
- Choose good shard key
- Avoid cross-shard queries

**Sharding Strategies:**
- Hash-based: hash(user_id) % num_shards
- Range-based: users A-M shard 1, N-Z shard 2
- Geographic: US shard, EU shard

### API Patterns

**REST:**
```
GET    /users/123      # Read user
POST   /users          # Create user
PUT    /users/123      # Update user
DELETE /users/123      # Delete user
```

**Pagination:**
- Offset-based: ?page=2&limit=20
- Cursor-based: ?cursor=abc123&limit=20 (preferred for large datasets)

**Rate Limiting:**
- Token bucket: Smooth traffic
- Sliding window: Rolling count

### Consistency Patterns

**Strong Consistency:**
- All reads see latest write
- Higher latency
- Use for: Financial transactions

**Eventual Consistency:**
- Reads may see stale data temporarily
- Lower latency, higher availability
- Use for: Social feeds, likes, views

**Read-Your-Writes:**
- User sees their own writes immediately
- Others may see stale data
- Use for: Profile updates

## Common Interview Questions

### URL Shortener (bit.ly)

**Key Points:**
- Generate unique short codes
- Redirect to original URL
- Analytics (optional)

**Scale:**
- 100M URLs created/month
- 10B redirects/month (100:1 read ratio)

**Components:**
- Application servers (stateless)
- Key-Value store for URL mapping
- Counter service for analytics
- Cache for hot URLs

**Short Code Generation:**
- Hash + collision handling
- Counter + base62 encoding
- UUID (longer but simple)

### Social Media Feed (Twitter)

**Key Points:**
- Timeline generation
- Fan-out on write vs. read
- Real-time updates

**Scale:**
- 500M DAU
- 12K writes/sec, 600K reads/sec

**Approaches:**
- **Fan-out on Write:** Pre-compute timelines
  - Pro: Fast reads
  - Con: Slow writes for celebrities

- **Fan-out on Read:** Compute on request
  - Pro: Fast writes
  - Con: Slow reads

**Hybrid:** Fan-out for regular users, on-read for celebrities

### Chat System (WhatsApp)

**Key Points:**
- Real-time messaging
- Delivery guarantees
- Online presence

**Components:**
- WebSocket servers (persistent connections)
- Message queue (for reliability)
- Database (for history)
- Presence service

**Message Flow:**
1. Client A sends message via WebSocket
2. Server queues message
3. Server pushes to Client B (if online)
4. Store in DB
5. Acknowledge to Client A

### Video Streaming (Netflix)

**Key Points:**
- Video upload and processing
- Adaptive bitrate streaming
- Global CDN

**Components:**
- Upload service (chunked uploads)
- Transcoding pipeline (multiple resolutions)
- CDN (edge caching)
- Recommendation service

**Transcoding Pipeline:**
1. Upload to blob storage
2. Queue transcoding job
3. Generate multiple bitrates (240p to 4K)
4. Store all versions
5. Update metadata

### Rate Limiter

**Key Points:**
- Limit requests per user/IP
- Handle distributed servers

**Algorithms:**
- **Token Bucket:** Bucket refills at rate R, max capacity B
- **Sliding Window Log:** Track all timestamps, count in window
- **Sliding Window Counter:** Approximate with weighted windows

**Distributed Rate Limiting:**
- Use Redis for shared state
- Lua scripts for atomicity
- Accept some over-counting for performance

## Numbers to Know

**Latency:**
| Operation | Time |
|-----------|------|
| L1 cache reference | 0.5 ns |
| L2 cache reference | 7 ns |
| RAM reference | 100 ns |
| SSD read | 150 μs |
| HDD read | 10 ms |
| Network round trip (same DC) | 0.5 ms |
| Network round trip (cross-region) | 100 ms |

**Throughput:**
| Operation | Throughput |
|-----------|------------|
| SSD sequential read | 500 MB/s |
| HDD sequential read | 100 MB/s |
| 1 Gbps network | 125 MB/s |
| 10 Gbps network | 1.25 GB/s |

**Capacity:**
| Unit | Value |
|------|-------|
| 1 KB | 1,000 bytes |
| 1 MB | 1,000 KB |
| 1 GB | 1,000 MB |
| 1 TB | 1,000 GB |
| 1 PB | 1,000 TB |

**Time:**
| Period | Seconds |
|--------|---------|
| 1 day | 86,400 |
| 1 month | 2.6M |
| 1 year | 31.5M |

## Interview Tips

### Do:
- Ask clarifying questions first
- Think out loud
- Draw diagrams
- Discuss trade-offs
- Mention monitoring and security
- Be honest about unknowns

### Don't:
- Jump into design without requirements
- Over-engineer the solution
- Ignore non-functional requirements
- Skip the math
- Be defensive about feedback

### Communication:
- "Let me start by clarifying requirements..."
- "Given the scale, I'm thinking..."
- "The trade-off here is..."
- "One concern with this approach is..."
- "If we had more time, we could..."

## Practice Resources

**Visualize Your Designs:**
Use [InfraSketch](/tools/system-design-tool) to quickly generate architecture diagrams from descriptions. Practice articulating your designs in natural language and see them come to life. Learn more about creating effective diagrams in our [Architecture Diagram Best Practices](/blog/architecture-diagram-best-practices) guide.

**Practice Problems:**
1. Design Twitter
2. Design WhatsApp
3. Design Netflix
4. Design Uber
5. Design Google Search
6. Design Dropbox
7. Design Instagram
8. Design Yelp
9. Design Amazon
10. Design Zoom

**Study Real Systems:**
- Netflix Tech Blog
- Uber Engineering Blog
- Meta Engineering Blog
- AWS Architecture Center
- Google Cloud Architecture Framework

## Conclusion

System design interviews test your ability to:
1. Gather requirements and handle ambiguity
2. Break down complex problems
3. Make and justify trade-offs
4. Communicate technical ideas clearly

Use this cheat sheet as a reference, but remember: practice is what makes the difference. Work through problems, draw diagrams, and get comfortable explaining your reasoning.

Good luck with your interviews!
