#!/usr/bin/env python3
# Helper script for interactive fzf search in amber CLI

import os
import sys
import json
import urllib.request
import urllib.parse

def fetch_items(query: str, item_type: str = ""):
    host = os.environ.get("AMBER_HOST", "127.0.0.1")
    port = os.environ.get("AMBER_PORT", "7474")

    if not query.strip():
        url = f"http://{host}:{port}/api/items?limit=150"
        if item_type:
            url += f"&type={urllib.parse.quote(item_type)}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "amber-cli/fzf"})
            with urllib.request.urlopen(req, timeout=3.0) as res:
                data = json.loads(res.read().decode())
                for item in data.get("items", []):
                    title = f"[{item.get('type', '')}] {item.get('title', '')}"
                    p_snippet = (item.get("payload") or "").replace("\n", " ")[:80]
                    tags = item.get("tags") or ""
                    raw_payload = (item.get("payload") or "").replace("\t", "    ")
                    print(f"{title}\t{p_snippet}\t{tags}\t{item.get('id', '')}\t{raw_payload}")
        except Exception:
            pass
    else:
        url = f"http://{host}:{port}/api/search?q={urllib.parse.quote(query)}&limit=100"
        if item_type:
            url += f"&type={urllib.parse.quote(item_type)}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "amber-cli/fzf"})
            with urllib.request.urlopen(req, timeout=3.0) as res:
                data = json.loads(res.read().decode())
                for item in data.get("results", []):
                    title = f"[{item.get('type', '')}] {item.get('title', '')}"
                    p_snippet = (item.get("payload") or "").replace("\n", " ")[:80]
                    tags = item.get("tags") or ""
                    raw_payload = (item.get("payload") or "").replace("\t", "    ")
                    print(f"{title}\t{p_snippet}\t{tags}\t{item.get('id', '')}\t{raw_payload}")
        except Exception:
            pass

if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else ""
    t = sys.argv[2] if len(sys.argv) > 2 else ""
    fetch_items(q, t)
