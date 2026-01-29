# NetTrace 🌐

Convert natural language descriptions into Cisco Packet Tracer configurations.

## Overview

NetTrace is a web application that uses AI (Mistral) to parse natural language network descriptions and generate:
- VLSM subnet calculations
- Cisco IOS CLI configurations
- Ready-to-use network topologies

## Features

- 🤖 **AI-Powered Parsing**: Uses Mistral AI to understand network requirements
- 📊 **VLSM Calculator**: Optimal subnet allocation with Variable Length Subnet Masking
- 🔧 **Cisco IOS Output**: Ready-to-paste configuration commands
- 🎨 **Dark Terminal UI**: Developer-friendly interface

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Mistral API Key

### Environment Setup

1. Clone the repository
2. Copy environment files:
   ```bash
   cp backend/.env.example backend/.env
   ```
3. Add your Mistral API key to `backend/.env`

### Running with Docker

```bash
docker-compose up -d
```

### Running Locally

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

**Frontend:**
```bash
cd frontend
yarn install
yarn start
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/generate` | Generate network config |

### Generate Request Example

```json
{
  "description": "Create 3 subnets with 50 hosts each from 192.168.1.0/24 with 1 router and 3 switches"
}
```

## Project Structure

```
NetTrace/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── routers/generate.py  # API endpoints
│   │   └── services/
│   │       ├── nlp_parser.py    # Mistral AI integration
│   │       ├── subnet_calculator.py
│   │       └── pkt_generator.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── services/api.js
│   │   └── App.js
│   └── package.json
└── docker-compose.yml
```

## Tech Stack

- **Backend**: Python, FastAPI, Mistral AI
- **Frontend**: React, TailwindCSS
- **Database**: PostgreSQL (optional for saving configs)

## License

MIT License
