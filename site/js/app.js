const App = {
    _allEvents: [],
    _currentView: 'month',

    async init() {
        const params = URLParams.parse();

        // Embed mode
        if (params.embed) {
            document.body.classList.add('embed-mode');
        }

        // Load data
        const data = await DataLoader.load();
        if (!data || !data.events) {
            document.getElementById('loading-state').innerHTML =
                '<p style="color:var(--color-status-canceled)">Failed to load race data.</p>';
            return;
        }

        this._allEvents = data.events;
        this._currentView = params.view || 'month';

        // Update metadata
        const genEl = document.getElementById('data-generated');
        if (genEl && data.generated_at) {
            const d = new Date(data.generated_at);
            genEl.textContent = `Updated ${d.toLocaleDateString()}`;
        }

        // Initialize components
        Filters.init(this._allEvents, params, () => this.render());
        CalendarMonth.init(params);
        EventModal.init();

        // Subscribe button
        const subBtn = document.getElementById('btn-subscribe');
        if (subBtn) {
            subBtn.addEventListener('click', () => this.openSubscribeModal());
        }

        // View toggle buttons
        document.getElementById('btn-month').addEventListener('click', () => this.switchView('month'));
        document.getElementById('btn-list').addEventListener('click', () => this.switchView('list'));

        // Clear filters button
        const clearBtn = document.getElementById('btn-clear-filters');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => Filters.clearAll());
        }

        // Set initial view
        this.switchView(this._currentView);

        // Initial render
        this.render();

        // Hide loading, show app
        document.getElementById('loading-state').classList.add('hidden');
        document.getElementById('app-content').classList.remove('hidden');
    },

    render() {
        const filtered = Filters.filter(this._allEvents);

        CalendarMonth.render(filtered);
        CalendarList.render(filtered);

        // Update event count
        const countEl = document.getElementById('event-count');
        if (countEl) {
            countEl.textContent = `${filtered.length} event${filtered.length !== 1 ? 's' : ''}`;
        }

        // Show/hide empty state
        const emptyState = document.getElementById('empty-state');
        const monthView = document.getElementById('month-view');
        const listView = document.getElementById('list-view');

        if (filtered.length === 0) {
            emptyState.classList.remove('hidden');
            monthView.classList.add('hidden');
            listView.classList.add('hidden');
        } else {
            emptyState.classList.add('hidden');
            if (this._currentView === 'month') {
                monthView.classList.remove('hidden');
                listView.classList.add('hidden');
            } else {
                monthView.classList.add('hidden');
                listView.classList.remove('hidden');
            }
        }
    },

    openSubscribeModal() {
        const feedUrl = window.location.origin + '/pcss-calendar.ics';
        const webcalUrl = feedUrl.replace(/^https?:/, 'webcal:');
        const googleUrl = 'https://calendar.google.com/calendar/r?cid=' + encodeURIComponent(feedUrl);

        const calIcon = '<svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="3" width="12" height="11" rx="1.5"/><line x1="2" y1="6.5" x2="14" y2="6.5"/><line x1="5.5" y1="1.5" x2="5.5" y2="4.5"/><line x1="10.5" y1="1.5" x2="10.5" y2="4.5"/></svg>';
        const linkIcon = '<svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M6.5 8.5a3 3 0 004 .5l2-2a3 3 0 00-4.24-4.24l-1.14 1.14"/><path d="M9.5 7.5a3 3 0 00-4-.5l-2 2a3 3 0 004.24 4.24l1.14-1.14"/></svg>';

        const html = `
            <h2 class="modal__name">Subscribe to Calendar</h2>
            <p style="font-size:0.85rem;color:var(--color-text-secondary);margin-bottom:var(--space-md)">
                Subscribe once and your calendar updates automatically as races are added or changed.
            </p>
            <div class="subscribe-options">
                <a href="${googleUrl}" target="_blank" rel="noopener" class="subscribe-option">
                    <div class="subscribe-option__icon">G</div>
                    <div class="subscribe-option__text">
                        <div class="subscribe-option__title">Google Calendar</div>
                        <div class="subscribe-option__desc">Subscribe in your Google Calendar</div>
                    </div>
                </a>
                <a href="${webcalUrl}" class="subscribe-option">
                    <div class="subscribe-option__icon">${calIcon}</div>
                    <div class="subscribe-option__text">
                        <div class="subscribe-option__title">Apple Calendar / Outlook</div>
                        <div class="subscribe-option__desc">Opens your default calendar app</div>
                    </div>
                </a>
                <button class="subscribe-option" onclick="App._copyFeedUrl('${feedUrl}', this)">
                    <div class="subscribe-option__icon">${linkIcon}</div>
                    <div class="subscribe-option__text">
                        <div class="subscribe-option__title">Copy Feed URL</div>
                        <div class="subscribe-option__desc" id="copy-feed-desc">Paste into any calendar app's "Add by URL"</div>
                    </div>
                </button>
            </div>`;

        document.getElementById('modal-body').innerHTML = html;
        document.getElementById('event-modal').classList.remove('hidden');
        document.getElementById('modal-backdrop').classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    },

    _copyFeedUrl(url, btn) {
        navigator.clipboard.writeText(url).then(() => {
            const desc = btn.querySelector('#copy-feed-desc');
            if (desc) {
                desc.innerHTML = '<span class="subscribe-copied">Copied to clipboard!</span>';
                setTimeout(() => { desc.textContent = 'Paste into any calendar app\'s "Add by URL"'; }, 2000);
            }
        });
    },

    switchView(view) {
        this._currentView = view;
        document.getElementById('btn-month').classList.toggle('view-btn--active', view === 'month');
        document.getElementById('btn-list').classList.toggle('view-btn--active', view === 'list');
        this.render();
        if (view === 'list') {
            CalendarList.scrollToToday();
        }
    }
};

document.addEventListener('DOMContentLoaded', () => App.init());
