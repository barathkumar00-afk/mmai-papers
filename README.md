# Brain Disease AI — MedExplain AI

> **Research Prototype for Multimodal Neurological & Neuro-Oncology Clinical Decision Support**

Brain Disease AI (MedExplain AI) is an open experimental framework designed to explore artificial intelligence assistance for brain MRI analysis, speech acoustic telemetry, and neurological clinical records. It unifies multiparametric brain imaging, phonetic speech cadence signals, and structured electronic health record (EHR) indicators into an interpretable differential assessment, grounded against peer-reviewed clinical society guidelines via Retrieval-Augmented Generation (RAG).

---

> [!IMPORTANT]
> ### Clinical & Regulatory Notice
> **Brain Disease AI is an experimental research and educational prototype.**
> - It is **not** an autonomous diagnostic system and is **not** certified as a medical device under FDA 21 CFR Part 882, EU MDR, or CE mark frameworks.
> - Model outputs represent candidate decision-support hypotheses and must **never** be used as a substitute for professional medical evaluation, neuroradiological interpretation, or clinical diagnosis by licensed healthcare practitioners.
> - No claims of standalone clinical efficacy, diagnostic sensitivity, specificity, or therapeutic safety are made without formal prospective clinical trials.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Installation and Local Setup](#installation-and-local-setup)
  - [Prerequisites](#prerequisites)
  - [1. Clone Repository](#1-clone-repository)
  - [2. Backend Setup (FastAPI & Python 3.12)](#2-backend-setup-fastapi--python-312)
  - [3. Frontend Setup (React 19 & Vite 8)](#3-frontend-setup-react-19--vite-8)
- [Environment Configuration](#environment-configuration)
- [API Reference](#api-reference)
- [Automated Testing & Verification](#automated-testing--verification)
- [Limitations & Responsible Use](#limitations--responsible-use)
- [Project Roadmap](#project-roadmap)
- [Contributing & License](#contributing--license)

---

## Overview

Clinical diagnosis of intracranial pathology—such as high-grade gliomas, meningiomas, and pituitary adenomas—requires synthesizing multiple distinct data modalities:
1. **Neuroimaging:** High-resolution contrast-enhanced MRI (T1+Gd, T2/FLAIR, DWI).
2. **Acoustic Telemetry:** Speech pacing, vocal pauses, and latency patterns indicative of motor speech impairment or cognitive slowing.
3. **Structured Clinical Indicators:** Glasgow Coma Scale (GCS), Karnofsky Performance Status (KPS), intracranial pressure (ICP), and inflammatory acute phase reactants.

Brain Disease AI provides a coordinated multimodal interface that ingests these inputs, runs modality-specific feature extraction, applies a calibrated integration layer, and retrieves authoritative clinical literature from an indexed vector knowledge base (WHO CNS5, EANO, SNO, NCCN) to generate explainable, auditable diagnostic justifications.

---

## Key Features

### 1. Brain MRI Image Analysis
- **Supported Formats:** PNG, JPEG, and DICOM (`.dcm`) uploads.
- **Preprocessing & Feature Extraction:** Automated image intensity windowing, spatial quadrant density distribution calculation, and 512-dimensional visual feature embedding.
- **Modality Detection:** Automated inference of scan modality (`mr_brain`) from file tokens and contrast profiles.
- **Interactive Radiology Inspection:** In-browser contrast inversion, high-contrast windowing, and anatomical target reticle overlay.

### 2. Speech & Acoustic Analysis
- **Acoustic Signal Processing:** Ingests 16kHz PCM WAV and MP3 recordings.
- **Telemetry Extraction:** Measures audio duration, root-mean-square (RMS) energy, speech cadence, and vocal pause intervals relevant to dysarthria and cognitive response latency.

### 3. Structured Neurological Telemetry
- **Standardized Clinical Scales:** Real-time ingestion and validation of:
  - Glasgow Coma Scale (GCS: 3–15)
  - Karnofsky Performance Status (KPS: 0–100%)
  - Intracranial Pressure (ICP: 5–15 mmHg normal baseline)
  - Room-air SpO2 and Serum C-Reactive Protein (CRP)
- **Symptom Lexicon Mapping:** Automated normalization of clinical presentation tokens (e.g., headache, focal seizures, bitemporal visual field loss, altered mental status).

### 4. Prototype Multimodal Integration Layer
- Combines visual scan features, speech acoustic markers, and validated EHR metrics into a normalized differential distribution across 4 target classes:
  - **Glioma / Glioblastoma** (WHO Grade 4 astrocytic neoplasm)
  - **Meningioma** (Dural-based extra-axial mass)
  - **Pituitary Macroadenoma** (Sellar/suprasellar lesion with chiasmatic compression)
  - **Normal Brain Control** (No intracranial mass lesion)
- *Implementation Note:* The current system uses a calibrated heuristic and statistical integration layer (`role: "integration_layer"`). It does not claim an end-to-end backpropagated cross-attention neural network.

### 5. Grounded Evidence Retrieval (RAG)
- **FAISS CPU Vector Database:** Indexing 10 peer-reviewed neuro-oncology and radiology clinical documents across 41 semantic chunks.
- **Zero Hallucination Anchoring:** Retrieved citations feature PubMed Central IDs, clinical society guidelines (WHO CNS5, EANO, SNO, NCCN), relevance percentages, and verbatim quoted evidence.

### 6. Explainable Clinical Dossiers & Audits
- **Interactive Multi-Head Attention Trace:** Simulated cross-modal token attribution heatmap visualizing feature weighting across spatial and tabular inputs.
- **Exportable PDF Dossier:** Printable clinical summary document complete with cryptographic hash identifier, patient timeline, and attending physician sign-off gating.

---

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                       User Interface                        │
│            React 19 + TypeScript + Vite 8 + Tailwind         │
│   (Workbench, 3D Fiber Tractography, Contrast Tools, PDF)   │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / Multipart Form-Data
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Gateway (Port 8000)              │
│       Input Sanitization • Content Sniffing • CORS Guard    │
└───────┬──────────────────────┬──────────────────────┬───────┘
        │                      │                      │
        ▼                      ▼                      ▼
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│ VisionService │      │ SpeechService │      │ClinicalService│
│  Intensity &  │      │  Librosa 16kHz│      │ GCS, KPS, ICP │
│ Quadrant Feats│      │ Cadence & RMS │      │ Symptom Flags │
└───────┬───────┘      └───────┬───────┘      └───────┬───────┘
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────┐
│             Multimodal Integration Layer (Fusion)           │
│   Calibrated Probability Differential (Glioma/Meningioma)   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│          Retrieval-Augmented Generation (RAG Core)          │
│       FAISS HNSW Vector Store + all-MiniLM-L6-v2 Embeddings  │
│        Indexed Guidelines: WHO CNS5, EANO, SNO, NCCN        │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│         Explanation & Clinical Synthesis Service            │
│      Grounded Differential • Attending Physician Gating     │
└─────────────────────────────────────────────────────────────┘
```

1. **Intake:** The client uploads a brain MRI scan, an optional cognitive speech audio recording, and clinical indicators via the unified `/api/multimodal/analyze` endpoint.
2. **Security & Validation:** Content-type sniffing validates file magic numbers (rejecting MIME mismatches and oversized or corrupt payloads).
3. **Modality Processing:** `VisionService` computes visual descriptors; `SpeechService` extracts speech cadence metrics; `ClinicalService` validates physiological parameters against reference ranges.
4. **Integration:** `FusionService` synthesizes modality signals into a calibrated differential ranking.
5. **Knowledge Grounding:** `RAGService` searches the local FAISS index using cosine similarity to attach relevant clinical society citations to the differential.
6. **Delivery:** The client receives a structured JSON payload containing the differential ranking, model confidence, attention weights, clinical recommendations, and evidence references.

---

## Architecture

The project is structured as a decoupled full-stack monorepo:

```
mmai-papers/
├── src/                          # Frontend Application (React 19 + Vite 8)
│   ├── assets/brain_scans/       # Brain MRI test fixtures (Glioma, Meningioma, etc.)
│   ├── components/               # UI components
│   │   ├── WorkbenchSection.tsx  # Interactive diagnostic suite & preset loader
│   │   ├── EvidenceSection.tsx   # FAISS simulated & live query explorer
│   │   ├── BrainHeroCanvas.tsx   # Three.js 3D brain connectome tractography
│   │   ├── ReportSection.tsx     # Grounded clinical dossier specification
│   │   ├── Modals.tsx            # Printable PDF export & Attention trace modal
│   │   ├── ModelStackSection.tsx # Architectural subsystem breakdown
│   │   └── Navbar.tsx / FooterBar.tsx
│   ├── App.tsx                   # Main component tree & state wiring
│   └── main.tsx                  # React DOM entry point
│
├── backend/                      # Backend Service (FastAPI + Python 3.12)
│   ├── app/
│   │   ├── api/routes/           # Endpoint handlers (multimodal, health, retrieval)
│   │   ├── core/                 # Config, security sanitization, and structured logging
│   │   ├── models/               # Model lifecycle manager
│   │   ├── schemas/              # Pydantic v2 data models
│   │   ├── services/             # Domain services (vision, speech, fusion, rag, llm)
│   │   └── utils/                # Validation and image/audio helpers
│   ├── data/
│   │   ├── indexes/              # Built FAISS medical.index and metadata.json
│   │   ├── knowledge/            # Markdown clinical guidelines (WHO CNS5, EANO, etc.)
│   │   └── samples/              # Test assets (MRI PNGs and 16kHz WAVs)
│   ├── scripts/                  # CLI utilities (ingest_knowledge.py, create_test_assets.py)
│   └── tests/                    # Pytest test suite (12 unit and integration tests)
│
├── Brain_disease_AI/             # Evaluation scripts & exploratory notebooks
│   ├── evaluate_qwen.py          # Vision-language model evaluation harness
│   └── evaluate.ipynb            # Jupyter exploration notebook
│
├── papers/                       # Indexed scientific review literature (PDFs)
├── package.json                  # Frontend dependencies and build scripts
└── vite.config.ts                # Vite 8 configuration
```

---

## Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend Framework** | React 19, TypeScript, Vite 8 |
| **Styling & Visualization** | Tailwind CSS, Three.js (3D Brain Connectome), Lucide React, Google Material Symbols |
| **Backend Framework** | FastAPI 0.115+, Uvicorn (ASGI), Pydantic v2 |
| **Machine Learning / Numerical** | PyTorch, Torchvision, NumPy, Pillow |
| **Audio Processing** | Librosa, Soundfile |
| **Vector Search & Embeddings** | FAISS (CPU HNSW), Sentence-Transformers (`all-MiniLM-L6-v2`) |
| **Testing** | Pytest 9, Starlette TestClient, HTTPX |

---

## Installation and Local Setup

### Prerequisites
- **Node.js:** v18.0.0 or higher (`node -v`)
- **Python:** v3.11 or v3.12 (`python --version`)
- **Operating System:** Windows 10/11, macOS, or Linux

---

### 1. Clone Repository

```bash
git clone https://github.com/barathkumar00-afk/mmai-papers.git
cd mmai-papers
```

---

### 2. Backend Setup (FastAPI & Python 3.12)

Open a terminal (PowerShell on Windows):

```powershell
# Navigate to the backend directory
cd "backend"

# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1
# On Linux/macOS: source .venv/bin/activate

# Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# (Optional) Rebuild the FAISS knowledge vector index
python scripts/ingest_knowledge.py --rebuild

# Start the FastAPI development server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The backend will be running at **`http://127.0.0.1:8000`**.  
Interactive Swagger documentation is available at **`http://127.0.0.1:8000/docs`**.

---

### 3. Frontend Setup (React 19 & Vite 8)

Open a **separate** terminal in the project root:

```powershell
# In the root repository directory
npm install

# Start the Vite development server
npm run dev
```

The frontend will be running at **`http://localhost:3000`** (or the port shown in your terminal).

---

## Environment Configuration

A template configuration is provided in `backend/.env.example`. By default, the application runs in self-contained heuristic mode (`MOCK_MODE=true`), requiring **zero** external API keys or cloud services:

```ini
# backend/.env
ENVIRONMENT=development
PORT=8000
HOST=127.0.0.1

# Running without external LLMs (uses local deterministic clinical heuristics)
MOCK_MODE=true

# Optional: Enable external OpenAI or local Ollama LLMs
# OPENAI_API_KEY=your_key_here
# OLLAMA_BASE_URL=http://localhost:11434
```

---

## API Reference

The backend provides structured REST endpoints under the `/api` prefix:

| Endpoint | Method | Status | Description |
| :--- | :---: | :---: | :--- |
| `/api/health` | `GET` | **Operational** | Verifies subsystem readiness, dependency versions, and active model flags. |
| `/api/health/ready` | `GET` | **Operational** | Kubernetes/Docker readiness probe returning detailed component health. |
| `/api/multimodal/analyze` | `POST` | **Operational** | Unified multipart endpoint ingesting image scan, audio file, and clinical JSON. |
| `/api/retrieve/evidence` | `POST` | **Operational** | Semantic search querying the FAISS vector database for clinical society citations. |
| `/api/image/analyze` | `POST` | **Operational** | Dedicated image upload endpoint extracting intensity and spatial features. |
| `/api/speech/analyze` | `POST` | **Operational** | Dedicated audio upload endpoint extracting speech duration, energy, and cadence. |
| `/api/clinical/analyze` | `POST` | **Operational** | Validates structured neurological metrics (GCS, KPS, ICP) and symptom tags. |
| `/api/explanation/generate`| `POST` | **Operational** | Produces evidence-grounded textual clinical rationales for a case. |
| `/api/report/generate` | `POST` | **Operational** | Compiles a full clinical audit dossier with uncertainty estimates. |

Full interactive API documentation with live schema testing is accessible at:
- **Swagger UI:** [`http://127.0.0.1:8000/docs`](http://127.0.0.1:8000/docs)
- **ReDoc:** [`http://127.0.0.1:8000/redoc`](http://127.0.0.1:8000/redoc)

---

## Automated Testing & Verification

The project includes an automated test suite verifying positive multimodal inference, edge cases, input validation, and vector retrieval.

### Running Backend Pytest Suite

```powershell
cd "backend"
.\.venv\Scripts\Activate.ps1
pytest -v
```

**Test Verification Summary:**
```text
tests/test_brain_multimodal.py::test_multimodal_brain_glioma_analysis PASSED
tests/test_brain_multimodal.py::test_multimodal_missing_all_parameters PASSED
tests/test_brain_multimodal.py::test_multimodal_unsupported_image_format PASSED
tests/test_brain_multimodal.py::test_multimodal_corrupted_image PASSED
tests/test_brain_multimodal.py::test_retrieval_neuro_oncology_faiss PASSED
tests/test_health.py::test_root_banner PASSED
tests/test_health.py::test_health_reports_dependencies PASSED
tests/test_health.py::test_health_declares_fusion_is_not_a_trained_model PASSED
tests/test_health.py::test_health_readiness_detail PASSED
tests/test_health.py::test_request_id_header_is_echoed_or_generated PASSED
tests/test_health.py::test_unknown_route_returns_structured_error PASSED
tests/test_health.py::test_openapi_schema_is_generated PASSED

======================= 12 passed, 0 failed in 10.48s =======================
```

### Running Frontend Production Build

```powershell
npm run build
```

The production bundle builds cleanly via Vite (`dist/` directory generated with zero TypeScript or bundling errors).

---

## Limitations & Responsible Use

To ensure medical and scientific integrity, the following technical limitations are explicitly documented:

1. **Non-Diagnostic Status:** This project is a software prototype created for academic exploration and interface design. It has not undergone clinical validation, multi-center retrospective trials, or prospective evaluation.
2. **Prototype Integration Layer:** The multimodal fusion engine is an architectural integration layer combining individual modality descriptors with clinical decision rules. It is not an end-to-end trained deep neural cross-attention network.
3. **No Unverified Clinical Metrics:** This repository does not claim specific clinical diagnostic sensitivity, specificity, or area-under-the-curve (AUC) benchmarks on patient populations.
4. **Local Heuristic vs. Cloud LLM:** In default local mode (`MOCK_MODE=true`), clinical explanations and recommendations are deterministic rule-based syntheses derived from verified WHO CNS5 and EANO guidelines to eliminate arbitrary LLM hallucinations.
5. **Data Privacy:** Do not upload real patient protected health information (PHI) or identifiable scans without institutional review board (IRB) approval and HIPAA/GDPR-compliant infrastructure.

---

## Project Roadmap

- [x] **Core Multimodal Pipeline:** Multipart file intake for Brain MRI, 16kHz audio, and clinical JSON.
- [x] **Vector Knowledge Base:** FAISS HNSW indexing of neuro-oncology guidelines (WHO CNS5, EANO, SNO, NCCN).
- [x] **Medical Workbench UI:** Interactive dark theme with 4 preset brain pathology cases, contrast tools, and telemetry.
- [x] **Automated Testing Suite:** 12 backend unit/integration tests and clean Vite production bundling.
- [ ] **Volumetric 3D MRI Visualization:** Integration of interactive NIfTI/DICOM multi-slice orthogonal viewers (Axial, Coronal, Sagittal).
- [ ] **Neural Cross-Attention Training:** End-to-end training of vision-language adapters on public neuro-oncology benchmarks (BraTS, Figshare Brain Tumor dataset).
- [ ] **FHIR / DICOMweb Integration:** Standardized interoperability with hospital PACS and electronic medical record protocols.

---

## Contributing & License

### Contributing
Contributions to improve code quality, documentation, test coverage, and scientific accuracy are welcome:
1. Fork the repository.
2. Create a dedicated feature branch (`git checkout -b feature/clinical-enhancement`).
3. Commit clear, well-tested changes (`git commit -m 'feat: add DICOM header tag validator'`).
4. Ensure all tests pass (`pytest -v` and `npm run build`).
5. Open a Pull Request with a detailed explanation of your changes.

### License
No explicit open-source license is currently declared for this repository. All rights are reserved by the original author. For licensing inquiries, academic collaboration, or permission to use, please contact the repository owner ([@barathkumar00-afk](https://github.com/barathkumar00-afk)).
