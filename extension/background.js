// mygoogle - Background Service Worker

const API_BASE = "http://127.0.0.1:7474";

// Check if a URL cannot be scripted (browser internal pages, webstore, etc.)
function isRestrictedUrl(url) {
  if (!url) return true;
  const restrictedProtocols = [
    "chrome://",
    "chrome-extension://",
    "edge://",
    "brave://",
    "about:",
    "devtools://",
    "view-source:",
    "data:"
  ];
  if (restrictedProtocols.some(prefix => url.startsWith(prefix))) return true;
  if (url.includes("chromewebstore.google.com") || url.includes("chrome.google.com/webstore")) return true;
  return false;
}

// Function injected into tab to extract text selection across DOM and inputs
function extractSelectionFromPage() {
  let text = "";
  if (window.getSelection) {
    text = window.getSelection().toString();
  }
  if (!text && document.activeElement) {
    const el = document.activeElement;
    if (el.tagName === "TEXTAREA" || (el.tagName === "INPUT" && el.type === "text")) {
      text = el.value.substring(el.selectionStart, el.selectionEnd);
    }
  }
  return text ? text.trim() : "";
}

// Setup context menus on install
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
      title: tab && tab.title ? `Quote from ${tab.title}` : "Saved Quote",
      payload: info.selectionText.trim(),
      source_url: tab && tab.url ? tab.url : null,
      auto_scrape: false
    }, "CLIP");
  } else if (info.menuItemId === "save-page" && tab) {
    const restricted = isRestrictedUrl(tab.url);
    await saveToMyGoogle({
      type: "bookmark",
      title: tab.title || tab.url,
      payload: tab.url,
      source_url: tab.url,
      auto_scrape: !restricted
    }, "BOOK");
  }
});

// Handle keyboard shortcut (Alt+S)
chrome.commands.onCommand.addListener(async (command) => {
  if (command === "quick-save") {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.id) return;

    const restricted = isRestrictedUrl(tab.url);
    let selectedText = "";

    if (!restricted) {
      try {
        const results = await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: extractSelectionFromPage
        });
        if (results && results[0] && results[0].result) {
          selectedText = results[0].result.trim();
        }
      } catch (err) {
        console.warn("Could not extract selection from tab:", err);
      }
    }

    if (selectedText) {
      await saveToMyGoogle({
        type: "highlight",
        title: tab.title ? `Quote from ${tab.title}` : "Saved Quote",
        payload: selectedText,
        source_url: tab.url,
        auto_scrape: false
      }, "CLIP");
    } else if (tab.url) {
      await saveToMyGoogle({
        type: "bookmark",
        title: tab.title || tab.url,
        payload: tab.url,
        source_url: tab.url,
        auto_scrape: !restricted
      }, "BOOK");
    }
  }
});

// Save to local daemon with badge feedback
async function saveToMyGoogle(data, badgeText = "OK") {
  try {
    const res = await fetch(`${API_BASE}/api/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });

    if (res.ok) {
      const color = badgeText === "CLIP" ? "#d29922" : "#238636";
      flashBadge(badgeText, color);
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
  }, 2200);
}
