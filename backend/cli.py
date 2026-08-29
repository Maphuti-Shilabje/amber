#!/usr/bin/env python3
# Amber - Unified CLI

import sys
import os
import argparse
import urllib.request
import urllib.parse
import json
import subprocess
import shutil
import webbrowser
from pathlib import Path

from backend.config import HOST, PORT

def get_base_url() -> str:
    h = os.environ.get("AMBER_HOST", HOST)
    p = os.environ.get("AMBER_PORT", str(PORT))
    return f"http://{h}:{p}"

def copy_to_clipboard(text: str) -> bool:
    if shutil.which("wl-copy"):
        try:
            p = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE)
            p.communicate(text.encode("utf-8"))
            return p.returncode == 0
        except Exception:
            pass
    if shutil.which("xclip"):
        try:
            p = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
            p.communicate(text.encode("utf-8"))
            return p.returncode == 0
        except Exception:
            pass
    if shutil.which("pbcopy"):
        try:
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            p.communicate(text.encode("utf-8"))
            return p.returncode == 0
        except Exception:
            pass
    print("Clipboard utility (wl-copy, xclip, pbcopy) not found.", file=sys.stderr)
    return False

def touch_item(base_url: str, item_id: str):
    try:
        req = urllib.request.Request(f"{base_url}/api/items/{item_id}/touch", method="POST")
        urllib.request.urlopen(req, timeout=1.0)
    except Exception:
        pass

def handle_save(args):
    base_url = get_base_url()
    payload = args.payload or args.cmd or args.url or args.quote or ""
    
    # Read from stdin if no payload given and stdin is piped
    if not payload and not sys.stdin.isatty():
        payload = sys.stdin.read().strip()
    
    item_type = args.type
    if args.cmd:
        item_type = "command"
    elif args.url:
        item_type = "bookmark"
    elif args.quote:
        item_type = "highlight"
    elif not item_type:
        item_type = "note"

    source_url = args.url if item_type == "bookmark" else args.source_url
    title = args.title or (payload.splitlines()[0][:50] if payload else "")
    if not title:
        print("Error: Missing required title or payload.", file=sys.stderr)
        sys.exit(1)
    if not payload:
        payload = title

    body = {
        "type": item_type,
        "title": title,
        "payload": payload,
        "source_url": source_url or None,
        "notes": args.notes or None,
        "tags": args.tags or None,
        "context": args.context or None,
        "auto_scrape": not args.no_scrape
    }

    try:
        req = urllib.request.Request(
            f"{base_url}/api/ingest",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5.0) as res:
            data = json.loads(res.read().decode())
            item_id = data.get("id", "")
            print(f"[OK] Preserved [{item_type}]: '{title}' (id: {item_id})")
    except urllib.error.URLError:
        print(f"Error: Amber daemon is not running on {base_url}", file=sys.stderr)
        print("Start it with: amber-server (or systemctl --user start amber)", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error saving item: {e}", file=sys.stderr)
        sys.exit(1)

def handle_interactive(query: str, item_type: str = ""):
    if not shutil.which("fzf"):
        print("Error: fzf is not installed. Install it with: sudo apt install fzf", file=sys.stderr)
        sys.exit(1)

    base_url = get_base_url()
    
    # Locate fzf backend helper
    cli_dir = Path(__file__).resolve().parent.parent / "cli"
    helper_script = cli_dir / "_fzf_backend.py"
    if not helper_script.exists():
        # Fallback to python module execution
        helper_cmd = f"python3 -m backend.cli _fzf_fetch"
    else:
        helper_cmd = str(helper_script)

    env = os.environ.copy()
    h = os.environ.get("AMBER_HOST", HOST)
    p = os.environ.get("AMBER_PORT", str(PORT))
    env["AMBER_HOST"] = h
    env["AMBER_PORT"] = p
    
    # Ensure package root is always in PYTHONPATH regardless of cwd
    pkg_root = str(Path(__file__).resolve().parent.parent)
    env["PYTHONPATH"] = pkg_root + (":" + env["PYTHONPATH"] if "PYTHONPATH" in env else "")

    # Fetch initial list
    initial_items = fetch_fzf_items(query, item_type)
    if not initial_items and not query:
        print("No items in memory found.", file=sys.stderr)
        sys.exit(0)

    py_exe = sys.executable
    fzf_args = [
        "fzf",
        "--query", query,
        "--disabled",
        "--bind", f'change:reload("{py_exe}" -m backend.cli _fzf_fetch {{q}} "{item_type}")',
        "--delimiter", "\t",
        "--with-nth", "1,2",
        "--preview", f'echo {{}} | cut -f4 | xargs -I@ curl -s "{base_url}/api/items/@" | jq -r \'"Title: " + .title + "\nType: " + .type + "\nContext: " + (.context // "none") + "\nTags: " + (.tags // "none") + "\n\n--- PAYLOAD ---\n" + .payload + "\n\n--- NOTES ---\n" + (.notes // "")\'',
        "--preview-window", "right:55%:wrap",
        "--bind", "ctrl-y:execute(echo {} | cut -f5 | wl-copy || echo {} | cut -f5 | xclip -selection clipboard)+abort",
        "--header", "Enter: Copy Payload | Ctrl-Y: Quick Copy | Esc: Cancel"
    ]

    try:
        proc = subprocess.Popen(
            fzf_args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            env=env
        )
        stdout, _ = proc.communicate(input=initial_items)
        selection = stdout.strip()
        if selection:
            parts = selection.split("\t")
            if len(parts) >= 5:
                title = parts[0]
                item_id = parts[3]
                payload = parts[4]
                copy_to_clipboard(payload)
                touch_item(base_url, item_id)
                print(f"[COPIED] {title}")
                print(payload)
    except Exception as e:
        print(f"Interactive mode error: {e}", file=sys.stderr)

def fetch_fzf_items(query: str, item_type: str = "") -> str:
    base_url = get_base_url()
    lines = []
    try:
        if not query.strip():
            url = f"{base_url}/api/items?limit=150"
            if item_type:
                url += f"&type={urllib.parse.quote(item_type)}"
            req = urllib.request.Request(url, headers={"User-Agent": "amber-cli/fzf"})
            with urllib.request.urlopen(req, timeout=2.0) as res:
                data = json.loads(res.read().decode())
                for item in data.get("items", []):
                    title = f"[{item.get('type', '')}] {item.get('title', '')}"
                    snippet = (item.get("payload") or "").replace("\n", " ")[:80]
                    tags = item.get("tags") or ""
                    raw_payload = (item.get("payload") or "").replace("\t", "    ")
                    lines.append(f"{title}\t{snippet}\t{tags}\t{item.get('id', '')}\t{raw_payload}")
        else:
            url = f"{base_url}/api/search?q={urllib.parse.quote(query)}&limit=100"
            if item_type:
                url += f"&type={urllib.parse.quote(item_type)}"
            req = urllib.request.Request(url, headers={"User-Agent": "amber-cli/fzf"})
            with urllib.request.urlopen(req, timeout=2.0) as res:
                data = json.loads(res.read().decode())
                for item in data.get("results", []):
                    title = f"[{item.get('type', '')}] {item.get('title', '')}"
                    snippet = (item.get("payload") or "").replace("\n", " ")[:80]
                    tags = item.get("tags") or ""
                    raw_payload = (item.get("payload") or "").replace("\t", "    ")
                    lines.append(f"{title}\t{snippet}\t{tags}\t{item.get('id', '')}\t{raw_payload}")
    except Exception:
        pass
    return "\n".join(lines)

def handle_search(query: str, limit: int = 10, item_type: str = "", copy_first: bool = False, open_first: bool = False):
    base_url = get_base_url()
    params = f"q={urllib.parse.quote(query)}&limit={limit}"
    if item_type:
        params += f"&type={urllib.parse.quote(item_type)}"

    url = f"{base_url}/api/search?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "amber-cli"})
        with urllib.request.urlopen(req, timeout=5.0) as res:
            data = json.loads(res.read().decode())
    except urllib.error.URLError:
        print(f"Error: Amber daemon is not running on {base_url}", file=sys.stderr)
        print("Start it with: amber-server (or systemctl --user start amber)", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Search error: {e}", file=sys.stderr)
        sys.exit(1)

    results = data.get("results", [])
    total_hits = data.get("total_hits", 0)
    elapsed_ms = data.get("elapsed_ms", 0)

    if total_hits == 0:
        print(f"No results found for '{query}' ({elapsed_ms}ms).")
        return

    if copy_first:
        top = results[0]
        copy_to_clipboard(top.get("payload", ""))
        touch_item(base_url, top.get("id", ""))
        print(f"[COPIED TO CLIPBOARD] {top.get('title', '')}")
        print(top.get("payload", ""))
        return

    if open_first:
        top = results[0]
        target_url = top.get("source_url") or top.get("payload", "")
        touch_item(base_url, top.get("id", ""))
        print(f"[OPENING IN BROWSER] {top.get('title', '')} -> {target_url}")
        webbrowser.open(target_url)
        return

    # ANSI Formatting
    BOLD = "\033[1m"
    GREEN = "\033[32m"
    CYAN = "\033[36m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    print(f"{BOLD}Results for:{RESET} '{query}' {DIM}({total_hits} hits in {elapsed_ms}ms){RESET}\n")

    for idx, item in enumerate(results, start=1):
        item_id = item.get("id", "")
        item_type = item.get("type", "note")
        title = item.get("title", "")
        payload = item.get("payload", "")
        context = item.get("context")
        source_url = item.get("source_url")
        notes = item.get("notes")
        tags = item.get("tags")
        use_count = item.get("use_count", 0)

        print(f"{BOLD}{CYAN}[{idx}] [{item_type}] {title}{RESET} {DIM}(used {use_count}x){RESET}")
        print(f"    {GREEN}{payload}{RESET}")
        if notes:
            print(f"    {DIM}Notes: {notes}{RESET}")
        if context or tags:
            print(f"    {DIM}Context: {context or 'none'} | Tags: {tags or 'none'}{RESET}")
        if source_url:
            print(f"    {DIM}URL: {source_url}{RESET}")
        print()

def main():
    # Internal fzf helper call
    if len(sys.argv) > 1 and sys.argv[1] == "_fzf_fetch":
        q = sys.argv[2] if len(sys.argv) > 2 else ""
        t = sys.argv[3] if len(sys.argv) > 3 else ""
        print(fetch_fzf_items(q, t))
        sys.exit(0)

    # Server subcommand
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        from backend.app import main as server_main
        server_main()
        return

    if len(sys.argv) > 1 and sys.argv[1] == "save":
        save_parser = argparse.ArgumentParser(prog="amber save", description="Preserve a command, bookmark, or note")
        save_parser.add_argument("-c", "--cmd", "--command", help="Preserve a shell command")
        save_parser.add_argument("-u", "--url", help="Preserve a bookmark URL")
        save_parser.add_argument("-q", "--quote", help="Preserve a highlighted quote")
        save_parser.add_argument("-p", "--payload", help="Generic payload content")
        save_parser.add_argument("-t", "--title", help="Title or description")
        save_parser.add_argument("-n", "--notes", help="Explanations or context notes")
        save_parser.add_argument("-g", "--tags", help="Comma-separated tags")
        save_parser.add_argument("--source-url", default=None, help="Source URL")
        save_parser.add_argument("--context", help="Environment context (e.g. Ubuntu, Bash)")
        save_parser.add_argument("--type", help="Item type override")
        save_parser.add_argument("--no-scrape", action="store_true", help="Disable auto web scraping for URLs")
        args = save_parser.parse_args(sys.argv[2:])
        handle_save(args)
        return

    parser = argparse.ArgumentParser(
        prog="amber",
        description="Amber - Personal local-first memory vault, command preservation & retrieval",
        add_help=True
    )
    parser.add_argument("query", nargs="*", default=[], help="Search query terms")
    parser.add_argument("-t", "--type", default="", help="Filter by type: command | snippet | bookmark | highlight | ai_chat | note")
    parser.add_argument("-l", "--limit", type=int, default=10, help="Limit number of results (default: 10)")
    parser.add_argument("-c", "--copy", action="store_true", help="Copy top result payload directly to clipboard")
    parser.add_argument("-o", "--open", action="store_true", help="Open top matching URL directly in browser")
    parser.add_argument("-i", "--interactive", action="store_true", help="Interactive fzf split-pane search")

    args = parser.parse_args()
    query_str = " ".join(args.query).strip()

    if args.interactive or (not query_str and len(sys.argv) == 1):
        handle_interactive(query_str, args.type)
        return

    if not query_str:
        parser.print_help()
        sys.exit(0)

    handle_search(
        query=query_str,
        limit=args.limit,
        item_type=args.type,
        copy_first=args.copy,
        open_first=args.open
    )

if __name__ == "__main__":
    main()
