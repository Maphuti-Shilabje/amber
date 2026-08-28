// mygoogle - Background Service Worker

const API_BASE = "http://127.0.0.1:7474";

// Setup context menus
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "save-selection",
    title: "Clip selection to mygoogle",
    contexts: ["selection"]
  });

  chrome.contextMenus.create({
    id: "save-page",
    title: "Save page bookmark to mygoogle",
    contexts: ["page"]
  });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === "save-selection" && info.selectionText) {
    await saveToMyGoogle({
      type: "highlight",
      title: (tab && tab.title) ? `Quote from ${tab.title}` : "Saved Quote",
      payload: info.selectionText,
      source_url: (tab && tab.url) ? tab.url : null,
      auto_scrape: false
    });
  } else if (info.menuItemId === "save-page" && tab) {
    await saveToMyGoogle({
      type: "bookmark",
      title: tab.title || tab.url,
      payload: tab.url,
      source_url: tab.url,
      auto_scrape: true
    });
  }
});

// Handle keyboard shortcut (Alt+S)
chrome.commands.onCommand.addListener(async (command) => {
  if (command === "quick-save") {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.id) return;

    try {
      const results = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: () => window.getSelection().toString()
      });

      const selectedText = results && results[0] && results[0].result ? results[0].result.trim() : "";

      if (selectedText) {
        await saveToMyGoogle({
          type: "highlight",
          title: `Quote from ${tab.title || "webpage"}`,
          payload: selectedText,
          source_url: tab.url,
          auto_scrape: false
        });
      } else {
        await saveToMyGoogle({
          type: "bookmark",
          title: tab.title || tab.url,
          payload: tab.url,
          source_url: tab.url,
          auto_scrape: true
        });
      }
    } catch (err) {
      console.error("Script execution failed:", err);
      flashBadge("ERR", "#d73a49");
    }
  }
});

// Save to local daemon
async function saveToMyGoogle(data) {
  try {
    const res = await fetch(`${API_BASE}/api/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });

    if (res.ok) {
      flashBadge("OK", "#238636");
    } else {
      flashBadge("ERR", "#d73a49");
    }
  } catch (err) {
    console.error("Failed to connect to mygoogle daemon:", err);
    flashBadge("OFF", "#8b949e");
  }
}

// Flash badge text for quick visual feedback
function flashBadge(text, color) {
  chrome.action.setBadgeText({ text: text });
  chrome.action.setBadgeBackgroundColor({ color: color });

  setTimeout(() => {
    chrome.action.setBadgeText({ text: "" });
  }, 2000);
}
