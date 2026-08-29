// Amber - Background Service Worker

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

// Injects an in-page toast notification directly on the active web page
function showToastInTab(tabId, message, color = "#238636") {
  if (!tabId) return;
  chrome.scripting.executeScript({
    target: { tabId: tabId },
    func: (msg, borderColor) => {
      let toast = document.getElementById("amber-inpage-toast");
      if (!toast) {
        toast = document.createElement("div");
        toast.id = "amber-inpage-toast";
        toast.style.cssText = `
          position: fixed;
          top: 24px;
          right: 24px;
          z-index: 2147483647;
          background: #0d1117;
          color: #f0f6fc;
          border: 1px solid #30363d;
          border-left: 4px solid ${borderColor};
          padding: 10px 16px;
          border-radius: 6px;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
          font-size: 13px;
          font-weight: 600;
          box-shadow: 0 8px 24px rgba(0,0,0,0.6);
          pointer-events: none;
          opacity: 0;
          transform: translateY(-10px);
          transition: opacity 0.2s ease, transform 0.2s ease;
        `;
        document.body.appendChild(toast);
      }
      toast.textContent = msg;
      requestAnimationFrame(() => {
        toast.style.opacity = "1";
        toast.style.transform = "translateY(0)";
      });
      setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateY(-10px)";
        setTimeout(() => toast.remove(), 300);
      }, 2000);
    },
    args: [message, color]
  }).catch(() => {});
}

// Setup context menus on install
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "save-selection",
    title: "Preserve selection in Amber",
    contexts: ["selection"]
  });

  chrome.contextMenus.create({
    id: "save-page",
    title: "Preserve page bookmark in Amber",
    contexts: ["page"]
  });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === "save-selection" && info.selectionText) {
    await saveToAmber({
      type: "highlight",
      title: tab && tab.title ? `Quote from ${tab.title}` : "Saved Quote",
      payload: info.selectionText.trim(),
      source_url: tab && tab.url ? tab.url : null,
      auto_scrape: false
    }, "CLIP", tab ? tab.id : null, "Quote preserved in Amber");
  } else if (info.menuItemId === "save-page" && tab) {
    const restricted = isRestrictedUrl(tab.url);
    await saveToAmber({
      type: "bookmark",
      title: tab.title || tab.url,
      payload: tab.url,
      source_url: tab.url,
      auto_scrape: !restricted
    }, "BOOK", tab.id, "Bookmark preserved in Amber");
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
      await saveToAmber({
        type: "highlight",
        title: tab.title ? `Quote from ${tab.title}` : "Saved Quote",
        payload: selectedText,
        source_url: tab.url,
        auto_scrape: false
      }, "CLIP", tab.id, "Quote preserved in Amber");
    } else if (tab.url) {
      await saveToAmber({
        type: "bookmark",
        title: tab.title || tab.url,
        payload: tab.url,
        source_url: tab.url,
        auto_scrape: !restricted
      }, "BOOK", tab.id, "Bookmark preserved in Amber");
    }
  }
});

// Save to local daemon with badge feedback and in-page toast
async function saveToAmber(data, badgeText = "OK", tabId = null, toastMessage = "Preserved in Amber") {
  try {
    const res = await fetch(`${API_BASE}/api/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });

    if (res.ok) {
      const color = badgeText === "CLIP" ? "#d29922" : "#238636";
      flashBadge(badgeText, color);
      if (tabId) {
        showToastInTab(tabId, toastMessage, color);
      }
    } else {
      flashBadge("ERR", "#d73a49");
      if (tabId) {
        showToastInTab(tabId, "Failed to preserve in Amber", "#d73a49");
      }
    }
  } catch (err) {
    console.error("Failed to connect to Amber daemon:", err);
    flashBadge("OFF", "#8b949e");
    if (tabId) {
      showToastInTab(tabId, "Amber daemon offline", "#8b949e");
    }
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
