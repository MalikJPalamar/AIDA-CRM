# AIDA-CRM Specification

## CRM Life-Cycle Implementation

The AIDA-CRM system implements a complete customer relationship management flow following the four-stage life-cycle:

### 1. Capture Stage
**Purpose**: Identify and capture potential leads from multiple channels
- **Lead Sources**: Web forms, API endpoints, social media, referrals
- **Data Collection**: Contact info, interest level, source attribution
- **Autonomy**: L1 (manual review) ➜ L5 (auto-qualification)
- **Storage**: Immediate capture to NATS stream → DuckDB analytics

### 2. Connect Stage
**Purpose**: Establish meaningful communication with captured leads
- **Communication Channels**: Email sequences, SMS, in-app messaging
- **Personalization**: AI-driven content based on lead profile and behavior
- **Autonomy**: L2 (template selection) ➜ L5 (fully personalized outreach)
- **Tracking**: Engagement metrics, response rates, communication history

### 3. Convert Stage
**Purpose**: Transform qualified leads into paying customers
- **Deal Pipeline**: Opportunity tracking, stage progression, probability scoring
- **Sales Automation**: Meeting scheduling, proposal generation, contract management
- **Autonomy**: L3 (guided workflows) ➜ L5 (autonomous deal closure)
- **Analytics**: Conversion rates, deal velocity, revenue attribution

### 4. Retain Stage
**Purpose**: Maintain and expand customer relationships
- **Customer Success**: Onboarding workflows, health scoring, expansion opportunities
- **Support Integration**: Ticket tracking, satisfaction monitoring, renewal prediction
- **Autonomy**: L4 (proactive alerts) ➜ L5 (autonomous retention actions)
- **Insights**: Churn prediction, lifetime value, advocacy potential

## Data Architecture

### Event-Driven Design
All life-cycle transitions emit events through NATS JetStream:
- `lead.captured` → Analytics, qualification workflows
- `lead.connected` → Communication tracking, engagement scoring
- `deal.converted` → Revenue recognition, customer onboarding
- `customer.retained` → Success workflows, expansion opportunities

### Storage Strategy
- **Transactional**: Supabase for real-time operations
- **Analytics**: DuckDB for aggregations and reporting
- **Semantic**: Chroma for AI-powered insights and personalization
- **Files**: Parquet for data lake storage

## Autonomy Progression

The system supports five levels of autonomy across all life-cycle stages:

- **L1 Draft-Only**: System suggests actions, human executes
- **L2 Assisted**: System performs with human approval
- **L3 Supervised**: System acts with human oversight
- **L4 Delegated**: System operates within defined boundaries
- **L5 Autonomous**: Full automation with human-on-the-loop

Each customer interaction can operate at different autonomy levels based on configuration, confidence scores, and business rules.