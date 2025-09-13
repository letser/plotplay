# PlotPlay - AI-Driven Text Adventure Engine

An interactive fiction engine combining branching narratives with AI-generated prose.

## Features
- Dynamic narrative generation using LLMs
- Character behavior and consent systems
- Appearance and wardrobe tracking
- Support for mature/NSFW content
- Save/load game states

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 20+

### Development Setup

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/plotplay.git
cd plotplay
```

2. Set up environment:
```bash
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys
```

3. Start with Docker Compose:
```bash
docker-compose up
```

4. Access the application:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Development without Docker

Backend:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```

## Project Structure
- `/backend` - FastAPI backend (Python)
- `/frontend` - React frontend (TypeScript)
- `/games` - Game content files
- `/shared` - Shared specifications

## License
MIT
