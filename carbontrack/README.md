# Carbon Footprint Awareness Platform

A smart, dynamic assistant platform designed to help individuals understand, track, and reduce their carbon footprint through contextual insights.

## Live Demo

🚀 **[View the Deployed Application Here](https://carbon-footprint-app-304612435021.us-central1.run.app/)**

## Overview

This project was built for **[Challenge 3]**, focusing on providing a highly optimized, beautifully designed, and containerized solution. It uses a blazing-fast Python (FastAPI) backend, `uv` for dependency management, and integrates the **Google Gemini LLM** to act as a dynamic sustainability assistant.

### User Persona
- **Target Audience:** Individuals seeking to track their daily/monthly emissions (transport, energy, and diet).
- **Goal:** Provide highly practical, real-world reduction actions tailored to their specific lifestyle data.

### Calculation Logic & Assumptions
The core calculation engine (`app/calculator.py`) translates user inputs into pounds of CO₂ equivalent:
1. **Transport:** Assumes an average of 19.6 lbs CO₂ per gallon of gasoline. It calculates weekly fuel usage `(miles / mpg)` and extrapolates to a monthly figure.
2. **Energy:** Assumes an average grid emission factor of 0.85 lbs CO₂ per kWh of electricity consumed.
3. **Diet:** Uses standard monthly flat-rate estimates based on dietary profiles:
   - Vegan: 200 lbs CO₂
   - Vegetarian: 250 lbs CO₂
   - Omnivore: 450 lbs CO₂
   - Heavy Meat: 600 lbs CO₂

### Technology Stack
- **Backend:** Python 3.11, FastAPI
- **Package Manager:** `uv` (Rust-based, incredibly fast resolution)
- **AI Integration:** `google-generativeai` (Gemini 2.5 Flash used for dynamic insights and conversational chatbot)
- **Frontend:** HTML5, Vanilla CSS (Glassmorphism design), Vanilla JS
- **Testing:** `pytest`
- **Infrastructure:** Docker (Multi-stage builds)

## Getting Started

### Prerequisites
- Docker installed on your machine.
- A Google Gemini API Key.

### 1. Setup Environment Variables
Create a `.env` file in the root of the project:
```bash
cp .env.example .env
```
Open `.env` and add your Gemini API Key:
```env
GEMINI_API_KEY=your_actual_api_key_here
```

### 2. Build and Run via Docker

We use an optimized multi-stage Dockerfile to keep the footprint extremely small (well under the 10MB challenge limit for source code).

Build the image:
```bash
docker build -t carbon-footprint-app .
```

Run the container:
```bash
docker run -p 8000:8000 --env-file .env carbon-footprint-app
```

### 3. Access the Application
Open your browser and navigate to:
`http://localhost:8000`

## Development & Testing
If you wish to run the project locally without Docker:

1. Install `uv`: `pip install uv`
2. Sync dependencies: `uv venv && uv pip install -e .[dev]`
3. Run tests: `uv run pytest`
4. Run server: `uv run uvicorn app.main:app --reload`
