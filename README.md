<p align="center">
  <img src="web/static/icons/icon-128.png" width="80" height="80" alt="Amber Logo" />
  <br />
  <h1 align="center">Amber</h1>
  <p align="center"><strong>Personal local-first memory vault, command preservation, and knowledge retrieval hub.</strong></p>
</p>

---

## Overview
Amber captures and preserves commands, code snippets, web highlights, and technical processes exactly as they were, without degradation or taxonomic overhead. It replaces public search engine noise with an instant-retrieval, content-indexed local engine.

Like resin that preserves biological organisms intact across millennia, Amber freezes your essential workflows—the 5% of a webpage you actually needed, the obscure one-line bash flag, or the synthesized AI recipe—directly into your private SQLite vault.

---

## Key Features

* **Hybrid Search Engine:** Fuses lexical full-text search (SQLite FTS5 BM25) and dense ONNX semantic vector embeddings (`BAAI/bge-small-en-v1.5` via FastEmbed) using Reciprocal Rank Fusion (RRF).
* **Zero-Admin Ingestion:** Append-only capture model. No required folder hierarchies, manual categorization, or tagging overhead.
* **Dual Presentation Adapters:**
  * **Unified CLI (`amber`):** Fast terminal lookups, instant clipboard piping (`amber -c`), and interactive `fzf` split-pane live search (`amber -i`).
  * **Web Omnibox (`http://127.0.0.1:7474`):** Spotlight-style keyboard navigation (`/`, `ArrowUp`/`ArrowDown`, `Enter`), action cards, and public search fallbacks.
* **Ambient Web Capture:** Manifest V3 browser extension with universal hotkey (`Alt+S`), text selection extraction, and in-page toast feedback.
* **Automatic Content Cleaning:** Background extraction via `trafilatura` strips cookie banners, navigation clutter, and ads from saved URLs to index pure content.
* **Configurable & Tuneable:** Full control over vector similarity floors, BM25 field weights, usage frequency boosts, and RRF smoothing constants.

---

## Directory Structure

```text
amber/
├── backend/          FastAPI daemon, SQLite FTS5 database, vector search, and scraper
├── cli/              Unified terminal binary (amber) and interactive fzf helper
├── web/              Static Omnibox web application (HTML, CSS, JS, icons)
├── extension/        Manifest V3 browser extension for Chrome, Brave, Edge, Firefox
├── tests/            Pytest backend integration test suite
├── .env.example      Configuration template with all available parameter dials
├── CONFIGURATION.md  Complete hyperparameter guide, BM25 weights, and tuning recipes
├── amber.service     systemd user service unit definition
└── pyproject.toml    Project dependencies and build definition
```

---

## Setup and Installation

### 1. Environment and Dependencies
```bash
# Clone and enter the repository
cd /path/to/amber

# Create virtual environment and install packages
uv venv
uv pip install -e .
```

### 2. Run the Backend Daemon
```bash
.venv/bin/uvicorn backend.app:app --host 127.0.0.1 --port 7474
```

To run continuously in the background via systemd:
```bash
mkdir -p ~/.config/systemd/user
cp amber.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now amber
```

---

## CLI Usage (`amber`)

Add the `cli/` directory to your `PATH` or create an alias in `~/.bashrc` or `~/.zshrc`:
```bash
alias amber="/path/to/amber/cli/amber"
alias ?="amber"
```

### Ingestion Examples
```bash
# Preserve a shell command with tags
amber save -c "docker system prune -a --volumes -f" -t "Docker complete cleanup" -g "docker,devops"

# Preserve a bookmark URL (with automatic background content scraping)
amber save -u "https://onyxcoffeelab.com" -t "Onyx Coffee Lab" -n "Specialty Ethiopian blueberry beans"

# Preserve a quote or text snippet
amber save -q "Simplicity is prerequisite for reliability." -t "Dijkstra Quote" -g "quotes"

# Preserve from stdin pipe
echo "ssh -i ~/.ssh/prod.pem ubuntu@192.168.1.50" | amber save -c -t "SSH Production"
```

### Search & Retrieval Examples
```bash
# Fast hybrid search
amber "docker cleanup"
amber "blueberry coffee"

# Search and copy top matching payload directly to clipboard
amber -c "docker"

# Search and open top matching URL directly in browser
amber -o "coffee"

# Interactive split-pane TUI (powered by live backend hybrid search)
amber -i
```

---

## Web Omnibox Setup

Open **`http://127.0.0.1:7474`** in your browser.

* **Keyboard Navigation:**
  * Press **`/`** to focus search.
  * Use **`ArrowUp`** / **`ArrowDown`** to cycle through cards.
  * Press **`Enter`** to copy the selected payload or open the link.
  * Press **`Esc`** to clear search or close modals.
* **Filter Chips:** Switch between All, Commands, Bookmarks, Highlights, AI Chats, and Notes.
* **Browser Address Bar Search:**
  1. Open Browser Settings -> Search Engines -> Manage Search Engines.
  2. Add a new search engine:
     * **Name:** `Amber`
     * **Shortcut:** `a` or `@amber`
     * **URL:** `http://127.0.0.1:7474/?q=%s`

---

## Browser Extension Setup

1. Open your browser extension manager (`chrome://extensions`, `edge://extensions`, or `brave://extensions`).
2. Enable **Developer mode**.
3. Click **Load unpacked** and select the `extension/` directory in this repository.
4. **Usage:**
   * **Highlight text on any webpage** $\rightarrow$ press **`Alt+S`** to preserve the exact quote.
   * **Click anywhere on the page** $\rightarrow$ press **`Alt+S`** to preserve the page bookmark and trigger background scraping.
   * Click the **Amber gemstone icon** in your toolbar to open the quick capture popup.

---

## Desktop Launcher & Spotlight Integrations

### 1. Zero-Dependency GNOME / Ubuntu Floating Shortcut (`Super+A` or `Alt+Space`)
Launch Amber as a floating Spotlight search bar from anywhere on your desktop:
1. Open **Ubuntu Settings** -> **Keyboard** -> **View and Customize Shortcuts** -> **Custom Shortcuts**.
2. Click **+** (Add Shortcut):
   * **Name:** `Amber Search`
   * **Command:** `/home/maphuti/Documents/projects/amber/cli/amber-popup`
   * **Shortcut:** Press **`Super+A`** (or **`Alt+Space`**).
3. Whenever you hit the shortcut, a floating search bar appears, copies on `Enter`, and dismisses automatically.

### 2. Raycast Extension (macOS)
```bash
cd integrations/raycast
npm install
npm run dev
```

---

## Configuration & Tuning

All scoring hyperparameters, similarity thresholds, BM25 field weights, and database timeouts can be customized via environment variables or a `.env` file.

See **[CONFIGURATION.md](CONFIGURATION.md)** for detailed documentation and tuning recipes (e.g. High-Precision matching, High-Recall conceptual search, and Habit-Driven usage weighting).

---

## Testing

Run the automated test suite:
```bash
.venv/bin/python -m pytest tests/test_backend.py -v
```

---

## Author

Created and maintained by **Maphuti Shilabje** ([Fretak](https://fretak.com)).

---

## License

MIT License. Local-first, private by design, and telemetry-free.
