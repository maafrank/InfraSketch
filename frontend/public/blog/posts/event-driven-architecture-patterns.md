# Event-Driven Architecture Patterns: A Complete Guide

Event-driven architecture (EDA) is a design paradigm where system components communicate through events. Instead of direct service-to-service calls, services emit events that other services can react to. This guide covers the key patterns, when to use them, and how to diagram event-driven systems.

## What is Event-Driven Architecture?

In event-driven architecture:

1. **Producers** emit events when something happens
2. **Event brokers** route events to interested parties
3. **Consumers** react to events asynchronously

This differs from request-response (REST) architectures where services call each other directly and wait for responses.

### Benefits of Event-Driven Architecture

- **Loose coupling:** Services don't need to know about each other
- **Scalability:** Scale producers and consumers independently
- **Resilience:** Failures don't cascade immediately
- **Real-time:** React to events as they happen
- **Auditability:** Events create a natural log of what happened

### Drawbacks

- **Complexity:** Harder to trace request flows
- **Eventual consistency:** Data may be temporarily inconsistent
- **Debugging:** Distributed debugging is challenging
- **Event ordering:** Maintaining order across partitions is hard

## Core Event-Driven Patterns

### 1. Event Notification

The simplest pattern. Services emit events to notify others that something happened.

```
┌─────────────┐     ┌───────────────┐     ┌─────────────┐
│ Order       │────▶│ Event Broker  │────▶│ Notification│
│ Service     │     │ (Kafka/SNS)   │     │ Service     │
└─────────────┘     └───────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ Analytics   │
                    │ Service     │
                    └─────────────┘
```

**When to use:**
- Simple notifications (email, SMS)
- Analytics and logging
- Cache invalidation

**Example events:**
- `OrderCreated`
- `UserRegistered`
- `PaymentReceived`

### 2. Event-Carried State Transfer

Events carry enough data for consumers to update their own state without calling back to the source.

```
Event: OrderCreated
{
  "eventId": "evt-123",
  "eventType": "OrderCreated",
  "timestamp": "2026-01-15T10:30:00Z",
  "data": {
    "orderId": "ord-456",
    "customerId": "cust-789",
    "customerName": "John Doe",
    "customerEmail": "john@example.com",
    "items": [...],
    "total": 99.99
  }
}
```

**When to use:**
- Consumers need data from the event to process
- Avoiding synchronous callbacks
- Building read models or projections

**Trade-off:** Events are larger, but consumers are more independent.

### 3. Event Sourcing

Store state as a sequence of events rather than current state. The current state is derived by replaying events.

```
┌─────────────────────────────────────────────────────────┐
│                    Event Store                          │
├─────────────────────────────────────────────────────────┤
│ 1. AccountCreated { accountId: "123", balance: 0 }      │
│ 2. MoneyDeposited { accountId: "123", amount: 100 }     │
│ 3. MoneyWithdrawn { accountId: "123", amount: 30 }      │
│ 4. MoneyDeposited { accountId: "123", amount: 50 }      │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼ Replay
              Current State: balance = 120
```

**When to use:**
- Complete audit trail required
- Need to reconstruct past states
- Complex business logic with many state transitions
- Debugging by replaying events

**Common technologies:** EventStoreDB, Apache Kafka, AWS Kinesis

### 4. CQRS (Command Query Responsibility Segregation)

Separate the write model (commands) from the read model (queries).

```
         Commands                          Queries
            │                                 │
            ▼                                 ▼
    ┌───────────────┐                 ┌───────────────┐
    │ Command       │                 │ Query         │
    │ Handler       │                 │ Handler       │
    └───────┬───────┘                 └───────┬───────┘
            │                                 │
            ▼                                 ▼
    ┌───────────────┐                 ┌───────────────┐
    │ Write Model   │────Events──────▶│ Read Model    │
    │ (Event Store) │                 │ (Projections) │
    └───────────────┘                 └───────────────┘
```

**When to use:**
- Different read and write patterns
- High-read, low-write workloads
- Complex queries across multiple aggregates
- Need optimized read models

**Example:** An e-commerce order system might:
- Write: Store individual order events
- Read: Maintain denormalized views for "orders by customer", "orders by product", "revenue by day"

### 5. Saga Pattern

Coordinate multi-step transactions across services using events.

**Choreography-based Saga:**

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│ Order   │────▶│ Payment │────▶│Inventory│────▶│Shipping │
│ Service │     │ Service │     │ Service │     │ Service │
└─────────┘     └─────────┘     └─────────┘     └─────────┘
     │               │               │               │
     │  OrderCreated │  PaymentDone  │ InventoryRes. │
     └───────────────┴───────────────┴───────────────┘
                    Event Bus
```

**Orchestration-based Saga:**

```
                 ┌─────────────────┐
                 │ Saga            │
                 │ Orchestrator    │
                 └────────┬────────┘
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    ┌─────────┐     ┌─────────┐     ┌─────────┐
    │ Payment │     │Inventory│     │Shipping │
    │ Service │     │ Service │     │ Service │
    └─────────┘     └─────────┘     └─────────┘
```

**When to use:**
- Multi-step business processes
- Distributed transactions
- Need compensating transactions for rollback

**Choreography vs Orchestration:**
- Choreography: Services coordinate via events (decoupled but harder to track)
- Orchestration: Central coordinator manages the flow (easier to track but single point of coordination)

## Message Brokers and Event Streaming

### Apache Kafka

Distributed event streaming platform:
- High throughput (millions of events/sec)
- Durable storage with configurable retention
- Consumer groups for parallel processing
- Partitioning for scalability
- Exactly-once semantics (with transactions)

**Best for:** High-volume event streaming, event sourcing, log aggregation

### RabbitMQ

Traditional message broker:
- Multiple messaging patterns (pub/sub, routing, RPC)
- Message acknowledgment
- Dead letter queues
- Flexible routing with exchanges

**Best for:** Task queues, RPC patterns, complex routing

### AWS SNS/SQS

Managed AWS services:
- SNS: Pub/sub notifications
- SQS: Message queuing
- Often used together: SNS fan-out to multiple SQS queues

**Best for:** AWS-native applications, simple event notification

### Redis Streams

Lightweight event streaming:
- Built into Redis
- Consumer groups
- Good for moderate volumes

**Best for:** Real-time features, when you already use Redis

## Designing Event-Driven Systems

### Event Design Principles

**1. Events are immutable facts**
- Events describe what happened, not commands
- Use past tense: `OrderCreated`, not `CreateOrder`
- Never modify published events

**2. Include all necessary context**
- Consumer shouldn't need to call back to producer
- Include IDs and relevant data
- Version your event schemas

**3. Design for failure**
- Idempotent consumers (handle duplicate events)
- Dead letter queues for failed processing
- Retry with exponential backoff

### Event Schema Example

```json
{
  "eventId": "evt-uuid-12345",
  "eventType": "OrderShipped",
  "version": "1.0",
  "timestamp": "2026-01-15T14:30:00Z",
  "source": "shipping-service",
  "correlationId": "req-uuid-67890",
  "data": {
    "orderId": "ord-123",
    "trackingNumber": "1Z999AA10123456784",
    "carrier": "UPS",
    "estimatedDelivery": "2026-01-18"
  },
  "metadata": {
    "userId": "user-456",
    "tenantId": "tenant-789"
  }
}
```

## Creating Event-Driven Diagrams with InfraSketch

Describe your event-driven system in natural language:

**Example prompt:**
> "Design an event-driven order processing system with Kafka as the event bus. Include order service, payment service, inventory service, and shipping service. Show the saga pattern for order fulfillment with compensating transactions."

InfraSketch will generate a diagram showing:
- Services with their event producers/consumers
- Event broker (Kafka) in the center
- Event flow arrows with event names
- Proper grouping of related components

### Refining Event-Driven Diagrams

Use chat to add details:
- "Add a dead letter queue for failed events"
- "Show the CQRS pattern with read replicas"
- "Add event sourcing for the order aggregate"
- "Include a schema registry for event versioning"

### Generate Design Documentation

Click "Create Design Doc" to get comprehensive documentation including:
- Event catalog with schema definitions
- Service responsibilities and owned events
- Data flow and consistency considerations
- Failure handling and recovery procedures

## Event-Driven Architecture Anti-Patterns

### 1. Event Explosion

Creating too many fine-grained events makes the system hard to understand.

**Solution:** Group related changes into meaningful domain events.

### 2. Synchronous Mindset

Trying to achieve request-response semantics with events.

**Solution:** Embrace eventual consistency and design for it.

### 3. Missing Correlation IDs

Unable to trace a request across services.

**Solution:** Include correlation IDs in all events and logs.

### 4. No Event Versioning

Breaking consumers when event schemas change.

**Solution:** Version events, use backward-compatible changes.

### 5. Ignoring Event Ordering

Assuming events arrive in order when they might not.

**Solution:** Design for out-of-order events or use ordering guarantees (Kafka partitions).

## Event-Driven Patterns in ML Systems

Event-driven architecture is increasingly important in machine learning systems, where real-time data processing and model updates are critical. Many production ML systems use event-driven patterns for several key functions:

### Real-Time Feature Computation

Streaming events (user clicks, transactions, sensor readings) feed into real-time feature computation pipelines. Frameworks like Kafka Streams or Apache Flink consume events and compute features (e.g., "number of transactions in the last 5 minutes") that are served to ML models for real-time inference. This is the foundation of systems like fraud detection and real-time recommendations.

### Model Retraining Triggers

Events can trigger automated model retraining. For example, a monitoring system detects data drift or model performance degradation and publishes an event. A retraining pipeline subscribes to these events and automatically kicks off a new training run with fresh data. This closes the feedback loop in production ML systems.

### Online Learning

Some ML systems update model parameters in response to individual events rather than retraining in batches. Online learning systems consume event streams and update models incrementally, enabling the system to adapt to changing patterns in near-real-time.

### Event Sourcing for ML Reproducibility

Event sourcing patterns are valuable for ML systems that need to reproduce historical states. By replaying events, teams can reconstruct the exact data that was available at any point in time, enabling reproducible feature computation and model training.

For more on these patterns, see [Streaming ML System Design](/blog/streaming-ml-system-design), [Machine Learning System Design Patterns](/blog/ml-system-design-patterns), and [Feature Store System Design](/blog/feature-store-system-design).

## Conclusion

Event-driven architecture enables scalable, loosely coupled systems. The key patterns (event notification, event sourcing, CQRS, sagas) each solve specific problems. Choosing the right pattern depends on your requirements for consistency, scalability, and operational complexity.

With InfraSketch, you can quickly visualize event-driven architectures by describing your system in plain English. Generate diagrams showing event flows, then export comprehensive design documentation.

---

**Ready to design your event-driven system?** [Try InfraSketch free](https://infrasketch.net) and create your architecture diagram in seconds.

## Related Resources

- [Microservices Architecture Diagram Guide](/blog/microservices-architecture-diagram-guide)
- [System Design Interview Cheat Sheet](/blog/system-design-interview-cheat-sheet)
- [The Complete Guide to System Design](/blog/complete-guide-system-design)
