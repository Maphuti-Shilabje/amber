import urllib.request
import urllib.parse
import json
import threading

try:
    from ulauncher.api.client.Extension import Extension
    from ulauncher.api.client.EventListener import EventListener
    from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent
    from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
    from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
    from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
    from ulauncher.api.shared.action.DoNothingAction import DoNothingAction
except ImportError:
    # Fallback / mock for environments without ulauncher installed
    class Extension:
        pass
    class EventListener:
        pass


def touch_item_async(base_url, item_id):
    def _touch():
        try:
            req = urllib.request.Request(f"{base_url}/api/items/{item_id}/touch", method="POST")
            urllib.request.urlopen(req, timeout=1.0)
        except Exception:
            pass
    threading.Thread(target=_touch, daemon=True).start()


class AmberExtension(Extension):
    def __init__(self):
        super(AmberExtension, self).__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())


class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        query = (event.get_argument() or "").strip()
        base_url = extension.preferences.get("amber_api_url", "http://127.0.0.1:7474")

        items = []
        try:
            if not query:
                url = f"{base_url}/api/items?limit=10"
                req = urllib.request.Request(url, headers={"User-Agent": "ulauncher-amber"})
                with urllib.request.urlopen(req, timeout=1.5) as res:
                    data = json.loads(res.read().decode())
                    raw_items = data.get("items", [])
            else:
                encoded_q = urllib.parse.quote(query)
                url = f"{base_url}/api/search?q={encoded_q}&limit=10"
                req = urllib.request.Request(url, headers={"User-Agent": "ulauncher-amber"})
                with urllib.request.urlopen(req, timeout=1.5) as res:
                    data = json.loads(res.read().decode())
                    raw_items = data.get("results", [])

            for item in raw_items:
                item_id = item.get("id", "")
                item_type = item.get("type", "note")
                title = item.get("title", "Untitled")
                payload = item.get("payload", "")
                snippet = payload.replace("\n", " ")[:90]

                # Touch item in background on copy
                touch_item_async(base_url, item_id)

                items.append(
                    ExtensionResultItem(
                        icon="images/icon.png",
                        name=f"[{item_type}] {title}",
                        description=snippet,
                        on_enter=CopyToClipboardAction(payload)
                    )
                )

        except Exception as e:
            items.append(
                ExtensionResultItem(
                    icon="images/icon.png",
                    name="Amber Daemon Offline",
                    description=f"Could not connect to {base_url}. Start daemon: uvicorn backend.app:app",
                    on_enter=DoNothingAction()
                )
            )

        if not items:
            items.append(
                ExtensionResultItem(
                    icon="images/icon.png",
                    name="No traces found in Amber",
                    description=f"No preserved records matched '{query}'",
                    on_enter=DoNothingAction()
                )
            )

        return RenderResultListAction(items)


if __name__ == "__main__":
    AmberExtension().run()
