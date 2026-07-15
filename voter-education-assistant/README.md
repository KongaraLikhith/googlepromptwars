# 🗳️ India Voter Education Assistant

## Overview
The India Voter Education Assistant is an interactive web application designed to empower Indian citizens by simplifying the election process. Powered by AI and Google Services, it provides a comprehensive guide to voter registration, helps find nearby polling stations, highlights important election dates, and answers complex election queries in simple terms.

## Chosen Vertical
Election Process Education

## Architecture
```
User (Browser)
   │
   ├── [HTTP/JS] ──> Frontend (HTML, Tailwind CSS, Vanilla JS)
   │                       │
   │                       v
   └── [REST API] ──> FastAPI Backend (Python)
                           │
                           ├──> Gemini AI (gemini-2.5-flash)
                           ├──> Google Maps API (Places & Geocoding)
                           ├──> Google Civic Information API
                           └──> Google Calendar Links
```

## Google Services Used
- **Gemini AI (gemini-2.5-flash):** Powers the conversational chat assistant.
- **Google Maps JavaScript API:** Interactive map showing nearby polling stations.
- **Google Places API:** Finds polling booths near the user's location.
- **Google Civic Information API:** Fetches election data, voter info, and representatives.
- **Google Calendar:** One-click event reminders via URL links.

## Features
- **💬 Chat Assistant:** AI-powered chatbot to answer questions about elections, EVMs, NOTA, Model Code of Conduct, etc.
- **🗺️ Find Polling Station:** Locates nearby polling booths using the user's GPS or manual address entry.
- **📅 Election Calendar:** Keeps track of important election milestones and easily adds them to Google Calendar.
- **📚 Voter Guide:** A comprehensive accordion-style FAQ covering voter registration, required documents, and election types.

## Local Development Setup

1. **Clone the repository:**
   ```bash
   git clone <repository_url>
   cd voter-education-assistant
   ```

2. **Set up a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   Copy `.env.example` to `.env` and fill in your API keys:
   ```bash
   cp .env.example .env
   ```

5. **Run the server:**
   ```bash
   uvicorn main:app --reload --port 8080
   ```
   Open `http://localhost:8080` in your browser.

6. **Run tests:**
   ```bash
   pytest
   ```

## Cloud Run Deployment

```bash
# Authenticate
gcloud auth login
gcloud config set project voter-edu-assistant

# Deploy
gcloud run deploy voter-education-assistant \
  --source . \
  --region asia-south1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=your_key,GOOGLE_MAPS_API_KEY=your_key,GOOGLE_CIVIC_API_KEY=your_key
```

## API Endpoints

### Chat
- **POST `/api/chat`**
  - **Request:** `{"message": "What is NOTA?", "history": []}`
  - **Response:** `{"response": "NOTA stands for None Of The Above...", "success": true}`

### Maps
- **POST `/api/polling-locations`**
  - **Request:** `{"lat": 28.6139, "lng": 77.2090}`
  - **Response:** `{"locations": [{"name": "Booth 1", ...}], "success": true}`
- **GET `/api/geocode?address=Delhi`**
  - **Response:** `{"result": {"lat": 28.6139, "lng": 77.2090, "formatted_address": "Delhi, India"}, "success": true}`

### Civic Data
- **GET `/api/elections?address=Delhi`**
  - **Response:** `{"elections": [...], "success": true, "fallback": false}`
- **GET `/api/voter-info?address=Delhi`**
  - **Response:** `{"polling_locations": [...], "success": true, "fallback": false}`
- **GET `/api/representatives?address=Delhi`**
  - **Response:** `{"offices": [...], "success": true, "fallback": false}`

### Calendar
- **GET `/api/election-events`**
  - **Response:** `{"events": [{"title": "Check Voter Registration", ...}], "success": true}`

## Assumptions Made
- The Google Civic API provides coverage or fallback for the regions queried. In India, coverage may be limited, so fallback mechanisms are built in.
- Google Maps API key provided has both Geocoding and Places API enabled.
- For finding polling booths, a radius of 10km around the user location is appropriate.
- User interface should be accessible and visually clear via a single-page app structure without heavy framework overhead.

## Future Improvements
- Multi-language UI support (Hindi, regional languages) directly accessible via UI toggles.
- Implementing Firebase Authentication to save user preferences and past chats.
- Direct integration with ECI's SMS APIs for tracking Voter ID status.
- State-specific election guidelines tailored to the user's specific region.