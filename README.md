# Ideas Hub – Backend API

Ideas Hub is a **FastAPI-based backend** built to explore how a real-world content platform could be designed, secured, and scaled at a foundational level.

This project focuses on **authentication, authorization, data modeling, and API design**, rather than just exposing CRUD endpoints. It demonstrates production-aware backend patterns while remaining intentionally scoped for learning and clarity.

---

## Problem This Backend Solves

The backend supports a realistic but intentionally simple use case:

> Users can create, manage, and engage with ideas while the system enforces authentication, permissions, and basic abuse protection.

The primary goal is not the domain itself, but practicing:

- Secure authentication flows
- Clean separation of concerns
- Scalable API structure
- Third-party service integration

---

## Core Features

### Authentication & Security

- JWT-based authentication (access & refresh tokens)
- Google OAuth 2.0 login
- Email verification and password reset
- Role-based access control (RBAC)
- Rate limiting on sensitive endpoints

### Idea & Engagement System

- Create, read, update, and delete ideas
- Soft deletion for data integrity
- Like / unlike functionality with duplicate protection
- Paginated idea listing

### Infrastructure & Integrations

- Async SQLAlchemy with MySQL
- Redis for rate limiting and future caching
- Cloudinary for image uploads
- Brevo for transactional emails
- Dockerized setup for environment consistency

---

## Technology Stack & Rationale

| Component        | Technology         | Reason                                        |
| ---------------- | ------------------ | --------------------------------------------- |
| API Framework    | FastAPI            | Async support, strong typing, OpenAPI docs    |
| Database         | MySQL              | Relational structure, predictable performance |
| ORM              | SQLAlchemy (async) | Explicit query control                        |
| Authentication   | JWT (python-jose)  | Stateless API authentication                  |
| Caching          | Redis              | Rate limiting and caching support             |
| Image Storage    | Cloudinary         | Offloaded media handling                      |
| Email Service    | Brevo              | Transactional email delivery                  |
| Containerization | Docker             | Consistent environments                       |

---

## Project Structure

app/
├── core/ # Configuration, security, shared utilities
├── db/ # Database session and models
├── schemas/ # Pydantic models (validation & serialization)
├── crud/ # Database access layer
├── services/ # Business logic and workflows
├── routers/ # API endpoints (thin controllers)

Design principle:  
Routers remain thin, business rules live in services, and database access is isolated to avoid tight coupling.

---

## API Documentation

Interactive API documentation is available via Swagger UI:

GET /docs

### Authentication (/auth)

- Signup, login, logout
- Token refresh
- Google OAuth login
- Password reset flow

### Users (/users)

- Get authenticated user profile
- Role-protected routes (admin example)

### Ideas (/ideas)

- Create, read, update, delete ideas
- Paginated listing
- Soft deletion

### Likes (/posts)

- Like / unlike ideas
- Retrieve like counts

### Uploads (/upload)

- Upload up to 5 images per request

---

## Environment Configuration

Configuration is managed entirely via environment variables.

Categories include:

- Database: MySQL credentials
- Security: JWT secrets and expiration
- OAuth: Google client credentials
- Caching: Redis connection
- Email: Brevo API credentials
- App Config: Environment, CORS, frontend URL

A complete reference is available in `.env.example`.

---

## Running the Project

### Clone the repository:

    git clone https://github.com/mhaiderzeshan/ideas-hub.git
    cd ideas-hub

### Local Setup (Without Docker)

    python -m venv env
    source env/bin/activate  # On Windows: env\Scripts\activate
    pip install -r requirements.txt
    uvicorn app.main:app --reload

### Docker Setup

    docker build -t ideas-hub .
    docker run -p 8000:8000 --env-file .env ideas-hub

---

## Limitations & Planned Improvements

This project is intentionally **not production-complete**.

Planned improvements include:

- Database migrations (Alembic)
- Background tasks for email delivery
- Centralized logging and monitoring
- API versioning
- Improved permission modeling
- CI/CD pipeline integration

---

## Purpose of This Project

This repository demonstrates:

- Backend fundamentals beyond basic CRUD
- Secure API authentication patterns
- Clean backend architecture
- Awareness of real-world trade-offs and limitations

---

## Final Note

This is a **learning-focused backend project built with production awareness**, not a finished SaaS product.
