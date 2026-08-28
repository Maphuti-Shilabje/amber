// mygoogle - Extension Popup Controller

const API_BASE = "http://127.0.0.1:7474";

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

      // Check if text is selected
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
        // Restricted page (chrome://, etc.)
      }
    }
  } catch (err) {
    console.error("Tab query failed:", err);
  }

  // Handle form submission
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = {
      type: typeSelect.value,
      title: titleInput.value.trim(),
      payload: payloadInput.value.trim(),
      source_url: currentUrl || null,
      tags: tagsInput.value.trim() || null,
      auto_scrape: typeSelect.value === "bookmark"
    };

    try {
      const res = await fetch(`${API_BASE}/api/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
      });

      if (res.ok) {
        statusDiv.textContent = "Saved to mygoogle!";
        statusDiv.style.color = "#3fb950";
        statusDiv.classList.remove("hidden");
        setTimeout(() => window.close(), 900);
      } else {
        statusDiv.textContent = "Failed to save.";
        statusDiv.style.color = "#f85149";
        statusDiv.classList.remove("hidden");
      }
    } catch (err) {
      statusDiv.textContent = "mygoogle daemon offline.";
      statusDiv.style.color = "#f85149";
      statusDiv.classList.remove("hidden");
    }
  });
});
