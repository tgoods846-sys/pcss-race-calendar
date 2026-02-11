const Filters = {
    _state: {
        disciplines: new Set(),
        circuits: new Set(),
        ageGroups: new Set(),
        pcssOnly: false,
        hidePast: false,
    },
    _onChangeCallback: null,

    init(allEvents, urlParams, onChange) {
        this._onChangeCallback = onChange;
        this._buildChips(allEvents);

        // Apply URL presets
        if (urlParams.discipline.length) {
            urlParams.discipline.forEach(d => this._state.disciplines.add(d.toUpperCase()));
        }
        if (urlParams.circuit.length) {
            urlParams.circuit.forEach(c => this._state.circuits.add(c));
        }
        if (urlParams.age.length) {
            urlParams.age.forEach(a => this._state.ageGroups.add(a.toUpperCase()));
        }
        if (urlParams.pcss) {
            this._state.pcssOnly = true;
        }
        if (urlParams.past) {
            this._state.hidePast = false;
        }

        this._syncChipUI();
    },

    _buildChips(allEvents) {
        const container = document.getElementById('filter-chips');
        if (!container) return;

        // Collect unique values from data
        const disciplines = new Set();
        const circuits = new Set();
        const ageGroups = new Set();

        allEvents.forEach(e => {
            (e.disciplines || []).forEach(d => disciplines.add(d));
            if (e.circuit) circuits.add(e.circuit);
            (e.age_groups || []).forEach(a => ageGroups.add(a));
        });

        let html = '';

        // Discipline chips
        const discOrder = ['SL', 'GS', 'SG', 'DH', 'PS', 'K', 'AC'];
        const discPresent = discOrder.filter(d => disciplines.has(d));
        if (discPresent.length) {
            html += '<div class="filter-group">';
            html += '<span class="filter-group__label">Disc</span>';
            discPresent.forEach(d => {
                html += `<button class="filter-chip filter-chip--${d.toLowerCase()}" data-filter="discipline" data-value="${d}">${d}</button>`;
            });
            html += '</div>';
            html += '<div class="filter-divider"></div>';
        }

        // Circuit chips
        const circuitOrder = ['IMD', 'Western Region', 'USSA', 'FIS'];
        const circPresent = circuitOrder.filter(c => circuits.has(c));
        if (circPresent.length) {
            html += '<div class="filter-group">';
            html += '<span class="filter-group__label">Circuit</span>';
            circPresent.forEach(c => {
                const cssClass = c.toLowerCase().replace(/\s+/g, '-');
                const label = c === 'Western Region' ? 'WR' : c;
                html += `<button class="filter-chip filter-chip--circuit-${cssClass}" data-filter="circuit" data-value="${c}">${label}</button>`;
            });
            html += '</div>';
            html += '<div class="filter-divider"></div>';
        }

        // Age group chips
        const ageOrder = ['U10', 'U12', 'U14', 'U16', 'U18', 'U19', 'U21'];
        const agePresent = ageOrder.filter(a => ageGroups.has(a));
        if (agePresent.length) {
            html += '<div class="filter-group">';
            html += '<span class="filter-group__label">Age</span>';
            agePresent.forEach(a => {
                html += `<button class="filter-chip filter-chip--age" data-filter="age" data-value="${a}">${a}</button>`;
            });
            html += '</div>';
        }

        // PCSS Confirmed toggle
        const hasPcss = allEvents.some(e => e.pcss_confirmed);
        if (hasPcss) {
            html += '<div class="filter-divider"></div>';
            html += `<button class="filter-chip filter-chip--pcss" data-filter="pcss" data-value="true">PCSS</button>`;
        }

        // Upcoming toggle (hide past events)
        html += '<div class="filter-divider"></div>';
        html += `<button class="filter-chip filter-chip--past" data-filter="past" data-value="true">Upcoming Only</button>`;

        container.innerHTML = html;

        // Bind click handlers
        container.querySelectorAll('.filter-chip').forEach(chip => {
            chip.addEventListener('click', () => this._toggleChip(chip));
        });
    },

    _toggleChip(chip) {
        const filter = chip.dataset.filter;
        const value = chip.dataset.value;

        if (filter === 'past') {
            this._state.hidePast = !this._state.hidePast;
        } else if (filter === 'pcss') {
            this._state.pcssOnly = !this._state.pcssOnly;
        } else if (filter === 'discipline') {
            this._state.disciplines.has(value)
                ? this._state.disciplines.delete(value)
                : this._state.disciplines.add(value);
        } else if (filter === 'circuit') {
            this._state.circuits.has(value)
                ? this._state.circuits.delete(value)
                : this._state.circuits.add(value);
        } else if (filter === 'age') {
            this._state.ageGroups.has(value)
                ? this._state.ageGroups.delete(value)
                : this._state.ageGroups.add(value);
        }

        this._syncChipUI();
        if (this._onChangeCallback) this._onChangeCallback();
    },

    _syncChipUI() {
        const container = document.getElementById('filter-chips');
        if (!container) return;

        container.querySelectorAll('.filter-chip').forEach(chip => {
            const filter = chip.dataset.filter;
            const value = chip.dataset.value;
            let isActive = false;

            if (filter === 'past') isActive = this._state.hidePast;
            else if (filter === 'pcss') isActive = this._state.pcssOnly;
            else if (filter === 'discipline') isActive = this._state.disciplines.has(value);
            else if (filter === 'circuit') isActive = this._state.circuits.has(value);
            else if (filter === 'age') isActive = this._state.ageGroups.has(value);

            chip.classList.toggle('filter-chip--active', isActive);
        });

        // Show/hide clear button
        const clearBtn = document.getElementById('btn-clear-filters');
        if (clearBtn) {
            const hasFilters = this._state.hidePast ||
                this._state.pcssOnly ||
                this._state.disciplines.size > 0 ||
                this._state.circuits.size > 0 ||
                this._state.ageGroups.size > 0;
            clearBtn.classList.toggle('hidden', !hasFilters);
        }
    },

    clearAll() {
        this._state.disciplines.clear();
        this._state.circuits.clear();
        this._state.ageGroups.clear();
        this._state.pcssOnly = false;
        this._state.hidePast = false;
        this._syncChipUI();
        if (this._onChangeCallback) this._onChangeCallback();
    },

    filter(events) {
        return events.filter(e => {
            // Hide past events
            if (this._state.hidePast && e.status === 'completed') return false;

            // PCSS filter
            if (this._state.pcssOnly && !e.pcss_confirmed) return false;

            // Discipline filter (OR within group)
            if (this._state.disciplines.size > 0) {
                const eventDiscs = new Set(e.disciplines || []);
                let match = false;
                for (const d of this._state.disciplines) {
                    if (eventDiscs.has(d)) { match = true; break; }
                }
                if (!match) return false;
            }

            // Circuit filter (OR within group)
            if (this._state.circuits.size > 0) {
                if (!this._state.circuits.has(e.circuit)) return false;
            }

            // Age group filter (OR within group)
            if (this._state.ageGroups.size > 0) {
                const eventAges = new Set(e.age_groups || []);
                let match = false;
                for (const a of this._state.ageGroups) {
                    if (eventAges.has(a)) { match = true; break; }
                }
                if (!match) return false;
            }

            return true;
        });
    }
};
