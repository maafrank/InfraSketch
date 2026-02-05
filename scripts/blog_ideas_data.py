#!/usr/bin/env python3
"""
365 unique blog post ideas for automated daily publishing to Dev.to.

Categories:
- system-design: 60 ideas
- architecture: 55 ideas
- interviews: 50 ideas
- devops: 55 ideas
- cloud: 55 ideas
- ai-ml: 45 ideas
- career: 45 ideas

Total: 365 ideas (one year of daily posts)
"""

BLOG_IDEAS = [
    # =============================================================================
    # SYSTEM DESIGN (60 ideas)
    # =============================================================================
    {
        "slug": "design-url-shortener",
        "title": "How to Design a URL Shortener: Complete System Design Guide",
        "category": "system-design",
        "outline": "Cover hashing strategies, database design, read/write optimization, analytics, and scaling to billions of URLs",
        "keywords": ["url shortener", "system design", "hashing", "base62"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-rate-limiter",
        "title": "Designing a Distributed Rate Limiter: Algorithms and Implementation",
        "category": "system-design",
        "outline": "Token bucket, leaky bucket, sliding window algorithms, Redis implementation, distributed coordination",
        "keywords": ["rate limiter", "distributed systems", "redis", "api throttling"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-news-feed",
        "title": "How to Design a News Feed System Like Facebook",
        "category": "system-design",
        "outline": "Fan-out strategies, ranking algorithms, caching, real-time updates, personalization",
        "keywords": ["news feed", "fan-out", "social media", "ranking algorithm"],
        "difficulty": "advanced"
    },
    {
        "slug": "design-chat-system",
        "title": "Designing a Real-Time Chat Application: WhatsApp Architecture",
        "category": "system-design",
        "outline": "WebSockets, message queues, presence system, end-to-end encryption, offline messaging",
        "keywords": ["chat system", "websocket", "real-time", "messaging"],
        "difficulty": "advanced"
    },
    {
        "slug": "design-notification-system",
        "title": "Building a Scalable Notification System: Push, Email, and SMS",
        "category": "system-design",
        "outline": "Multi-channel delivery, priority queues, rate limiting, user preferences, delivery tracking",
        "keywords": ["notification system", "push notifications", "message queue"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-search-autocomplete",
        "title": "Designing Search Autocomplete: Trie Data Structures at Scale",
        "category": "system-design",
        "outline": "Trie implementation, ranking suggestions, distributed tries, caching strategies",
        "keywords": ["autocomplete", "trie", "search", "typeahead"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-web-crawler",
        "title": "How to Design a Web Crawler: Googlebot Architecture Explained",
        "category": "system-design",
        "outline": "URL frontier, politeness policies, distributed crawling, deduplication, content extraction",
        "keywords": ["web crawler", "distributed systems", "crawling", "scraping"],
        "difficulty": "advanced"
    },
    {
        "slug": "design-pastebin",
        "title": "Designing Pastebin: A Text Sharing Service Architecture",
        "category": "system-design",
        "outline": "Content storage, expiration handling, URL generation, access controls, analytics",
        "keywords": ["pastebin", "content storage", "system design basics"],
        "difficulty": "beginner"
    },
    {
        "slug": "design-youtube",
        "title": "How YouTube Works: Video Streaming Architecture Deep Dive",
        "category": "system-design",
        "outline": "Video encoding, CDN distribution, adaptive bitrate streaming, recommendation engine",
        "keywords": ["video streaming", "cdn", "transcoding", "youtube"],
        "difficulty": "advanced"
    },
    {
        "slug": "design-uber",
        "title": "Designing Uber: Real-Time Ride Matching System",
        "category": "system-design",
        "outline": "Geospatial indexing, real-time matching, surge pricing, driver dispatch, ETA calculation",
        "keywords": ["uber", "geospatial", "matching algorithm", "ride sharing"],
        "difficulty": "advanced"
    },
    {
        "slug": "design-instagram",
        "title": "Instagram Architecture: Photo Sharing at Scale",
        "category": "system-design",
        "outline": "Image storage, CDN, news feed, stories feature, explore recommendations",
        "keywords": ["instagram", "photo sharing", "social media", "cdn"],
        "difficulty": "advanced"
    },
    {
        "slug": "design-dropbox",
        "title": "How Dropbox Works: File Sync System Design",
        "category": "system-design",
        "outline": "Block-level sync, deduplication, conflict resolution, metadata management, versioning",
        "keywords": ["dropbox", "file sync", "cloud storage", "deduplication"],
        "difficulty": "advanced"
    },
    {
        "slug": "design-twitter-search",
        "title": "Designing Twitter Search: Real-Time Indexing at Scale",
        "category": "system-design",
        "outline": "Inverted index, real-time indexing, ranking, sharding strategies, query parsing",
        "keywords": ["search engine", "inverted index", "twitter", "real-time search"],
        "difficulty": "advanced"
    },
    {
        "slug": "design-key-value-store",
        "title": "Building a Distributed Key-Value Store from Scratch",
        "category": "system-design",
        "outline": "Consistent hashing, replication, CAP theorem trade-offs, conflict resolution",
        "keywords": ["key-value store", "distributed database", "consistent hashing"],
        "difficulty": "advanced"
    },
    {
        "slug": "design-ticketmaster",
        "title": "Designing Ticketmaster: High-Traffic Event Booking System",
        "category": "system-design",
        "outline": "Inventory management, seat locking, queue systems, flash sale handling",
        "keywords": ["ticketmaster", "booking system", "inventory", "flash sale"],
        "difficulty": "advanced"
    },
    {
        "slug": "design-google-docs",
        "title": "How Google Docs Works: Real-Time Collaborative Editing",
        "category": "system-design",
        "outline": "Operational transformation, CRDTs, conflict resolution, cursor synchronization",
        "keywords": ["google docs", "collaborative editing", "crdt", "real-time"],
        "difficulty": "advanced"
    },
    {
        "slug": "design-payment-system",
        "title": "Designing a Payment Processing System: Stripe Architecture",
        "category": "system-design",
        "outline": "Transaction handling, idempotency, PCI compliance, fraud detection, reconciliation",
        "keywords": ["payment system", "fintech", "transactions", "idempotency"],
        "difficulty": "advanced"
    },
    {
        "slug": "design-hotel-booking",
        "title": "Designing a Hotel Booking System Like Booking.com",
        "category": "system-design",
        "outline": "Inventory management, search and filtering, pricing strategies, double booking prevention",
        "keywords": ["hotel booking", "reservation system", "inventory management"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-amazon-shopping-cart",
        "title": "Designing Amazon's Shopping Cart: E-commerce at Scale",
        "category": "system-design",
        "outline": "Cart persistence, inventory reservation, session management, checkout flow",
        "keywords": ["shopping cart", "e-commerce", "amazon", "inventory"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-recommendation-engine",
        "title": "Building a Recommendation Engine: Netflix Algorithm Explained",
        "category": "system-design",
        "outline": "Collaborative filtering, content-based filtering, hybrid approaches, A/B testing",
        "keywords": ["recommendation engine", "netflix", "collaborative filtering"],
        "difficulty": "advanced"
    },
    {
        "slug": "design-ad-click-aggregator",
        "title": "Designing an Ad Click Aggregator: Real-Time Analytics",
        "category": "system-design",
        "outline": "Stream processing, time-series data, aggregation strategies, fraud detection",
        "keywords": ["ad tech", "click tracking", "stream processing", "analytics"],
        "difficulty": "advanced"
    },
    {
        "slug": "design-google-maps",
        "title": "How Google Maps Works: Routing and Navigation System",
        "category": "system-design",
        "outline": "Graph algorithms, real-time traffic, ETA calculation, map tile serving",
        "keywords": ["google maps", "routing", "navigation", "geospatial"],
        "difficulty": "advanced"
    },
    {
        "slug": "design-stock-exchange",
        "title": "Designing a Stock Exchange: Order Matching Engine",
        "category": "system-design",
        "outline": "Order book, matching algorithms, low-latency requirements, market data distribution",
        "keywords": ["stock exchange", "trading", "order matching", "low latency"],
        "difficulty": "advanced"
    },
    {
        "slug": "design-email-system",
        "title": "Designing an Email Service: Gmail Architecture Overview",
        "category": "system-design",
        "outline": "SMTP protocol, spam filtering, storage optimization, search indexing",
        "keywords": ["email system", "gmail", "smtp", "spam filtering"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-spotify",
        "title": "How Spotify Works: Music Streaming Architecture",
        "category": "system-design",
        "outline": "Audio streaming, playlist management, recommendation, offline mode, licensing",
        "keywords": ["spotify", "music streaming", "audio", "recommendations"],
        "difficulty": "advanced"
    },
    {
        "slug": "design-parking-lot",
        "title": "Designing a Parking Lot System: OOP Meets System Design",
        "category": "system-design",
        "outline": "Object-oriented design, spot allocation, payment processing, sensor integration",
        "keywords": ["parking lot", "oop", "system design basics"],
        "difficulty": "beginner"
    },
    {
        "slug": "design-leaderboard",
        "title": "Designing a Real-Time Gaming Leaderboard",
        "category": "system-design",
        "outline": "Redis sorted sets, rank calculation, sharding, real-time updates",
        "keywords": ["leaderboard", "gaming", "redis", "real-time"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-distributed-cache",
        "title": "Building a Distributed Cache: Memcached vs Redis",
        "category": "system-design",
        "outline": "Cache eviction policies, consistency models, partitioning, cache invalidation",
        "keywords": ["distributed cache", "redis", "memcached", "caching"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-logging-system",
        "title": "Designing a Centralized Logging System: ELK Stack Architecture",
        "category": "system-design",
        "outline": "Log aggregation, indexing, search, alerting, retention policies",
        "keywords": ["logging", "elk stack", "observability", "log aggregation"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-metrics-system",
        "title": "Building a Metrics Collection System: Prometheus Architecture",
        "category": "system-design",
        "outline": "Time-series database, pull vs push, aggregation, alerting rules",
        "keywords": ["metrics", "prometheus", "monitoring", "time-series"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-job-scheduler",
        "title": "Designing a Distributed Job Scheduler: Cron at Scale",
        "category": "system-design",
        "outline": "Task queuing, distributed locking, retry mechanisms, priority scheduling",
        "keywords": ["job scheduler", "distributed systems", "task queue"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-api-gateway",
        "title": "Designing an API Gateway: Kong and AWS API Gateway",
        "category": "system-design",
        "outline": "Request routing, authentication, rate limiting, request transformation",
        "keywords": ["api gateway", "microservices", "routing", "authentication"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-content-delivery-network",
        "title": "How CDNs Work: CloudFront and Cloudflare Explained",
        "category": "system-design",
        "outline": "Edge caching, cache invalidation, origin shield, DDoS protection",
        "keywords": ["cdn", "cloudfront", "cloudflare", "edge caching"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-food-delivery",
        "title": "Designing DoorDash: Food Delivery System Architecture",
        "category": "system-design",
        "outline": "Order management, driver dispatch, ETA prediction, restaurant integration",
        "keywords": ["food delivery", "doordash", "logistics", "dispatch"],
        "difficulty": "advanced"
    },
    {
        "slug": "design-airline-reservation",
        "title": "Designing an Airline Reservation System",
        "category": "system-design",
        "outline": "Seat inventory, booking workflow, pricing tiers, overbooking strategies",
        "keywords": ["airline reservation", "booking system", "inventory"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-dating-app",
        "title": "Designing Tinder: Location-Based Matching System",
        "category": "system-design",
        "outline": "Geospatial queries, matching algorithm, swipe mechanics, chat integration",
        "keywords": ["dating app", "tinder", "geospatial", "matching"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-file-sharing",
        "title": "Designing WeTransfer: Large File Sharing System",
        "category": "system-design",
        "outline": "Chunked uploads, temporary storage, link expiration, download acceleration",
        "keywords": ["file sharing", "upload", "cloud storage"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-calendar-system",
        "title": "Designing Google Calendar: Event Scheduling at Scale",
        "category": "system-design",
        "outline": "Recurring events, timezone handling, availability checking, notifications",
        "keywords": ["calendar", "scheduling", "google calendar"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-code-deployment",
        "title": "Designing a Code Deployment System: GitHub Actions Architecture",
        "category": "system-design",
        "outline": "Pipeline execution, artifact storage, parallel jobs, secrets management",
        "keywords": ["deployment", "ci/cd", "github actions", "pipeline"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-live-streaming",
        "title": "Designing Twitch: Live Video Streaming Platform",
        "category": "system-design",
        "outline": "Ingest servers, transcoding, CDN distribution, chat integration, latency optimization",
        "keywords": ["live streaming", "twitch", "video", "real-time"],
        "difficulty": "advanced"
    },
    {
        "slug": "design-social-graph",
        "title": "Designing a Social Graph: LinkedIn Connections",
        "category": "system-design",
        "outline": "Graph database, degree of separation, friend suggestions, graph traversal",
        "keywords": ["social graph", "linkedin", "graph database", "connections"],
        "difficulty": "advanced"
    },
    {
        "slug": "design-poll-voting",
        "title": "Designing a Real-Time Polling System",
        "category": "system-design",
        "outline": "Vote counting, duplicate prevention, real-time updates, result caching",
        "keywords": ["polling", "voting", "real-time", "counters"],
        "difficulty": "beginner"
    },
    {
        "slug": "design-url-preview",
        "title": "Designing Link Preview Generation: Open Graph Fetching",
        "category": "system-design",
        "outline": "Metadata extraction, caching, image proxy, rate limiting external requests",
        "keywords": ["link preview", "open graph", "metadata", "web scraping"],
        "difficulty": "beginner"
    },
    {
        "slug": "design-location-tracking",
        "title": "Designing a Fleet Location Tracking System",
        "category": "system-design",
        "outline": "GPS data ingestion, real-time updates, geofencing, historical playback",
        "keywords": ["location tracking", "gps", "fleet management", "geofencing"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-coupon-system",
        "title": "Designing a Coupon and Promo Code System",
        "category": "system-design",
        "outline": "Code generation, validation rules, usage limits, fraud prevention",
        "keywords": ["coupon system", "promo codes", "e-commerce"],
        "difficulty": "beginner"
    },
    {
        "slug": "design-auction-system",
        "title": "Designing eBay: Online Auction Platform",
        "category": "system-design",
        "outline": "Bid management, auction timing, sniping prevention, winner notification",
        "keywords": ["auction", "ebay", "bidding", "real-time"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-image-search",
        "title": "Designing Reverse Image Search: Google Images",
        "category": "system-design",
        "outline": "Feature extraction, similarity search, vector databases, indexing",
        "keywords": ["image search", "computer vision", "similarity search"],
        "difficulty": "advanced"
    },
    {
        "slug": "design-news-aggregator",
        "title": "Designing a News Aggregator: Google News Architecture",
        "category": "system-design",
        "outline": "Content crawling, deduplication, clustering, personalization",
        "keywords": ["news aggregator", "content aggregation", "clustering"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-inventory-system",
        "title": "Designing an Inventory Management System",
        "category": "system-design",
        "outline": "Stock tracking, warehouse management, reorder points, multi-location",
        "keywords": ["inventory management", "warehouse", "e-commerce"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-subscription-billing",
        "title": "Designing a Subscription Billing System",
        "category": "system-design",
        "outline": "Recurring charges, proration, dunning, plan changes, usage-based billing",
        "keywords": ["subscription billing", "saas", "payments", "recurring"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-document-store",
        "title": "Designing a Document Database: MongoDB Internals",
        "category": "system-design",
        "outline": "Document model, indexing, sharding, replication, query optimization",
        "keywords": ["mongodb", "document database", "nosql"],
        "difficulty": "advanced"
    },
    {
        "slug": "design-event-ticketing",
        "title": "Designing an Event Ticketing Platform: Queue Management",
        "category": "system-design",
        "outline": "Virtual queues, fair distribution, scalping prevention, QR code validation",
        "keywords": ["event ticketing", "queue management", "e-commerce"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-online-judge",
        "title": "Designing LeetCode: Online Code Judge System",
        "category": "system-design",
        "outline": "Sandboxed execution, test case management, plagiarism detection, ranking",
        "keywords": ["online judge", "leetcode", "code execution", "sandbox"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-blogging-platform",
        "title": "Designing Medium: Blogging Platform Architecture",
        "category": "system-design",
        "outline": "Content storage, rich text editing, recommendations, paywall, SEO",
        "keywords": ["blogging", "medium", "content platform", "cms"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-short-video",
        "title": "Designing TikTok: Short Video Platform Architecture",
        "category": "system-design",
        "outline": "Video upload, recommendation algorithm, content moderation, effects processing",
        "keywords": ["tiktok", "short video", "social media", "recommendations"],
        "difficulty": "advanced"
    },
    {
        "slug": "design-digital-wallet",
        "title": "Designing a Digital Wallet: Apple Pay Architecture",
        "category": "system-design",
        "outline": "Account balance, transaction history, security, NFC integration",
        "keywords": ["digital wallet", "payments", "fintech", "mobile payments"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-customer-support",
        "title": "Designing a Customer Support Ticketing System",
        "category": "system-design",
        "outline": "Ticket routing, priority queues, SLA tracking, agent assignment",
        "keywords": ["customer support", "ticketing", "helpdesk"],
        "difficulty": "beginner"
    },
    {
        "slug": "design-authentication-system",
        "title": "Designing an Authentication System: OAuth and SSO",
        "category": "system-design",
        "outline": "Token management, session handling, MFA, social login, password reset",
        "keywords": ["authentication", "oauth", "sso", "security"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-ab-testing",
        "title": "Designing an A/B Testing Platform: Experimentation at Scale",
        "category": "system-design",
        "outline": "Traffic splitting, statistical significance, feature flags, metrics collection",
        "keywords": ["ab testing", "experimentation", "feature flags"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-warehouse-management",
        "title": "Designing a Warehouse Management System: Fulfillment at Scale",
        "category": "system-design",
        "outline": "Inventory tracking, pick-pack-ship, routing optimization, integration",
        "keywords": ["warehouse management", "fulfillment", "logistics"],
        "difficulty": "intermediate"
    },

    # =============================================================================
    # ARCHITECTURE (55 ideas)
    # =============================================================================
    {
        "slug": "microservices-vs-monolith",
        "title": "Microservices vs Monolith: When to Use Each Architecture",
        "category": "architecture",
        "outline": "Trade-offs, migration strategies, team structure, deployment complexity",
        "keywords": ["microservices", "monolith", "architecture decision"],
        "difficulty": "intermediate"
    },
    {
        "slug": "event-driven-architecture-intro",
        "title": "Event-Driven Architecture: A Practical Introduction",
        "category": "architecture",
        "outline": "Event sourcing basics, message brokers, event choreography vs orchestration",
        "keywords": ["event-driven", "architecture", "messaging", "events"],
        "difficulty": "intermediate"
    },
    {
        "slug": "cqrs-pattern-explained",
        "title": "CQRS Pattern Explained: Command Query Responsibility Segregation",
        "category": "architecture",
        "outline": "Read/write separation, eventual consistency, implementation patterns",
        "keywords": ["cqrs", "architecture pattern", "read write separation"],
        "difficulty": "advanced"
    },
    {
        "slug": "saga-pattern-microservices",
        "title": "Saga Pattern: Managing Distributed Transactions",
        "category": "architecture",
        "outline": "Choreography vs orchestration, compensation logic, failure handling",
        "keywords": ["saga pattern", "distributed transactions", "microservices"],
        "difficulty": "advanced"
    },
    {
        "slug": "hexagonal-architecture",
        "title": "Hexagonal Architecture: Ports and Adapters Pattern",
        "category": "architecture",
        "outline": "Domain isolation, dependency inversion, testability, adapter implementation",
        "keywords": ["hexagonal architecture", "ports adapters", "clean code"],
        "difficulty": "advanced"
    },
    {
        "slug": "clean-architecture-guide",
        "title": "Clean Architecture: Building Maintainable Applications",
        "category": "architecture",
        "outline": "Dependency rule, use cases, entities, interface adapters, frameworks",
        "keywords": ["clean architecture", "uncle bob", "software design"],
        "difficulty": "intermediate"
    },
    {
        "slug": "domain-driven-design-basics",
        "title": "Domain-Driven Design: Getting Started with DDD",
        "category": "architecture",
        "outline": "Bounded contexts, aggregates, entities, value objects, ubiquitous language",
        "keywords": ["ddd", "domain driven design", "software architecture"],
        "difficulty": "advanced"
    },
    {
        "slug": "api-design-best-practices",
        "title": "RESTful API Design: Best Practices and Common Mistakes",
        "category": "architecture",
        "outline": "Resource naming, HTTP methods, versioning, pagination, error handling",
        "keywords": ["api design", "rest", "http", "best practices"],
        "difficulty": "intermediate"
    },
    {
        "slug": "graphql-vs-rest",
        "title": "GraphQL vs REST: Choosing the Right API Style",
        "category": "architecture",
        "outline": "Query flexibility, over-fetching, caching, tooling, use cases",
        "keywords": ["graphql", "rest", "api", "comparison"],
        "difficulty": "intermediate"
    },
    {
        "slug": "service-mesh-explained",
        "title": "Service Mesh Explained: Istio and Linkerd Deep Dive",
        "category": "architecture",
        "outline": "Sidecar proxy, traffic management, observability, security policies",
        "keywords": ["service mesh", "istio", "linkerd", "kubernetes"],
        "difficulty": "advanced"
    },
    {
        "slug": "database-per-service",
        "title": "Database Per Service Pattern: Data Management in Microservices",
        "category": "architecture",
        "outline": "Data isolation, cross-service queries, data consistency, migration",
        "keywords": ["database per service", "microservices", "data management"],
        "difficulty": "intermediate"
    },
    {
        "slug": "strangler-fig-pattern",
        "title": "Strangler Fig Pattern: Migrating Legacy Systems Safely",
        "category": "architecture",
        "outline": "Incremental migration, routing, feature parity, rollback strategies",
        "keywords": ["strangler fig", "legacy migration", "modernization"],
        "difficulty": "intermediate"
    },
    {
        "slug": "circuit-breaker-pattern",
        "title": "Circuit Breaker Pattern: Building Resilient Services",
        "category": "architecture",
        "outline": "Failure detection, fallback strategies, recovery, implementation with Resilience4j",
        "keywords": ["circuit breaker", "resilience", "fault tolerance"],
        "difficulty": "intermediate"
    },
    {
        "slug": "bulkhead-pattern",
        "title": "Bulkhead Pattern: Isolating Failures in Distributed Systems",
        "category": "architecture",
        "outline": "Resource isolation, thread pools, connection limits, failure containment",
        "keywords": ["bulkhead pattern", "isolation", "fault tolerance"],
        "difficulty": "intermediate"
    },
    {
        "slug": "retry-pattern-strategies",
        "title": "Retry Patterns: Handling Transient Failures Gracefully",
        "category": "architecture",
        "outline": "Exponential backoff, jitter, idempotency, retry budgets",
        "keywords": ["retry pattern", "fault tolerance", "exponential backoff"],
        "difficulty": "beginner"
    },
    {
        "slug": "sidecar-pattern",
        "title": "Sidecar Pattern: Extending Service Capabilities",
        "category": "architecture",
        "outline": "Logging, monitoring, security, configuration management via sidecars",
        "keywords": ["sidecar pattern", "kubernetes", "microservices"],
        "difficulty": "intermediate"
    },
    {
        "slug": "ambassador-pattern",
        "title": "Ambassador Pattern: Offloading Cross-Cutting Concerns",
        "category": "architecture",
        "outline": "Connection management, protocol translation, request routing",
        "keywords": ["ambassador pattern", "proxy", "microservices"],
        "difficulty": "intermediate"
    },
    {
        "slug": "backend-for-frontend",
        "title": "Backend for Frontend (BFF): API Design for Multiple Clients",
        "category": "architecture",
        "outline": "Client-specific APIs, aggregation, mobile vs web optimization",
        "keywords": ["bff", "backend for frontend", "api design"],
        "difficulty": "intermediate"
    },
    {
        "slug": "api-gateway-pattern",
        "title": "API Gateway Pattern: Centralized Entry Point Design",
        "category": "architecture",
        "outline": "Request routing, authentication, rate limiting, response aggregation",
        "keywords": ["api gateway", "microservices", "routing"],
        "difficulty": "intermediate"
    },
    {
        "slug": "event-sourcing-guide",
        "title": "Event Sourcing: Storing State as a Sequence of Events",
        "category": "architecture",
        "outline": "Event store, snapshots, projections, temporal queries, rebuilding state",
        "keywords": ["event sourcing", "events", "audit log"],
        "difficulty": "advanced"
    },
    {
        "slug": "outbox-pattern",
        "title": "Outbox Pattern: Reliable Event Publishing",
        "category": "architecture",
        "outline": "Transactional outbox, polling publisher, CDC, exactly-once delivery",
        "keywords": ["outbox pattern", "reliable messaging", "events"],
        "difficulty": "advanced"
    },
    {
        "slug": "twelve-factor-app",
        "title": "12-Factor App: Principles for Cloud-Native Applications",
        "category": "architecture",
        "outline": "Codebase, dependencies, config, backing services, build/run, processes",
        "keywords": ["12 factor", "cloud native", "best practices"],
        "difficulty": "intermediate"
    },
    {
        "slug": "serverless-architecture",
        "title": "Serverless Architecture: When and How to Go Serverless",
        "category": "architecture",
        "outline": "FaaS, cold starts, cost optimization, event-driven design, limitations",
        "keywords": ["serverless", "lambda", "faas", "cloud"],
        "difficulty": "intermediate"
    },
    {
        "slug": "modular-monolith",
        "title": "Modular Monolith: The Best of Both Worlds",
        "category": "architecture",
        "outline": "Module boundaries, internal APIs, deployment simplicity, future splitting",
        "keywords": ["modular monolith", "architecture", "monolith"],
        "difficulty": "intermediate"
    },
    {
        "slug": "vertical-slice-architecture",
        "title": "Vertical Slice Architecture: Feature-Based Organization",
        "category": "architecture",
        "outline": "Feature folders, minimal abstractions, CQRS alignment, testing strategies",
        "keywords": ["vertical slice", "architecture", "feature organization"],
        "difficulty": "intermediate"
    },
    {
        "slug": "onion-architecture",
        "title": "Onion Architecture: Layered Domain-Centric Design",
        "category": "architecture",
        "outline": "Domain model, domain services, application services, infrastructure",
        "keywords": ["onion architecture", "layered architecture", "ddd"],
        "difficulty": "intermediate"
    },
    {
        "slug": "data-mesh-architecture",
        "title": "Data Mesh: Decentralized Data Architecture",
        "category": "architecture",
        "outline": "Domain ownership, data as product, self-serve platform, federated governance",
        "keywords": ["data mesh", "data architecture", "decentralized"],
        "difficulty": "advanced"
    },
    {
        "slug": "cell-based-architecture",
        "title": "Cell-Based Architecture: Scaling with Isolation",
        "category": "architecture",
        "outline": "Cell design, routing, blast radius reduction, deployment strategies",
        "keywords": ["cell architecture", "scaling", "isolation"],
        "difficulty": "advanced"
    },
    {
        "slug": "actor-model-architecture",
        "title": "Actor Model: Concurrent System Design with Akka",
        "category": "architecture",
        "outline": "Actors, message passing, supervision, location transparency",
        "keywords": ["actor model", "akka", "concurrency"],
        "difficulty": "advanced"
    },
    {
        "slug": "reactive-architecture",
        "title": "Reactive Architecture: Building Responsive Systems",
        "category": "architecture",
        "outline": "Reactive manifesto, back-pressure, non-blocking I/O, reactive streams",
        "keywords": ["reactive", "architecture", "responsive systems"],
        "difficulty": "advanced"
    },
    {
        "slug": "multi-tenant-architecture",
        "title": "Multi-Tenant Architecture: SaaS Design Patterns",
        "category": "architecture",
        "outline": "Tenant isolation, database strategies, customization, billing",
        "keywords": ["multi-tenant", "saas", "architecture"],
        "difficulty": "intermediate"
    },
    {
        "slug": "plugin-architecture",
        "title": "Plugin Architecture: Building Extensible Systems",
        "category": "architecture",
        "outline": "Plugin interfaces, lifecycle management, dependency injection, versioning",
        "keywords": ["plugin architecture", "extensibility", "modular"],
        "difficulty": "intermediate"
    },
    {
        "slug": "pipes-and-filters",
        "title": "Pipes and Filters Pattern: Data Processing Pipelines",
        "category": "architecture",
        "outline": "Filter components, pipeline composition, parallel processing, error handling",
        "keywords": ["pipes filters", "data pipeline", "processing"],
        "difficulty": "intermediate"
    },
    {
        "slug": "space-based-architecture",
        "title": "Space-Based Architecture: Extreme Scalability Patterns",
        "category": "architecture",
        "outline": "Processing units, virtualized middleware, data pumps, data grids",
        "keywords": ["space based architecture", "scalability", "in-memory"],
        "difficulty": "advanced"
    },
    {
        "slug": "caching-strategies",
        "title": "Caching Strategies: Cache-Aside, Write-Through, and More",
        "category": "architecture",
        "outline": "Caching patterns, invalidation strategies, distributed caching, TTL",
        "keywords": ["caching", "cache strategies", "performance"],
        "difficulty": "intermediate"
    },
    {
        "slug": "database-sharding",
        "title": "Database Sharding: Horizontal Scaling Strategies",
        "category": "architecture",
        "outline": "Sharding keys, consistent hashing, cross-shard queries, rebalancing",
        "keywords": ["sharding", "database scaling", "horizontal scaling"],
        "difficulty": "advanced"
    },
    {
        "slug": "read-replica-pattern",
        "title": "Read Replicas: Scaling Database Reads",
        "category": "architecture",
        "outline": "Replication lag, consistency trade-offs, routing strategies, failover",
        "keywords": ["read replicas", "database scaling", "replication"],
        "difficulty": "intermediate"
    },
    {
        "slug": "write-ahead-log",
        "title": "Write-Ahead Log: Durability in Database Systems",
        "category": "architecture",
        "outline": "WAL mechanics, checkpointing, recovery, performance implications",
        "keywords": ["wal", "write ahead log", "database internals"],
        "difficulty": "advanced"
    },
    {
        "slug": "consensus-algorithms",
        "title": "Consensus Algorithms: Raft and Paxos Explained",
        "category": "architecture",
        "outline": "Leader election, log replication, safety guarantees, partition handling",
        "keywords": ["consensus", "raft", "paxos", "distributed systems"],
        "difficulty": "advanced"
    },
    {
        "slug": "cap-theorem-deep-dive",
        "title": "CAP Theorem: Understanding Distributed System Trade-offs",
        "category": "architecture",
        "outline": "Consistency, availability, partition tolerance, PACELC, real-world examples",
        "keywords": ["cap theorem", "distributed systems", "trade-offs"],
        "difficulty": "intermediate"
    },
    {
        "slug": "eventual-consistency",
        "title": "Eventual Consistency: Patterns and Practices",
        "category": "architecture",
        "outline": "Conflict resolution, vector clocks, CRDTs, read-your-writes",
        "keywords": ["eventual consistency", "distributed systems", "crdt"],
        "difficulty": "advanced"
    },
    {
        "slug": "idempotency-patterns",
        "title": "Idempotency in APIs: Designing Safe Retry Logic",
        "category": "architecture",
        "outline": "Idempotency keys, database constraints, deduplication, timeout handling",
        "keywords": ["idempotency", "api design", "reliability"],
        "difficulty": "intermediate"
    },
    {
        "slug": "message-queue-patterns",
        "title": "Message Queue Patterns: Kafka, RabbitMQ, and SQS",
        "category": "architecture",
        "outline": "Point-to-point, pub/sub, dead letter queues, ordering guarantees",
        "keywords": ["message queue", "kafka", "rabbitmq", "sqs"],
        "difficulty": "intermediate"
    },
    {
        "slug": "distributed-tracing",
        "title": "Distributed Tracing: Observability in Microservices",
        "category": "architecture",
        "outline": "Trace context, spans, sampling strategies, Jaeger, Zipkin",
        "keywords": ["distributed tracing", "observability", "jaeger"],
        "difficulty": "intermediate"
    },
    {
        "slug": "feature-flag-architecture",
        "title": "Feature Flag Architecture: Progressive Delivery",
        "category": "architecture",
        "outline": "Flag types, targeting rules, gradual rollouts, kill switches",
        "keywords": ["feature flags", "progressive delivery", "deployment"],
        "difficulty": "intermediate"
    },
    {
        "slug": "blue-green-deployment",
        "title": "Blue-Green Deployment: Zero-Downtime Releases",
        "category": "architecture",
        "outline": "Environment setup, traffic switching, database migrations, rollback",
        "keywords": ["blue green deployment", "zero downtime", "deployment"],
        "difficulty": "intermediate"
    },
    {
        "slug": "canary-deployment",
        "title": "Canary Deployment: Safe Production Rollouts",
        "category": "architecture",
        "outline": "Traffic splitting, metrics monitoring, automated rollback, progressive rollout",
        "keywords": ["canary deployment", "progressive delivery", "rollout"],
        "difficulty": "intermediate"
    },
    {
        "slug": "database-migration-strategies",
        "title": "Database Migration Strategies: Schema Changes Without Downtime",
        "category": "architecture",
        "outline": "Expand-contract, shadow tables, online migrations, version compatibility",
        "keywords": ["database migration", "schema changes", "zero downtime"],
        "difficulty": "intermediate"
    },
    {
        "slug": "api-versioning-strategies",
        "title": "API Versioning: URL, Header, and Media Type Approaches",
        "category": "architecture",
        "outline": "Versioning strategies, backwards compatibility, deprecation, migration paths",
        "keywords": ["api versioning", "backwards compatibility", "api design"],
        "difficulty": "intermediate"
    },
    {
        "slug": "grpc-vs-rest",
        "title": "gRPC vs REST: When to Use Protocol Buffers",
        "category": "architecture",
        "outline": "Performance comparison, streaming, code generation, browser support",
        "keywords": ["grpc", "rest", "protocol buffers", "api"],
        "difficulty": "intermediate"
    },
    {
        "slug": "websocket-architecture",
        "title": "WebSocket Architecture: Real-Time Communication Patterns",
        "category": "architecture",
        "outline": "Connection management, scaling, heartbeats, fallback strategies",
        "keywords": ["websocket", "real-time", "bidirectional"],
        "difficulty": "intermediate"
    },
    {
        "slug": "async-api-design",
        "title": "Async API Design: Handling Long-Running Operations",
        "category": "architecture",
        "outline": "Polling, webhooks, server-sent events, job status tracking",
        "keywords": ["async api", "long running operations", "webhooks"],
        "difficulty": "intermediate"
    },
    {
        "slug": "rate-limiting-strategies",
        "title": "Rate Limiting Strategies: Protecting Your APIs",
        "category": "architecture",
        "outline": "Token bucket, sliding window, distributed rate limiting, headers",
        "keywords": ["rate limiting", "api protection", "throttling"],
        "difficulty": "intermediate"
    },
    {
        "slug": "secrets-management",
        "title": "Secrets Management: Vault, AWS Secrets Manager, and Beyond",
        "category": "architecture",
        "outline": "Secret rotation, access control, encryption, audit logging",
        "keywords": ["secrets management", "vault", "security"],
        "difficulty": "intermediate"
    },
    {
        "slug": "anti-corruption-layer",
        "title": "Anti-Corruption Layer: Protecting Your Domain from External Systems",
        "category": "architecture",
        "outline": "Translation layer, bounded contexts, integration patterns, testing",
        "keywords": ["anti-corruption layer", "ddd", "integration"],
        "difficulty": "intermediate"
    },

    # =============================================================================
    # INTERVIEWS (50 ideas)
    # =============================================================================
    {
        "slug": "system-design-interview-framework",
        "title": "System Design Interview Framework: A Step-by-Step Approach",
        "category": "interviews",
        "outline": "Requirements gathering, high-level design, deep dives, trade-offs discussion",
        "keywords": ["system design interview", "framework", "interview prep"],
        "difficulty": "intermediate"
    },
    {
        "slug": "behavioral-interview-star",
        "title": "STAR Method: Mastering Behavioral Interviews",
        "category": "interviews",
        "outline": "Situation, Task, Action, Result format with real examples",
        "keywords": ["behavioral interview", "star method", "soft skills"],
        "difficulty": "beginner"
    },
    {
        "slug": "google-interview-prep",
        "title": "Google Interview Preparation: Complete Guide",
        "category": "interviews",
        "outline": "Interview process, coding rounds, system design, Googleyness",
        "keywords": ["google interview", "faang", "interview prep"],
        "difficulty": "intermediate"
    },
    {
        "slug": "amazon-leadership-principles",
        "title": "Amazon Leadership Principles: Interview Deep Dive",
        "category": "interviews",
        "outline": "14 leadership principles, example questions, story preparation",
        "keywords": ["amazon interview", "leadership principles", "behavioral"],
        "difficulty": "intermediate"
    },
    {
        "slug": "meta-interview-guide",
        "title": "Meta Interview Guide: What to Expect and How to Prepare",
        "category": "interviews",
        "outline": "Interview rounds, coding focus, system design, culture fit",
        "keywords": ["meta interview", "facebook", "faang"],
        "difficulty": "intermediate"
    },
    {
        "slug": "netflix-culture-interview",
        "title": "Netflix Interview: Culture and Technical Expectations",
        "category": "interviews",
        "outline": "Culture deck, technical depth, senior expectations, feedback culture",
        "keywords": ["netflix interview", "culture", "senior engineer"],
        "difficulty": "advanced"
    },
    {
        "slug": "startup-vs-faang-interviews",
        "title": "Startup vs FAANG Interviews: Key Differences",
        "category": "interviews",
        "outline": "Process differences, expectations, evaluation criteria, preparation tips",
        "keywords": ["startup interview", "faang comparison", "interview differences"],
        "difficulty": "intermediate"
    },
    {
        "slug": "staff-engineer-interview",
        "title": "Staff Engineer Interview: What Makes It Different",
        "category": "interviews",
        "outline": "Scope and influence, cross-team collaboration, technical vision, mentorship",
        "keywords": ["staff engineer", "senior interview", "career growth"],
        "difficulty": "advanced"
    },
    {
        "slug": "system-design-estimation",
        "title": "Back-of-Envelope Estimation: Numbers Every Engineer Should Know",
        "category": "interviews",
        "outline": "Latency numbers, storage calculations, throughput estimation, capacity planning",
        "keywords": ["estimation", "system design", "capacity planning"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-interview-mistakes",
        "title": "10 Common System Design Interview Mistakes",
        "category": "interviews",
        "outline": "Jumping to solutions, ignoring trade-offs, poor communication, scope creep",
        "keywords": ["interview mistakes", "system design", "tips"],
        "difficulty": "beginner"
    },
    {
        "slug": "coding-interview-patterns",
        "title": "Coding Interview Patterns: The 15 Essential Patterns",
        "category": "interviews",
        "outline": "Two pointers, sliding window, BFS/DFS, dynamic programming, and more",
        "keywords": ["coding interview", "patterns", "algorithms"],
        "difficulty": "intermediate"
    },
    {
        "slug": "whiteboard-coding-tips",
        "title": "Whiteboard Coding: Tips for In-Person Interviews",
        "category": "interviews",
        "outline": "Space management, thinking aloud, handling mistakes, time management",
        "keywords": ["whiteboard coding", "in-person interview", "tips"],
        "difficulty": "beginner"
    },
    {
        "slug": "remote-interview-tips",
        "title": "Remote Technical Interview Tips: Succeed from Home",
        "category": "interviews",
        "outline": "Setup, communication, screen sharing, handling technical issues",
        "keywords": ["remote interview", "virtual interview", "work from home"],
        "difficulty": "beginner"
    },
    {
        "slug": "salary-negotiation-engineers",
        "title": "Salary Negotiation for Software Engineers: Complete Guide",
        "category": "interviews",
        "outline": "Research, timing, competing offers, total compensation, equity",
        "keywords": ["salary negotiation", "compensation", "job offer"],
        "difficulty": "intermediate"
    },
    {
        "slug": "interview-questions-to-ask",
        "title": "Questions to Ask Your Interviewer: Making a Good Impression",
        "category": "interviews",
        "outline": "Team questions, technical questions, culture questions, red flags",
        "keywords": ["interview questions", "ask interviewer", "due diligence"],
        "difficulty": "beginner"
    },
    {
        "slug": "mock-interview-practice",
        "title": "How to Practice with Mock Interviews Effectively",
        "category": "interviews",
        "outline": "Finding partners, platforms, giving feedback, tracking progress",
        "keywords": ["mock interview", "practice", "preparation"],
        "difficulty": "beginner"
    },
    {
        "slug": "design-notification-interview",
        "title": "Design a Notification System: Interview Walkthrough",
        "category": "interviews",
        "outline": "Requirements, components, scaling, prioritization, delivery guarantees",
        "keywords": ["notification system", "interview question", "system design"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-cache-interview",
        "title": "Design a Distributed Cache: Interview Walkthrough",
        "category": "interviews",
        "outline": "Eviction policies, consistency, partitioning, replication",
        "keywords": ["distributed cache", "interview question", "system design"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-search-interview",
        "title": "Design a Search System: Interview Walkthrough",
        "category": "interviews",
        "outline": "Indexing, ranking, relevance, scaling, real-time updates",
        "keywords": ["search system", "interview question", "system design"],
        "difficulty": "advanced"
    },
    {
        "slug": "design-payment-interview",
        "title": "Design a Payment System: Interview Walkthrough",
        "category": "interviews",
        "outline": "Transaction flow, idempotency, security, reconciliation",
        "keywords": ["payment system", "interview question", "fintech"],
        "difficulty": "advanced"
    },
    {
        "slug": "design-ride-sharing-interview",
        "title": "Design Uber/Lyft: Interview Walkthrough",
        "category": "interviews",
        "outline": "Matching algorithm, location services, pricing, surge handling",
        "keywords": ["ride sharing", "uber", "interview question"],
        "difficulty": "advanced"
    },
    {
        "slug": "design-social-network-interview",
        "title": "Design a Social Network: Interview Walkthrough",
        "category": "interviews",
        "outline": "User graph, feed generation, notifications, privacy",
        "keywords": ["social network", "interview question", "system design"],
        "difficulty": "advanced"
    },
    {
        "slug": "design-video-streaming-interview",
        "title": "Design Netflix/YouTube: Interview Walkthrough",
        "category": "interviews",
        "outline": "Video encoding, CDN, recommendations, streaming protocols",
        "keywords": ["video streaming", "netflix", "interview question"],
        "difficulty": "advanced"
    },
    {
        "slug": "design-chat-interview",
        "title": "Design WhatsApp: Interview Walkthrough",
        "category": "interviews",
        "outline": "Real-time messaging, presence, group chat, encryption",
        "keywords": ["chat system", "whatsapp", "interview question"],
        "difficulty": "advanced"
    },
    {
        "slug": "design-ecommerce-interview",
        "title": "Design Amazon: Interview Walkthrough",
        "category": "interviews",
        "outline": "Product catalog, cart, checkout, inventory, recommendations",
        "keywords": ["ecommerce", "amazon", "interview question"],
        "difficulty": "advanced"
    },
    {
        "slug": "coding-interview-tree-problems",
        "title": "Tree Problems in Coding Interviews: Complete Guide",
        "category": "interviews",
        "outline": "Traversals, BST operations, balanced trees, common patterns",
        "keywords": ["trees", "coding interview", "data structures"],
        "difficulty": "intermediate"
    },
    {
        "slug": "coding-interview-graph-problems",
        "title": "Graph Problems in Coding Interviews: BFS, DFS, and Beyond",
        "category": "interviews",
        "outline": "Traversals, shortest path, topological sort, cycle detection",
        "keywords": ["graphs", "coding interview", "algorithms"],
        "difficulty": "intermediate"
    },
    {
        "slug": "coding-interview-dp",
        "title": "Dynamic Programming Interview Questions: Patterns and Solutions",
        "category": "interviews",
        "outline": "Memoization vs tabulation, common patterns, optimization",
        "keywords": ["dynamic programming", "coding interview", "dp"],
        "difficulty": "advanced"
    },
    {
        "slug": "coding-interview-strings",
        "title": "String Manipulation Interview Questions",
        "category": "interviews",
        "outline": "Pattern matching, parsing, substring problems, anagrams",
        "keywords": ["strings", "coding interview", "algorithms"],
        "difficulty": "intermediate"
    },
    {
        "slug": "coding-interview-arrays",
        "title": "Array Interview Questions: Two Pointers and Sliding Window",
        "category": "interviews",
        "outline": "In-place operations, subarrays, sorted arrays, matrix problems",
        "keywords": ["arrays", "coding interview", "two pointers"],
        "difficulty": "intermediate"
    },
    {
        "slug": "interview-anxiety-management",
        "title": "Managing Interview Anxiety: Techniques That Work",
        "category": "interviews",
        "outline": "Preparation routines, breathing exercises, reframing, building confidence",
        "keywords": ["interview anxiety", "stress management", "confidence"],
        "difficulty": "beginner"
    },
    {
        "slug": "take-home-assignment-tips",
        "title": "Take-Home Assignment Tips: Stand Out from Other Candidates",
        "category": "interviews",
        "outline": "Time management, documentation, testing, going the extra mile",
        "keywords": ["take home assignment", "interview project", "coding test"],
        "difficulty": "beginner"
    },
    {
        "slug": "api-design-interview",
        "title": "API Design Interview Questions: REST and Beyond",
        "category": "interviews",
        "outline": "Resource modeling, versioning, pagination, error handling",
        "keywords": ["api design", "interview question", "rest api"],
        "difficulty": "intermediate"
    },
    {
        "slug": "database-interview-questions",
        "title": "Database Interview Questions: SQL and NoSQL",
        "category": "interviews",
        "outline": "Query optimization, indexing, transactions, CAP theorem",
        "keywords": ["database interview", "sql", "nosql"],
        "difficulty": "intermediate"
    },
    {
        "slug": "concurrency-interview",
        "title": "Concurrency Interview Questions: Threads, Locks, and More",
        "category": "interviews",
        "outline": "Race conditions, deadlocks, thread-safe patterns, async programming",
        "keywords": ["concurrency", "interview questions", "multithreading"],
        "difficulty": "advanced"
    },
    {
        "slug": "oop-design-interview",
        "title": "Object-Oriented Design Interview Questions",
        "category": "interviews",
        "outline": "Design patterns, SOLID principles, class diagrams, real examples",
        "keywords": ["oop", "design interview", "object oriented"],
        "difficulty": "intermediate"
    },
    {
        "slug": "low-level-design-interview",
        "title": "Low-Level Design Interview: Machine Coding Round",
        "category": "interviews",
        "outline": "Class design, interfaces, extensibility, code organization",
        "keywords": ["low level design", "machine coding", "lld"],
        "difficulty": "intermediate"
    },
    {
        "slug": "interview-follow-up-email",
        "title": "Interview Follow-Up: Emails That Get Responses",
        "category": "interviews",
        "outline": "Thank you notes, timing, content, handling silence",
        "keywords": ["follow up email", "after interview", "thank you note"],
        "difficulty": "beginner"
    },
    {
        "slug": "referral-job-search",
        "title": "Getting Referrals: The Most Effective Job Search Strategy",
        "category": "interviews",
        "outline": "Building network, asking for referrals, LinkedIn strategies",
        "keywords": ["job referral", "networking", "job search"],
        "difficulty": "beginner"
    },
    {
        "slug": "portfolio-projects-engineers",
        "title": "Portfolio Projects That Impress: What to Build",
        "category": "interviews",
        "outline": "Project ideas, documentation, deployment, code quality",
        "keywords": ["portfolio", "side projects", "resume"],
        "difficulty": "beginner"
    },
    {
        "slug": "resume-software-engineer",
        "title": "Software Engineer Resume: What Actually Gets Interviews",
        "category": "interviews",
        "outline": "Format, content, keywords, ATS optimization, impact statements",
        "keywords": ["resume", "cv", "job application"],
        "difficulty": "beginner"
    },
    {
        "slug": "linkedin-profile-engineers",
        "title": "LinkedIn Profile Optimization for Software Engineers",
        "category": "interviews",
        "outline": "Headline, summary, experience, skills, recruiter visibility",
        "keywords": ["linkedin", "profile", "job search"],
        "difficulty": "beginner"
    },
    {
        "slug": "interview-red-flags",
        "title": "Interview Red Flags: Signs of a Bad Workplace",
        "category": "interviews",
        "outline": "Process red flags, cultural red flags, technical red flags",
        "keywords": ["red flags", "interview warning signs", "company research"],
        "difficulty": "beginner"
    },
    {
        "slug": "career-change-to-tech",
        "title": "Career Change to Tech: Complete Roadmap",
        "category": "interviews",
        "outline": "Learning path, building experience, first job strategies",
        "keywords": ["career change", "breaking into tech", "bootcamp"],
        "difficulty": "beginner"
    },
    {
        "slug": "interview-without-experience",
        "title": "How to Interview Without Professional Experience",
        "category": "interviews",
        "outline": "Highlighting projects, transferable skills, storytelling",
        "keywords": ["entry level", "no experience", "first job"],
        "difficulty": "beginner"
    },
    {
        "slug": "design-metrics-dashboard-interview",
        "title": "Design a Metrics Dashboard: Interview Walkthrough",
        "category": "interviews",
        "outline": "Data pipeline, aggregation, real-time updates, visualization",
        "keywords": ["metrics dashboard", "interview question", "analytics"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-file-storage-interview",
        "title": "Design Google Drive: Interview Walkthrough",
        "category": "interviews",
        "outline": "File storage, sync, sharing, versioning, collaboration",
        "keywords": ["file storage", "google drive", "interview question"],
        "difficulty": "advanced"
    },
    {
        "slug": "design-booking-system-interview",
        "title": "Design a Booking System: Interview Walkthrough",
        "category": "interviews",
        "outline": "Availability, reservations, double-booking prevention, pricing",
        "keywords": ["booking system", "interview question", "system design"],
        "difficulty": "intermediate"
    },
    {
        "slug": "design-food-delivery-interview",
        "title": "Design DoorDash: Interview Walkthrough",
        "category": "interviews",
        "outline": "Order flow, dispatch, ETA, restaurant integration",
        "keywords": ["food delivery", "doordash", "interview question"],
        "difficulty": "advanced"
    },
    {
        "slug": "design-monitoring-interview",
        "title": "Design a Monitoring System: Interview Walkthrough",
        "category": "interviews",
        "outline": "Metrics collection, alerting, dashboards, scaling",
        "keywords": ["monitoring system", "interview question", "observability"],
        "difficulty": "intermediate"
    },

    # =============================================================================
    # DEVOPS (55 ideas)
    # =============================================================================
    {
        "slug": "kubernetes-basics",
        "title": "Kubernetes Basics: Pods, Services, and Deployments",
        "category": "devops",
        "outline": "Core concepts, YAML manifests, kubectl commands, getting started",
        "keywords": ["kubernetes", "k8s", "containers", "orchestration"],
        "difficulty": "beginner"
    },
    {
        "slug": "docker-best-practices",
        "title": "Docker Best Practices: Writing Production-Ready Dockerfiles",
        "category": "devops",
        "outline": "Multi-stage builds, layer caching, security, image size optimization",
        "keywords": ["docker", "dockerfile", "containers", "best practices"],
        "difficulty": "intermediate"
    },
    {
        "slug": "cicd-pipeline-design",
        "title": "CI/CD Pipeline Design: From Commit to Production",
        "category": "devops",
        "outline": "Pipeline stages, testing strategies, deployment automation, rollback",
        "keywords": ["cicd", "pipeline", "continuous integration", "deployment"],
        "difficulty": "intermediate"
    },
    {
        "slug": "github-actions-guide",
        "title": "GitHub Actions: Complete CI/CD Guide",
        "category": "devops",
        "outline": "Workflows, jobs, actions, secrets, matrix builds, caching",
        "keywords": ["github actions", "cicd", "automation"],
        "difficulty": "intermediate"
    },
    {
        "slug": "jenkins-vs-github-actions",
        "title": "Jenkins vs GitHub Actions: Which CI/CD Tool to Choose",
        "category": "devops",
        "outline": "Feature comparison, use cases, migration considerations",
        "keywords": ["jenkins", "github actions", "cicd comparison"],
        "difficulty": "intermediate"
    },
    {
        "slug": "terraform-basics",
        "title": "Terraform Basics: Infrastructure as Code Introduction",
        "category": "devops",
        "outline": "HCL syntax, providers, state management, modules, workspaces",
        "keywords": ["terraform", "iac", "infrastructure as code"],
        "difficulty": "beginner"
    },
    {
        "slug": "terraform-best-practices",
        "title": "Terraform Best Practices: Modules, State, and Team Workflows",
        "category": "devops",
        "outline": "Module design, remote state, workspaces, CI/CD integration",
        "keywords": ["terraform", "best practices", "iac"],
        "difficulty": "intermediate"
    },
    {
        "slug": "kubernetes-helm-charts",
        "title": "Helm Charts: Kubernetes Package Management",
        "category": "devops",
        "outline": "Chart structure, values, templates, dependencies, chart repositories",
        "keywords": ["helm", "kubernetes", "package management"],
        "difficulty": "intermediate"
    },
    {
        "slug": "kubernetes-operators",
        "title": "Kubernetes Operators: Automating Application Management",
        "category": "devops",
        "outline": "Custom resources, reconciliation loop, operator SDK, use cases",
        "keywords": ["kubernetes operators", "custom resources", "automation"],
        "difficulty": "advanced"
    },
    {
        "slug": "kubernetes-networking",
        "title": "Kubernetes Networking: Services, Ingress, and Network Policies",
        "category": "devops",
        "outline": "Service types, ingress controllers, CNI, network policies",
        "keywords": ["kubernetes networking", "ingress", "services"],
        "difficulty": "intermediate"
    },
    {
        "slug": "kubernetes-storage",
        "title": "Kubernetes Storage: Volumes, PVs, and Storage Classes",
        "category": "devops",
        "outline": "Volume types, persistent volumes, storage classes, CSI drivers",
        "keywords": ["kubernetes storage", "persistent volumes", "pvc"],
        "difficulty": "intermediate"
    },
    {
        "slug": "kubernetes-security",
        "title": "Kubernetes Security: RBAC, Pod Security, and Secrets",
        "category": "devops",
        "outline": "RBAC, service accounts, pod security standards, secrets management",
        "keywords": ["kubernetes security", "rbac", "pod security"],
        "difficulty": "intermediate"
    },
    {
        "slug": "gitops-argocd",
        "title": "GitOps with ArgoCD: Declarative Kubernetes Deployments",
        "category": "devops",
        "outline": "GitOps principles, ArgoCD setup, sync strategies, rollback",
        "keywords": ["gitops", "argocd", "kubernetes", "deployment"],
        "difficulty": "intermediate"
    },
    {
        "slug": "prometheus-monitoring",
        "title": "Prometheus Monitoring: Metrics Collection and Alerting",
        "category": "devops",
        "outline": "Metrics types, PromQL, alerting rules, Grafana integration",
        "keywords": ["prometheus", "monitoring", "metrics", "alerting"],
        "difficulty": "intermediate"
    },
    {
        "slug": "grafana-dashboards",
        "title": "Grafana Dashboards: Visualization Best Practices",
        "category": "devops",
        "outline": "Panel types, variables, annotations, alerting, dashboard design",
        "keywords": ["grafana", "dashboards", "visualization"],
        "difficulty": "intermediate"
    },
    {
        "slug": "elk-stack-logging",
        "title": "ELK Stack: Centralized Logging with Elasticsearch",
        "category": "devops",
        "outline": "Elasticsearch, Logstash, Kibana, Filebeat, log parsing",
        "keywords": ["elk stack", "logging", "elasticsearch", "kibana"],
        "difficulty": "intermediate"
    },
    {
        "slug": "opentelemetry-guide",
        "title": "OpenTelemetry: Unified Observability for Modern Apps",
        "category": "devops",
        "outline": "Traces, metrics, logs, instrumentation, exporters",
        "keywords": ["opentelemetry", "observability", "tracing"],
        "difficulty": "intermediate"
    },
    {
        "slug": "incident-management",
        "title": "Incident Management: On-Call Best Practices",
        "category": "devops",
        "outline": "Alert fatigue, runbooks, post-mortems, on-call rotations",
        "keywords": ["incident management", "on-call", "sre"],
        "difficulty": "intermediate"
    },
    {
        "slug": "sre-sli-slo-sla",
        "title": "SLIs, SLOs, and SLAs: Reliability Engineering Fundamentals",
        "category": "devops",
        "outline": "Defining indicators, setting objectives, error budgets",
        "keywords": ["sre", "sli", "slo", "sla", "reliability"],
        "difficulty": "intermediate"
    },
    {
        "slug": "chaos-engineering",
        "title": "Chaos Engineering: Testing System Resilience",
        "category": "devops",
        "outline": "Principles, tools (Chaos Monkey, Gremlin), experiment design",
        "keywords": ["chaos engineering", "resilience", "testing"],
        "difficulty": "advanced"
    },
    {
        "slug": "load-testing-guide",
        "title": "Load Testing: K6, JMeter, and Locust Compared",
        "category": "devops",
        "outline": "Test types, tool comparison, scripting, analysis",
        "keywords": ["load testing", "performance testing", "k6"],
        "difficulty": "intermediate"
    },
    {
        "slug": "ansible-automation",
        "title": "Ansible Automation: Configuration Management Guide",
        "category": "devops",
        "outline": "Playbooks, roles, inventory, modules, idempotency",
        "keywords": ["ansible", "automation", "configuration management"],
        "difficulty": "intermediate"
    },
    {
        "slug": "nginx-configuration",
        "title": "NGINX Configuration: From Basic to Advanced",
        "category": "devops",
        "outline": "Server blocks, reverse proxy, load balancing, caching, SSL",
        "keywords": ["nginx", "web server", "reverse proxy"],
        "difficulty": "intermediate"
    },
    {
        "slug": "linux-commands-devops",
        "title": "Essential Linux Commands for DevOps Engineers",
        "category": "devops",
        "outline": "File operations, process management, networking, troubleshooting",
        "keywords": ["linux", "commands", "devops", "sysadmin"],
        "difficulty": "beginner"
    },
    {
        "slug": "bash-scripting-devops",
        "title": "Bash Scripting for DevOps: Automation Essentials",
        "category": "devops",
        "outline": "Variables, loops, functions, error handling, best practices",
        "keywords": ["bash", "scripting", "automation", "shell"],
        "difficulty": "intermediate"
    },
    {
        "slug": "container-security",
        "title": "Container Security: Scanning, Runtime, and Best Practices",
        "category": "devops",
        "outline": "Image scanning, runtime security, secrets, least privilege",
        "keywords": ["container security", "docker security", "scanning"],
        "difficulty": "intermediate"
    },
    {
        "slug": "kubernetes-autoscaling",
        "title": "Kubernetes Autoscaling: HPA, VPA, and Cluster Autoscaler",
        "category": "devops",
        "outline": "Horizontal pod autoscaler, vertical scaling, cluster scaling",
        "keywords": ["kubernetes autoscaling", "hpa", "scaling"],
        "difficulty": "intermediate"
    },
    {
        "slug": "kubernetes-troubleshooting",
        "title": "Kubernetes Troubleshooting: Common Issues and Solutions",
        "category": "devops",
        "outline": "Pod debugging, networking issues, resource constraints, logs",
        "keywords": ["kubernetes troubleshooting", "debugging", "k8s"],
        "difficulty": "intermediate"
    },
    {
        "slug": "service-mesh-comparison",
        "title": "Service Mesh Comparison: Istio vs Linkerd vs Consul",
        "category": "devops",
        "outline": "Feature comparison, performance, complexity, use cases",
        "keywords": ["service mesh", "istio", "linkerd", "consul"],
        "difficulty": "advanced"
    },
    {
        "slug": "secrets-in-kubernetes",
        "title": "Secrets Management in Kubernetes: Options and Best Practices",
        "category": "devops",
        "outline": "Native secrets, sealed secrets, external secrets, Vault integration",
        "keywords": ["kubernetes secrets", "secrets management", "vault"],
        "difficulty": "intermediate"
    },
    {
        "slug": "docker-compose-production",
        "title": "Docker Compose for Development and Beyond",
        "category": "devops",
        "outline": "Service definitions, networking, volumes, environment variables",
        "keywords": ["docker compose", "local development", "containers"],
        "difficulty": "beginner"
    },
    {
        "slug": "immutable-infrastructure",
        "title": "Immutable Infrastructure: Principles and Implementation",
        "category": "devops",
        "outline": "Golden images, deployment patterns, rollback strategies",
        "keywords": ["immutable infrastructure", "deployment", "devops"],
        "difficulty": "intermediate"
    },
    {
        "slug": "infrastructure-testing",
        "title": "Infrastructure Testing: Terratest, InSpec, and More",
        "category": "devops",
        "outline": "Testing IaC, compliance testing, integration testing",
        "keywords": ["infrastructure testing", "terratest", "compliance"],
        "difficulty": "intermediate"
    },
    {
        "slug": "cost-optimization-cloud",
        "title": "Cloud Cost Optimization: Strategies That Actually Work",
        "category": "devops",
        "outline": "Right-sizing, reserved instances, spot instances, monitoring",
        "keywords": ["cost optimization", "cloud costs", "finops"],
        "difficulty": "intermediate"
    },
    {
        "slug": "ssl-tls-certificates",
        "title": "SSL/TLS Certificates: Complete Management Guide",
        "category": "devops",
        "outline": "Certificate types, Let's Encrypt, renewal automation, troubleshooting",
        "keywords": ["ssl", "tls", "certificates", "https"],
        "difficulty": "intermediate"
    },
    {
        "slug": "dns-for-developers",
        "title": "DNS for Developers: How Domain Resolution Works",
        "category": "devops",
        "outline": "Record types, propagation, TTL, common configurations",
        "keywords": ["dns", "domain", "networking"],
        "difficulty": "beginner"
    },
    {
        "slug": "vpc-networking-aws",
        "title": "VPC Networking: Subnets, Security Groups, and NAT",
        "category": "devops",
        "outline": "VPC design, public/private subnets, routing, peering",
        "keywords": ["vpc", "networking", "aws", "security groups"],
        "difficulty": "intermediate"
    },
    {
        "slug": "database-backups",
        "title": "Database Backup Strategies: RTO, RPO, and Best Practices",
        "category": "devops",
        "outline": "Backup types, scheduling, testing restores, disaster recovery",
        "keywords": ["database backup", "disaster recovery", "rto rpo"],
        "difficulty": "intermediate"
    },
    {
        "slug": "log-aggregation-patterns",
        "title": "Log Aggregation Patterns: Centralized Logging Architecture",
        "category": "devops",
        "outline": "Collection, parsing, storage, retention, search",
        "keywords": ["log aggregation", "logging", "observability"],
        "difficulty": "intermediate"
    },
    {
        "slug": "alerting-best-practices",
        "title": "Alerting Best Practices: Reducing Noise and Fatigue",
        "category": "devops",
        "outline": "Alert hierarchy, actionable alerts, escalation, documentation",
        "keywords": ["alerting", "monitoring", "on-call"],
        "difficulty": "intermediate"
    },
    {
        "slug": "deployment-rollback",
        "title": "Deployment Rollback Strategies: When Things Go Wrong",
        "category": "devops",
        "outline": "Rollback triggers, database considerations, feature flags",
        "keywords": ["rollback", "deployment", "disaster recovery"],
        "difficulty": "intermediate"
    },
    {
        "slug": "container-orchestration-comparison",
        "title": "Container Orchestration: Kubernetes vs ECS vs Docker Swarm",
        "category": "devops",
        "outline": "Feature comparison, complexity, managed services, use cases",
        "keywords": ["container orchestration", "kubernetes", "ecs"],
        "difficulty": "intermediate"
    },
    {
        "slug": "infrastructure-drift",
        "title": "Infrastructure Drift: Detection and Prevention",
        "category": "devops",
        "outline": "Drift causes, detection tools, remediation, prevention strategies",
        "keywords": ["infrastructure drift", "terraform", "iac"],
        "difficulty": "intermediate"
    },
    {
        "slug": "zero-downtime-deployment",
        "title": "Zero-Downtime Deployments: Techniques and Trade-offs",
        "category": "devops",
        "outline": "Rolling updates, blue-green, canary, database migrations",
        "keywords": ["zero downtime", "deployment", "availability"],
        "difficulty": "intermediate"
    },
    {
        "slug": "kubernetes-resource-management",
        "title": "Kubernetes Resource Management: Requests, Limits, and QoS",
        "category": "devops",
        "outline": "Resource quotas, limit ranges, QoS classes, capacity planning",
        "keywords": ["kubernetes resources", "limits", "requests"],
        "difficulty": "intermediate"
    },
    {
        "slug": "multi-environment-management",
        "title": "Multi-Environment Management: Dev, Staging, and Production",
        "category": "devops",
        "outline": "Environment parity, configuration management, promotion",
        "keywords": ["environments", "staging", "production"],
        "difficulty": "intermediate"
    },
    {
        "slug": "artifact-management",
        "title": "Artifact Management: Docker Registry, Nexus, and Artifactory",
        "category": "devops",
        "outline": "Registry options, versioning, cleanup policies, security",
        "keywords": ["artifact management", "docker registry", "nexus"],
        "difficulty": "intermediate"
    },
    {
        "slug": "configuration-management-comparison",
        "title": "Configuration Management: Ansible vs Chef vs Puppet",
        "category": "devops",
        "outline": "Approach comparison, learning curve, use cases, ecosystem",
        "keywords": ["configuration management", "ansible", "chef", "puppet"],
        "difficulty": "intermediate"
    },
    {
        "slug": "kubernetes-multi-cluster",
        "title": "Multi-Cluster Kubernetes: Federation and Management",
        "category": "devops",
        "outline": "Use cases, federation patterns, traffic management, tooling",
        "keywords": ["multi-cluster", "kubernetes", "federation"],
        "difficulty": "advanced"
    },
    {
        "slug": "devops-metrics",
        "title": "DevOps Metrics: DORA and Beyond",
        "category": "devops",
        "outline": "Deployment frequency, lead time, MTTR, change failure rate",
        "keywords": ["devops metrics", "dora", "engineering metrics"],
        "difficulty": "intermediate"
    },
    {
        "slug": "kubernetes-debugging-tools",
        "title": "Kubernetes Debugging Tools: kubectl, k9s, and Lens",
        "category": "devops",
        "outline": "kubectl tricks, k9s navigation, Lens features, debugging workflows",
        "keywords": ["kubernetes tools", "debugging", "k9s", "lens"],
        "difficulty": "beginner"
    },
    {
        "slug": "policy-as-code",
        "title": "Policy as Code: OPA, Kyverno, and Compliance Automation",
        "category": "devops",
        "outline": "Policy engines, admission control, compliance checks",
        "keywords": ["policy as code", "opa", "kyverno", "compliance"],
        "difficulty": "advanced"
    },
    {
        "slug": "platform-engineering",
        "title": "Platform Engineering: Building Internal Developer Platforms",
        "category": "devops",
        "outline": "Platform team, self-service, golden paths, developer experience",
        "keywords": ["platform engineering", "internal platform", "developer experience"],
        "difficulty": "advanced"
    },
    {
        "slug": "progressive-delivery",
        "title": "Progressive Delivery: Feature Flags and Gradual Rollouts",
        "category": "devops",
        "outline": "Feature flags, percentage rollouts, targeting, experimentation",
        "keywords": ["progressive delivery", "feature flags", "rollout"],
        "difficulty": "intermediate"
    },
    {
        "slug": "kubernetes-backup-restore",
        "title": "Kubernetes Backup and Restore: Velero and Beyond",
        "category": "devops",
        "outline": "Backup strategies, Velero setup, disaster recovery, testing",
        "keywords": ["kubernetes backup", "velero", "disaster recovery"],
        "difficulty": "intermediate"
    },

    # =============================================================================
    # CLOUD (55 ideas)
    # =============================================================================
    {
        "slug": "aws-vs-azure-vs-gcp",
        "title": "AWS vs Azure vs GCP: Cloud Provider Comparison",
        "category": "cloud",
        "outline": "Service mapping, pricing, strengths, migration considerations",
        "keywords": ["aws", "azure", "gcp", "cloud comparison"],
        "difficulty": "intermediate"
    },
    {
        "slug": "aws-lambda-guide",
        "title": "AWS Lambda: Serverless Functions Complete Guide",
        "category": "cloud",
        "outline": "Function design, triggers, cold starts, layers, best practices",
        "keywords": ["aws lambda", "serverless", "functions"],
        "difficulty": "intermediate"
    },
    {
        "slug": "aws-s3-best-practices",
        "title": "AWS S3 Best Practices: Storage, Security, and Performance",
        "category": "cloud",
        "outline": "Bucket policies, lifecycle rules, versioning, encryption, performance",
        "keywords": ["aws s3", "object storage", "cloud storage"],
        "difficulty": "intermediate"
    },
    {
        "slug": "aws-dynamodb-guide",
        "title": "AWS DynamoDB: NoSQL Database Deep Dive",
        "category": "cloud",
        "outline": "Data modeling, partition keys, GSIs, capacity modes, best practices",
        "keywords": ["dynamodb", "nosql", "aws database"],
        "difficulty": "intermediate"
    },
    {
        "slug": "aws-rds-aurora",
        "title": "AWS RDS and Aurora: Managed Databases Explained",
        "category": "cloud",
        "outline": "Instance types, read replicas, Aurora serverless, backups",
        "keywords": ["aws rds", "aurora", "managed database"],
        "difficulty": "intermediate"
    },
    {
        "slug": "aws-ecs-fargate",
        "title": "AWS ECS and Fargate: Container Orchestration Guide",
        "category": "cloud",
        "outline": "Task definitions, services, Fargate vs EC2, networking",
        "keywords": ["aws ecs", "fargate", "containers"],
        "difficulty": "intermediate"
    },
    {
        "slug": "aws-eks-guide",
        "title": "AWS EKS: Managed Kubernetes Deep Dive",
        "category": "cloud",
        "outline": "Cluster setup, node groups, networking, add-ons, cost optimization",
        "keywords": ["aws eks", "kubernetes", "managed kubernetes"],
        "difficulty": "intermediate"
    },
    {
        "slug": "aws-api-gateway",
        "title": "AWS API Gateway: Building Serverless APIs",
        "category": "cloud",
        "outline": "REST vs HTTP APIs, Lambda integration, authorization, throttling",
        "keywords": ["api gateway", "serverless", "aws api"],
        "difficulty": "intermediate"
    },
    {
        "slug": "aws-sqs-sns",
        "title": "AWS SQS and SNS: Messaging Services Explained",
        "category": "cloud",
        "outline": "Queues vs topics, FIFO, dead-letter queues, fan-out patterns",
        "keywords": ["aws sqs", "sns", "messaging", "queues"],
        "difficulty": "intermediate"
    },
    {
        "slug": "aws-cloudformation",
        "title": "AWS CloudFormation: Infrastructure as Code Guide",
        "category": "cloud",
        "outline": "Template structure, intrinsic functions, nested stacks, drift detection",
        "keywords": ["cloudformation", "iac", "aws infrastructure"],
        "difficulty": "intermediate"
    },
    {
        "slug": "aws-cdk-guide",
        "title": "AWS CDK: Infrastructure as Code with Programming Languages",
        "category": "cloud",
        "outline": "Constructs, stacks, aspects, testing, best practices",
        "keywords": ["aws cdk", "iac", "infrastructure as code"],
        "difficulty": "intermediate"
    },
    {
        "slug": "aws-iam-guide",
        "title": "AWS IAM: Security and Access Management Deep Dive",
        "category": "cloud",
        "outline": "Policies, roles, identity federation, best practices, troubleshooting",
        "keywords": ["aws iam", "security", "access management"],
        "difficulty": "intermediate"
    },
    {
        "slug": "aws-cloudwatch",
        "title": "AWS CloudWatch: Monitoring and Observability Guide",
        "category": "cloud",
        "outline": "Metrics, logs, alarms, dashboards, insights, Container Insights",
        "keywords": ["cloudwatch", "monitoring", "aws observability"],
        "difficulty": "intermediate"
    },
    {
        "slug": "aws-step-functions",
        "title": "AWS Step Functions: Orchestrating Serverless Workflows",
        "category": "cloud",
        "outline": "State machines, workflow patterns, error handling, Express workflows",
        "keywords": ["step functions", "workflow", "serverless"],
        "difficulty": "intermediate"
    },
    {
        "slug": "aws-eventbridge",
        "title": "AWS EventBridge: Event-Driven Architecture",
        "category": "cloud",
        "outline": "Event buses, rules, scheduling, cross-account events, archives",
        "keywords": ["eventbridge", "events", "serverless"],
        "difficulty": "intermediate"
    },
    {
        "slug": "aws-cognito-guide",
        "title": "AWS Cognito: User Authentication and Authorization",
        "category": "cloud",
        "outline": "User pools, identity pools, OAuth flows, customization",
        "keywords": ["aws cognito", "authentication", "identity"],
        "difficulty": "intermediate"
    },
    {
        "slug": "aws-cloudfront-guide",
        "title": "AWS CloudFront: CDN Configuration and Optimization",
        "category": "cloud",
        "outline": "Distributions, behaviors, caching, Lambda@Edge, security",
        "keywords": ["cloudfront", "cdn", "aws edge"],
        "difficulty": "intermediate"
    },
    {
        "slug": "aws-route53-guide",
        "title": "AWS Route 53: DNS and Traffic Management",
        "category": "cloud",
        "outline": "Hosted zones, routing policies, health checks, domain registration",
        "keywords": ["route53", "dns", "traffic management"],
        "difficulty": "intermediate"
    },
    {
        "slug": "aws-elasticache",
        "title": "AWS ElastiCache: Redis and Memcached in the Cloud",
        "category": "cloud",
        "outline": "Cluster modes, scaling, replication, use cases, best practices",
        "keywords": ["elasticache", "redis", "caching", "aws"],
        "difficulty": "intermediate"
    },
    {
        "slug": "aws-kinesis-guide",
        "title": "AWS Kinesis: Real-Time Data Streaming",
        "category": "cloud",
        "outline": "Data Streams, Firehose, Analytics, sharding, consumers",
        "keywords": ["kinesis", "streaming", "real-time data"],
        "difficulty": "intermediate"
    },
    {
        "slug": "aws-secrets-manager",
        "title": "AWS Secrets Manager: Secure Credential Management",
        "category": "cloud",
        "outline": "Secret rotation, access control, SDK integration, pricing",
        "keywords": ["secrets manager", "security", "credentials"],
        "difficulty": "beginner"
    },
    {
        "slug": "aws-well-architected",
        "title": "AWS Well-Architected Framework: Building Better Systems",
        "category": "cloud",
        "outline": "Six pillars, review process, best practices, common patterns",
        "keywords": ["well-architected", "aws best practices", "architecture"],
        "difficulty": "intermediate"
    },
    {
        "slug": "serverless-framework-guide",
        "title": "Serverless Framework: Multi-Cloud Deployment",
        "category": "cloud",
        "outline": "Configuration, plugins, deployment stages, offline development",
        "keywords": ["serverless framework", "deployment", "serverless"],
        "difficulty": "intermediate"
    },
    {
        "slug": "azure-functions-guide",
        "title": "Azure Functions: Serverless on Microsoft Cloud",
        "category": "cloud",
        "outline": "Triggers, bindings, durable functions, deployment options",
        "keywords": ["azure functions", "serverless", "microsoft azure"],
        "difficulty": "intermediate"
    },
    {
        "slug": "azure-kubernetes-service",
        "title": "Azure Kubernetes Service (AKS): Complete Guide",
        "category": "cloud",
        "outline": "Cluster setup, networking, scaling, monitoring, integration",
        "keywords": ["aks", "azure kubernetes", "managed kubernetes"],
        "difficulty": "intermediate"
    },
    {
        "slug": "gcp-cloud-run",
        "title": "GCP Cloud Run: Serverless Containers Made Simple",
        "category": "cloud",
        "outline": "Container deployment, scaling, networking, Cloud Run jobs",
        "keywords": ["cloud run", "gcp", "serverless containers"],
        "difficulty": "intermediate"
    },
    {
        "slug": "gcp-bigquery-guide",
        "title": "Google BigQuery: Data Warehouse at Scale",
        "category": "cloud",
        "outline": "Data modeling, partitioning, clustering, cost optimization, ML integration",
        "keywords": ["bigquery", "data warehouse", "gcp analytics"],
        "difficulty": "intermediate"
    },
    {
        "slug": "gcp-cloud-functions",
        "title": "GCP Cloud Functions: Event-Driven Serverless",
        "category": "cloud",
        "outline": "Function types, triggers, environment, deployment, 2nd gen",
        "keywords": ["cloud functions", "gcp serverless", "functions"],
        "difficulty": "intermediate"
    },
    {
        "slug": "multi-cloud-strategy",
        "title": "Multi-Cloud Strategy: Benefits, Challenges, and Patterns",
        "category": "cloud",
        "outline": "Use cases, abstraction layers, data consistency, vendor lock-in",
        "keywords": ["multi-cloud", "hybrid cloud", "cloud strategy"],
        "difficulty": "advanced"
    },
    {
        "slug": "cloud-migration-strategies",
        "title": "Cloud Migration Strategies: 6 Rs of Migration",
        "category": "cloud",
        "outline": "Rehost, replatform, refactor, assessment, migration planning",
        "keywords": ["cloud migration", "6rs", "migration strategy"],
        "difficulty": "intermediate"
    },
    {
        "slug": "serverless-patterns",
        "title": "Serverless Patterns: Event Processing, APIs, and More",
        "category": "cloud",
        "outline": "Common patterns, anti-patterns, cold start mitigation",
        "keywords": ["serverless patterns", "architecture", "best practices"],
        "difficulty": "intermediate"
    },
    {
        "slug": "cloud-native-storage",
        "title": "Cloud-Native Storage: EBS, EFS, S3, and When to Use Each",
        "category": "cloud",
        "outline": "Storage types, performance tiers, use cases, cost comparison",
        "keywords": ["cloud storage", "ebs", "efs", "s3"],
        "difficulty": "intermediate"
    },
    {
        "slug": "managed-databases-comparison",
        "title": "Managed Database Services: AWS, Azure, and GCP Compared",
        "category": "cloud",
        "outline": "RDS, Cloud SQL, Azure SQL, feature comparison, migration",
        "keywords": ["managed database", "cloud database", "comparison"],
        "difficulty": "intermediate"
    },
    {
        "slug": "cloud-networking-basics",
        "title": "Cloud Networking Fundamentals: VPCs, Subnets, and Gateways",
        "category": "cloud",
        "outline": "Network design, security groups, NACLs, peering, Transit Gateway",
        "keywords": ["cloud networking", "vpc", "subnets"],
        "difficulty": "intermediate"
    },
    {
        "slug": "cloud-security-posture",
        "title": "Cloud Security Posture Management: Best Practices",
        "category": "cloud",
        "outline": "Security assessment, compliance, remediation, tools",
        "keywords": ["cloud security", "cspm", "compliance"],
        "difficulty": "intermediate"
    },
    {
        "slug": "aws-organizations",
        "title": "AWS Organizations: Multi-Account Strategy",
        "category": "cloud",
        "outline": "Account structure, SCPs, consolidated billing, landing zones",
        "keywords": ["aws organizations", "multi-account", "governance"],
        "difficulty": "intermediate"
    },
    {
        "slug": "cloud-finops",
        "title": "Cloud FinOps: Managing Cloud Costs at Scale",
        "category": "cloud",
        "outline": "Cost visibility, optimization, governance, culture, tools",
        "keywords": ["finops", "cloud cost", "cost management"],
        "difficulty": "intermediate"
    },
    {
        "slug": "reserved-vs-spot-instances",
        "title": "Reserved vs Spot vs On-Demand: AWS Pricing Guide",
        "category": "cloud",
        "outline": "Pricing models, savings plans, spot interruption handling",
        "keywords": ["aws pricing", "spot instances", "reserved instances"],
        "difficulty": "intermediate"
    },
    {
        "slug": "serverless-cold-starts",
        "title": "Serverless Cold Starts: Understanding and Mitigating",
        "category": "cloud",
        "outline": "Causes, measurement, provisioned concurrency, optimization",
        "keywords": ["cold start", "serverless", "lambda performance"],
        "difficulty": "intermediate"
    },
    {
        "slug": "aws-amplify-guide",
        "title": "AWS Amplify: Full-Stack Development Platform",
        "category": "cloud",
        "outline": "Authentication, API, storage, hosting, CI/CD integration",
        "keywords": ["aws amplify", "full-stack", "serverless"],
        "difficulty": "intermediate"
    },
    {
        "slug": "vercel-nextjs-deployment",
        "title": "Vercel for Next.js: Deployment and Edge Functions",
        "category": "cloud",
        "outline": "Deployment, edge functions, ISR, analytics, team collaboration",
        "keywords": ["vercel", "nextjs", "edge functions"],
        "difficulty": "beginner"
    },
    {
        "slug": "cloudflare-workers",
        "title": "Cloudflare Workers: Edge Computing Platform",
        "category": "cloud",
        "outline": "Worker development, KV storage, Durable Objects, R2",
        "keywords": ["cloudflare workers", "edge computing", "serverless"],
        "difficulty": "intermediate"
    },
    {
        "slug": "aws-lambda-layers",
        "title": "AWS Lambda Layers: Sharing Code and Dependencies",
        "category": "cloud",
        "outline": "Layer creation, versioning, sharing, size limits, best practices",
        "keywords": ["lambda layers", "code sharing", "serverless"],
        "difficulty": "intermediate"
    },
    {
        "slug": "event-sourcing-aws",
        "title": "Event Sourcing on AWS: DynamoDB Streams and EventBridge",
        "category": "cloud",
        "outline": "Event store patterns, projections, replays, architecture",
        "keywords": ["event sourcing", "aws", "dynamodb streams"],
        "difficulty": "advanced"
    },
    {
        "slug": "aws-batch-guide",
        "title": "AWS Batch: Large-Scale Batch Processing",
        "category": "cloud",
        "outline": "Job definitions, compute environments, queues, spot integration",
        "keywords": ["aws batch", "batch processing", "compute"],
        "difficulty": "intermediate"
    },
    {
        "slug": "aws-glue-guide",
        "title": "AWS Glue: ETL and Data Catalog",
        "category": "cloud",
        "outline": "Crawlers, jobs, data catalog, Glue Studio, cost optimization",
        "keywords": ["aws glue", "etl", "data catalog"],
        "difficulty": "intermediate"
    },
    {
        "slug": "aws-athena-guide",
        "title": "AWS Athena: Serverless SQL Queries on S3",
        "category": "cloud",
        "outline": "Query optimization, partitioning, formats, cost management",
        "keywords": ["aws athena", "sql", "serverless analytics"],
        "difficulty": "intermediate"
    },
    {
        "slug": "cloud-disaster-recovery",
        "title": "Cloud Disaster Recovery: Strategies and Implementation",
        "category": "cloud",
        "outline": "DR tiers, RTO/RPO, pilot light, warm standby, multi-region",
        "keywords": ["disaster recovery", "cloud dr", "business continuity"],
        "difficulty": "intermediate"
    },
    {
        "slug": "aws-waf-shield",
        "title": "AWS WAF and Shield: Web Application Protection",
        "category": "cloud",
        "outline": "WAF rules, managed rules, Shield Advanced, DDoS protection",
        "keywords": ["aws waf", "shield", "web security"],
        "difficulty": "intermediate"
    },
    {
        "slug": "cloud-load-balancing",
        "title": "Cloud Load Balancing: ALB, NLB, and Global Accelerator",
        "category": "cloud",
        "outline": "Load balancer types, target groups, health checks, routing",
        "keywords": ["load balancing", "alb", "nlb", "aws"],
        "difficulty": "intermediate"
    },
    {
        "slug": "private-cloud-connectivity",
        "title": "Private Cloud Connectivity: VPN, Direct Connect, and PrivateLink",
        "category": "cloud",
        "outline": "Connection options, security, performance, cost comparison",
        "keywords": ["direct connect", "vpn", "privatelink", "connectivity"],
        "difficulty": "intermediate"
    },
    {
        "slug": "container-registry-options",
        "title": "Container Registry Options: ECR, ACR, GCR, and Docker Hub",
        "category": "cloud",
        "outline": "Feature comparison, security scanning, pricing, integration",
        "keywords": ["container registry", "ecr", "docker hub"],
        "difficulty": "beginner"
    },
    {
        "slug": "serverless-database-options",
        "title": "Serverless Databases: Aurora Serverless, DynamoDB, and More",
        "category": "cloud",
        "outline": "Scaling models, pricing, use cases, performance characteristics",
        "keywords": ["serverless database", "aurora serverless", "dynamodb"],
        "difficulty": "intermediate"
    },
    {
        "slug": "aws-app-runner",
        "title": "AWS App Runner: Simplified Container Deployment",
        "category": "cloud",
        "outline": "Service deployment, auto-scaling, networking, use cases",
        "keywords": ["app runner", "containers", "aws deployment"],
        "difficulty": "beginner"
    },
    {
        "slug": "aws-lambda-performance",
        "title": "AWS Lambda Performance Optimization: Memory, Layers, and More",
        "category": "cloud",
        "outline": "Memory tuning, provisioned concurrency, layers, ARM architecture",
        "keywords": ["lambda performance", "optimization", "serverless"],
        "difficulty": "intermediate"
    },

    # =============================================================================
    # AI/ML (45 ideas)
    # =============================================================================
    {
        "slug": "mlops-introduction",
        "title": "MLOps Introduction: From Model to Production",
        "category": "ai-ml",
        "outline": "MLOps lifecycle, CI/CD for ML, model versioning, monitoring",
        "keywords": ["mlops", "machine learning", "production ml"],
        "difficulty": "intermediate"
    },
    {
        "slug": "vector-databases-explained",
        "title": "Vector Databases Explained: Pinecone, Weaviate, and Milvus",
        "category": "ai-ml",
        "outline": "Embeddings, similarity search, indexing, use cases, comparison",
        "keywords": ["vector database", "embeddings", "similarity search"],
        "difficulty": "intermediate"
    },
    {
        "slug": "rag-architecture",
        "title": "RAG Architecture: Building AI with Your Own Data",
        "category": "ai-ml",
        "outline": "Retrieval augmented generation, chunking, embedding, prompting",
        "keywords": ["rag", "retrieval augmented generation", "llm"],
        "difficulty": "intermediate"
    },
    {
        "slug": "llm-application-development",
        "title": "Building LLM Applications: Architecture and Best Practices",
        "category": "ai-ml",
        "outline": "Prompt engineering, chains, agents, memory, evaluation",
        "keywords": ["llm", "langchain", "ai applications"],
        "difficulty": "intermediate"
    },
    {
        "slug": "prompt-engineering-guide",
        "title": "Prompt Engineering: Techniques for Better AI Outputs",
        "category": "ai-ml",
        "outline": "Prompting techniques, few-shot learning, chain of thought, evaluation",
        "keywords": ["prompt engineering", "llm", "ai prompts"],
        "difficulty": "beginner"
    },
    {
        "slug": "fine-tuning-llms",
        "title": "Fine-Tuning LLMs: When and How to Customize Models",
        "category": "ai-ml",
        "outline": "Fine-tuning vs prompting, data preparation, training, evaluation",
        "keywords": ["fine-tuning", "llm customization", "machine learning"],
        "difficulty": "advanced"
    },
    {
        "slug": "embedding-models-comparison",
        "title": "Embedding Models Compared: OpenAI, Cohere, and Open Source",
        "category": "ai-ml",
        "outline": "Model comparison, benchmarks, use cases, cost analysis",
        "keywords": ["embeddings", "text embeddings", "vector search"],
        "difficulty": "intermediate"
    },
    {
        "slug": "ai-agents-architecture",
        "title": "AI Agents: Architecture and Implementation Patterns",
        "category": "ai-ml",
        "outline": "Agent frameworks, tool use, memory, reasoning, orchestration",
        "keywords": ["ai agents", "autonomous agents", "llm agents"],
        "difficulty": "advanced"
    },
    {
        "slug": "langchain-guide",
        "title": "LangChain: Building LLM-Powered Applications",
        "category": "ai-ml",
        "outline": "Chains, agents, memory, retrievers, callbacks, deployment",
        "keywords": ["langchain", "llm framework", "ai development"],
        "difficulty": "intermediate"
    },
    {
        "slug": "openai-api-guide",
        "title": "OpenAI API: Complete Developer Guide",
        "category": "ai-ml",
        "outline": "Chat completions, function calling, assistants, best practices",
        "keywords": ["openai api", "gpt", "ai development"],
        "difficulty": "beginner"
    },
    {
        "slug": "claude-api-guide",
        "title": "Anthropic Claude API: Building with Constitutional AI",
        "category": "ai-ml",
        "outline": "API usage, system prompts, tool use, context windows",
        "keywords": ["claude api", "anthropic", "ai development"],
        "difficulty": "beginner"
    },
    {
        "slug": "model-deployment-options",
        "title": "ML Model Deployment: Cloud, Edge, and Serverless Options",
        "category": "ai-ml",
        "outline": "Deployment patterns, scaling, latency considerations, cost",
        "keywords": ["model deployment", "mlops", "inference"],
        "difficulty": "intermediate"
    },
    {
        "slug": "feature-stores-explained",
        "title": "Feature Stores: Managing ML Features at Scale",
        "category": "ai-ml",
        "outline": "Feature engineering, storage, serving, versioning, tools",
        "keywords": ["feature store", "ml features", "mlops"],
        "difficulty": "intermediate"
    },
    {
        "slug": "ml-model-monitoring",
        "title": "ML Model Monitoring: Detecting Drift and Degradation",
        "category": "ai-ml",
        "outline": "Data drift, concept drift, performance monitoring, alerting",
        "keywords": ["model monitoring", "ml drift", "production ml"],
        "difficulty": "intermediate"
    },
    {
        "slug": "aws-sagemaker-guide",
        "title": "AWS SageMaker: End-to-End ML Platform",
        "category": "ai-ml",
        "outline": "Studio, training, deployment, pipelines, ground truth",
        "keywords": ["sagemaker", "aws ml", "machine learning platform"],
        "difficulty": "intermediate"
    },
    {
        "slug": "hugging-face-guide",
        "title": "Hugging Face: Transformers and Model Hub Guide",
        "category": "ai-ml",
        "outline": "Transformers library, model hub, inference API, fine-tuning",
        "keywords": ["hugging face", "transformers", "nlp"],
        "difficulty": "intermediate"
    },
    {
        "slug": "llm-evaluation-methods",
        "title": "LLM Evaluation: Metrics and Testing Strategies",
        "category": "ai-ml",
        "outline": "Evaluation frameworks, benchmarks, human evaluation, automated testing",
        "keywords": ["llm evaluation", "ai testing", "benchmarks"],
        "difficulty": "intermediate"
    },
    {
        "slug": "semantic-search-implementation",
        "title": "Semantic Search: Implementation with Vector Databases",
        "category": "ai-ml",
        "outline": "Embedding generation, indexing, query processing, ranking",
        "keywords": ["semantic search", "vector search", "embeddings"],
        "difficulty": "intermediate"
    },
    {
        "slug": "conversational-ai-design",
        "title": "Conversational AI: Designing Effective Chatbots",
        "category": "ai-ml",
        "outline": "Conversation design, intent handling, context management, fallbacks",
        "keywords": ["conversational ai", "chatbot", "dialogue systems"],
        "difficulty": "intermediate"
    },
    {
        "slug": "ai-cost-optimization",
        "title": "AI Cost Optimization: Reducing LLM API Expenses",
        "category": "ai-ml",
        "outline": "Caching, model selection, prompt optimization, batch processing",
        "keywords": ["ai costs", "llm optimization", "cost reduction"],
        "difficulty": "intermediate"
    },
    {
        "slug": "local-llm-deployment",
        "title": "Running LLMs Locally: Ollama, llama.cpp, and vLLM",
        "category": "ai-ml",
        "outline": "Local inference, quantization, hardware requirements, performance",
        "keywords": ["local llm", "ollama", "self-hosted ai"],
        "difficulty": "intermediate"
    },
    {
        "slug": "multimodal-ai-applications",
        "title": "Multimodal AI: Vision, Audio, and Text Integration",
        "category": "ai-ml",
        "outline": "Vision models, audio processing, multimodal architectures",
        "keywords": ["multimodal ai", "vision models", "audio ai"],
        "difficulty": "advanced"
    },
    {
        "slug": "ai-security-best-practices",
        "title": "AI Security: Prompt Injection and Model Protection",
        "category": "ai-ml",
        "outline": "Prompt injection, jailbreaking, output filtering, security patterns",
        "keywords": ["ai security", "prompt injection", "llm security"],
        "difficulty": "intermediate"
    },
    {
        "slug": "structured-output-llms",
        "title": "Structured Output from LLMs: JSON, Code, and More",
        "category": "ai-ml",
        "outline": "Output parsing, function calling, validation, error handling",
        "keywords": ["structured output", "llm json", "function calling"],
        "difficulty": "intermediate"
    },
    {
        "slug": "ai-powered-code-review",
        "title": "AI-Powered Code Review: Tools and Implementation",
        "category": "ai-ml",
        "outline": "Code analysis, review automation, integration, best practices",
        "keywords": ["ai code review", "code analysis", "developer tools"],
        "difficulty": "intermediate"
    },
    {
        "slug": "document-ai-processing",
        "title": "Document AI: Extracting Information from Documents",
        "category": "ai-ml",
        "outline": "OCR, document parsing, entity extraction, classification",
        "keywords": ["document ai", "ocr", "information extraction"],
        "difficulty": "intermediate"
    },
    {
        "slug": "recommendation-systems-ml",
        "title": "Recommendation Systems: Collaborative and Content-Based Filtering",
        "category": "ai-ml",
        "outline": "Algorithm types, cold start, evaluation metrics, production systems",
        "keywords": ["recommendation systems", "collaborative filtering", "ml"],
        "difficulty": "intermediate"
    },
    {
        "slug": "time-series-forecasting",
        "title": "Time Series Forecasting: Traditional and ML Approaches",
        "category": "ai-ml",
        "outline": "ARIMA, Prophet, neural approaches, evaluation, deployment",
        "keywords": ["time series", "forecasting", "prediction"],
        "difficulty": "intermediate"
    },
    {
        "slug": "anomaly-detection-ml",
        "title": "Anomaly Detection: ML Techniques for Outlier Detection",
        "category": "ai-ml",
        "outline": "Statistical methods, isolation forest, autoencoders, streaming",
        "keywords": ["anomaly detection", "outliers", "ml algorithms"],
        "difficulty": "intermediate"
    },
    {
        "slug": "nlp-pipeline-production",
        "title": "NLP Pipeline: Building Production Text Processing",
        "category": "ai-ml",
        "outline": "Tokenization, NER, sentiment, classification, deployment",
        "keywords": ["nlp", "text processing", "natural language"],
        "difficulty": "intermediate"
    },
    {
        "slug": "gpu-optimization-ml",
        "title": "GPU Optimization for ML: Training and Inference",
        "category": "ai-ml",
        "outline": "GPU selection, memory optimization, distributed training, cost",
        "keywords": ["gpu optimization", "ml training", "deep learning"],
        "difficulty": "advanced"
    },
    {
        "slug": "model-quantization",
        "title": "Model Quantization: Making Models Smaller and Faster",
        "category": "ai-ml",
        "outline": "Quantization techniques, accuracy trade-offs, deployment benefits",
        "keywords": ["quantization", "model compression", "inference"],
        "difficulty": "advanced"
    },
    {
        "slug": "ml-experiment-tracking",
        "title": "ML Experiment Tracking: MLflow, Weights & Biases, and More",
        "category": "ai-ml",
        "outline": "Experiment logging, comparison, reproducibility, collaboration",
        "keywords": ["experiment tracking", "mlflow", "wandb"],
        "difficulty": "intermediate"
    },
    {
        "slug": "data-labeling-strategies",
        "title": "Data Labeling: Strategies for Building Quality Datasets",
        "category": "ai-ml",
        "outline": "Labeling approaches, quality control, active learning, tools",
        "keywords": ["data labeling", "annotation", "ml data"],
        "difficulty": "intermediate"
    },
    {
        "slug": "ai-ethics-responsible-ai",
        "title": "AI Ethics: Building Responsible AI Systems",
        "category": "ai-ml",
        "outline": "Bias detection, fairness, transparency, governance",
        "keywords": ["ai ethics", "responsible ai", "bias"],
        "difficulty": "intermediate"
    },
    {
        "slug": "synthetic-data-generation",
        "title": "Synthetic Data Generation: When and How to Use It",
        "category": "ai-ml",
        "outline": "Generation techniques, privacy benefits, quality validation",
        "keywords": ["synthetic data", "data generation", "privacy"],
        "difficulty": "intermediate"
    },
    {
        "slug": "computer-vision-production",
        "title": "Computer Vision in Production: Object Detection and Beyond",
        "category": "ai-ml",
        "outline": "Model selection, preprocessing, inference optimization, edge deployment",
        "keywords": ["computer vision", "object detection", "cv production"],
        "difficulty": "advanced"
    },
    {
        "slug": "speech-recognition-api",
        "title": "Speech Recognition APIs: Whisper, Deepgram, and Assembly AI",
        "category": "ai-ml",
        "outline": "API comparison, accuracy, latency, use cases, integration",
        "keywords": ["speech recognition", "whisper", "transcription"],
        "difficulty": "intermediate"
    },
    {
        "slug": "text-to-speech-guide",
        "title": "Text-to-Speech: Building Natural Voice Applications",
        "category": "ai-ml",
        "outline": "TTS services, voice cloning, SSML, streaming, integration",
        "keywords": ["text to speech", "tts", "voice synthesis"],
        "difficulty": "intermediate"
    },
    {
        "slug": "ai-testing-strategies",
        "title": "AI Testing Strategies: Unit Tests to Integration Tests",
        "category": "ai-ml",
        "outline": "Test types, mock strategies, regression testing, CI/CD",
        "keywords": ["ai testing", "ml testing", "quality assurance"],
        "difficulty": "intermediate"
    },
    {
        "slug": "knowledge-graphs-llm",
        "title": "Knowledge Graphs with LLMs: Building Intelligent Systems",
        "category": "ai-ml",
        "outline": "Graph construction, querying, RAG integration, use cases",
        "keywords": ["knowledge graphs", "llm", "graph rag"],
        "difficulty": "advanced"
    },
    {
        "slug": "ai-cache-strategies",
        "title": "AI Caching Strategies: Semantic Cache and Response Reuse",
        "category": "ai-ml",
        "outline": "Semantic caching, cache keys, invalidation, cost savings",
        "keywords": ["ai caching", "semantic cache", "llm optimization"],
        "difficulty": "intermediate"
    },
    {
        "slug": "model-serving-infrastructure",
        "title": "Model Serving Infrastructure: Building Scalable Inference",
        "category": "ai-ml",
        "outline": "Serving patterns, batching, load balancing, autoscaling",
        "keywords": ["model serving", "inference", "mlops"],
        "difficulty": "advanced"
    },
    {
        "slug": "llm-memory-architectures",
        "title": "LLM Memory: Conversation History and Long-Term Memory",
        "category": "ai-ml",
        "outline": "Memory types, summarization, retrieval, persistence",
        "keywords": ["llm memory", "conversation history", "ai memory"],
        "difficulty": "intermediate"
    },
    {
        "slug": "ai-workflow-automation",
        "title": "AI Workflow Automation: Building Intelligent Pipelines",
        "category": "ai-ml",
        "outline": "Workflow orchestration, LLM integration, error handling, monitoring",
        "keywords": ["ai workflow", "automation", "orchestration"],
        "difficulty": "intermediate"
    },

    # =============================================================================
    # CAREER (45 ideas)
    # =============================================================================
    {
        "slug": "junior-to-senior-engineer",
        "title": "From Junior to Senior Engineer: A Growth Roadmap",
        "category": "career",
        "outline": "Skill progression, ownership, mentorship, technical depth",
        "keywords": ["career growth", "senior engineer", "progression"],
        "difficulty": "beginner"
    },
    {
        "slug": "staff-engineer-role",
        "title": "What Does a Staff Engineer Actually Do?",
        "category": "career",
        "outline": "Responsibilities, scope, influence, technical leadership",
        "keywords": ["staff engineer", "career ladder", "technical leadership"],
        "difficulty": "intermediate"
    },
    {
        "slug": "tech-lead-guide",
        "title": "Becoming a Tech Lead: Technical and People Skills",
        "category": "career",
        "outline": "Role definition, team leadership, technical decisions, stakeholders",
        "keywords": ["tech lead", "leadership", "team management"],
        "difficulty": "intermediate"
    },
    {
        "slug": "engineering-manager-transition",
        "title": "IC to Engineering Manager: Making the Transition",
        "category": "career",
        "outline": "Role changes, people management, letting go of code, growth",
        "keywords": ["engineering manager", "management", "career transition"],
        "difficulty": "intermediate"
    },
    {
        "slug": "architect-role-explained",
        "title": "Software Architect Role: What It Really Means",
        "category": "career",
        "outline": "Architect types, responsibilities, influence without authority",
        "keywords": ["software architect", "architecture role", "career"],
        "difficulty": "intermediate"
    },
    {
        "slug": "remote-work-productivity",
        "title": "Remote Work Productivity: Tips for Software Engineers",
        "category": "career",
        "outline": "Environment setup, communication, work-life balance, collaboration",
        "keywords": ["remote work", "work from home", "productivity"],
        "difficulty": "beginner"
    },
    {
        "slug": "side-projects-career",
        "title": "Side Projects That Boost Your Career",
        "category": "career",
        "outline": "Project selection, time management, portfolio building, visibility",
        "keywords": ["side projects", "career growth", "portfolio"],
        "difficulty": "beginner"
    },
    {
        "slug": "technical-writing-engineers",
        "title": "Technical Writing for Engineers: Documentation That Helps",
        "category": "career",
        "outline": "Writing skills, documentation types, clarity, maintenance",
        "keywords": ["technical writing", "documentation", "communication"],
        "difficulty": "beginner"
    },
    {
        "slug": "public-speaking-engineers",
        "title": "Public Speaking for Engineers: Conferences and Meetups",
        "category": "career",
        "outline": "Topic selection, presentation skills, getting accepted, delivery",
        "keywords": ["public speaking", "conferences", "presentations"],
        "difficulty": "intermediate"
    },
    {
        "slug": "open-source-contributions",
        "title": "Contributing to Open Source: Getting Started Guide",
        "category": "career",
        "outline": "Finding projects, first contributions, community engagement",
        "keywords": ["open source", "contributions", "community"],
        "difficulty": "beginner"
    },
    {
        "slug": "building-personal-brand",
        "title": "Building Your Personal Brand as a Developer",
        "category": "career",
        "outline": "Content creation, social media, networking, authenticity",
        "keywords": ["personal brand", "developer marketing", "visibility"],
        "difficulty": "beginner"
    },
    {
        "slug": "tech-blog-writing",
        "title": "Starting a Tech Blog: Tips for Developers",
        "category": "career",
        "outline": "Platform selection, content strategy, consistency, audience building",
        "keywords": ["tech blog", "blogging", "content creation"],
        "difficulty": "beginner"
    },
    {
        "slug": "imposter-syndrome-tech",
        "title": "Dealing with Imposter Syndrome in Tech",
        "category": "career",
        "outline": "Recognition, coping strategies, building confidence, community",
        "keywords": ["imposter syndrome", "confidence", "mental health"],
        "difficulty": "beginner"
    },
    {
        "slug": "burnout-prevention",
        "title": "Burnout Prevention for Software Engineers",
        "category": "career",
        "outline": "Warning signs, prevention strategies, recovery, boundaries",
        "keywords": ["burnout", "mental health", "work-life balance"],
        "difficulty": "beginner"
    },
    {
        "slug": "networking-introverts",
        "title": "Networking for Introverted Engineers",
        "category": "career",
        "outline": "Comfortable approaches, online networking, building relationships",
        "keywords": ["networking", "introverts", "professional relationships"],
        "difficulty": "beginner"
    },
    {
        "slug": "mentorship-guide",
        "title": "Being a Good Mentor: Guide for Senior Engineers",
        "category": "career",
        "outline": "Mentorship structure, feedback, growth mindset, boundaries",
        "keywords": ["mentorship", "coaching", "leadership"],
        "difficulty": "intermediate"
    },
    {
        "slug": "finding-mentor",
        "title": "Finding a Mentor: Strategies That Work",
        "category": "career",
        "outline": "Identifying mentors, making the ask, maintaining relationships",
        "keywords": ["finding mentor", "career development", "guidance"],
        "difficulty": "beginner"
    },
    {
        "slug": "code-review-feedback",
        "title": "Giving Effective Code Review Feedback",
        "category": "career",
        "outline": "Constructive criticism, tone, prioritization, learning opportunity",
        "keywords": ["code review", "feedback", "team collaboration"],
        "difficulty": "beginner"
    },
    {
        "slug": "technical-debt-communication",
        "title": "Communicating Technical Debt to Non-Technical Stakeholders",
        "category": "career",
        "outline": "Business impact, prioritization, analogies, roadmap",
        "keywords": ["technical debt", "stakeholder communication", "business"],
        "difficulty": "intermediate"
    },
    {
        "slug": "promoting-your-work",
        "title": "Promoting Your Work: Visibility Without Being Annoying",
        "category": "career",
        "outline": "Documentation, demos, stakeholder updates, credit sharing",
        "keywords": ["self-promotion", "visibility", "career advancement"],
        "difficulty": "beginner"
    },
    {
        "slug": "startup-vs-big-tech",
        "title": "Startup vs Big Tech: Choosing Your Environment",
        "category": "career",
        "outline": "Trade-offs, career impact, compensation, growth opportunities",
        "keywords": ["startup", "big tech", "career choice"],
        "difficulty": "beginner"
    },
    {
        "slug": "freelancing-engineers",
        "title": "Freelancing as a Software Engineer: Getting Started",
        "category": "career",
        "outline": "Finding clients, pricing, contracts, time management",
        "keywords": ["freelancing", "consulting", "self-employment"],
        "difficulty": "intermediate"
    },
    {
        "slug": "consulting-career",
        "title": "Tech Consulting: Building a Consulting Practice",
        "category": "career",
        "outline": "Niche selection, client acquisition, pricing, delivery",
        "keywords": ["consulting", "tech consulting", "business"],
        "difficulty": "intermediate"
    },
    {
        "slug": "performance-review-prep",
        "title": "Preparing for Performance Reviews: Engineer's Guide",
        "category": "career",
        "outline": "Documentation, self-assessment, feedback seeking, goal setting",
        "keywords": ["performance review", "career growth", "feedback"],
        "difficulty": "beginner"
    },
    {
        "slug": "one-on-one-meetings",
        "title": "Making the Most of 1:1 Meetings with Your Manager",
        "category": "career",
        "outline": "Agenda setting, career discussions, feedback, relationship building",
        "keywords": ["one on one", "manager relationship", "career"],
        "difficulty": "beginner"
    },
    {
        "slug": "handling-layoffs",
        "title": "Handling Tech Layoffs: Preparation and Recovery",
        "category": "career",
        "outline": "Financial preparation, job search, emotional management, networking",
        "keywords": ["layoffs", "job loss", "career resilience"],
        "difficulty": "beginner"
    },
    {
        "slug": "continuous-learning-engineers",
        "title": "Continuous Learning: Staying Current as an Engineer",
        "category": "career",
        "outline": "Learning strategies, time management, practical application",
        "keywords": ["continuous learning", "skill development", "growth"],
        "difficulty": "beginner"
    },
    {
        "slug": "work-life-balance-tech",
        "title": "Work-Life Balance in Tech: Setting Boundaries",
        "category": "career",
        "outline": "Boundary setting, communication, sustainable pace, recovery",
        "keywords": ["work-life balance", "boundaries", "wellness"],
        "difficulty": "beginner"
    },
    {
        "slug": "building-influence-engineer",
        "title": "Building Influence as an Engineer: Beyond Code",
        "category": "career",
        "outline": "Technical influence, stakeholder relationships, decision making",
        "keywords": ["influence", "leadership", "senior engineer"],
        "difficulty": "intermediate"
    },
    {
        "slug": "leading-without-authority",
        "title": "Leading Without Authority: Influence at Any Level",
        "category": "career",
        "outline": "Persuasion, collaboration, building trust, driving initiatives",
        "keywords": ["leadership", "influence", "collaboration"],
        "difficulty": "intermediate"
    },
    {
        "slug": "technical-decisions-alignment",
        "title": "Getting Buy-In for Technical Decisions",
        "category": "career",
        "outline": "Stakeholder analysis, communication strategies, documentation",
        "keywords": ["decision making", "buy-in", "communication"],
        "difficulty": "intermediate"
    },
    {
        "slug": "cross-functional-collaboration",
        "title": "Cross-Functional Collaboration: Working with Product and Design",
        "category": "career",
        "outline": "Understanding roles, communication, shared goals, conflict resolution",
        "keywords": ["cross-functional", "collaboration", "product teams"],
        "difficulty": "intermediate"
    },
    {
        "slug": "dealing-with-conflict",
        "title": "Dealing with Conflict in Engineering Teams",
        "category": "career",
        "outline": "Conflict types, resolution strategies, communication, escalation",
        "keywords": ["conflict resolution", "team dynamics", "communication"],
        "difficulty": "intermediate"
    },
    {
        "slug": "developer-productivity",
        "title": "Developer Productivity: Tools and Habits That Matter",
        "category": "career",
        "outline": "Workflow optimization, focus time, automation, measurement",
        "keywords": ["productivity", "developer tools", "efficiency"],
        "difficulty": "beginner"
    },
    {
        "slug": "debugging-faster",
        "title": "Debugging Faster: Systematic Approaches to Problem Solving",
        "category": "career",
        "outline": "Debugging strategies, tooling, documentation, prevention",
        "keywords": ["debugging", "problem solving", "troubleshooting"],
        "difficulty": "beginner"
    },
    {
        "slug": "reading-technical-content",
        "title": "Reading Technical Content Effectively: Papers, Docs, and Code",
        "category": "career",
        "outline": "Reading strategies, note-taking, retention, application",
        "keywords": ["technical reading", "learning", "documentation"],
        "difficulty": "beginner"
    },
    {
        "slug": "building-second-brain",
        "title": "Building a Second Brain for Engineers",
        "category": "career",
        "outline": "Knowledge management, note-taking systems, retrieval, tools",
        "keywords": ["second brain", "knowledge management", "notes"],
        "difficulty": "beginner"
    },
    {
        "slug": "time-management-engineers",
        "title": "Time Management for Software Engineers",
        "category": "career",
        "outline": "Prioritization, focus blocks, meeting management, estimation",
        "keywords": ["time management", "productivity", "planning"],
        "difficulty": "beginner"
    },
    {
        "slug": "saying-no-work",
        "title": "Saying No at Work: Setting Professional Boundaries",
        "category": "career",
        "outline": "When to say no, how to decline, alternatives, reputation",
        "keywords": ["saying no", "boundaries", "workload"],
        "difficulty": "beginner"
    },
    {
        "slug": "navigating-reorgs",
        "title": "Navigating Reorgs: Staying Effective During Change",
        "category": "career",
        "outline": "Understanding reorgs, maintaining visibility, relationship building",
        "keywords": ["reorg", "organizational change", "career"],
        "difficulty": "intermediate"
    },
    {
        "slug": "building-trust-team",
        "title": "Building Trust with Your Team: Foundation of Collaboration",
        "category": "career",
        "outline": "Trust components, consistency, vulnerability, reliability",
        "keywords": ["trust", "team building", "collaboration"],
        "difficulty": "beginner"
    },
    {
        "slug": "owning-mistakes",
        "title": "Owning Your Mistakes: Growth Through Accountability",
        "category": "career",
        "outline": "Accountability culture, communication, learning, prevention",
        "keywords": ["accountability", "mistakes", "growth mindset"],
        "difficulty": "beginner"
    },
    {
        "slug": "asking-for-raise",
        "title": "Asking for a Raise: When and How to Negotiate",
        "category": "career",
        "outline": "Timing, preparation, documentation, negotiation tactics",
        "keywords": ["raise", "salary negotiation", "compensation"],
        "difficulty": "intermediate"
    },
    {
        "slug": "career-planning-engineers",
        "title": "Career Planning for Engineers: 5-Year Roadmap",
        "category": "career",
        "outline": "Goal setting, skill planning, milestone tracking, flexibility",
        "keywords": ["career planning", "goals", "professional development"],
        "difficulty": "beginner"
    },
    {
        "slug": "staying-technical-management",
        "title": "Staying Technical as a Manager: Balancing Roles",
        "category": "career",
        "outline": "Time allocation, code reviews, architecture involvement, learning",
        "keywords": ["technical manager", "hands-on", "balance"],
        "difficulty": "intermediate"
    },
]


def get_ideas_by_category(category: str) -> list:
    """Return all ideas for a specific category."""
    return [idea for idea in BLOG_IDEAS if idea["category"] == category]


def get_category_counts() -> dict:
    """Return count of ideas per category."""
    counts = {}
    for idea in BLOG_IDEAS:
        cat = idea["category"]
        counts[cat] = counts.get(cat, 0) + 1
    return counts


if __name__ == "__main__":
    counts = get_category_counts()
    total = sum(counts.values())
    print(f"Total blog ideas: {total}")
    print("\nBy category:")
    for cat, count in sorted(counts.items()):
        print(f"  {cat}: {count}")

