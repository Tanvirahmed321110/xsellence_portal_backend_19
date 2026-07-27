
//============== for Notification
const notificationSidebar = document.getElementById('notification-sidebar');

if (notificationSidebar) {
    const overlay = document.getElementById('overlay');
    const notificationButton = document.getElementById('notification-btn');
    const closeButton = document.getElementById('close3');

    // Keep sidebar open/close behavior simple and reusable.
    function closeNotificationSidebar() {
        notificationSidebar.classList.remove('open');
        overlay.classList.remove('show');
    }

    if (notificationButton) {
        notificationButton.onclick = function () {
            notificationSidebar.classList.add('open');
            overlay.classList.add('show');
        };
    }

    if (closeButton) {
        closeButton.onclick = closeNotificationSidebar;
    }

    if (overlay) {
        overlay.onclick = closeNotificationSidebar;
    }
}

//============== For Delete Confirmation
function openDeleteModal(element) {
    let modal = document.getElementById('deleteModal');
    let confirmBtn = document.getElementById('confirmYes');
    if (!modal || !confirmBtn) return false;

    // ✅ href এর বদলে form submit
    let form = element.closest('form');
    confirmBtn.onclick = function () {
        form.submit();
    };

    modal.classList.add('active');
    return false;
}

function closeModal(modalId) {
    let modal = document.getElementById(modalId);
    if (!modal) return;
    modal.classList.remove('active');
}

function deleteModalF(deleteModal) {
    let modal = document.getElementById('deleteModal');
    if (!modal) return;
    modal.addEventListener('click', function (e) {
        if (e.target === this) closeModal(deleteModal);
    });
}



//==============  For List and Grid View  (Global)
function getViewStorageKey() {
    return 'xsellenceViewMode:' + window.location.pathname;
}

function setView(type) {
    const panelGrid = document.getElementById('panel-grid');
    const panelList = document.getElementById('panel-list');
    const btnGrid = document.getElementById('btn-grid');
    const btnList = document.getElementById('btn-list');

    if (!panelGrid || !panelList || !btnGrid || !btnList) {
        return;
    }

    const normalizedType = type === 'list' ? 'list' : 'grid';

    panelGrid.classList.toggle('visible', normalizedType === 'grid');
    panelList.classList.toggle('visible', normalizedType === 'list');
    btnGrid.classList.toggle('active', normalizedType === 'grid');
    btnList.classList.toggle('active', normalizedType === 'list');
    localStorage.setItem(getViewStorageKey(), normalizedType);
}

function initializeSavedViewMode() {
    const panelGrid = document.getElementById('panel-grid');
    const panelList = document.getElementById('panel-list');
    const btnGrid = document.getElementById('btn-grid');
    const btnList = document.getElementById('btn-list');

    if (!panelGrid || !panelList || !btnGrid || !btnList) {
        return;
    }

    setView(localStorage.getItem(getViewStorageKey()) || 'grid');
}


// ============  For Search  (Global)
function searchF(cardSelector, nameSelector, idSelector) {

    const searchInput = document.querySelector('.search-input')
    const cards = document.querySelectorAll(cardSelector)
    const listRows = document.querySelectorAll('#panel-list tbody tr')

    // ✅ Get or CREATE error container dynamically
    let errorContainer = document.getElementById('error-container')

    if (!errorContainer) {
        errorContainer = document.createElement('div')
        errorContainer.id = 'error-container'
        errorContainer.innerHTML = `
            <div class="design-wrapper mt-7">
                <div class="empty-4">
                    <div class="e4-glass">
                        <div class="e4-ring">
                            <span class="e4-icon-center">
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                                    <circle cx="11" cy="11" r="7"></circle>
                                    <path d="M16.5 16.5L21 21"></path>
                                    <line x1="8" y1="11" x2="14" y2="11"></line>
                                </svg>
                            </span>
                        </div>
                        <h2 class="e4-title">Data <strong style="color: red;">'NOT'</strong> Found</h2>
                        <p class="e4-sub">No records matched your current search or filter criteria.</p>
                        <div class="e4-pills">
                            <span class="e4-pill">0 results</span>
                            <span class="e4-pill">try new filter</span>
                            <span class="e4-pill">clear search</span>
                        </div>
                    </div>
                </div>
            </div>
        `
        errorContainer.style.display = 'none' // hidden by default

        // ✅ Insert after the cards container
        const panel = document.getElementById('panel-grid')
        panel.parentNode.insertBefore(errorContainer, panel.nextSibling)
    }

    // validation
    if (!searchInput || !cards.length) {
        console.log('Required Elements not found')
        return
    }

    // search event
    searchInput.addEventListener('keyup', function () {
        const value = this.value.trim().toLowerCase()
        let found = false

        if (value === '') {
            cards.forEach(card => card.style.display = 'block')
            listRows.forEach(row => row.style.display = '')
            errorContainer.style.display = 'none'
            return
        }

        cards.forEach(card => {
            const nameEl = card.querySelector(nameSelector)
            const idEl = card.querySelector(idSelector)

            if (!nameEl || !idEl) return

            const cardName = nameEl.innerText.toLowerCase()
            const cardId = idEl.getAttribute('href').split('/').pop()

            if (cardName.includes(value) || cardId.includes(value)) {
                card.style.display = 'block'
                found = true
            } else {
                card.style.display = 'none'
            }
        })

        listRows.forEach(row => {
            const name = row.children[0].innerText.toLowerCase()
            const idEl = row.querySelector('.btn-primary')

            let rowId = ''
            if (idEl) {
                rowId = idEl.getAttribute('href').split('/').pop()
            }

            if (name.includes(value) || rowId.includes(value)) {
                row.style.display = ''
                found = true
            } else {
                row.style.display = 'none'
            }
        })

        // ✅ show/hide with style.display instead of classList
        errorContainer.style.display = found ? 'none' : 'block'
    })
}




document.addEventListener("DOMContentLoaded", function () {
    initializeSavedViewMode();

    //=============  Sidebar
    const sidebar = document.getElementById('sidebar');

    function openSidebarDesktop() {
    const collaps_btn = document.getElementById('collaps-btn');
    const main_content = document.querySelector('.main-content');
    const notic_board = document.getElementById('notic-board');

    if (!collaps_btn || !main_content || !sidebar || !notic_board) {
        console.log("Sidebar elements not found ❌");
        return;
    }

    // Page load হলে previous state apply
    const isCollapsed = localStorage.getItem('sidebarCollapsed');

    if (isCollapsed === 'true') {
        sidebar.classList.add('sidebar-small');
        main_content.classList.add('main-content-big');
        notic_board.classList.add('big');
    }

    collaps_btn.addEventListener('click', function () {
        sidebar.classList.toggle('sidebar-small');
        main_content.classList.toggle('main-content-big');
        notic_board.classList.toggle('big');

        // Save state
        localStorage.setItem(
            'sidebarCollapsed',
            sidebar.classList.contains('sidebar-small')
        );
    });
}

openSidebarDesktop();




    //===============  For Mobile Sidebar
    function mobileSidebar() {
        const mobile_menu_btn = document.getElementById('mobile-menu-btn')
        const menuIcon = document.getElementById('menu-icon');

        if (!mobile_menu_btn || !menuIcon) {
            console.log("Sidebar elements not found ❌");
            return;
        }

        let isOpen = false;

        const hamburger = `
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <line x1="3" y1="7" x2="21" y2="7" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                <line x1="7" y1="12" x2="21" y2="12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                <line x1="11" y1="17" x2="21" y2="17" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>`;

        const closeIcon = `
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <line x1="5" y1="5" x2="19" y2="19" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                <line x1="19" y1="5" x2="5" y2="19" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>`;

        menuIcon.innerHTML = hamburger;

        mobile_menu_btn.addEventListener('click', function () {
            sidebar.classList.toggle('active');
            isOpen = !isOpen;
            menuIcon.innerHTML = isOpen ? closeIcon : hamburger;
        });
    }

    mobileSidebar()




    //============= For Theme Button
    // const toggle = document.getElementById("themeToggle");
    //
    // toggle.addEventListener("click", () => {
    //     const currentTheme = document.documentElement.getAttribute("data-theme");
    //
    //     if (currentTheme === "dark") {
    //         document.documentElement.setAttribute("data-theme", "light");
    //         localStorage.setItem("theme", "light");
    //     } else {
    //         document.documentElement.setAttribute("data-theme", "dark");
    //         localStorage.setItem("theme", "dark");
    //     }
    // });




    // ============  For Date input field Change Placeholder color
    document.querySelectorAll('input[type="date"]').forEach(function (input) {
        toggleDateColor(input);

        input.addEventListener('change', function () {
            toggleDateColor(this);
        });
    });

    function toggleDateColor(input) {
        if (input.value) {
            input.style.color = 'var(--color-text-header)';
            input.style.fontWeight = '500'
        } else {
            input.style.color = 'var(--color-text-placeholder)';
        }
    }




    // for current date
//    const dateEl = document.querySelector('header .date span')
//    const today = new Date()
//    const options = { day: "2-digit", month: "short", year: 'numeric' }
//    dateEl.innerText = today.toLocaleDateString('en-GB', options)


// date and time show update
    const dateEl = document.getElementById('live-date');
    const timeEl = document.getElementById('live-time');
    if (!dateEl || !timeEl) return;

    function updateDateTime() {
    const now = new Date();
    dateEl.textContent = now.toLocaleDateString('en-GB', {
        day: '2-digit', month: 'short', year: 'numeric',
        timeZone: 'Asia/Dhaka'
    });
    timeEl.textContent = now.toLocaleTimeString('en-US', {
        hour: '2-digit', minute: '2-digit', second: '2-digit',
        hour12: true,
        timeZone: 'Asia/Dhaka'
    });
}

    updateDateTime();
    setInterval(updateDateTime, 1000);


    // For audio sound
    const links = document.querySelectorAll('button');
    const sound = document.getElementById('click-sound');

    links.forEach(link => {
        link.addEventListener('click', function () {
            sound.currentTime = 0;
            sound.play();
        });
    });




    // for submit form
    const successSound = document.getElementById('success-sound');
    const errorSound = document.getElementById('error-sound');
    const submitBtns = document.querySelectorAll('form button');

    submitBtns.forEach(btn => {
        btn.addEventListener('click', function (e) {
            const form = this.closest('form');

            if (form.checkValidity()) {
                successSound.currentTime = 0;
                successSound.play();
                console.log("Success");
            } else {
                errorSound.currentTime = 0;
                errorSound.play();
                console.log("Error");
                form.reportValidity();
            }
        });
    });




    //  ===============  For Status Filter
    function setStatusFilter() {
        const select = document.getElementById('filter-status')
        if (!select) return
        const status = new URLSearchParams(window.location.search).get('status')
        if (status && select) select.value = status
    }
    setStatusFilter()



    //============   For Dropdown Open  ===========
    document.addEventListener("click", function (event) {
        const label = event.target.closest(".select-open-label");
        if (!label) return;

        const selectId = label.dataset.selectTarget;
        const select = document.getElementById(selectId);
        if (!select) return;

        select.focus();

        if (typeof select.showPicker === "function") {
            select.showPicker();
        } else {
            select.click();
        }
    });



});


// XSELLENCE ADD START: dynamic assignment/status notification popup + sidebar
(function () {
    const stack = document.getElementById('assignment-notification-stack');
    const sidebarBody = document.getElementById('notification-sidebar-body');
    const badge = document.getElementById('notification-badge');
    const blink = document.getElementById('notification-header-blink');

    if (!stack || !sidebarBody || !badge || !blink) {
        return;
    }

    const dismissedStorageKey = 'xsellenceDismissedNotificationPopups';
    const seenPopupIds = new Set();
    const dismissedPopupIds = new Set();

    try {
        const savedDismissedIds = JSON.parse(localStorage.getItem(dismissedStorageKey) || '[]');
        if (Array.isArray(savedDismissedIds)) {
            savedDismissedIds.forEach(function (notificationId) {
                if (notificationId) {
                    dismissedPopupIds.add(String(notificationId));
                }
            });
        }
    } catch (error) {}

    function persistDismissedPopupIds() {
        try {
            localStorage.setItem(dismissedStorageKey, JSON.stringify(Array.from(dismissedPopupIds)));
        } catch (error) {}
    }

    function playNotificationSound() {
        const sound = document.getElementById('success-sound') || document.getElementById('click-sound');

        if (!sound) {
            return;
        }

        sound.currentTime = 0;
        const playPromise = sound.play();

        if (playPromise && typeof playPromise.catch === 'function') {
            playPromise.catch(function () {});
        }
    }

    function callJsonRoute(url, params) {
        return fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'call',
                params: params || {},
            }),
        }).then(function (response) {
            return response.json();
        }).then(function (data) {
            return data.result || {};
        });
    }

    function formatRelativeTime(dateValue) {
        if (!dateValue) {
            return 'JUST NOW';
        }

        // Odoo returns naive UTC datetimes, so force UTC parsing before
        // comparing with the browser's local time (Bangladesh timezone here).
        const normalizedDateValue = /z$|[+-]\d{2}:\d{2}$/i.test(dateValue)
            ? dateValue
            : dateValue.replace(' ', 'T') + 'Z';
        const createdAt = new Date(normalizedDateValue);
        if (Number.isNaN(createdAt.getTime())) {
            return 'JUST NOW';
        }

        const diffSeconds = Math.max(0, Math.floor((Date.now() - createdAt.getTime()) / 1000));
        if (diffSeconds < 60) {
            return 'JUST NOW';
        }

        const diffMinutes = Math.floor(diffSeconds / 60);
        if (diffMinutes < 60) {
            return diffMinutes + ' MIN AGO';
        }

        const diffHours = Math.floor(diffMinutes / 60);
        if (diffHours < 24) {
            return diffHours + ' HR AGO';
        }

        const diffDays = Math.floor(diffHours / 24);
        return diffDays + ' DAY AGO';
    }

    function getNotificationIcon(notification) {
        const title = (notification.title || '').toLowerCase();
        const model = notification.res_model || '';

        if (model === 'project.project' || title.indexOf('project') !== -1) {
            return '&#128193;';
        }

        if (model === 'project.task' || title.indexOf('task') !== -1) {
            return '&#128451;&#65039;';
        }

        return '&#128276;';
    }

    function formatSidebarDescription(notification) {
        const description = notification.desc || notification.title || 'New notification';
        let match = null;

        if (notification.res_model === 'project.project') {
            match = description.match(/^You have been added to (.+) project\.$/);
            if (match) {
                return 'You have been added to <span class="s3-name">' + match[1] + '</span> project.';
            }

            match = description.match(/^(.+) added you to (.+) project\.$/);
            if (match) {
                return match[1] + ' added you to <span class="s3-name">' + match[2] + '</span> project.';
            }

            match = description.match(/^(.+) removed you from (.+) project\.$/);
            if (match) {
                return match[1] + ' removed you from <span class="s3-name">' + match[2] + '</span> project.';
            }

            match = description.match(/^(.+) project status changed to (.+)\.$/);
            if (match) {
                return '<span class="s3-name">' + match[1] + '</span> project status changed to ' + match[2] + '.';
            }

            match = description.match(/^(.+) commented on (.+) project: (.+)$/);
            if (match) {
                return match[1] + ' commented on <span class="s3-name">' + match[2] + '</span> project: ' + match[3];
            }
        }

        if (notification.res_model === 'project.task') {
            match = description.match(/^You have been added to (.+) task\.$/);
            if (match) {
                return 'You have been added to <span class="s3-name">' + match[1] + '</span> task.';
            }

            match = description.match(/^(.+) added you to (.+) task\.$/);
            if (match) {
                return match[1] + ' added you to <span class="s3-name">' + match[2] + '</span> task.';
            }

            match = description.match(/^(.+) removed you from (.+) task\.$/);
            if (match) {
                return match[1] + ' removed you from <span class="s3-name">' + match[2] + '</span> task.';
            }

            match = description.match(/^(.+) task status changed to (.+)\.$/);
            if (match) {
                return '<span class="s3-name">' + match[1] + '</span> task status changed to ' + match[2] + '.';
            }

            match = description.match(/^(.+) commented on (.+) task: (.+)$/);
            if (match) {
                return match[1] + ' commented on <span class="s3-name">' + match[2] + '</span> task: ' + match[3];
            }
        }

        return description;
    }

    function formatPopupDescription(notification) {
        return formatSidebarDescription(notification).replaceAll(
            '<span class="s3-name">',
            '<strong>'
        ).replaceAll(
            '</span>',
            '</strong>'
        );
    }

    function buildPopup(notification) {
        const popup = document.createElement('div');
        const content = document.createElement('div');
        const title = document.createElement('h4');
        const desc = document.createElement('p');
        const actions = document.createElement('div');
        const closeBtn = document.createElement('button');
        const viewBtn = document.createElement('button');

        popup.className = 'assignment-notification-popup';
        popup.dataset.notificationId = notification.id;
        popup.dataset.viewUrl = notification.view_url || '/dashboard';

        content.className = 'assignment-notification-content';
        title.textContent = notification.title || 'New Assignment';
        desc.innerHTML = formatPopupDescription(notification);

        actions.className = 'assignment-notification-actions';

        closeBtn.type = 'button';
        closeBtn.className = 'assignment-notification-close';
        closeBtn.textContent = 'Close';

        viewBtn.type = 'button';
        viewBtn.className = 'assignment-notification-view';
        viewBtn.textContent = 'View';

        actions.appendChild(closeBtn);
        actions.appendChild(viewBtn);
        content.appendChild(title);
        content.appendChild(desc);
        content.appendChild(actions);
        popup.appendChild(content);

        return popup;
    }

    function buildSidebarItem(notification) {
        const item = document.createElement('a');
        const icon = document.createElement('div');
        const textWrap = document.createElement('div');
        const desc = document.createElement('p');
        const time = document.createElement('small');

        item.href = notification.view_url || '/dashboard';
        item.className = notification.is_read ? 's3-item' : 's3-item new';
        item.dataset.notificationId = notification.id;
        item.dataset.viewUrl = notification.view_url || '/dashboard';

        icon.className = 's3-icon';
        icon.innerHTML = getNotificationIcon(notification);

        textWrap.className = 's3-text';
        desc.innerHTML = formatSidebarDescription(notification);
        time.textContent = formatRelativeTime(notification.create_date);

        textWrap.appendChild(desc);
        textWrap.appendChild(time);
        item.appendChild(icon);
        item.appendChild(textWrap);

        return item;
    }

    function renderEmptyState() {
        sidebarBody.innerHTML = '';

        const empty = document.createElement('div');
        const emptyIcon = document.createElement('div');
        const emptyTitle = document.createElement('p');
        const emptyText = document.createElement('small');

        empty.className = 's3-empty';
        empty.id = 'notification-empty-state';
        emptyIcon.className = 's3-empty-icon';
        emptyIcon.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
                <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
            </svg>
        `;
        emptyTitle.textContent = 'No notifications yet';
        emptyText.textContent = "You're all caught up!";

        empty.appendChild(emptyIcon);
        empty.appendChild(emptyTitle);
        empty.appendChild(emptyText);
        sidebarBody.appendChild(empty);
    }

    function updateUnreadState(unreadCount) {
        const safeUnreadCount = Math.max(0, Number(unreadCount) || 0);

        badge.textContent = String(safeUnreadCount);
        badge.style.display = 'inline-flex';
        blink.style.display = safeUnreadCount ? 'inline-block' : 'none';
    }

    function showPopup(popup) {
        if (!popup) {
            return;
        }

        popup.classList.remove('is-hidden');
        popup.classList.add('is-visible');
    }

    function hidePopup(popup) {
        if (!popup) {
            return;
        }

        popup.classList.remove('is-visible');
        popup.classList.add('is-hidden');
    }

    function markNotificationRead(notificationId) {
        if (!notificationId) {
            return Promise.resolve();
        }

        dismissedPopupIds.delete(String(notificationId));
        persistDismissedPopupIds();

        return callJsonRoute('/assignment/notifications/read', {
            notification_id: notificationId,
        }).catch(function () {});
    }

    function applyReadState(notificationId) {
        const sidebarItem = sidebarBody.querySelector('[data-notification-id="' + notificationId + '"]');

        if (sidebarItem) {
            sidebarItem.classList.remove('new');
        }

        const currentUnreadCount = Math.max(0, Number(badge.textContent) || 0);
        updateUnreadState(currentUnreadCount - 1);
    }

    function renderSidebar(notifications) {
        sidebarBody.innerHTML = '';

        if (!notifications.length) {
            renderEmptyState();
            return;
        }

        notifications.forEach(function (notification) {
            sidebarBody.appendChild(buildSidebarItem(notification));
        });
    }

    function syncPopups(notifications) {
        let newPopupCount = 0;

        notifications.forEach(function (notification) {
            if (
                notification.is_read ||
                seenPopupIds.has(notification.id) ||
                dismissedPopupIds.has(String(notification.id))
            ) {
                return;
            }

            const popup = buildPopup(notification);
            stack.appendChild(popup);
            seenPopupIds.add(notification.id);
            requestAnimationFrame(function () {
                showPopup(popup);
            });
            newPopupCount += 1;
        });

        if (newPopupCount) {
            playNotificationSound();
        }
    }

    function loadNotifications() {
        callJsonRoute('/assignment/notifications').then(function (result) {
            const notifications = Array.isArray(result.notifications) ? result.notifications : [];

            renderSidebar(notifications);
            updateUnreadState(result.unread_count || 0);
            syncPopups(notifications);
        }).catch(function () {});
    }

    stack.addEventListener('click', function (event) {
        const closeBtn = event.target.closest('.assignment-notification-close');
        const viewBtn = event.target.closest('.assignment-notification-view');

        if (closeBtn) {
            const popup = closeBtn.closest('.assignment-notification-popup');
            const notificationId = popup ? popup.dataset.notificationId : null;

            hidePopup(popup);
            if (notificationId) {
                dismissedPopupIds.add(String(notificationId));
                persistDismissedPopupIds();
            }
            return;
        }

        if (viewBtn) {
            const popup = viewBtn.closest('.assignment-notification-popup');
            const notificationId = popup ? popup.dataset.notificationId : null;
            const viewUrl = popup ? popup.dataset.viewUrl : '/dashboard';

            hidePopup(popup);
            markNotificationRead(notificationId).finally(function () {
                applyReadState(notificationId);
                window.location.href = viewUrl || '/dashboard';
            });
        }
    });

    sidebarBody.addEventListener('click', function (event) {
        const notificationItem = event.target.closest('.s3-item');

        if (!notificationItem) {
            return;
        }

        event.preventDefault();

        const notificationId = notificationItem.dataset.notificationId;
        const viewUrl = notificationItem.dataset.viewUrl || notificationItem.getAttribute('href') || '/dashboard';

        markNotificationRead(notificationId).finally(function () {
            applyReadState(notificationId);
            window.location.href = viewUrl;
        });
    });

    loadNotifications();
    window.setInterval(loadNotifications, 30000);
})();
// XSELLENCE ADD END: dynamic assignment/status notification popup + sidebar



// Dashboard dark theme toggle
(function () {
    const themeToggle = document.getElementById('themeToggle');
    const savedTheme = localStorage.getItem('dashboardTheme');

    if (savedTheme === 'dark') {
        document.body.classList.add('dark-theme');
    }

    window.toggleTheme = function () {
        document.body.classList.toggle('dark-theme');

        const activeTheme = document.body.classList.contains('dark-theme') ? 'dark' : 'light';
        localStorage.setItem('dashboardTheme', activeTheme);
    };

    if (themeToggle) {
        themeToggle.setAttribute('title', 'Theme');
        themeToggle.setAttribute('aria-label', 'Toggle dark theme');
        themeToggle.addEventListener('click', window.toggleTheme);
    }
})();
