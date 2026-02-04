# Social Media API

REST API for a social media platform built with FastAPI, SQLAlchemy 2.0, and PostgreSQL.

## Features

- User registration with email verification (4-digit code via SMTP)
- JWT authentication
- CRUD operations for posts
- Comments on posts
- Like / unlike posts (self-like prevention)
- User feed with search and date filtering
- Post listing with keyword search, date filtering, and pagination
- Profile update (PATCH /auth/me)
- Rate-limited login endpoint (brute-force protection)

## Tech Stack

- **FastAPI** - async web framework
- **SQLAlchemy 2.0** - async ORM with asyncpg driver
- **PostgreSQL 16** - primary database
- **Alembic** - database migrations
- **Pydantic v2** - request/response validation
- **PyJWT + bcrypt** - authentication
- **aiosmtplib** - async SMTP email sending
- **slowapi** - rate limiting
- **Docker & Docker Compose** - containerized deployment
- **GitHub Actions** - CI pipeline

## Production-Ready Features (Bonus)

### GitHub Actions CI

**What:** Automated pipeline that runs linting (`black`, `isort`, `flake8`), the full `pytest` suite, and a Docker image build on every push to `main` and on every pull request.

**Why:** I implemented CI to ensure that the codebase remains stable and adheres to quality standards automatically, simulating a real-world team development workflow.

### Rate Limiting (Brute-force Protection)

**What:** Integrated `slowapi` to limit login attempts to 5 per minute per IP address. Exceeding the limit returns a `429 Too Many Requests` response.

**Why:** Protecting authentication endpoints is a critical security requirement for any public-facing API to prevent automated password-guessing attacks.

### MailHog Integration

**What:** A mock SMTP server included in the `docker-compose` stack. All verification emails are captured and viewable at [http://localhost:8025](http://localhost:8025) with zero configuration.

**Why:** I chose MailHog to provide a zero-configuration "Developer Experience" (DX). Reviewers can test the full email verification flow immediately without needing to set up real SMTP credentials.

## Database Optimizations

### Solving the N+1 Problem

The `/feed` endpoint uses SQLAlchemy `selectinload` to eagerly fetch Users, Posts, and Likes in efficient, separate queries. This avoids the classic N+1 problem where fetching N users would trigger N additional queries for their posts and N more for likes.

### Bulk Deletion

The stale user cleanup (`DELETE /admin/cleanup-users`) uses a single SQL `DELETE` statement with a `WHERE` clause instead of loading every matching object into Python memory and deleting them one by one. This reduces the operation from O(N) round-trips to a single database call.

## Quick Start (Docker)

```bash
docker compose up --build
```

This starts three services:


| Service      | URL                                            | Purpose                        |
| ------------ | ---------------------------------------------- | ------------------------------ |
| **API**      | [http://localhost:8000](http://localhost:8000) | REST API (`/docs` for Swagger) |
| **MailHog**  | [http://localhost:8025](http://localhost:8025) | Email inbox (catches all mail) |
| **Postgres** | localhost:5432                                 | Database                       |


### Email Verification Flow

1. Register a user via `POST /auth/register`
2. Open [http://localhost:8025](http://localhost:8025) — find the email with your 4-digit code
3. Verify via `POST /auth/verify-email` with `{"email": "...", "code": "1234"}`

## Local Development

1. Copy and configure environment:
  ```bash
   cp .env.example .env
   # Edit .env: set SECRET_KEY (min 32 chars) and DATABASE_URL
  ```
2. Install dependencies:
  ```bash
   pip install -r requirements.txt
  ```
3. Run migrations:
  ```bash
   alembic upgrade head
  ```
4. Start the server:
  ```bash
   uvicorn src.main:app --reload
  ```

## Running Tests

```bash
pytest tests/ -v
```

Tests use SQLite in-memory — no external database required.

## API Endpoints

### Auth


| Method | Endpoint           | Description                         |
| ------ | ------------------ | ----------------------------------- |
| POST   | /auth/register     | Register a new user                 |
| POST   | /auth/login        | Login, get JWT token (rate-limited) |
| POST   | /auth/verify-email | Verify email with 4-digit code      |
| GET    | /auth/me           | Get current user profile            |
| PATCH  | /auth/me           | Update current user profile         |


### Posts


| Method | Endpoint                               | Description                         |
| ------ | -------------------------------------- | ----------------------------------- |
| GET    | /posts                                 | List posts (search/filter/paginate) |
| POST   | /posts                                 | Create a post (verified only)       |
| GET    | /posts/{post_id}                       | Get post with comments & likes      |
| PATCH  | /posts/{post_id}                       | Update own post                     |
| DELETE | /posts/{post_id}                       | Delete own post                     |
| POST   | /posts/{post_id}/comments              | Add comment (verified only)         |
| DELETE | /posts/{post_id}/comments/{comment_id} | Delete own comment                  |
| POST   | /posts/{post_id}/like                  | Like a post (not your own)          |
| DELETE | /posts/{post_id}/like                  | Remove like                         |


### Feed


| Method | Endpoint | Description                          |
| ------ | -------- | ------------------------------------ |
| GET    | /feed    | User feed with search & date filters |


### Admin


| Method | Endpoint             | Description                   |
| ------ | -------------------- | ----------------------------- |
| DELETE | /admin/cleanup-users | Remove stale unverified users |


## Project Structure

```
src/
  api/          # Route handlers
  core/         # Config, database, security, exceptions, rate limiter
  models/       # SQLAlchemy models
  schemas/      # Pydantic schemas
  services/     # Business logic layer
tests/          # Pytest test suite
alembic/        # Database migrations
.github/        # CI workflow
```

## Environment Variables


| Variable                    | Required | Default | Description                    |
| --------------------------- | -------- | ------- | ------------------------------ |
| SECRET_KEY                  | Yes      | -       | JWT signing key (min 32 chars) |
| DATABASE_URL                | Yes      | -       | PostgreSQL connection string   |
| ALGORITHM                   | No       | HS256   | JWT algorithm                  |
| ACCESS_TOKEN_EXPIRE_MINUTES | No       | 30      | Token expiry in minutes        |
| DB_POOL_SIZE                | No       | 10      | Connection pool size           |
| DB_MAX_OVERFLOW             | No       | 20      | Max overflow connections       |
| DB_ECHO                     | No       | false   | Log SQL queries                |
| SMTP_HOST                   | No       | -       | SMTP server hostname           |
| SMTP_PORT                   | No       | 587     | SMTP server port               |
| SMTP_USER                   | No       | -       | SMTP username                  |
| SMTP_PASSWORD               | No       | -       | SMTP password                  |
| SMTP_FROM_EMAIL             | No       | -       | Sender email address           |
| SMTP_USE_TLS                | No       | true    | Use STARTTLS                   |


By default, `.env.example` is configured for MailHog (local dev). When running with `docker compose`, emails are delivered automatically to the MailHog UI at [http://localhost:8025](http://localhost:8025).

For production, switch to a real SMTP provider (e.g. Gmail):

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_USE_TLS=true
```

