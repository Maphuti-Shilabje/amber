# mygoogle

Personal local-first search engine, command hub, and memory cache.

## Overview
mygoogle is designed to solve developer fragmentation, bookmark silos, and repetitive search overhead by replacing public search with a private, content-indexed local memory.

- Hybrid Search: Combines SQLite FTS5 (BM25 keyword matching) and FastEmbed (dense ONNX vector embeddings) using Reciprocal Rank Fusion (RRF).
- Zero Admin Overhead: Ingests commands, web clips, and notes with one click or command without manual tagging or folder hierarchies.
- Dual Interfaces: Seamless CLI search (`mysearch`, `mysave`) and Web Omnibox UI (`http://127.0.0.1:7474`).
- Ambient Capture: Manifest V3 browser extension with instant keyboard shortcut (`Alt+S`) and context menu capture.

## Directory Structure
- backend/: FastAPI daemon, SQLite database, FTS5 triggers, vector indexing, and web scraper.
- cli/: Terminal search and capture scripts (`mysearch`, `mysave`).
- web/: Minimalist omnibox frontend served directly by the backend daemon.
- extension/: Manifest V3 browser extension for Chrome, Brave, Edge, and Firefox.
- tests/: Integration test suite.

## Setup and Installation

### 1. Environment and Dependencies
```bash
uv venv
uv pip install -e .
```

### 2. Run the Backend Daemon
```bash
.venv/bin/uvicorn backend.app:app --host 127.0.0.1 --port 7474
```

To run continuously via systemd:
```bash
mkdir -p ~/.config/systemd/user
cp mygoogle.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now mygoogle
```

### 3. CLI Usage

Add `cli/` to your PATH or create aliases in `~/.bashrc` / `~/.zshrc`:
```bash
alias ?="/path/to/mygoogle/cli/mysearch"
alias save="/path/to/mygoogle/cli/mysave"
```

Examples:
```bash
# Ingest commands or links
save -c "python3 -m venv .venv && source .venv/bin/activate" -t "Create Python venv" -g "python,venv"
save -u "https://onyxcoffeelab.com" -t "Onyx Coffee Lab" -n "Specialty Ethiopian beans"

# Search in terminal
? "venv"
? "blueberry coffee"

# Copy top result directly to clipboard
? -c "venv"

# Open top URL directly in browser
? -o "coffee"
```

### 4. Web Omnibox Setup
Open `http://127.0.0.1:7474` in your browser.

- Press `/` to focus the search bar.
- Use `ArrowUp` / `ArrowDown` to navigate cards.
- Press `Enter` to copy a command or open a link.
- Click `+ Ingest` to save anything directly from the browser.

To use mygoogle from your browser address bar:
1. Go to Browser Settings -> Search Engines -> Manage Search Engines.
2. Add a new search engine:
   - Name: mygoogle
   - Shortcut: `m` or `@me`
   - URL: `http://127.0.0.1:7474/?q=%s`

### 5. Browser Extension Setup
1. Open your browser extension manager (`chrome://extensions` or `edge://extensions`).
2. Enable "Developer mode".
3. Click "Load unpacked" and select the `extension/` folder in this repository.
4. Use `Alt+S` on any webpage to instantly save the page or highlighted quote.
