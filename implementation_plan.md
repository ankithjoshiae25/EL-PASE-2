# Last Mile Mobility Platform - MVP Implementation Plan

## 1. Overview
We will build a **Web-based MVP** for the Last Mile Mobility Platform. 
Due to the absence of Node.js in the current environment, we will use **Python (FastAPI)** for the backend and **Vanilla HTML/CSS/JavaScript** for the frontend. This ensures a robust application that runs smoothly on your machine.

## 2. Tech Stack
- **Backend**: FastAPI (Python)
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Database**: SQLite (for MVP simplicity, replacing PostgreSQL)
- **Maps**: Leaflet.js (using OpenStreetMap tiles)
- **Routing Engine**: Mocked/Calculated locally for MVP (simulating OSRM/Google Maps)

## 3. Architecture
- `app/`: Contains the FastAPI application
    - `main.py`: Entry point
    - `api/`: API endpoints (routing, cabs, public transport)
    - `models/`: Database models
    - `services/`: Business logic (mocking APIs, algorithms)
- `static/`: Static assets
    - `css/`: Stylesheets (Modern, Glassmorphism)
    - `js/`: Frontend logic (Map interaction, API calls)
- `templates/`: HTML templates (Jinja2)

## 4. Key Features to Implement
1.  **Home Screen**: Map view with "Where to?" input.
2.  **Route Options**: Display multi-modal options (Cab, Metro, Bus, Walk).
3.  **Mock Data Engine**:
    - Simulate Cab availability and pricing (Uber, Ola, Rapido).
    - Simulate Metro/Bus schedules (Bangalore context).
4.  **Recommendation Logic**: Simple weighting algorithm (Time vs Cost).

## 5. Step-by-Step Plan
1.  **Setup**: Initialize Python environment and install dependencies (`fastapi`, `uvicorn`, `jinja2`).
2.  **Backend Core**: Set up FastAPI with template serving.
3.  **Frontend Foundation**: Create the main map interface using Leaflet.js.
4.  **API Implementation**:
    - `/api/search`: Returns routes based on start/end points.
    - `/api/cabs`: Returns mock cab data.
    - `/api/transit`: Returns mock metro/bus data.
5.  **Integration**: Connect frontend to backend APIs.
6.  **Styling**: Apply premium aesthetics (Glassmorphism, animations).

## 6. Execution
We will start by setting up the environment and the basic server.
