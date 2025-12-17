/**
 * Pre-generated content for the onboarding tutorial.
 * This content is displayed during the tutorial without making real AI calls.
 */

// Initial diagram generated from the tutorial prompt
export const TUTORIAL_DIAGRAM = {
  nodes: [
    {
      id: 'api-gateway',
      type: 'gateway',
      label: 'API Gateway',
      description: 'Entry point for all API requests. Handles routing, authentication, and request validation.',
      inputs: [],
      outputs: ['user-service', 'product-service'],
      metadata: { technology: 'Kong', notes: 'Handles 10k req/s' },
      position: { x: 400, y: 50 },
    },
    {
      id: 'user-service',
      type: 'service',
      label: 'User Service',
      description: 'Manages user registration, authentication, and profile data.',
      inputs: ['api-gateway'],
      outputs: ['user-db', 'cache'],
      metadata: { technology: 'Node.js', notes: null },
      position: { x: 200, y: 200 },
    },
    {
      id: 'product-service',
      type: 'service',
      label: 'Product Service',
      description: 'Handles product catalog, inventory, and pricing.',
      inputs: ['api-gateway'],
      outputs: ['product-db'],
      metadata: { technology: 'Python/FastAPI', notes: null },
      position: { x: 600, y: 200 },
    },
    {
      id: 'user-db',
      type: 'database',
      label: 'User Database',
      description: 'PostgreSQL database storing user accounts and profiles.',
      inputs: ['user-service'],
      outputs: [],
      metadata: { technology: 'PostgreSQL', notes: null },
      position: { x: 100, y: 400 },
    },
    {
      id: 'product-db',
      type: 'database',
      label: 'Product Database',
      description: 'MongoDB database for flexible product schemas.',
      inputs: ['product-service'],
      outputs: [],
      metadata: { technology: 'MongoDB', notes: null },
      position: { x: 600, y: 400 },
    },
    {
      id: 'cache',
      type: 'cache',
      label: 'Session Cache',
      description: 'Redis cache for session tokens and frequently accessed data.',
      inputs: ['user-service'],
      outputs: [],
      metadata: { technology: 'Redis', notes: null },
      position: { x: 300, y: 400 },
    },
  ],
  edges: [
    { id: 'e1', source: 'api-gateway', target: 'user-service', label: 'Auth requests', type: 'default' },
    { id: 'e2', source: 'api-gateway', target: 'product-service', label: 'Product requests', type: 'default' },
    { id: 'e3', source: 'user-service', target: 'user-db', label: 'CRUD', type: 'default' },
    { id: 'e4', source: 'user-service', target: 'cache', label: 'Session data', type: 'default' },
    { id: 'e5', source: 'product-service', target: 'product-db', label: 'CRUD', type: 'default' },
  ],
};

// Diagram after "add rate limiting" modification
export const TUTORIAL_DIAGRAM_WITH_RATE_LIMITER = {
  nodes: [
    ...TUTORIAL_DIAGRAM.nodes,
    {
      id: 'rate-limiter',
      type: 'service',
      label: 'Rate Limiter',
      description: 'Protects services from abuse by limiting request rates per user/IP.',
      inputs: ['api-gateway'],
      outputs: ['user-service', 'product-service'],
      metadata: { technology: 'Redis + Lua', notes: '1000 req/min per user' },
      position: { x: 400, y: 125 },
    },
  ],
  edges: [
    { id: 'e1-new', source: 'api-gateway', target: 'rate-limiter', label: 'All requests', type: 'default' },
    { id: 'e2-new', source: 'rate-limiter', target: 'user-service', label: 'Auth requests', type: 'default' },
    { id: 'e3-new', source: 'rate-limiter', target: 'product-service', label: 'Product requests', type: 'default' },
    { id: 'e3', source: 'user-service', target: 'user-db', label: 'CRUD', type: 'default' },
    { id: 'e4', source: 'user-service', target: 'cache', label: 'Session data', type: 'default' },
    { id: 'e5', source: 'product-service', target: 'product-db', label: 'CRUD', type: 'default' },
  ],
};

// Diagram after adding Redis Cache manually
export const TUTORIAL_DIAGRAM_WITH_REDIS = {
  nodes: [
    ...TUTORIAL_DIAGRAM_WITH_RATE_LIMITER.nodes,
    {
      id: 'product-cache',
      type: 'cache',
      label: 'Product Cache',
      description: 'Caches frequently accessed product data for faster retrieval.',
      inputs: ['product-service'],
      outputs: [],
      metadata: { technology: 'Redis', notes: 'TTL: 5 minutes' },
      position: { x: 700, y: 300 },
    },
  ],
  edges: [
    ...TUTORIAL_DIAGRAM_WITH_RATE_LIMITER.edges,
    { id: 'e6', source: 'product-service', target: 'product-cache', label: 'Cache reads', type: 'default' },
  ],
};

// Diagram after creating a connection (user-db to cache for backup)
export const TUTORIAL_DIAGRAM_WITH_CONNECTION = {
  nodes: TUTORIAL_DIAGRAM_WITH_REDIS.nodes,
  edges: [
    ...TUTORIAL_DIAGRAM_WITH_REDIS.edges,
    { id: 'e7', source: 'user-db', target: 'cache', label: 'Backup sync', type: 'default' },
  ],
};

// Diagram after grouping databases together (collapsed by default)
export const TUTORIAL_DIAGRAM_WITH_GROUP = {
  nodes: [
    // Keep non-grouped nodes
    ...TUTORIAL_DIAGRAM_WITH_CONNECTION.nodes.filter(n => n.id !== 'user-db' && n.id !== 'product-db'),
    // Add group node
    {
      id: 'databases-group',
      type: 'database',
      label: 'Databases',
      description: 'Contains all database components for the e-commerce system.',
      inputs: ['user-service', 'product-service'],
      outputs: [],
      metadata: { technology: 'PostgreSQL, MongoDB', notes: '2 databases' },
      position: { x: 350, y: 400 },
      is_group: true,
      is_collapsed: true,
      child_ids: ['user-db', 'product-db'],
    },
    // Grouped nodes with parent_id
    {
      id: 'user-db',
      type: 'database',
      label: 'User Database',
      description: 'PostgreSQL database storing user accounts and profiles.',
      inputs: ['user-service'],
      outputs: [],
      metadata: { technology: 'PostgreSQL', notes: null },
      position: { x: 100, y: 450 },
      parent_id: 'databases-group',
    },
    {
      id: 'product-db',
      type: 'database',
      label: 'Product Database',
      description: 'MongoDB database for flexible product schemas.',
      inputs: ['product-service'],
      outputs: [],
      metadata: { technology: 'MongoDB', notes: null },
      position: { x: 600, y: 450 },
      parent_id: 'databases-group',
    },
  ],
  edges: TUTORIAL_DIAGRAM_WITH_CONNECTION.edges,
};

// Diagram with group expanded (to show the expand/collapse effect)
export const TUTORIAL_DIAGRAM_WITH_GROUP_EXPANDED = {
  nodes: [
    // Keep non-grouped nodes
    ...TUTORIAL_DIAGRAM_WITH_CONNECTION.nodes.filter(n => n.id !== 'user-db' && n.id !== 'product-db'),
    // Add group node - expanded
    {
      id: 'databases-group',
      type: 'database',
      label: 'Databases',
      description: 'Contains all database components for the e-commerce system.',
      inputs: ['user-service', 'product-service'],
      outputs: [],
      metadata: { technology: 'PostgreSQL, MongoDB', notes: '2 databases' },
      position: { x: 350, y: 400 },
      is_group: true,
      is_collapsed: false,
      child_ids: ['user-db', 'product-db'],
    },
    // Grouped nodes with parent_id
    {
      id: 'user-db',
      type: 'database',
      label: 'User Database',
      description: 'PostgreSQL database storing user accounts and profiles.',
      inputs: ['user-service'],
      outputs: [],
      metadata: { technology: 'PostgreSQL', notes: null },
      position: { x: 100, y: 450 },
      parent_id: 'databases-group',
    },
    {
      id: 'product-db',
      type: 'database',
      label: 'Product Database',
      description: 'MongoDB database for flexible product schemas.',
      inputs: ['product-service'],
      outputs: [],
      metadata: { technology: 'MongoDB', notes: null },
      position: { x: 600, y: 450 },
      parent_id: 'databases-group',
    },
  ],
  edges: TUTORIAL_DIAGRAM_WITH_CONNECTION.edges,
};

// Initial messages for the chat panel
export const TUTORIAL_INITIAL_MESSAGES = [
  {
    role: 'user',
    content: 'Build a simple e-commerce API with user authentication and product catalog',
  },
  {
    role: 'assistant',
    content: `## System Overview
I've designed an e-commerce API architecture with 6 components.

**Component Types**
- gateway (API Gateway)
- service (User Service, Product Service)
- database (User Database, Product Database)
- cache (Session Cache)

**What's Next?**
- Click any node to focus the conversation on that component
- Ask questions about the overall system design
- Request changes to add, remove, or modify components

Feel free to explore the diagram and ask me anything!`,
  },
];

// Messages after rate limiter is added
export const TUTORIAL_RATE_LIMITER_MESSAGES = [
  ...TUTORIAL_INITIAL_MESSAGES,
  {
    role: 'user',
    content: 'Add rate limiting to protect against abuse',
  },
  {
    role: 'assistant',
    content: `I've added a **Rate Limiter** component between the API Gateway and your services.

**Changes Made:**
- Added Rate Limiter service using Redis + Lua scripts
- Configured to allow 1000 requests per minute per user
- All requests now flow through the rate limiter before reaching services

This protects your User Service and Product Service from:
- DDoS attacks
- Brute force login attempts
- API abuse from misbehaving clients

*(Graph has been updated)*`,
  },
];

// Pre-generated design document
export const TUTORIAL_DESIGN_DOC = `# E-Commerce API Design Document

## Executive Summary

This document outlines the architecture for a scalable e-commerce API platform. The system handles user authentication, product catalog management, and is designed for high availability and performance.

## System Overview

The architecture follows a microservices pattern with clear separation of concerns:

- **API Gateway**: Single entry point handling routing, authentication, and rate limiting
- **User Service**: Manages user accounts, authentication, and sessions
- **Product Service**: Handles product catalog, inventory, and search
- **Data Layer**: PostgreSQL for users, MongoDB for products, Redis for caching

## Component Details

### API Gateway (Kong)
- Routes requests to appropriate microservices
- Handles JWT validation and API key management
- Provides request/response transformation
- Enables circuit breaking for fault tolerance

### User Service (Node.js)
- User registration and profile management
- Password hashing with bcrypt
- JWT token generation and refresh
- Session management via Redis

### Product Service (Python/FastAPI)
- Product CRUD operations
- Full-text search with MongoDB Atlas
- Inventory tracking
- Price management

### Rate Limiter (Redis + Lua)
- Token bucket algorithm implementation
- 1000 requests/minute per user
- Sliding window rate limiting
- Distributed rate limiting across instances

## Data Flow

1. Client sends request to API Gateway
2. Gateway validates authentication token
3. Rate limiter checks request limits
4. Request routes to appropriate service
5. Service processes request, accessing databases as needed
6. Response returns through the same path

## Infrastructure Requirements

- **Compute**: Kubernetes cluster with auto-scaling
- **Database**: Managed PostgreSQL and MongoDB Atlas
- **Cache**: Redis Cluster for high availability
- **CDN**: CloudFront for static assets

## Security Considerations

- All traffic encrypted with TLS 1.3
- API keys rotated every 90 days
- Database credentials in AWS Secrets Manager
- Rate limiting prevents brute force attacks

## Scalability

- Horizontal scaling via Kubernetes
- Database read replicas for heavy read workloads
- Redis cluster for distributed caching
- CDN for static content delivery
`;

// Prompt text for the tutorial
export const TUTORIAL_PROMPTS = {
  initial: 'Build a simple e-commerce API with user authentication and product catalog',
  addRateLimiter: 'Add rate limiting to protect against abuse',
};

// Node to add manually during tutorial
export const TUTORIAL_MANUAL_NODE = {
  id: 'product-cache',
  type: 'cache',
  label: 'Product Cache',
  description: 'Caches frequently accessed product data for faster retrieval.',
  inputs: [],
  outputs: [],
  metadata: { technology: 'Redis', notes: 'TTL: 5 minutes' },
  position: { x: 700, y: 300 },
};
