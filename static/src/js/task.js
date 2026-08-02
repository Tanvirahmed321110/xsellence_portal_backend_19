function initTaskSearch() {
    const searchInput = document.getElementById("task-search");
    const searchForm = searchInput ? searchInput.closest("form") : null;

    if (!searchInput || !searchForm || searchForm.dataset.searchBound === "1") {
        return;
    }

    searchForm.dataset.searchBound = "1";
    let submitTimer = null;
    let requestController = null;

    function fetchTasks() {
        const formData = new FormData(searchForm);
        const params = new URLSearchParams();
        const shouldRestoreFocus = document.activeElement === searchInput;
        const selectionStart = shouldRestoreFocus ? searchInput.selectionStart : null;
        const selectionEnd = shouldRestoreFocus ? searchInput.selectionEnd : null;

        for (const [key, value] of formData.entries()) {
            if (value !== null && String(value).trim() !== "") {
                params.set(key, value);
            }
        }

        const url = params.toString() ? searchForm.action + "?" + params.toString() : searchForm.action;

        if (requestController) {
            requestController.abort();
        }
        requestController = new AbortController();

        fetch(url, {
            method: "GET",
            headers: {"X-Requested-With": "XMLHttpRequest"},
            signal: requestController.signal,
        })
            .then(response => response.text())
            .then(html => {
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, "text/html");
                const nextWrap = doc.querySelector(".projects-wrap");
                const currentWrap = document.querySelector(".projects-wrap");

                if (!nextWrap || !currentWrap) {
                    window.location.href = url;
                    return;
                }

                currentWrap.replaceWith(nextWrap);
                window.history.replaceState({}, "", url);

                if (typeof initializeSavedViewMode === "function") {
                    initializeSavedViewMode();
                }

                if (typeof deleteModalF === "function") {
                    deleteModalF('deleteModal');
                }

                initTaskSearch();

                if (shouldRestoreFocus) {
                    const nextInput = document.getElementById("task-search");
                    if (nextInput) {
                        nextInput.focus();
                        if (selectionStart !== null && selectionEnd !== null) {
                            nextInput.setSelectionRange(selectionStart, selectionEnd);
                        }
                    }
                }
            })
            .catch(error => {
                if (error && error.name === "AbortError") {
                    return;
                }
                window.location.href = url;
            });
    }

    searchForm.addEventListener("submit", function (event) {
        event.preventDefault();
        if (submitTimer) {
            clearTimeout(submitTimer);
        }
        fetchTasks();
    });

    searchInput.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
            event.preventDefault();
            if (submitTimer) {
                clearTimeout(submitTimer);
            }
            fetchTasks();
        }
    });

    searchInput.addEventListener("input", function () {
        if (submitTimer) {
            clearTimeout(submitTimer);
        }
        submitTimer = setTimeout(fetchTasks, 300);
    });
}

document.addEventListener("DOMContentLoaded", function () {
    deleteModalF('deleteModal');
    initTaskSearch();
});
