function applyFilters() {
    const loader = document.getElementById("timesheetLoader");

    if (loader) {
        loader.classList.add("show");
    }

    const project = document.getElementById("filter-project")?.value || "";
    const startDate = document.getElementById("filter-start-date")?.value || "";
    const endDate = document.getElementById("filter-end-date")?.value || "";

    if (startDate && endDate && startDate > endDate) {
        if (loader) {
            loader.classList.remove("show");
        }
        alert("From date cannot be greater than To date.");
        return;
    }

    const params = new URLSearchParams();

    if (project) {
        params.set("project_id", project);
    }

    if (startDate) {
        params.set("start_date", startDate);
    }

    if (endDate) {
        params.set("end_date", endDate);
    }

    const queryString = params.toString();

    window.location.href = queryString
        ? "/timesheets?" + queryString
        : "/timesheets";
}