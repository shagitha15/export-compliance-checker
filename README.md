# Export Customs Documentation Compliance Checker

An enterprise-grade full-stack platform for international trade customs document ingestion, OCR parsing, Gemini LLM structured understanding, cross-document reconciliation, and Indian export customs statutory verification (DGFT FTP 2023, CBIC, RBI FEMA).

---

## 🏗️ Architecture Overview

The platform uses a decoupled client-server architecture:

- **`client/`**: React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons.
- **`server/`**: Python 3.13, FastAPI, Pydantic v2, PyMuPDF, Google GenAI SDK, Supabase PostgreSQL, Pinecone Vector DB.

---

## 🚀 Quickstart

### Prerequisites
- Python 3.11+
- Node.js 18+ & npm
- Docker & Docker Compose (optional)

### 1. Environment Configuration
Copy `.env.example` to `.env` in the root and in both subprojects:
```bash
cp .env.example .env
```

### 2. Backend Setup
```bash
cd server
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
API Documentation will be accessible at: `http://localhost:8000/docs`

### 3. Frontend Setup
```bash
cd client
npm install
npm run dev
```
Frontend will be accessible at: `http://localhost:5173`

---

## 🧪 Testing

```bash
# Run backend tests
make test-server

# Run frontend tests
make test-client
```
