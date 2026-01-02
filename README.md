# AI Code Review Platform

AI-powered code review platform using Claude Opus 4.5/Sonnet for intelligent code analysis.

## Tech Stack

**Frontend:**
- Next.js 16.1 with React 19.2
- TypeScript 5.9
- Tailwind CSS 4.1
- Monaco Editor
- TanStack Query 5.90
- Zustand 5.0

**Backend:**
- FastAPI 0.128
- SQLAlchemy 2.0 (async)
- Celery 5.6
- Redis 8

**AI:**
- Claude Sonnet 4.5 (primary reviews)
- Claude Opus 4.5 (complex analysis)
- Claude Haiku 4.5 (triage)
- LangChain/LangGraph (multi-step workflows)

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 20+
- Anthropic API key
- (Optional) GitHub App for repo integration

### 1. Setup Environment

```bash
# Copy example env and add your API key
cp .env.example .env

# Edit .env and add your ANTHROPIC_API_KEY
```

### 2. Start Backend (Docker)

```bash
# Start Redis, Backend API, and Celery worker
docker-compose up --build -d

# Check logs
docker-compose logs -f backend
```

### 3. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

### 4. Open the App

- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs

## GitHub Integration (Optional)

1. Create a GitHub App at https://github.com/settings/apps/new
2. Set permissions: **Contents (Read)**, **Pull requests (Read & Write)**
3. Add credentials to `.env`:
   ```
   GITHUB_APP_ID=your_app_id
   GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
   GITHUB_WEBHOOK_SECRET=your_secret
   ```
4. Restart Docker: `docker-compose up --build -d`
5. Install the app on your repos, then click "Sync from GitHub" in the UI

## Usage

1. Open http://localhost:3000
2. Paste code and select language
3. Click "Submit for Review"
4. Click "Start Analysis" to run AI review
5. View issues with inline code highlighting

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/reviews` | Create new review |
| GET | `/api/reviews` | List all reviews |
| GET | `/api/reviews/{id}` | Get review details |
| POST | `/api/reviews/{id}/analyze` | Start AI analysis |
| DELETE | `/api/reviews/{id}` | Delete review |

## Project Structure

```
code-review/
├── frontend/
│   ├── src/
│   │   ├── app/           # Next.js pages
│   │   ├── components/    # React components
│   │   ├── lib/           # API client, utils
│   │   └── stores/        # Zustand stores
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI routes
│   │   ├── core/          # Config, database
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/
│   │   │   ├── ai/        # Claude integration
│   │   │   └── analysis/  # Code parsing
│   │   └── tasks/         # Celery tasks
│   └── requirements.txt
│
└── docker-compose.yml
```

## AI Models

The platform uses a tiered approach:

- **Haiku** ($1/$5 MTok): Quick triage, classification
- **Sonnet** ($3/$15 MTok): Standard code review (default)
- **Opus** ($5/$25 MTok): Complex architectural analysis

Toggle "Use Claude Opus" for complex reviews.

## License

MIT
