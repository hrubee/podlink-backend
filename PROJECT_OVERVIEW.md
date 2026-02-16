# PodMatch.AI - Complete Project Overview

## 📋 Executive Summary

**PodMatch.AI** is a production-ready, AI-powered SaaS platform designed to connect podcast hosts with the perfect guests using semantic search, neural collaborative filtering, and real-time communications. The platform is built as a microservices architecture with complete authentication, payment processing, admin controls, and safety features.

**Status:** ✅ **Production Ready** - All 7 development phases completed

---

## 🏗️ Architecture Overview

### Microservices Architecture

The system consists of **4 main services** orchestrated via Docker Compose and deployable to Kubernetes:

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                    │
│                     Port 3000 - React/TypeScript             │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼──────┐  ┌──────▼──────┐  ┌─────▼────────┐
│   Backend    │  │ ML Service  │  │  Ingestion   │
│   (FastAPI)  │  │  (PyTorch)  │  │   Service    │
│   Port 8000  │  │  Port 8001  │  │  Port 8002   │
└──────┬───────┘  └─────────────┘  └──────┬───────┘
       │                                   │
       └───────────┬───────────────────────┘
                   │
        ┌──────────▼──────────┐
        │   PostgreSQL + Redis │
        │   (Data + Cache)     │
        └──────────────────────┘
```

---

## 🎯 Core Features

### 1. **Authentication & Authorization** ✅
- **JWT-based authentication** with bcrypt password hashing
- **Role-based access control** (Admin, Agency, Host, Guest)
- **GDPR-compliant** soft/hard delete functionality
- Token expiry: 8 days (configurable)

### 2. **AI-Powered Matching** ✅
- **Neural Collaborative Filtering (NCF)** for personalized recommendations
- **Semantic Search** using FAISS + Sentence Transformers
- **Tinder-style swipe interface** for discovering matches
- **Mutual match detection** with Redis-backed real-time notifications

### 3. **Real-Time Chat** ✅
- **WebSocket-based messaging** with connection manager
- **Message persistence** in PostgreSQL
- **Content moderation** with automatic flagging
- **Match verification** - only matched users can chat

### 4. **Payment Integration** ✅
- **Razorpay integration** for subscriptions
- **7-day free trial** with automatic conversion
- **Quota management** using Redis sliding window
- **Webhook verification** for secure payment events
- Free tier: 10 outreach attempts per 30 days

### 5. **Discovery & Search** ✅
- **Podchaser API integration** for real podcast data
- **Trending podcasts** discovery feed
- **Profile search** for hosts and guests
- **Detailed creator profiles** with social links and podcast appearances

### 6. **Admin & Safety** ✅
- **Admin dashboard** with real-time metrics
- **User reporting system** integrated into chat
- **Ban/unban functionality** with audit logging
- **Moderation queue** for reviewing reports
- **Observability middleware** for performance tracking

### 7. **Agency Management** ✅
- **White-label agency accounts** with custom slugs
- **Client onboarding** and management
- **Multi-tenant support** for managing multiple clients
- **Agency member roles** (owner, manager, member)

---

## 📁 Project Structure

```
podcast/
├── apps/
│   ├── backend/              # FastAPI Core API
│   │   ├── app/
│   │   │   ├── api/          # API endpoints
│   │   │   │   └── v1/
│   │   │   │       └── endpoints/
│   │   │   │           ├── auth.py         # Signup/Login/Delete
│   │   │   │           ├── matches.py      # Like/Match/Search
│   │   │   │           ├── chat.py         # WebSocket chat
│   │   │   │           ├── payments.py     # Razorpay integration
│   │   │   │           ├── admin.py        # Admin controls
│   │   │   │           ├── agency.py       # Agency management
│   │   │   │           └── discovery.py    # Profile discovery
│   │   │   ├── core/         # Security, config, middleware
│   │   │   ├── models/       # SQLAlchemy models
│   │   │   │   ├── user.py
│   │   │   │   ├── matches.py
│   │   │   │   ├── chat.py
│   │   │   │   ├── safety.py
│   │   │   │   └── agency.py
│   │   │   └── services/     # Business logic
│   │   │       ├── matching.py
│   │   │       ├── chat.py
│   │   │       ├── payments.py
│   │   │       └── agency.py
│   │   └── main.py
│   │
│   ├── frontend/             # Next.js 14 App
│   │   ├── src/
│   │   │   ├── app/          # Pages (App Router)
│   │   │   │   ├── page.tsx           # Landing page
│   │   │   │   ├── login/
│   │   │   │   ├── signup/
│   │   │   │   ├── dashboard/
│   │   │   │   │   ├── page.tsx       # Discovery feed
│   │   │   │   │   ├── discover/
│   │   │   │   │   ├── matches/
│   │   │   │   │   ├── messages/
│   │   │   │   │   └── billing/
│   │   │   │   ├── admin/
│   │   │   │   └── agency/
│   │   │   ├── components/   # React components
│   │   │   │   ├── discovery/
│   │   │   │   │   ├── DiscoveryFeed.tsx
│   │   │   │   │   └── SwipeCard.tsx
│   │   │   │   ├── chat/
│   │   │   │   │   └── ChatWindow.tsx
│   │   │   │   ├── admin/
│   │   │   │   ├── agency/
│   │   │   │   ├── billing/
│   │   │   │   └── layout/
│   │   │   ├── lib/          # API client
│   │   │   ├── store/        # Zustand state management
│   │   │   └── middleware.ts # Route protection
│   │   └── package.json
│   │
│   ├── ml-service/           # PyTorch ML Service
│   │   ├── app/
│   │   │   ├── services/
│   │   │   │   ├── ranking.py         # NCF model
│   │   │   │   └── vector_search.py   # FAISS search
│   │   │   └── models/
│   │   ├── registry/         # Trained models
│   │   └── main.py
│   │
│   └── ingestion-service/    # Data Pipeline
│       ├── app/
│       │   ├── clients/
│       │   │   └── podchaser.py       # Podchaser API client
│       │   ├── training/
│       │   │   ├── bulk_ingest.py     # Bulk data ingestion
│       │   │   └── train_model.py     # Model training
│       │   ├── tasks/
│       │   │   └── scheduler.py       # Periodic jobs
│       │   └── db/
│       └── main.py
│
├── infra/
│   ├── docker/               # Dockerfiles
│   │   ├── backend.Dockerfile
│   │   ├── frontend.Dockerfile
│   │   ├── ml-service.Dockerfile
│   │   └── ingestion.Dockerfile
│   ├── k8s/                  # Kubernetes manifests
│   │   ├── backend-deployment.yaml
│   │   ├── frontend-deployment.yaml
│   │   ├── ml-service-deployment.yaml
│   │   ├── ingestion-service-deployment.yaml
│   │   ├── hpa.yaml          # Auto-scaling
│   │   ├── ingress.yaml      # Load balancer
│   │   └── secrets-config.yaml
│   └── ci-cd/
│       └── github-actions.yml
│
├── docker-compose.yml        # Local development
├── .env                      # Environment variables
├── README.md
├── ARCHITECTURE.md
├── PHASE_COMPLETE.md         # Phase 6 completion
└── PHASE_7_COMPLETE.md       # Phase 7 completion
```

---

## 🗄️ Database Schema

### PostgreSQL Tables

#### **users**
```sql
- id (PK)
- email (unique)
- hashed_password
- full_name
- role (admin|agency|host|guest)
- is_active
- is_deleted (soft delete)
- deleted_at
- is_public
- agency_id (FK)
- created_at, updated_at
```

#### **matches**
```sql
- id (PK)
- user_one_id
- user_two_id
- is_active
- created_at, matched_at
```

#### **interactions**
```sql
- id (PK)
- actor_id
- target_id
- interaction_type (like|dislike)
- created_at
```

#### **chat_messages**
```sql
- id (PK)
- room_id
- sender_id
- content
- is_flagged
- flagged_reason
- created_at
```

#### **user_reports**
```sql
- id (PK)
- reporter_id (FK)
- target_id (FK)
- reason
- details
- status (pending|resolved|dismissed)
- created_at, resolved_at
```

#### **agencies**
```sql
- id (PK)
- name
- slug (unique)
- website
- logo_url
- owner_id (FK)
- created_at, updated_at
```

### Redis Data Structures

```
likes:{user_id}:{target_id}           → "1" (TTL: 30 days)
active_matches:{user_id}              → SET of matched user IDs
limits:matches:{user_id}              → Match count (TTL: 30 days)
user:{user_id}:quota:outreach:zset    → ZSET for sliding window quota
user:{user_id}:is_paid                → "1" if premium
user:{user_id}:notifications          → HASH of notification counts
```

---

## 🔌 API Endpoints

### Authentication (`/v1`)
- `POST /signup` - Create new user account
- `POST /login/access-token` - Login and get JWT
- `DELETE /me` - GDPR-compliant account deletion

### Matching (`/v1`)
- `POST /like` - Like a user (with quota check)
- `GET /search?q={query}` - Semantic search via ML service
- `GET /matches` - Get active matches
- `POST /unmatch` - Remove a match
- `POST /report` - Report a user

### Chat (`/v1/chat`)
- `WS /ws/{user_id}` - WebSocket connection
- `GET /history/{room_id}` - Message history
- `POST /send` - Send message (with moderation)

### Discovery (`/v1/discovery`)
- `GET /search/profiles?q={query}` - Search hosts/guests
- `GET /discover/trending` - Trending podcasts
- `GET /profile/{id}` - Detailed profile
- `GET /search/podcasts?q={query}` - Search podcasts

### Payments (`/v1/payments`)
- `POST /subscribe` - Create Razorpay subscription
- `POST /webhook/razorpay` - Handle payment events
- `GET /status` - Check premium status

### Admin (`/v1/admin`)
- `GET /stats` - System metrics
- `GET /reports` - User reports queue
- `POST /users/{id}/ban` - Ban user

### Agency (`/v1/agency`)
- `POST /create` - Create agency
- `POST /{id}/onboard-client` - Add client
- `GET /{id}/clients` - List clients
- `GET /my-agencies` - User's agencies

### ML Service (`http://ml-service:8001`)
- `POST /search` - Semantic vector search
- `POST /rank` - Neural ranking
- `POST /ingest-vectors` - Add to vector DB
- `GET /health` - Service status

### Ingestion Service (`http://ingestion-service:8002`)
- `GET /search/podcasts?q={query}` - Search Podchaser
- `GET /search/creators?q={query}` - Search creators
- `GET /discover/trending` - Trending podcasts
- `GET /creator/{id}` - Creator details
- `POST /training/bulk-ingest` - Bulk data ingestion
- `GET /training/status` - Training status

---

## 🛠️ Technology Stack

### Backend
- **Framework:** FastAPI 0.104.1
- **Database:** PostgreSQL 15
- **Cache:** Redis 7
- **ORM:** SQLAlchemy 2.0
- **Auth:** JWT (python-jose) + bcrypt
- **Payments:** Razorpay SDK
- **Server:** Uvicorn

### Frontend
- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **Animations:** Framer Motion
- **State:** Zustand
- **HTTP:** Axios
- **Icons:** Lucide React

### ML/AI
- **Framework:** PyTorch 2.1
- **Embeddings:** Sentence Transformers
- **Vector DB:** FAISS
- **Model:** Neural Collaborative Filtering (NCF)
- **NLP:** Transformers (HuggingFace)

### Infrastructure
- **Containerization:** Docker
- **Orchestration:** Kubernetes (EKS/GKE ready)
- **Load Balancer:** Nginx Ingress
- **Auto-scaling:** Horizontal Pod Autoscaler (HPA)
- **CI/CD:** GitHub Actions

### External APIs
- **Podchaser API:** Podcast metadata and creator data
- **Razorpay:** Payment processing

---

## 🚀 Getting Started

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for local frontend dev)
- Python 3.11+ (for local backend dev)

### Quick Start

1. **Clone and Setup Environment**
```bash
cd /Users/hrushi/Downloads/Desktop\ offline/podcast
cp .env.example .env
# Edit .env with your credentials
```

2. **Start All Services**
```bash
docker-compose up -d --build
```

3. **Access Services**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/docs
- ML Service: http://localhost:8001/docs
- Ingestion Service: http://localhost:8002/docs

4. **Initialize Training Data (Optional)**
```bash
# Ingest 100 trending podcasts
curl -X POST "http://localhost:8002/training/bulk-ingest?num_trending=100"

# Check status
curl http://localhost:8002/training/status
```

### Environment Variables

Key variables in `.env`:

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/podcast
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=yoursecretkeyhere
ACCESS_TOKEN_EXPIRE_MINUTES=11520

# Podchaser API
PODCHASER_API_KEY=your_key
PODCHASER_API_SECRET=your_secret

# Razorpay
RAZORPAY_KEY_ID=your_key
RAZORPAY_KEY_SECRET=your_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_ML_URL=http://localhost:8001
```

---

## 🎨 Frontend Features

### Landing Page
- Modern, animated hero section
- Feature showcase with glassmorphism design
- Social proof section
- Responsive navigation

### Authentication
- Signup with role selection (Host/Guest/Agency)
- Login with JWT token management
- Persistent auth state via Zustand

### Dashboard
- **Discovery Feed:** Tinder-style swipe cards
- **Semantic Search:** AI-powered profile search
- **Matches:** View active connections
- **Messages:** Real-time WebSocket chat
- **Billing:** Subscription management

### Admin Panel
- Real-time system metrics
- User reports moderation queue
- Ban/unban functionality
- Audit log tracking

### Agency Portal
- Create and manage agencies
- Onboard clients
- White-label branding support

---

## 🧠 AI/ML Pipeline

### 1. Vector Search (FAISS)
```python
# Semantic search flow
query = "AI expert in machine learning"
embedding = sentence_transformer.encode(query)
results = faiss_index.search(embedding, k=10)
```

### 2. Neural Collaborative Filtering
```python
# Recommendation flow
user_embedding = user_encoder(user_id)
item_embedding = item_encoder(candidate_ids)
scores = mlp_layers(concat(user_embedding, item_embedding))
ranked_results = sort_by_score(scores)
```

### 3. Training Pipeline
1. **Data Collection:** Fetch interactions from PostgreSQL
2. **Preprocessing:** Map IDs to continuous indices
3. **Training:** PyTorch NCF model (10-20 epochs)
4. **Validation:** HR@10 and NDCG metrics
5. **Deployment:** Save to `registry/latest.pt`

---

## 🔒 Security Features

### Authentication
- JWT tokens with 8-day expiry
- Bcrypt password hashing (cost factor: 12)
- Role-based access control (RBAC)
- WebSocket token validation

### Data Protection
- GDPR-compliant soft/hard delete
- Encrypted passwords (never stored plain)
- Secure webhook signature verification
- SQL injection protection via ORM

### Rate Limiting
- Redis-based sliding window quota
- Free tier: 10 outreach/30 days
- Premium: Unlimited access
- Match limits: 30 per 30 days

### Observability
- Request/response logging
- Performance tracking (X-Process-Time header)
- Global exception handling
- Audit logging for admin actions

---

## 📊 Performance Optimizations

### Caching Strategy
- **Redis for hot data:** Active matches, likes, quotas
- **PostgreSQL for cold data:** Historical interactions, profiles
- **TTL management:** 30-day expiry for temporary data

### Database Optimization
- Indexed columns: user_id, email, room_id
- Soft delete for GDPR compliance
- Batch operations for bulk ingestion

### Microservices Benefits
- **Independent scaling:** ML service can scale separately
- **Fault isolation:** Frontend continues if ML service is down
- **Technology flexibility:** Python for ML, TypeScript for UI

---

## 🚢 Deployment

### Local Development
```bash
docker-compose up -d
```

### Production (Kubernetes)
```bash
# Apply all manifests
kubectl apply -f infra/k8s/

# Check status
kubectl get pods
kubectl get services
kubectl get ingress
```

### Auto-scaling Configuration
```yaml
# HPA for backend
minReplicas: 2
maxReplicas: 10
targetCPUUtilizationPercentage: 70
```

---

## 📈 Monitoring & Metrics

### Admin Dashboard Metrics
- Total users
- Active matches
- Message volume
- Pending reports

### ML Service Health
- Vector count in FAISS index
- Ranking engine status
- Model version

### Performance Tracking
- Request duration (X-Process-Time)
- Slow query logging (>1s)
- Error rate monitoring

---

## 🧪 Testing

### API Testing
```bash
# Backend API docs
open http://localhost:8000/docs

# Test authentication
curl -X POST http://localhost:8000/v1/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123","full_name":"Test User","role":"host"}'
```

### Frontend Testing
```bash
cd apps/frontend
npm run dev
open http://localhost:3000
```

---

## 📝 Development Phases

### ✅ Phase 1-4: Backend Foundation
- Core API endpoints
- Database models
- Authentication & authorization
- Matching logic
- Payment integration

### ✅ Phase 5: Infrastructure
- Docker containerization
- Kubernetes manifests
- CI/CD pipeline
- Auto-scaling configuration

### ✅ Phase 6: Frontend Integration
- Next.js application
- Component library
- State management
- API integration
- Real-time chat

### ✅ Phase 7: Admin & Safety
- Admin dashboard
- User reporting
- Moderation queue
- Audit logging
- Observability middleware

---

## 🔮 Future Enhancements

### Planned Features
1. **Advanced Analytics**
   - User engagement metrics
   - Match success rates
   - Revenue analytics

2. **Enhanced ML**
   - Multi-modal embeddings (text + audio)
   - Reinforcement learning for recommendations
   - A/B testing framework

3. **Communication**
   - Video call integration
   - Calendar scheduling
   - Email notifications

4. **Monetization**
   - Tiered pricing plans
   - Agency white-labeling
   - Marketplace for premium features

---

## 📚 Documentation

- **README.md** - Quick start guide
- **ARCHITECTURE.md** - System design overview
- **TRAINING.md** - AI training pipeline
- **PHASE_COMPLETE.md** - Phase 6 completion notes
- **PHASE_7_COMPLETE.md** - Phase 7 completion notes

---

## 🤝 Contributing

This is a production-ready SaaS platform. For contributions:
1. Follow the existing code structure
2. Maintain test coverage
3. Update documentation
4. Follow security best practices

---

## 📄 License

Proprietary - All rights reserved

---

## 🙏 Acknowledgments

- **Podchaser API** for podcast metadata
- **Razorpay** for payment processing
- **HuggingFace** for ML models
- **FastAPI** for the excellent framework

---

**Built with ❤️ by Antigravity AI**

*Last Updated: January 31, 2026*
