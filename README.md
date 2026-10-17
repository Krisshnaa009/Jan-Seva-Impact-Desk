# JanSeva Impact Desk 🌿
### NGO Report & Receipt Engine

> **Turn receipts and field evidence into organized, review-ready NGO reports.**

An AI-powered expense management application designed for small NGOs and community organisations. Upload receipt images, extract data automatically, validate expenses, and generate professional PDF reports — all with a clean, human-friendly interface.

---

## Problem & Intended Users

Small NGOs and community groups often struggle to maintain accurate, audit-ready expense records. Field workers collect paper receipts, and staff manually transcribe data into spreadsheets — a slow, error-prone process. JanSeva Impact Desk automates receipt data extraction, flags errors, and produces PDF reports suitable for donor reviews.

**Target users:** NGO program officers, finance coordinators, field staff.

---

## Features

| Feature | Description |
|---|---|
| 📤 Receipt Upload | Upload PNG/JPG/JPEG receipt images in bulk |
| 🤖 AI Extraction | Extract date, vendor, amount, category via Gemini Vision |
| 🎭 Demo/Mock Mode | Fully functional without any API key |
| ✅ Validation | Detect missing fields, invalid amounts, duplicate receipts |
| 🔍 Review Workflow | Edit, approve, flag, or reject individual records |
| 📊 Dashboard | Live metrics from session data |
| 📄 PDF Reports | Professional, downloadable expense reports |
| 🔒 Secure Config | API key via env var or Streamlit secrets — never hardcoded |

---

## Technology Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| UI | Streamlit |
| AI | Google Gemini API (`gemini-1.5-flash`) |
| Data models | Pydantic v2 |
| Financial math | Python `decimal` |
| PDF generation | ReportLab |
| Image processing | Pillow |
| Testing | `unittest` |

---

## Project Structure

```
janseva-impact-desk/
├── app.py                    # Streamlit application entry point
├── requirements.txt
├── README.md
├── .gitignore
├── .env.example              # Copy to .env and add your API key
├── models/
│   ├── __init__.py
│   └── expense.py            # Pydantic models: ExpenseRecord, ExpenseStatus
├── services/
│   ├── __init__.py
│   ├── receipt_extractor.py  # Gemini Vision + mock extraction
│   ├── validation_service.py # Deterministic validation + duplicate detection
│   ├── report_service.py     # Financial calculations (Decimal)
│   └── pdf_service.py        # ReportLab PDF generation
├── utils/
│   ├── __init__.py
│   └── config.py             # Env/Streamlit secrets config loader
├── tests/
│   ├── test_validation.py    # Validation logic tests
│   ├── test_calculations.py  # Financial calculation tests
│   └── test_reports.py       # PDF generation + mock mode tests
└── sample_data/
    └── README.md             # Information about demo data
```

---

## macOS Installation

### 1. Prerequisites

```bash
# Requires Python 3.10 or later
python3 --version

# Install Homebrew if needed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python
```

### 2. Clone or Download the Project

```bash
cd ~/projects   # or any directory
# If using git:
git clone <your-repo-url> janseva-impact-desk
cd janseva-impact-desk
```

### 3. Set Up Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Gemini API Configuration

**Option A — Environment variable (recommended for local development):**

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your API key
# Get a free key at: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your_actual_key_here
```

Then load it before starting the app:

```bash
export $(cat .env | xargs)
streamlit run app.py
```

**Option B — Streamlit secrets (recommended for deployment):**

Create `.streamlit/secrets.toml`:

```toml
GEMINI_API_KEY = "your_actual_key_here"
```

**Important:** `.env` is listed in `.gitignore`. Never commit your API key to Git.

---

## Running the Application

```bash
# From inside janseva-impact-desk/
source .venv/bin/activate

# Without API key (demo/mock mode):
streamlit run app.py

# With Gemini API key:
GEMINI_API_KEY=your_key streamlit run app.py
```

The app opens at **http://localhost:8501** in your browser.

---

## Running Tests

```bash
# From inside janseva-impact-desk/
source .venv/bin/activate

# Run all tests
python -m pytest tests/ -v

# Or with unittest directly
python -m unittest discover tests/ -v

# Run individual test files
python -m unittest tests/test_validation -v
python -m unittest tests/test_calculations -v
python -m unittest tests/test_reports -v
```

All tests run without internet access or a real API key. AI calls are mocked.

---

## 5-Minute Demo Guide

1. **Start the app** — `streamlit run app.py`
2. **Load Demo Data** — Click "Load Demo Dataset" on the Upload page
3. **Dashboard** — Show live metrics (total, pending, approved, amount)
4. **Review & Approve** — Show validation errors, edit a record, approve it
5. **Generate Report** — Fill org/project details, download the PDF

---

## Deployment

### Streamlit Community Cloud (Free)

1. Push your code to a **public** GitHub repository (ensure `.env` is in `.gitignore`)
2. Visit [share.streamlit.io](https://share.streamlit.io)
3. Click **New app** → select your repo → set `app.py` as the entry point
4. In **Advanced settings → Secrets**, add:
   ```toml
   GEMINI_API_KEY = "your_key_here"
   ```
5. Click **Deploy**

No manual approval needed for Streamlit Community Cloud.

---

## Known Limitations

- **Session state only:** Records are not persisted to a database. Refreshing the page clears the session. Add SQLite or a cloud DB for persistence.
- **Image quality:** AI extraction accuracy depends on receipt image clarity. Low-resolution or blurry images will produce incomplete extractions.
- **Single currency PDF total:** The PDF sums all approved amounts regardless of currency differences.
- **No authentication:** Any user with the URL can access the app. Add Streamlit auth or OAuth for production.
- **Gemini rate limits:** The free Gemini tier has request limits. For high-volume use, upgrade your API plan.

---

## Responsible Use & Privacy Notes

- **Do not upload real personal data** (PAN numbers, Aadhaar, bank details) to a public deployment.
- All AI-extracted data must be **reviewed and approved by a human** before inclusion in official reports.
- This tool does **not automatically detect fraud**. Possible duplicates are flagged for human review only.
- Generated reports carry a **draft disclaimer** and have not been independently audited.
- Comply with your organisation's data protection and financial reporting policies.

---

## License

MIT — Free to use and modify for non-commercial and educational purposes.

---

*Built for a student hackathon demonstration. Not production-ready without additional security, persistence, and audit controls.*
>>>>>>> 0042ea0 (Initial commit: JanSeva Impact Desk NGO Report & Receipt Engine)
