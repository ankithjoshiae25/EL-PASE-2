# Last Mile Mobility Platform MVP

## Overview
This is the MVP for the Last Mile Mobility Platform, built with **FastAPI** (Backend) and **Vanilla HTML/JS** (Frontend). It features a glassmorphism UI, interactive map, and AI-powered route recommendations.

## Prerequisites
- Python 3.8+
- `pip`

## Installation
1.  Navigate to the project directory:
    ```bash
    cd c:\Users\deepa\OneDrive\Desktop\ELPHASE2
    ```
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: If `requirements.txt` is missing, run: `pip install fastapi uvicorn jinja2 requests`)*

## Running the App
1.  Start the server:
    ```bash
    python -m uvicorn app.main:app --reload
    ```
2.  Open your browser and go to:
    [http://localhost:8000](http://localhost:8000)

## Features
- **Interactive Map**: Powered by Leaflet.js and OpenStreetMap.
- **Smart Search**: Enter a destination (e.g., "Koramangala", "Indiranagar") to see routes.
- **Multi-Modal Routing**: Compare Cab, Metro, Bus, and Walk options.
- **AI Scoring**: Routes are ranked by an AI score based on time, cost, and safety.
