// mygoogle - Extension Popup Controller

const API_BASE = "http://127.0.0.1:7474";

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

document.addEventListener("DOMContentLoaded", async () => {
  const titleInput = document.getElementById("pop-title");
  const payloadInput = document.getElementById("pop-payload");
  const typeSelect = document.getElementById("pop-type");
  const tagsInput = document.getElementById("pop-tags");
  const form = document.getElementById("popup-form");
  const statusDiv = document.getElementById("pop-status");

  let currentUrl = "";

  // Get active tab info
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab) {
      currentUrl = tab.url || "";
      titleInput.value = tab.title || "";
      payloadInput.value = currentUrl;

      // Only attempt script injection on non-restricted pages
      if (!isRestrictedUrl(currentUrl)) {
        try {
          const results = await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            func: () => window.getSelection().toString()
          });
          const selected = results && results[0] && results[0].result ? results[0].result.trim() : "";
          if (selected) {
            typeSelect.value = "highlight";
            payloadInput.value = selected;
            titleInput.value = `Quote from ${tab.title || "webpage"}`;
          }
        } catch (e) {
          // Ignore script restriction errors
        }
      }
    }
  } catch (err) {
    console.error("Tab query failed:", err);
  }

  // Handle form submission
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const isRestricted = isRestrictedUrl(currentUrl);
    const data = {
      type: typeSelect.value,
      title: titleInput.value.trim(),
      payload: payloadInput.value.trim(),
      source_url: currentUrl || null,
      tags: tagsInput.value.trim() || null,
      auto_scrape: !isRestricted && typeSelect.value === "bookmark"
    };

    try {
      const res = await fetch(`${API_BASE}/api/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
      });

      if (res.ok) {
        statusDiv.textContent = "Preserved in Amber!";
        statusDiv.style.color = "#3fb950";
        statusDiv.classList.remove("hidden");
        setTimeout(() => window.close(), 900);
      } else {
        statusDiv.textContent = "Failed to preserve.";
        statusDiv.style.color = "#f85149";
        statusDiv.classList.remove("hidden");
      }
    } catch (err) {
      statusDiv.textContent = "Amber daemon offline.";
      statusDiv.style.color = "#f85149";
      statusDiv.classList.remove("hidden");
    }
  });
});
