# 🤖 BAKAI INDIA MCP SERVER
### The Ultimate AI Services Ecosystem for Robot BAKAI (Xiaozhi AI Ecosystem)

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![MCP Protocol 2.0](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-orange.svg)](https://modelcontextprotocol.io/)
[![Xiaozhi AI Compatible](https://img.shields.io/badge/Xiaozhi-AI%20Ecosystem-green.svg)](https://xiaozhi.me/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)]()

---

## 1. Project Overview

**BAKAI INDIA MCP SERVER** is an advanced, production-grade Model Context Protocol (MCP) server engineered specifically for the AI robot **BAKAI**, running on the **Xiaozhi AI ecosystem** (ESP32-S3 hardware + Xiaozhi Cloud/Server WebSocket backend).

It bridges BAKAI with real, authenticated Indian and international online services, featuring:
- 📻 **Comprehensive Indian Internet Radio Directory**: All India Radio (Akashvani), Vividh Bharati, FM Gold/Rainbow, Assamese & Northeast regional stations, Bengali, Tamil, Telugu, Malayalam, Kannada, Marathi, Punjabi, and verified online FM streams.
- 📰 **Authentic National & Regional News**: Live feeds from *The Hindu*, *The Sentinel Assam*, *NDTV*, *BBC World*, *TechCrunch*, and *ESPNcricinfo* with verified publishers, real dates, and zero-key RSS fallback.
- 🎵 **Music & Audio Controls**: YouTube and Spotify metadata search, deep-links, playback control actions, and hardware player status tracking.
- 🛍️ **Amazon India & Website Launcher**: Clean ASIN parsing, tracker-free links, and safe launch of approved Indian platforms (IRCTC, DigiLocker, India.gov.in, Maps, etc.).
- 🔍 **Advanced Internet Research**: Deep encyclopedic research, fact-checking, and general knowledge with prompt injection defenses.
- ☀️ **Weather & Daily Utilities**: Free Open-Meteo live weather for all Indian cities, IST time clock, AST-based safe math calculator (zero `eval`), and versatile unit converter (including Indian units like Tola, Seer, Maund, Bigha, Lakh, Crore).
- 🎙️ **Natural Voice Interaction**: Voice phrasing is included where supported; live-data tools return structured provider responses.

---

## 2. Architecture & Ecosystem Diagram

```mermaid
flowchart TD
    subgraph Robot["🤖 Hardware Client (BAKAI)"]
        ESP["ESP32-S3 Core"]
        I2S["MAX98357A I2S DAC + Speaker"]
        MIC["INMP441 Microphone"]
        ESP --> I2S
        MIC --> ESP
    end

    subgraph XiaozhiCloud["☁️ Xiaozhi AI Ecosystem"]
        XZ_WS["Xiaozhi WebSocket Server\n(wss://api.xiaozhi.me/v1/mcp)"]
        LLM["Xiaozhi Agentic LLM Loop"]
        XZ_WS <--> LLM
    end

    subgraph Bridge["🌉 MCP Bridge Layer"]
        M2X["mcp2xiaozhi Bridge / bridge_runner.py\n(WebSocket Client + JSON-RPC Dispatcher)"]
    end

    subgraph MCPServer["🚀 BAKAI India MCP Server (server.py)"]
        direction TB
        STDIO["STDIO / SSE Transport Engine"]
        SEC["Security Layer (SSRF & Safe AST)"]
        CACHE["TTL In-Memory Cache"]
        
        RADIO["Radio Directory\n(Akashvani & Regional)"]
        NEWS["News Engine\n(The Hindu & Sentinel Assam)"]
        MUSIC["Music & YouTube\n(Spotify & Audio Player)"]
        SHOP["Amazon India & Launcher\n(IRCTC, DigiLocker)"]
        RESEARCH["Internet Research\n(Wikipedia & DDG)"]
        UTIL["Weather & Daily Utils\n(Open-Meteo & IST Clock)"]
    end

    ESP <==>|Audio OPUS & JSON Control| XZ_WS
    XZ_WS <==>|tools/list & tools/call| M2X
    M2X <==>|Standard JSON-RPC (STDIO)| STDIO
    STDIO --> SEC --> CACHE
    CACHE --> RADIO & NEWS & MUSIC & SHOP & RESEARCH & UTIL
```

---

## 3. Project File Structure

```text
bakai-india-mcp/
├── server.py                  # Main MCP Server entry point (FastMCP / MCPServer)
├── mcp_config.json            # Configuration for MCP desktop clients & bridges
├── requirements.txt           # Version-pinned Python dependencies
├── .env.example               # Template of all environment variables
├── .env                       # Local active environment configuration
├── .gitignore                 # Git ignore patterns
├── README.md                  # Comprehensive architectural and deployment documentation
│
├── core/                      # Core infrastructure
│   ├── __init__.py
│   ├── config.py              # Settings and environment loader
│   ├── security.py            # SSRF protection, URL validation, AST math evaluator
│   ├── cache.py               # Async TTL in-memory cache
│   └── logging.py             # Redacting stderr logger (preserves stdout for JSON-RPC)
│
├── radio/                     # Indian Radio System
│   ├── __init__.py
│   ├── india_stations.json    # Curated database of verified Akashvani & FM streams
│   └── radio_tools.py         # Playback, search, health checking, and robot actions
│
├── news/                      # Indian & Global News
│   ├── __init__.py
│   └── news_tools.py          # RSS feed fetchers (The Hindu, Sentinel Assam, BBC, TechCrunch)
│
├── music/                     # Music & Audio Services
│   ├── __init__.py
│   ├── youtube_tools.py       # Official YouTube Data API v3 & public search
│   └── spotify_tools.py       # Spotify API OAuth & Xiaozhi player controls
│
├── shopping/                  # Amazon India & Launcher
│   ├── __init__.py
│   └── amazon_tools.py        # Amazon India search, ASIN extractor, safe website allowlist
│
├── internet/                  # Internet Research & Knowledge
│   ├── __init__.py
│   ├── search_tools.py        # Deep research, fact check, general knowledge, Wikipedia REST
│   └── website_tools.py       # Safe URL inspect and status checker
│
├── utilities/                 # Daily Utilities & Weather
│   ├── __init__.py
│   ├── weather_tools.py       # Open-Meteo live weather & multi-day forecast
│   ├── daily_tools.py         # IST clock, AST math calculator, Indian unit converter
│   ├── live_api.py            # Shared timeout-bounded HTTP and provider error handling
│   ├── live_data_tools.py     # Public feeds, AQI, forecasts, holidays, metals, ISS
│   ├── mobility_tools.py      # Flight, rail, bus, maps, transit, and traffic tools
│   └── cricket_tools.py       # API-Sports Cricket scores and fixtures
│
├── bridge/                    # Xiaozhi Integration & Management
│   ├── mcp2xiaozhi_config.json # Configuration for mcp2xiaozhi Node/Python bridge
│   ├── bridge_runner.py       # Standalone pure Python WebSocket client for Xiaozhi endpoint
│   ├── dashboard_api.py       # Optional status dashboard web server (port 8088)
│   └── firmware_guide.md      # ESP32 MAX98357A I2S wiring and Xiaozhi firmware code
│
└── tests/                     # Unit and integration test suite
    ├── __init__.py
    ├── conftest.py            # Pytest fixtures and sys.path setup
    ├── test_radio.py          # Radio search, streaming, and state lifecycle tests
    ├── test_news.py           # Real date and publisher verification tests
    ├── test_tools.py          # Security, SSRF, math, utilities, and music tests
    ├── test_server.py         # Tool registration and Xiaozhi bridge execution tests
    └── test_live_tools.py     # New live-data and travel tool tests
```

---

## 4. Complete List of 51 MCP Tools

| Module | Tool Name | Description | Example Spoken Request |
| :--- | :--- | :--- | :--- |
| **Radio** | `india_radio_list` | Lists stations filtered by language, region, or category | *"असम के कौन से रेडियो उपलब्ध हैं?"* |
| | `radio_search` | Searches stations by name, city, or keyword | *"विविध भारती रेडियो खोजो"* |
| | `radio_play` | Verifies stream and triggers playback on BAKAI | *"विविध भारती चलाओ"* |
| | `radio_stop` | Stops active radio playback | *"रेडियो बंद करो"* |
| | `radio_now_playing` | Reports station name and elapsed listening time | *"कौन सा रेडियो स्टेशन चल रहा है?"* |
| **News** | `india_news` | National headlines from The Hindu, NDTV, TOI | *"आज की मुख्य भारतीय खबरें सुनाओ"* |
| | `assam_news` | Regional news from The Sentinel Assam & Tribune | *"असम और पूर्वोत्तर की ताज़ा खबरें क्या हैं?"* |
| | `world_news` | Global news headlines from BBC World | *"दुनिया की खबरें बताओ"* |
| | `technology_news` | AI and gadget updates from TechCrunch | *"आज की टेक्नोलॉजी न्यूज़ क्या है?"* |
| | `sports_news` | Live cricket and sports updates | *"खेल समाचार सुनाओ"* |
| | `news_search` | Targeted search on any topic | *"ISRO गगनयान पर ताज़ा ख़बर क्या है?"* |
| **Music** | `youtube_search` | Searches YouTube videos, songs, and channels | *"YouTube पर अरिजीत सिंह के गाने खोजो"* |
| | `youtube_open` | Opens YouTube video or search link on display | *"YouTube खोलो"* |
| | `spotify_search` | Searches Spotify catalog for tracks & albums | *"Spotify पर दिल हूम हूम करे खोजो"* |
| | `spotify_open` | Launches Spotify app / web player for a song | *"Spotify खोलो"* |
| | `music_control` | Hardware playback commands (play, pause, next, vol) | *"गाना रोको" / "आवाज़ बढ़ाओ"* |
| | `music_now_playing` | Reports current song and volume level | *"कौन सा गाना बज रहा है?"* |
| **Shopping** | `amazon_search` | Searches Amazon India with clean search links | *"Amazon पर ESP32 विकास बोर्ड खोजो"* |
| | `amazon_product_info`| Validates Amazon link & extracts ASIN | *"इस Amazon लिंक की जानकारी दो"* |
| | `open_website` | Safe launcher for IRCTC, DigiLocker, Maps, etc. | *"IRCTC की वेबसाइट खोलो"* |
| | `website_search` | Finds official websites for Indian organizations | *"प्रसार भारती की आधिकारिक वेबसाइट बताओ"* |
| **Research** | `web_search` | Up-to-date web facts with injection defenses | *"काजीरंगा राष्ट्रीय उद्यान के बारे में बताओ"* |
| | `deep_research` | Multi-source background, history, and citations | *"लाचित बोरफुकन और अहोम साम्राज्य पर शोध करो"* |
| | `fact_check` | Validates statements against credible sources | *"क्या गुवाहाटी असम की राजधानी है?"* |
| | `general_knowledge`| Direct factual question answering | *"भारत के प्रथम राष्ट्रपति कौन थे?"* |
| **Utilities**| `get_weather` | Live temperature, humidity, and condition | *"आज गुवाहाटी का मौसम बताओ"* |
| | `weather_forecast` | 3-day temperature range and rain probability | *"कल गुवाहाटी में बारिश होगी क्या?"* |
| | `get_india_time` | Exact IST time (UTC+05:30), date, and weekday | *"भारत में अभी क्या समय हुआ है?"* |
| | `calculator` | AST-based safe math evaluator (zero `eval`) | *"25 गुना 40 जमा 150 कितना होगा?"* |
| | `unit_converter` | SI, imperial, and Indian units (Tola, Bigha, etc.) | *"5 तोला में कितने ग्राम होते हैं?"* |
| **Phone** | `phone_find_contact` | Searches contacts on the connected Android phone | *"माँ का नंबर खोजो"* |

### New live-data and travel tools

| Tool | Data source / behavior | Credentials or access |
| :--- | :--- | :--- |
| `check_aqi` | Current modeled AQI and PM readings via [Open-Meteo Air Quality](https://open-meteo.com/en/docs/air-quality-api) | No key |
| `cricket_live_score`, `cricket_schedule` | Live games and date fixtures via [API-Sports Cricket](https://api-sports.io/documentation/cricket/v1) | `CRICKET_API_KEY` |
| `flight_search` | Real flight offers via [Amadeus Self-Service](https://developers.amadeus.com/) production API | `AMADEUS_CLIENT_ID`, `AMADEUS_CLIENT_SECRET`, production access |
| `flight_status` | Flight status via [Aviationstack](https://aviationstack.com/documentation) | `AVIATIONSTACK_API_KEY` |
| `train_search` | Link to official IRCTC search page; no inventory is scraped or represented as live | No key; provider page completes the search |
| `train_pnr_status` | Official Indian Railways enquiry link; live lookup is not available without an authorized railway partner | Additional provider access required |
| `bus_search` | Link to redBus; no inventory is scraped or represented as live | No key; provider page completes the search |
| `bus_live_tracking` | Requires the bus operator or authorized ticketing-partner tracking API | Additional provider access required |
| `metro_routes`, `traffic_status`, `map_directions` | Structured transit, route, and traffic-aware duration via [Google Maps Routes API](https://developers.google.com/maps/documentation/routes/compute_route_directions) | `GOOGLE_MAPS_API_KEY` and enabled billing/API access; map links remain available without the key |
| `fuel_price` | No stable documented public India-wide API is configured | Licensed fuel-data provider required |
| `gold_price` | INR spot quote via [Metals-API](https://metals-api.com/documentation); taxes/local premiums excluded | `METALS_API_KEY` |
| `earthquake_alerts` | Recent events via the [USGS FDSN GeoJSON API](https://earthquake.usgs.gov/fdsnws/event/1/) | No key |
| `rain_alert` | Hourly precipitation forecast via [Open-Meteo](https://open-meteo.com/en/docs) | No key |
| `uv_index` | Current modeled UV via [Open-Meteo Air Quality](https://open-meteo.com/en/docs/air-quality-api) | No key |
| `exchange_rates` | Daily reference rates via [Frankfurter](https://frankfurter.dev/) | No key; rates are not intraday trading quotes |
| `holiday_calendar` | Public holiday dates via [Calendarific](https://calendarific.com/api-documentation) | `CALENDARIFIC_API_KEY` |
| `iss_tracker` | ISS position via [N2YO](https://www.n2yo.com/api/) | `N2YO_API_KEY` |

No tool claims that a reservation, ticket purchase, payment, or booking was completed. PNR status, bus tracking, and fuel pricing return explicit provider-access errors until an authorized integration is supplied.

---

## 5. Installation on Windows 11

### Step 1: Open PowerShell
Open Windows PowerShell (Run as Administrator if installing system-wide).

### Step 2: Clone or Open Project Directory
```powershell
cd C:\Users\Krishnav\.gemini\antigravity\scratch\bakai-india-mcp
```

### Step 3: Create & Activate Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 4: Install Dependencies
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 5: Configure Environment Variables
Copy the template and edit your parameters:
```powershell
copy .env.example .env
notepad .env
```

---

## 6. Running and Verifying the Server Locally

### 1. Test Registered MCP Tools
Verify that all 51 tools are properly discovered:
```powershell
python server.py --list-tools
```

### 2. Run the Full Automated Test Suite
Run the unit and integration tests:
```powershell
python -m pytest tests -v
```

### 3. Run in STDIO Transport Mode (Default for Bridges)
```powershell
python server.py --transport stdio
```

### 4. Run in SSE HTTP Transport Mode (For Web / Remote Clients)
```powershell
python server.py --transport sse --port 8080 --host 0.0.0.0
```

---

## 7. Xiaozhi AI Ecosystem Integration

Xiaozhi connects to MCP servers over WebSockets (`wss://api.xiaozhi.me/v1/mcp` or self-hosted servers). Because standard MCP operates over STDIO or SSE, a bridge is used to relay JSON-RPC tool calls.

### Option A: Using the Standalone Python Bridge (`bridge_runner.py`)
No Node.js or external package is required. The built-in Python bridge connects directly to your Xiaozhi WebSocket endpoint:

```powershell
python bridge\bridge_runner.py "wss://api.xiaozhi.me/v1/mcp"
```

### Codespaces quick start

From the Codespaces terminal, run:

```bash
cd /workspaces/bakai-india-mcp/bakai-india-mcp
python -m pip install -r requirements.txt
cp -n .env.example .env
```

Set `XIAOZHI_TOKEN` and, if needed, `XIAOZHI_DEVICE_ID` in `.env`, then start the bridge with:

```bash
python bridge/bridge_runner.py
```

The bridge uses `XIAOZHI_WS_ENDPOINT` from `.env` (default: `wss://api.xiaozhi.me/v1/mcp`).

The bridge:
1. Performs the initial handshake with your `XIAOZHI_DEVICE_ID` and `XIAOZHI_TOKEN`.
2. Registers all 51 BAKAI tools with Xiaozhi cloud via `tools/list`.
3. Handles `tools/call` events in real-time, executing the Python function and returning the conversational speech + robot action.
4. Auto-reconnects with exponential backoff on network interruptions.

### Option B: Using `mcp2xiaozhi` (Node / Official CLI)
If your deployment uses the official `mcp2xiaozhi` bridge:
```bash
npx mcp2xiaozhi -c bridge/mcp2xiaozhi_config.json
```

---

## 8. Hardware Speaker & Firmware Integration

When a radio station or audio track is played, the MCP server returns an action payload:
```json
{
  "action": "play_audio",
  "url": "https://air.pc.cdn.bitgravity.com/air/live/pbaudio001/playlist.m3u8",
  "format": "hls",
  "title": "All India Radio Vividh Bharati"
}
```

### ESP32-S3 Wiring for MAX98357A I2S Amplifier:
- **BCLK** $\to$ GPIO 15
- **LRC** $\to$ GPIO 16
- **DIN** $\to$ GPIO 7
- **VIN** $\to$ 5V
- **GND** $\to$ GND

Detailed C/C++ ESP-IDF pipeline code and buffer recommendations are provided in [bridge/firmware_guide.md](file:///C:/Users/Krishnav/.gemini/antigravity/scratch/bakai-india-mcp/bridge/firmware_guide.md).

---

## 9. Optional Web Dashboard API

To monitor server status, test radio streams, and view active tools without affecting your Netlify frontend:

```powershell
python bridge\dashboard_api.py
```
Open **`http://localhost:8088`** in your browser:
- Real-time station list with one-click direct stream preview.
- Active tool capability pills.
- Dynamic `/api/verify-stream` endpoint to ping audio streams.

---

## 10. Always-On Production Deployment

### Windows 11 Always-On Service (via NSSM)
1. Download [NSSM (Non-Sucking Service Manager)](https://nssm.cc/).
2. Run in administrator PowerShell:
```powershell
nssm install BakaiIndiaMcp "C:\Users\Krishnav\.gemini\antigravity\scratch\bakai-india-mcp\venv\Scripts\python.exe" "C:\Users\Krishnav\.gemini\antigravity\scratch\bakai-india-mcp\bridge\bridge_runner.py"
nssm set BakaiIndiaMcp AppDirectory "C:\Users\Krishnav\.gemini\antigravity\scratch\bakai-india-mcp"
nssm start BakaiIndiaMcp
```

### Linux / Cloud VPS (systemd unit)
Create `/etc/systemd/system/bakai-mcp.service`:
```ini
[Unit]
Description=BAKAI India MCP Bridge Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/bakai-india-mcp
EnvironmentFile=/opt/bakai-india-mcp/.env
ExecStart=/opt/bakai-india-mcp/venv/bin/python bridge/bridge_runner.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable bakai-mcp
sudo systemctl start bakai-mcp
```

---

## 11. Security & Reliability Highlights

1. **Strict SSRF Defense**: All external URLs are checked against private IP networks (`127.0.0.1`, `10.0.0.0/8`, `192.168.0.0/16`, `172.16.0.0/12`, loopback, and link-local ranges) before fetching.
2. **Zero `eval()` AST Calculator**: Math expressions are parsed into Python's Abstract Syntax Tree; attribute access, dunders, and arbitrary function executions are impossible.
3. **Prompt Injection Filtering**: Untrusted internet search responses are scrubbed of LLM control tokens (`<|im_start|>`, `[SYSTEM_INSTRUCTION]`, etc.).
4. **Credential Redaction**: Sensitive API keys and authorization tokens are automatically masked in all log outputs.
5. **Stdio Protocol Integrity**: All server log messages are routed strictly to `sys.stderr`, keeping `sys.stdout` pure for JSON-RPC MCP messages.
