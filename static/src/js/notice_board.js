function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value || "";
    return div.innerHTML;
}
console.log('heelo')
function buildTickerItems(items) {
    return items.map((item) => `
        <div class="ticker-item">
            <span class="icon">${escapeHtml(item.icon)}</span>
            <p>${escapeHtml(item.text)}</p>
        </div>
    `).join("");
}

async function loadNoticeBoard() {
    const board = document.getElementById("notic-board");
    const track = document.getElementById("ticker-track");

    if (!board || !track) {
        return;
    }

    try {
        const response = await fetch("/notice-board/data", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            credentials: "same-origin",
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: {},
                id: Date.now(),
            }),
        });

        const payload = await response.json();
        const result = payload.result || {};
        const items = (result && result.items) || [];



        const html = buildTickerItems(items);
        track.innerHTML = html + html;
        board.style.display = "block";
    } catch (error) {
        console.error("Notice board load failed", error);
        board.style.display = "none";
    }
}

document.addEventListener("DOMContentLoaded", loadNoticeBoard);
