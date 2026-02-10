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
