// mygoogle - Web Omnibox Client

document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const searchInput = document.getElementById("search-input");
    const btnClearSearch = document.getElementById("btn-clear-search");
    const resultsContainer = document.getElementById("results-container");
    const searchMeta = document.getElementById("search-meta");
    const resultsCount = document.getElementById("results-count");
    const resultsLatency = document.getElementById("results-latency");
    const filterChips = document.querySelectorAll(".chip");
    const publicFallback = document.getElementById("public-fallback");
    const statsCounter = document.getElementById("stats-counter");
    const toast = document.getElementById("toast");

    // Fallback links
    const linkGoogle = document.getElementById("link-google");
    const linkDdg = document.getElementById("link-ddg");
    const linkGithub = document.getElementById("link-github");
    const linkKagi = document.getElementById("link-kagi");

    // Modal elements
    const btnOpenIngest = document.getElementById("btn-open-ingest");
    const btnCloseModal = document.getElementById("btn-close-modal");
    const btnCancelIngest = document.getElementById("btn-cancel-ingest");
    const modalIngest = document.getElementById("modal-ingest");
    const formIngest = document.getElementById("form-ingest");

    // State
    let currentQuery = "";
    let currentFilter = "";
    let debounceTimer = null;
    let selectedIndex = -1;
    let currentResults = [];

    // Initialize
    fetchStats();
    
    // Check URL parameters for search query
    const urlParams = new URLSearchParams(window.location.search);
    const initialQuery = urlParams.get("q");
    if (initialQuery) {
        currentQuery = initialQuery.trim();
        searchInput.value = currentQuery;
        btnClearSearch.classList.remove("hidden");
        performSearch(currentQuery, currentFilter);
    } else {
        loadRecentItems();
    }

    // Event Listeners
    searchInput.addEventListener("input", (e) => {
        currentQuery = e.target.value.trim();
        if (currentQuery.length > 0) {
            btnClearSearch.classList.remove("hidden");
        } else {
            btnClearSearch.classList.add("hidden");
        }

        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            if (currentQuery.length > 0) {
                performSearch(currentQuery, currentFilter);
            } else {
                loadRecentItems();
            }
        }, 150);
    });

    btnClearSearch.addEventListener("click", () => {
        searchInput.value = "";
        currentQuery = "";
        btnClearSearch.classList.add("hidden");
        searchInput.focus();
        loadRecentItems();
    });

    // Filter Chips
    filterChips.forEach(chip => {
        chip.addEventListener("click", () => {
            filterChips.forEach(c => c.classList.remove("active"));
            chip.classList.add("active");
            currentFilter = chip.dataset.type;
            if (currentQuery.length > 0) {
                performSearch(currentQuery, currentFilter);
            } else {
                loadRecentItems();
            }
        });
    });

    // Keyboard Shortcuts
    document.addEventListener("keydown", (e) => {
        // Focus search with '/'
        if (e.key === "/" && document.activeElement !== searchInput && !modalIngest.classList.contains("active")) {
            e.preventDefault();
            searchInput.focus();
            searchInput.select();
        }

        // Clear or close modal with Esc
        if (e.key === "Escape") {
            if (!modalIngest.classList.contains("hidden")) {
                closeModal();
            } else if (searchInput.value) {
                searchInput.value = "";
                currentQuery = "";
                btnClearSearch.classList.add("hidden");
                loadRecentItems();
            }
        }

        // Navigate search results
        if (e.key === "ArrowDown") {
            if (currentResults.length > 0) {
                e.preventDefault();
                selectedIndex = Math.min(selectedIndex + 1, currentResults.length - 1);
                updateCardSelection();
            }
        } else if (e.key === "ArrowUp") {
            if (currentResults.length > 0) {
                e.preventDefault();
                selectedIndex = Math.max(selectedIndex - 1, 0);
                updateCardSelection();
            }
        } else if (e.key === "Enter" && selectedIndex >= 0 && selectedIndex < currentResults.length) {
            // Action on selected card
            const item = currentResults[selectedIndex];
            if (item.type === "command" || item.type === "snippet" || item.type === "highlight") {
                copyToClipboard(item.payload, item.id);
            } else if (item.source_url) {
                window.open(item.source_url, "_blank");
                touchItem(item.id);
            }
        }
    });

    // Ingest Modal Handlers
    btnOpenIngest.addEventListener("click", openModal);
    btnCloseModal.addEventListener("click", closeModal);
    btnCancelIngest.addEventListener("click", closeModal);

    formIngest.addEventListener("submit", async (e) => {
        e.preventDefault();
        const payloadData = {
            type: document.getElementById("input-type").value,
            title: document.getElementById("input-title").value.trim(),
            payload: document.getElementById("input-payload").value.trim(),
            source_url: document.getElementById("input-url").value.trim() || null,
            notes: document.getElementById("input-notes").value.trim() || null,
            tags: document.getElementById("input-tags").value.trim() || null,
            context: document.getElementById("input-context").value.trim() || null,
            auto_scrape: true
        };

        try {
            const res = await fetch("/api/ingest", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payloadData)
            });
            if (res.ok) {
                showToast("Item saved to memory");
                closeModal();
                formIngest.reset();
                fetchStats();
                loadRecentItems();
            } else {
                showToast("Failed to save item");
            }
        } catch (err) {
            console.error("Ingest error:", err);
            showToast("Error connecting to daemon");
        }
    });

    // Core Fetch Functions
    async function performSearch(query, itemType) {
        let url = `/api/search?q=${encodeURIComponent(query)}&limit=25`;
        if (itemType) {
            url += `&type=${encodeURIComponent(itemType)}`;
        }

        try {
            const res = await fetch(url);
            const data = await res.json();
            currentResults = data.results || [];
            selectedIndex = currentResults.length > 0 ? 0 : -1;

            renderResults(currentResults);
            
            searchMeta.classList.remove("hidden");
            resultsCount.textContent = `${data.total_hits} memory matches`;
            resultsLatency.textContent = `${data.elapsed_ms}ms`;

            updateFallbackLinks(query);
            publicFallback.classList.remove("hidden");
        } catch (err) {
            console.error("Search error:", err);
        }
    }

    async function loadRecentItems() {
        let url = `/api/items?limit=20`;
        if (currentFilter) {
            url += `&type=${encodeURIComponent(currentFilter)}`;
        }

        try {
            const res = await fetch(url);
            const data = await res.json();
            currentResults = data.items || [];
            selectedIndex = -1;

            renderResults(currentResults, true);
            searchMeta.classList.add("hidden");
            publicFallback.classList.add("hidden");
        } catch (err) {
            console.error("Load items error:", err);
        }
    }

    async function fetchStats() {
        try {
            const res = await fetch("/api/stats");
            const data = await res.json();
            statsCounter.textContent = `${data.total_items} items indexed`;
        } catch (err) {
            statsCounter.textContent = "daemon offline";
        }
    }

    // Render Cards
    function renderResults(items, isRecent = false) {
        resultsContainer.innerHTML = "";

        if (items.length === 0) {
            resultsContainer.innerHTML = `
                <div class="result-card">
                    <span class="result-notes">${isRecent ? "No items in memory yet. Use the '+ Ingest' button or CLI to add one." : "No memory matches found."}</span>
                </div>
            `;
            return;
        }

        items.forEach((item, idx) => {
            const card = document.createElement("div");
            card.className = `result-card ${idx === selectedIndex ? "selected" : ""}`;
            card.dataset.index = idx;

            const isCode = item.type === "command" || item.type === "snippet";
            const isHighlight = item.type === "highlight";
            const tags = item.tags ? item.tags.split(",").map(t => `<span class="tag-item">${escapeHtml(t.trim())}</span>`).join("") : "";

            let payloadHtml = "";
            if (item.payload) {
                payloadHtml = `
                    <div class="payload-box ${isHighlight ? "payload-highlight" : ""}">
                        ${escapeHtml(item.payload)}
                    </div>
                `;
            }

            card.innerHTML = `
                <div class="result-header">
                    <div class="result-title-area">
                        <span class="type-badge type-${item.type}">${item.type}</span>
                        <span class="result-title">${escapeHtml(item.title)}</span>
                    </div>
                    <div class="result-actions">
                        ${isCode || isHighlight ? `<button class="btn-card-action btn-copy" data-id="${item.id}">Copy</button>` : ""}
                        ${item.source_url ? `<a href="${escapeHtml(item.source_url)}" target="_blank" class="btn-card-action btn-visit" data-id="${item.id}">Visit</a>` : ""}
                        <button class="btn-card-action btn-delete" data-id="${item.id}">Delete</button>
                    </div>
                </div>

                ${payloadHtml}

                ${item.notes ? `<div class="result-notes">${escapeHtml(item.notes)}</div>` : ""}

                <div class="result-footer">
                    <div class="meta-tags">
                        ${tags}
                        ${item.context ? `<span class="dim">Context: ${escapeHtml(item.context)}</span>` : ""}
                    </div>
                    <div class="meta-usage">
                        ${item.use_count > 0 ? `<span class="dim">Used ${item.use_count}x</span>` : ""}
                    </div>
                </div>
            `;

            // Action button bindings
            const copyBtn = card.querySelector(".btn-copy");
            if (copyBtn) {
                copyBtn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    copyToClipboard(item.payload, item.id);
                });
            }

            const visitBtn = card.querySelector(".btn-visit");
            if (visitBtn) {
                visitBtn.addEventListener("click", () => {
                    touchItem(item.id);
                });
            }

            const deleteBtn = card.querySelector(".btn-delete");
            if (deleteBtn) {
                deleteBtn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    deleteItem(item.id);
                });
            }

            card.addEventListener("click", () => {
                selectedIndex = idx;
                updateCardSelection();
                if (isCode || isHighlight) {
                    copyToClipboard(item.payload, item.id);
                } else if (item.source_url) {
                    window.open(item.source_url, "_blank");
                    touchItem(item.id);
                }
            });

            resultsContainer.appendChild(card);
        });
    }

    function updateCardSelection() {
        const cards = document.querySelectorAll(".result-card");
        cards.forEach((card, idx) => {
            if (idx === selectedIndex) {
                card.classList.add("selected");
                card.scrollIntoView({ block: "nearest", behavior: "smooth" });
            } else {
                card.classList.remove("selected");
            }
        });
    }

    function updateFallbackLinks(query) {
        const eq = encodeURIComponent(query);
        linkGoogle.href = `https://www.google.com/search?q=${eq}`;
        linkDdg.href = `https://duckduckgo.com/?q=${eq}`;
        linkGithub.href = `https://github.com/search?q=${eq}`;
        linkKagi.href = `https://kagi.com/search?q=${eq}`;
    }

    async function copyToClipboard(text, itemId) {
        try {
            await navigator.clipboard.writeText(text);
            showToast("Copied to clipboard");
            if (itemId) touchItem(itemId);
        } catch (err) {
            console.error("Clipboard copy error:", err);
        }
    }

    async function touchItem(itemId) {
        try {
            await fetch(`/api/items/${itemId}/touch`, { method: "POST" });
            fetchStats();
        } catch (err) {
            console.error("Touch error:", err);
        }
    }

    async function deleteItem(itemId) {
        if (confirm("Delete this item from memory?")) {
            try {
                const res = await fetch(`/api/items/${itemId}`, { method: "DELETE" });
                if (res.ok) {
                    showToast("Item deleted");
                    fetchStats();
                    if (currentQuery.length > 0) {
                        performSearch(currentQuery, currentFilter);
                    } else {
                        loadRecentItems();
                    }
                }
            } catch (err) {
                console.error("Delete error:", err);
            }
        }
    }

    function showToast(msg) {
        toast.textContent = msg;
        toast.classList.remove("hidden");
        setTimeout(() => {
            toast.classList.add("hidden");
        }, 2200);
    }

    function openModal() {
        modalIngest.classList.remove("hidden");
        document.getElementById("input-title").focus();
    }

    function closeModal() {
        modalIngest.classList.add("hidden");
    }

    function escapeHtml(str) {
        if (!str) return "";
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});
