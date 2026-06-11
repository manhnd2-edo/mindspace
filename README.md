# CTS Operations Agent

AI-powered operations agent for the VNGGames CTS social media team.  
Built with **FastAPI + Claude Sonnet** and deployed on **GreenNode AgentBase** via Docker.

---

## Modules

| Module | Description | Endpoint(s) |
|---|---|---|
| Report Generator | Pull Sprout Social data → Claude summary → Teams | `POST /report/generate` |
| Knowledge Base | Store/retrieve product knowledge, generate content plans | `POST /knowledge/entries`, `GET /knowledge/entries`, `POST /knowledge/plan` |
| Airtable Monitor | Daily anomaly check on content plan → Teams alert | `POST /airtable/check`, `GET /airtable/summary` |
| Sentiment Tracker | Weekly inbox sentiment summary → Teams | `POST /sentiment/report` |
| Chat | Free-text conversation with the agent | `POST /chat` |

---

## Setup

### 1. Clone & configure

```bash
git clone <repo>
cd cts-operations-agent
cp .env.example .env
# Edit .env with your credentials
```

### 2. Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
mkdir -p data/knowledge
uvicorn app.main:app --reload
```

Open: http://localhost:8000/docs

### 3. Docker

```bash
docker compose up --build
```

### 4. GreenNode AgentBase deployment

```bash
# Build and push image
docker build -t cts-operations-agent .
docker tag cts-operations-agent <your-registry>/cts-operations-agent:latest
docker push <your-registry>/cts-operations-agent:latest

# Deploy on GreenNode: set env vars via their dashboard, port 8000
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `GREENNODE_API_KEY` | GreenNode MaaS bearer token |
| `GREENNODE_BASE_URL` | MaaS base URL (default: `https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1`) |
| `GREENNODE_MODEL` | Model ID (default: `qwen/qwen3-5-27b`) |
| `SPROUT_TOKEN` | Sprout Social Bearer token |
| `SPROUT_CUSTOMER_ID` | Sprout Social customer/profile ID |
| `AIRTABLE_TOKEN` | Airtable Personal Access Token |
| `AIRTABLE_BASE_ID` | Airtable base ID (starts with `app`) |
| `AIRTABLE_TABLE_NAME` | Table name in the base (default: `Content Planning`) |
| `TEAMS_WEBHOOK_URL` | Microsoft Teams incoming webhook URL |

---

## Scheduled Jobs

| Job | Schedule | Action |
|---|---|---|
| Airtable daily check | Every day 09:00 ICT | Detect anomalies, alert Teams |
| Weekly sentiment report | Every Monday 08:00 ICT | Generate & send sentiment summary |

---

## API Quick Reference

### Generate a weekly report
```bash
curl -X POST http://localhost:8000/report/generate \
  -H "Content-Type: application/json" \
  -d '{"period": "weekly", "product": "PUBG Mobile VN", "send_to_teams": true}'
```

### Add knowledge entry
```bash
curl -X POST http://localhost:8000/knowledge/entries \
  -H "Content-Type: application/json" \
  -d '{"title": "PUBG Season 20", "content": "Season 20 launches June 2026...", "tags": ["pubg","season"]}'
```

### Generate content plan
```bash
curl -X POST http://localhost:8000/knowledge/plan \
  -H "Content-Type: application/json" \
  -d '{"product": "PUBG Mobile VN", "period": "Tuần 24/2026", "topic": "Season 20 ra mắt"}'
```

### Manual Airtable check
```bash
curl -X POST http://localhost:8000/airtable/check
```

### Chat with the agent
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Tạo kế hoạch nội dung cho sự kiện PUBG Esports tháng 7"}'
```
