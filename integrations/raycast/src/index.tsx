import { ActionPanel, Action, List, getPreferenceValues, showToast, Toast } from "@raycast/api";
import { useState, useEffect } from "react";
import fetch from "node-fetch";

interface AmberItem {
  id: string;
  type: string;
  title: string;
  payload: string;
  source_url?: string;
  notes?: string;
  tags?: string;
  use_count?: number;
}

interface Preferences {
  apiUrl?: string;
}

export default function Command() {
  const preferences = getPreferenceValues<Preferences>();
  const baseUrl = preferences.apiUrl || "http://127.0.0.1:7474";

  const [searchText, setSearchText] = useState("");
  const [items, setItems] = useState<AmberItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchItems() {
      setIsLoading(true);
      try {
        const url = searchText.trim()
          ? `${baseUrl}/api/search?q=${encodeURIComponent(searchText.trim())}&limit=25`
          : `${baseUrl}/api/items?limit=25`;

        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = (await res.json()) as { items?: AmberItem[]; results?: AmberItem[] };
        setItems(data.results || data.items || []);
      } catch (err) {
        showToast({
          style: Toast.Style.Failure,
          title: "Amber Daemon Offline",
          message: `Could not connect to ${baseUrl}`,
        });
        setItems([]);
      } finally {
        setIsLoading(false);
      }
    }

    const timer = setTimeout(fetchItems, 120);
    return () => clearTimeout(timer);
  }, [searchText, baseUrl]);

  async function touchItem(id: string) {
    try {
      await fetch(`${baseUrl}/api/items/${id}/touch`, { method: "POST" });
    } catch {
      // Ignore background touch errors
    }
  }

  return (
    <List
      isLoading={isLoading}
      onSearchTextChange={setSearchText}
      searchBarPlaceholder="Search preserved commands, quotes, and notes..."
      throttle
    >
      {items.map((item) => (
        <List.Item
          key={item.id}
          title={item.title}
          subtitle={item.payload.replace(/\n/g, " ")}
          accessories={[
            { tag: item.type },
            item.use_count ? { text: `Used ${item.use_count}x` } : {},
          ]}
          actions={
            <ActionPanel>
              <Action.CopyToClipboard
                title="Copy Payload to Clipboard"
                content={item.payload}
                onCopy={() => touchItem(item.id)}
              />
              {item.source_url && (
                <Action.OpenInBrowser
                  title="Open Source Link"
                  url={item.source_url}
                  onOpen={() => touchItem(item.id)}
                />
              )}
              {item.notes && (
                <Action.CopyToClipboard
                  title="Copy Notes"
                  content={item.notes}
                  shortcut={{ modifiers: ["cmd"], key: "n" }}
                />
              )}
            </ActionPanel>
          }
        />
      ))}
    </List>
  );
}
