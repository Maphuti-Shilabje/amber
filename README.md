# Amber

Personal local-first memory vault, command preservation, and knowledge retrieval hub.

## Overview
Amber captures and preserves commands, code snippets, web highlights, and notes exactly as they were, without degradation. It replaces public search noise with a content-indexed, instant-retrieval local engine.

- Hybrid Search: Combines SQLite FTS5 (BM25 keyword matching) and FastEmbed (dense ONNX vector embeddings) using Reciprocal Rank Fusion (RRF).
- Zero Admin Overhead: Ingests commands, web clips, and notes with one click or command without manual tagging or folder hierarchies.
- Dual Interfaces: Seamless unified CLI (`amber`) and Web Omnibox UI (`http://127.0.0.1:7474`).
- Ambient Capture: Manifest V3 browser extension with instant keyboard shortcut (`Alt+S`) and in-page toast feedback.

## Directory Structure
- backend/: FastAPI daemon, SQLite database, FTS5 triggers, vector indexing, and web scraper.
- cli/: Unified terminal client (`cli/amber`).
- web/: Minimalist omnibox frontend served directly by the backend daemon.
- extension/: Manifest V3 browser extension for Chrome, Brave, Edge, and Firefox.
- tests/: Integration test suite.
- CONFIGURATION.md: Complete reference for all search hyperparameters, BM25 weights, and tuning recipes.

## Configuration & Tuning
All hyperparameters (similarity thresholds, BM25 weights, RRF constants, and usage boosts) can be customized via environment variables or a `.env` file. See [CONFIGURATION.md](file:///home/maphuti/Documents/projects/mygoogle/CONFIGURATION.md) for full documentation and tuning recipes.

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
cp amber.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now amber
```

### 3. CLI Usage

Add `cli/` to your PATH or create an alias in `~/.bashrc` / `~/.zshrc`:
```bash
alias amber="/path/to/project/cli/amber"
alias ?="amber"
```

Examples:
```bash
# Ingest commands, URLs, or notes
amber save -c "python3 -m venv .venv && source .venv/bin/activate" -t "Create Python venv" -g "python,venv"
amber save -u "https://onyxcoffeelab.com" -t "Onyx Coffee Lab" -n "Specialty Ethiopian blueberry beans"

# Search in terminal
amber "venv"
amber "blueberry coffee"

# Copy top result directly to clipboard
amber -c "venv"

# Open top URL directly in browser
amber -o "coffee"

# Interactive fzf mode with live split preview
amber -i
```

### 4. Web Omnibox Setup
Open `http://127.0.0.1:7474` in your browser.

- Press `/` to focus the search bar.
- Use `ArrowUp` / `ArrowDown` to navigate cards.
- Press `Enter` to copy a command or open a link.
- Click `+ Ingest` to save anything directly from the browser.

To use Amber from your browser address bar:
1. Go to Browser Settings -> Search Engines -> Manage Search Engines.
2. Add a new search engine:
   - Name: Amber
   - Shortcut: `a` or `@amber`
   - URL: `http://127.0.0.1:7474/?q=%s`

### 5. Browser Extension Setup
1. Open your browser extension manager (`chrome://extensions` or `edge://extensions`).
2. Enable "Developer mode".
3. Click "Load unpacked" and select the `extension/` folder in this repository.
4. Use `Alt+S` on any webpage to instantly save the page or highlighted quote with in-page feedback.
