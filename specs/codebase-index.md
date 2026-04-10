# AIDA-CRM Codebase Index & Architecture Analysis

## Repository Topology

| Path | Purpose |
| --- | --- |
| `core/` | Primary FastAPI application responsible for business logic, persistence, and integrations with NATS, Supabase/Postgres, Chroma, and DuckDB. |
| `edge/` | Edge-facing FastAPI gateway that handles ingress, auth delegation, rate limiting, and request telemetry before proxying to the core services. |
| `ui/` | Next.js 13+ frontend (App Router) implementing dashboards, shadcn/ui design system, and Tailwind-based components. |
| `config/` | Environment templates and shared configuration artefacts for local and hosted deployments. |
| `memory/` | Immutable guiding principles that shape AI/agent behaviour. |
| `plans/` | High-level architecture and rollout plans for edge ↔ core orchestration. |
| `specs/` | Functional and technical specifications, including this code index. |
| `tests/` | API-level tests and fixtures for exercising lifecycle behaviours. |
| `tasks/` | Automation scripts and task definitions for operational workflows. |

## Platform Stack Overview

The stack is intentionally split into edge, core, and data planes:

- **Frontend**: Next.js (App Router), TypeScript, shadcn/ui, Tailwind CSS for the operator-facing interface.【F:README.md†L74-L79】【F:ui/app/page.tsx†L1-L47】
- **Core API**: FastAPI 0.104 with async SQLAlchemy, Pydantic v2, and structured logging via structlog; exposes REST endpoints for the CRM lifecycle.【F:core/app/main.py†L1-L117】【F:core/requirements.txt†L1-L19】
- **Edge API**: Hardened FastAPI deployment on Fly.io with rate limiting, auth, observability, and CORS controls to shield the core plane.【F:README.md†L9-L21】【F:edge/app/main.py†L1-L98】
- **Data & AI**: Supabase/PostgreSQL for transactions, DuckDB for analytics, Chroma for vector retrieval, NATS JetStream for events, and OpenRouter LLM access for intelligent automation.【F:README.md†L23-L52】【F:core/app/core/config.py†L21-L55】
- **Observability & Ops**: Prometheus, Grafana, and structured JSON logging for runtime telemetry across edge and core services.【F:README.md†L58-L64】【F:core/app/main.py†L36-L84】【F:edge/app/main.py†L14-L71】

## Backend Architecture (Core Plane)

### Application Lifecycle

- Central FastAPI app configures CORS, Prometheus instrumentation, and structured logging via a shared lifespan hook.【F:core/app/main.py†L12-L111】
- Startup initialises the async SQLAlchemy engine, builds metadata for all models, and attempts to connect to NATS; shutdown disposes connections gracefully.【F:core/app/main.py†L44-L78】【F:core/app/core/database.py†L31-L66】

### Persistence Models

- **Leads** capture prospect metadata, qualification status, attribution, and engagement relationships.【F:core/app/models/leads.py†L15-L68】
- **Deals** track opportunities, pipeline stage, probability, and weighted revenue while linking back to originating leads and owners.【F:core/app/models/deals.py†L15-L71】
- **Communications** log omnichannel outreach, engagement signals, and relational context to leads, deals, and senders.【F:core/app/models/communications.py†L15-L66】
- **Events** store durable audit records of domain events, replay metadata, and retry state for JetStream workflows.【F:core/app/models/events.py†L15-L53】
- **Users** provide authentication/assignment anchors for lifecycle automation.【F:core/app/models/users.py†L12-L34】

### Service Layer & Business Logic

- **LeadService** orchestrates capture, deduplication, AI-driven qualification, scoring-based next actions, and NATS event publication for downstream automation.【F:core/app/services/lead_service.py†L18-L124】【F:core/app/services/lead_service.py†L158-L232】
- **DealService** derives new deals from qualified leads, performs AI-guided stage management, enforces pipeline transitions, and emits progression events with recommended actions.【F:core/app/services/deal_service.py†L20-L118】【F:core/app/services/deal_service.py†L120-L199】
- **CommunicationService** manages email/SMS orchestration, enhances content with AI, persists engagement telemetry, and emits communication events for automation.【F:core/app/services/communication_service.py†L1-L176】
- **CustomerSuccessService** activates onboarding workflows after closed-won deals, tracks health scores, identifies risks/expansion, and coordinates retention playbooks through AI and communications integrations.【F:core/app/services/customer_success_service.py†L1-L104】【F:core/app/services/customer_success_service.py†L106-L176】
- **AutonomyEngine** governs L1-L5 autonomy decisions, blending AI analysis with policy/permission checks to determine whether actions execute automatically, request approval, or escalate.【F:core/app/services/autonomy_engine.py†L20-L104】
- Shared **AIService** adapters (OpenRouter) and **NATS client** abstractions standardise external integrations for all services.【F:core/app/core/config.py†L41-L55】【F:core/app/services/lead_service.py†L24-L28】

### API Surface

Versioned FastAPI routers expose lifecycle operations for leads, deals, communications, customer success, and webhooks, binding request DTOs to the service layer and translating failures into HTTP semantics.【F:core/app/main.py†L113-L144】【F:core/app/api/leads.py†L1-L120】

## Edge Architecture

- Edge FastAPI app applies Trusted Host, CORS, rate limiting, Prometheus instrumentation, and custom exception handlers to secure ingress traffic.【F:edge/app/main.py†L1-L132】
- Routers provide lightweight health, auth, and lead endpoints that proxy/mediate requests to the core plane while enforcing perimeter policies.【F:edge/app/main.py†L99-L114】
- Shared configuration keeps secrets in `.env` and toggles metrics, logging, and autonomy defaults per environment.【F:edge/app/core/config.py†L9-L52】

## Frontend Architecture

- Next.js App Router renders a CRM operator dashboard using composable layout primitives; Stats, LeadChart, AutonomyLevels, and RecentLeads components visualise telemetry from the core APIs.【F:ui/app/page.tsx†L1-L47】
- Component guidelines, tokens, and Playbook documentation codify UI standards for consistent autonomous UX flows.【F:ui/Playbook.md†L1-L120】
- Tailwind configuration and design tokens centralise theming, while `lib/` hosts API clients/hooks for interacting with edge/core services.【F:ui/tailwind.config.js†L1-L79】

## Eventing & Data Flow

1. **Capture**: Leads enter via edge or core APIs, triggering AI qualification and `leads.captured` events on NATS for analytics and nurture orchestration.【F:core/app/services/lead_service.py†L60-L121】【F:core/app/services/lead_service.py†L198-L232】
2. **Connect**: Communication workflows personalise outreach using AIService, logging engagements to the communications table and feeding the AutonomyEngine for next best actions.【F:core/app/models/communications.py†L15-L66】【F:core/app/services/autonomy_engine.py†L28-L104】
3. **Convert**: DealService progresses opportunities with AI-guided recommendations, updating probabilities and emitting `deals.progressed` events for forecasting and success handoffs.【F:core/app/services/deal_service.py†L20-L199】
4. **Retain**: CustomerSuccessService monitors health, predicts churn/expansion, and coordinates retention plays, pushing results back through events for analytics and automation loops.【F:core/app/services/customer_success_service.py†L1-L176】
5. **Analytics**: DuckDB paths and Chroma endpoints defined in configuration highlight downstream analytical workloads and AI recall pipelines consuming event streams.【F:core/app/core/config.py†L29-L55】

## Key Operational Considerations

- **Autonomy Levels**: Default thresholds and caps are configurable, enabling gradual rollout of autonomous behaviours per team/process.【F:core/app/core/config.py†L57-L63】【F:core/app/services/autonomy_engine.py†L20-L104】
- **Observability**: Both edge and core expose `/metrics` endpoints gated by configuration flags, ensuring Prometheus scraping compatibility across environments.【F:core/app/main.py†L145-L160】【F:edge/app/main.py†L116-L132】
- **Security**: JWT settings, secret keys, and CORS policies are centralised in config modules; the edge gateway adds rate limiting and trusted-host controls for perimeter defense.【F:core/app/core/config.py†L13-L41】【F:edge/app/main.py†L38-L84】

## Next Steps for Contributors

1. **Setup**: Use Docker Compose for local orchestration; install UI dependencies separately for Next.js development.【F:README.md†L32-L57】
2. **Environment**: Populate `.env` with OpenRouter, Supabase, and NATS credentials to unlock AI and data integrations.【F:README.md†L59-L69】【F:core/app/core/config.py†L41-L55】
3. **Testing**: Run pytest for backend coverage and `npm test` within `ui/` for frontend suites; integration scenarios rely on docker-compose test bundles.【F:README.md†L65-L73】

