# System Architecture: Federal Tax Intelligence (FTI)

This document outlines the architectural design of the FTI platform, detailing the interactions between the local LLMs, AI semantic search pipeline, Python processing core, FastAPI backend, and Next.js frontend.

## 1. High-Level Architecture

The system follows a modern decoupled architecture:

1.  **Frontend Presentation Layer:** Next.js (React) + TailwindCSS
2.  **API & Orchestration Layer:** FastAPI (Python)
3.  **Data & Intelligence Engine (Core):** Pandas, NetworkX, scikit-learn
4.  **Local AI Services:** Ollama (LLM), Sentence-Transformers (Embeddings)

---

## 2. Component Breakdown

### A. Frontend (Next.js App Router)
- **Framework:** Next.js 14 (App Router)
- **Styling:** TailwindCSS with a customized dark-mode intelligence theme.
- **State Management:** React Hooks + Session Storage for secure agent authentication.
- **Key Modules:**
  - AppShell: Handles login guarding, layout, and global navigation.
  - ChatWidget: Global floating UI for Lumi, the AI assistant.
  - Page specific modules (/ingestion, /resolution, /risk, /graph, /profile).

### B. Backend API (FastAPI)
- **Framework:** FastAPI running on Uvicorn (Port 8000).
- **Core Responsibilities:**
  - Serves RESTful JSON endpoints to the Next.js frontend.
  - Wraps the underlying Data Science core/ engine.
  - Coordinates GPU-accelerated model inference via Singleton services.
- **Key Services (ackend/services/):**
  - ModelService: Lazily loads BAAI/bge-m3 and bge-reranker-base into VRAM (CUDA).
  - EmbeddingService: Manages FAISS vector indexes for semantic similarity.
  - RerankerService: Executes cross-encoder scoring on candidate records.
  - LLMService: Interfaces asynchronously with the local Ollama daemon.
  - DataService: In-memory caching and Pandas DataFrame querying for blazing-fast retrievals.

### C. Artificial Intelligence & Semantic Search Pipeline
The search architecture utilizes a 3-stage retrieval augmented approach:
1.  **Stage 1: Base Retrieval:** RapidFuzz text matching + standard Pandas Boolean masking.
2.  **Stage 2: Dense Retrieval (Semantic):** Converts query to a 1024-d dense vector using ge-m3. Queries the FAISS Index (IndexFlatIP) for top 50 semantic matches (e.g., matching "sadia" to a child record's parent name).
3.  **Stage 3: Cross-Encoder Reranking:** Takes the combined candidates and scores them against the query using ge-reranker-base to generate a final 0.0-1.0 confidence score.

### D. LLM Integration (Lumi)
- **Engine:** Ollama running qwen2.5:3b locally.
- **Integration:** The FastAPI backend (LLMService) communicates with Ollama's REST API (http://localhost:11434/api/generate).
- **Prompting:** Uses context-injected zero-shot prompting to analyze Citizen Profiles, audit trails, and risk metrics dynamically without requiring fine-tuning.

### E. Data Processing Core (core/)
- **ETL:** Loads raw CSV datasets (Tax, NADRA, Vehicles, Travel, etc.) and normalizes them.
- **Entity Resolution (ER):** Merges disparate records using multi-pass blocking, phonetic algorithms (Soundex), and cross-lingual matching (Urdu/English).
- **Graph Analytics:** NetworkX builds a property graph of citizens, addresses, businesses, and phone numbers to detect hidden communities and syndicate rings.
- **ML Risk Scoring:** Isolation Forests and LOF evaluate normalized feature matrices to generate Deviation Scores and Risk Categories (A-E).

---

## 3. Data Flow

1.  **Ingestion:** un_pipeline.py executes the core engine to process raw data -> outputs data/processed_v2/.
2.  **Startup:** Start_Tax_Intelligence.bat boots Ollama, FastAPI, and Next.js. FastAPI preloads models and builds the FAISS index in the background.
3.  **User Request:** Agent queries a citizen via the Next.js UI.
4.  **API Execution:** Next.js hits /api/v1/search.
5.  **AI Processing:** FastAPI runs the 3-stage semantic search.
6.  **Response:** The UI renders the reranked results.
7.  **Investigation:** Agent opens a profile and chats with Lumi. FastAPI injects the citizen's financial context into the Ollama prompt, returning an expert tax intelligence summary.
