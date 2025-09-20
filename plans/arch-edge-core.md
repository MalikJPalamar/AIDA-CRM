# AIDA-CRM Architecture Plan

## Edge/Core Architecture

### Edge Layer (Fly.io)
**Purpose**: Stateless, globally distributed API gateway
- **Runtime**: FastAPI with async/await
- **Responsibilities**:
  - API ingress and rate limiting
  - Authentication and authorization
  - Request routing to core services
  - Response caching and optimization
- **Scaling**: Auto-scale based on request volume
- **Regions**: Multi-region deployment for low latency

### Core Layer (Private VPS)
**Purpose**: Stateful business logic and data processing
- **Orchestration**: Docker Swarm for service management
- **Services**:
  - `aida-api`: Main business logic service
  - `nats`: Message bus and event streaming
  - `duckdb`: Analytics and OLAP workloads
  - `supabase-proxy`: Transactional database access
  - `chroma`: Vector database for AI features
  - `prometheus`: Metrics collection
  - `grafana`: Observability dashboards

## Data Flow Architecture

### Request Flow
```
Client → Edge (Fly.io) → Core (VPS) → Data Layer
```

### Event Flow
```
Action → NATS Stream → Event Handlers → Data Updates → Analytics
```

### Data Bus (NATS JetStream)
**Streams**:
- `crm.leads`: Lead capture and qualification events
- `crm.deals`: Deal progression and conversion events
- `crm.comms`: Communication and engagement events
- `crm.analytics`: Metrics and insights events

**Subjects**:
- `leads.captured`, `leads.qualified`, `leads.rejected`
- `deals.created`, `deals.progressed`, `deals.won`, `deals.lost`
- `comms.sent`, `comms.opened`, `comms.clicked`, `comms.replied`
- `analytics.computed`, `analytics.alerted`

## Service Interactions

### API Service
- Handles HTTP requests from edge
- Publishes events to NATS
- Queries data from Supabase/DuckDB
- Triggers AI workflows via Chroma

### Event Processors
- Subscribe to NATS streams
- Process business logic asynchronously
- Update analytics in DuckDB
- Trigger downstream workflows

### AI/ML Pipeline
- Chroma for semantic search and personalization
- OpenRouter/Kimi-K2 for content generation
- Vector embeddings for lead scoring
- Autonomy level progression logic

## Security Architecture

### Authentication
- JWT tokens for API access
- Service-to-service mTLS
- Database connection encryption

### Authorization
- Role-based access control (RBAC)
- Resource-level permissions
- Audit logging for all actions

### Data Protection
- Encryption at rest and in transit
- PII anonymization for analytics
- GDPR compliance workflows

## Deployment Strategy

### Infrastructure as Code
- Docker Compose for local development
- Docker Swarm for production deployment
- Automated health checks and recovery

### CI/CD Pipeline
- GitHub Actions for build and test
- Automated deployment to VPS
- Blue-green deployment for zero downtime

### Monitoring and Observability
- Prometheus metrics collection
- Grafana dashboards for visualization
- Distributed tracing with OTEL
- Error tracking with Sentry integration