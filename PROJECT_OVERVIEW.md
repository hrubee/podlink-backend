# PodLink.AI - Complete Project Overview

## 📋 Executive Summary

**PodLink.AI** is a production-ready, AI-powered SaaS platform designed to connect podcast hosts with the perfect guests using semantic search, neural collaborative filtering, and real-time communications. The platform is built as a microservices architecture with complete authentication, payment processing, admin controls, and safety features.

**Status:** ✅ **Production Ready** - Core backend and ML services completed

---

## 🏗️ Architecture Overview

### Microservices Architecture

The system consists of **2 main services** orchestrated via Docker Compose:

```
┌─────────────────────────────────────────────────────────────┐
│                        External Clients                      │
│                     (Mobile / Web Apps)                      │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼──────┐  ┌──────▼──────┐  ┌─────▼────────┐
│   Backend    │  │ ML Service  │  │   Shared     │
│   (FastAPI)  │  │  (PyTorch)  │  │    Libs      │
│   Port 8000  │  │  Port 8001  │  │    Files     │
└──────┬───────┘  └─────────────┘  └──────────────┘
       │                                   
       │                                   
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
- **Role-based access control** (Admin, Host, Guest)
- **GDPR-compliant** soft/hard delete functionality
- Token expiry: 8 hours (configurable)

### 2. **AI-Powered Matching** ✅
- **Neural Collaborative Filtering (NCF)** for personalized recommendations
- **Semantic Search** using FAISS + Sentence Transformers
- **Tinder-style swipe logic** for discovering matches
- **Mutual match detection** with Redis-backed real-time state

### 3. **Real-Time Chat** ✅
- **WebSocket-based messaging** with connection manager
- **Message persistence** in PostgreSQL
- **Content moderation** with automatic flagging
- **Match verification** - only matched users can chat

### 4. **Payment Integration** ✅
- **Razorpay integration** for subscriptions
- **Tiered Plans** (Free & Pro) with monthly/annual options
- **Quota management** using Redis sliding window
- **Webhook verification** for secure payment events

### 5. **Discovery & Search** ✅
- **Internal Profile Discovery** for hosts and guests
- **Profile search** using hybrid ranking
- **Detailed creator profiles** with social links and podcast data

### 6. **Admin & Safety** ✅
- **Admin dashboard** with real-time metrics
- **User reporting system** integrated into chat
- **Ban/unban functionality** with audit logging
- **Observability middleware** for performance tracking

---

## 📁 Project Structure

```
podlink/
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
│   │   │   │           └── admin.py        # Admin controls
│   │   │   ├── core/         # Security, config, middleware
│   │   │   ├── models/       # SQLAlchemy models
│   │   │   │   ├── user.py
│   │   │   │   ├── matches.py
│   │   │   │   └── chat.py
│   │   │   └── services/     # Business logic
│   │   │       ├── matching.py
│   │   │       ├── chat.py
│   │   │       └── payments.py
│   │   └── main.py
│   │
│   ├── ml-service/           # PyTorch ML Service
│   │   ├── app/
│   │   │   ├── services/
│   │   │   │   ├── ranking.py         # NCF model
│   │   │   │   └── vector_search.py   # FAISS search
│   │   └── main.py
│   │
├── libs/
│   └── shared/               # Shared utilities
│
├── infra/
│   └── docker/               # Dockerfiles
│       ├── backend.Dockerfile
│       └── ml-service.Dockerfile
│
├── docker-compose.yml        # Local development
├── .env                      # Environment variables
└── README.md
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
- role (admin|host|guest)
- is_active
- is_deleted (soft delete)
- matching_signals (topics, bio, etc.)
```

#### **matches**
```sql
- id (PK)
- user_one_id
- user_two_id
- is_active
- matched_at
```

#### **chat_messages**
```sql
- id (PK)
- room_id
- sender_id
- content
- created_at
```

### Redis Data Structures

```
likes:{user_id}:{target_id}           → "1" (TTL: 30 days)
active_matches:{user_id}              → SET of matched user IDs
limits:matches:{user_id}              → Match count (TTL: 30 days)
```

---

## 🔌 API Endpoints

### Authentication (`/v1`)
- `POST /signup` - Create account
- `POST /login/access-token` - JWT authentication
- `DELETE /me` - GDPR-compliant account deletion

### Matching (`/v1`)
- `POST /like` - Like a user (with quota check)
- `GET /matches` - Get active matches
- `POST /unmatch` - Remove a match
- `POST /report` - Report a user

### Chat (`/v1/chat`)
- `WS /ws/{user_id}` - WebSocket connection
- `GET /history/{room_id}` - Message history
- `POST /send` - Send message (with moderation)

### Payments (`/v1/payments`)
- `POST /subscribe` - Create Razorpay subscription
- `POST /webhook/razorpay` - Handle payment events
- `GET /status` - Check premium status

### Admin (`/v1/admin`)
- `GET /stats` - System metrics
- `GET /reports` - User reports queue
- `POST /users/{id}/ban` - Ban user

### ML Service (`http://ml-service:8001`)
- `POST /search` - Semantic vector search
- `POST /rank` - Neural ranking
- `POST /ingest-vectors` - Add to vector DB
- `GET /health` - Service status

---

## 🛠️ Technology Stack

### Backend
- **Framework:** FastAPI
- **Database:** PostgreSQL
- **Cache:** Redis
- **ORM:** SQLAlchemy 2.0
- **Auth:** JWT + bcrypt
- **Payments:** Razorpay
- **Server:** Uvicorn

### ML/AI
- **Framework:** PyTorch
- **Embeddings:** Sentence Transformers
- **Vector DB:** FAISS
- **Model:** Neural Collaborative Filtering (NCF)
- **NLP:** Transformers (HuggingFace)

### Infrastructure
- **Containerization:** Docker
- **Deployment:** Railway / Nixpacks
- **Load Balancer:** Nginx Ingress (for K8s, if used)
- **Auto-scaling:** Horizontal Pod Autoscaler (HPA) (for K8s, if used)

### External APIs
- **Razorpay:** Payment processing

---

## 🚀 Getting Started

### Prerequisites
- Docker & Docker Compose
- Python 3.11+

### Quick Start

1. **Clone and Setup Environment**
```bash
cp .env.example .env
# Edit .env with your credentials
```

2. **Start Services**
```bash
docker-compose up -d --build
```

3. **Access Services**
- Backend API: http://localhost:8000/docs
- ML Service: http://localhost:8001/docs

### Environment Variables

Key variables in `.env`:

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/podlink
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=yoursecretkeyhere
ACCESS_TOKEN_EXPIRE_MINUTES=480

# Razorpay
RAZORPAY_KEY_ID=your_key
RAZORPAY_KEY_SECRET=your_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
```

---

## 🧠 AI/ML Pipeline

### 1. Vector Search (FAISS)
Semantic search flows use deep embeddings to find matches based on expertise and audience overlap rather than exact keywords.

### 2. Neural Collaborative Filtering
Personalized ranking based on historical match success and user interaction patterns.

### 3. Training Pipeline
1. **Data Collection:** Fetch interactions from PostgreSQL
2. **Preprocessing:** Map IDs to continuous indices
3. **Training:** PyTorch NCF model (10-20 epochs)
4. **Validation:** HR@10 and NDCG metrics
5. **Deployment:** Save to `registry/latest.pt`

---

## 🔒 Security Features

### Authentication
- JWT tokens with 8-hour expiry
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
- **Fault isolation:** Backend continues if ML service is down
- **Technology flexibility:** Python for ML

---

## 🚢 Deployment

### Local Development
```bash
docker-compose up -d
```

### Production (Railway)
The project is optimized for Railway deployment using the provided `railway.json` and Nixpacks configuration.

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


- **Razorpay** for payment processing
- **HuggingFace** for ML models
- **FastAPI** for the excellent framework

---

**Built with ❤️ by Antigravity AI**

*Last Updated: January 31, 2026*
