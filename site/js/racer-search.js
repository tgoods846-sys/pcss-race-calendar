const RacerSearch = {
    _data: null,
    _loaded: false,
    _loading: false,
    _selectedRacer: null,
    _highlightIndex: -1,
    _onChangeCallback: null,
    _inputEl: null,
    _dropdownEl: null,
    _wrapperEl: null,

    init(onChange) {
        this._onChangeCallback = onChange;
        this._insertSearchUI();
        this._bindEvents();
    },

    initFromURL(racerKey) {
        if (!racerKey) return;
        this._loadData(() => {
            if (!this._data) return;
            const match = this._data.racers.find(r => r.key === racerKey);
            if (match) {
                this._selectedRacer = match;
                this._inputEl.value = match.name;
                this._wrapperEl.classList.add('racer-search--has-value');
                if (this._onChangeCallback) this._onChangeCallback();
            }
        });
    },

    getSelectedEventIds() {
        if (!this._selectedRacer) return null;
        return new Set(this._selectedRacer.event_ids);
    },

    clear() {
        this._selectedRacer = null;
        this._highlightIndex = -1;
        if (this._inputEl) {
            this._inputEl.value = '';
            this._wrapperEl.classList.remove('racer-search--has-value');
        }
        this._hideDropdown();
        this._updateURL('');
    },

    _insertSearchUI() {
        const filtersInner = document.querySelector('.filters-bar__inner');
        if (!filtersInner) return;

        const wrapper = document.createElement('div');
        wrapper.className = 'racer-search';
        wrapper.innerHTML =
            '<input type="text" class="racer-search__input" placeholder="Search racer..." autocomplete="off" spellcheck="false">' +
            '<button class="racer-search__clear" type="button" aria-label="Clear search">&times;</button>' +
            '<div class="racer-search__dropdown hidden"></div>';

        filtersInner.insertBefore(wrapper, filtersInner.firstChild);

        this._wrapperEl = wrapper;
        this._inputEl = wrapper.querySelector('.racer-search__input');
        this._dropdownEl = wrapper.querySelector('.racer-search__dropdown');
    },

    _bindEvents() {
        if (!this._inputEl) return;

        this._inputEl.addEventListener('input', () => this._onInput());
        this._inputEl.addEventListener('keydown', (e) => this._onKeydown(e));
        this._inputEl.addEventListener('focus', () => {
            if (this._inputEl.value.length >= 2 && !this._selectedRacer) {
                this._onInput();
            }
        });

        this._wrapperEl.querySelector('.racer-search__clear').addEventListener('click', () => {
            this.clear();
            if (this._onChangeCallback) this._onChangeCallback();
        });

        document.addEventListener('click', (e) => {
            if (!this._wrapperEl.contains(e.target)) {
                this._hideDropdown();
            }
        });
    },

    _onInput() {
        const query = this._inputEl.value.trim().toLowerCase();

        // If a racer was selected and the user edits the text, deselect
        if (this._selectedRacer) {
            this._selectedRacer = null;
            this._wrapperEl.classList.remove('racer-search--has-value');
            this._updateURL('');
            if (this._onChangeCallback) this._onChangeCallback();
        }

        if (query.length < 2) {
            this._hideDropdown();
            return;
        }

        // Lazy load data on first keystroke
        if (!this._loaded && !this._loading) {
            this._loadData(() => this._showResults(query));
            return;
        }

        if (this._loaded) {
            this._showResults(query);
        }
    },

    _onKeydown(e) {
        if (!this._dropdownEl || this._dropdownEl.classList.contains('hidden')) {
            return;
        }

        const items = this._dropdownEl.querySelectorAll('.racer-search__item');
        if (!items.length) return;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            this._highlightIndex = Math.min(this._highlightIndex + 1, items.length - 1);
            this._updateHighlight(items);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            this._highlightIndex = Math.max(this._highlightIndex - 1, 0);
            this._updateHighlight(items);
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (this._highlightIndex >= 0 && this._highlightIndex < items.length) {
                items[this._highlightIndex].click();
            }
        } else if (e.key === 'Escape') {
            this._hideDropdown();
            this._inputEl.blur();
        }
    },

    _updateHighlight(items) {
        items.forEach((item, i) => {
            item.classList.toggle('racer-search__item--highlight', i === this._highlightIndex);
        });
        // Scroll into view
        if (this._highlightIndex >= 0 && items[this._highlightIndex]) {
            items[this._highlightIndex].scrollIntoView({ block: 'nearest' });
        }
    },

    _showResults(query) {
        if (!this._data || !this._data.racers) {
            this._hideDropdown();
            return;
        }

        const matches = this._data.racers
            .filter(r => r.key.includes(query))
            .slice(0, 10);

        if (matches.length === 0) {
            this._dropdownEl.innerHTML = '<div class="racer-search__empty">No racers found</div>';
            this._dropdownEl.classList.remove('hidden');
            this._highlightIndex = -1;
            return;
        }

        this._dropdownEl.innerHTML = matches.map((r, i) =>
            '<button class="racer-search__item" data-key="' + r.key + '">' +
                '<span class="racer-search__name">' + this._escapeHtml(r.name) + '</span>' +
                '<span class="racer-search__count">' + r.event_ids.length + ' event' + (r.event_ids.length !== 1 ? 's' : '') + '</span>' +
            '</button>'
        ).join('');

        this._dropdownEl.classList.remove('hidden');
        this._highlightIndex = -1;

        // Bind click handlers
        this._dropdownEl.querySelectorAll('.racer-search__item').forEach(item => {
            item.addEventListener('click', () => {
                const key = item.dataset.key;
                const racer = this._data.racers.find(r => r.key === key);
                if (racer) {
                    this._selectRacer(racer);
                }
            });
        });
    },

    _selectRacer(racer) {
        this._selectedRacer = racer;
        this._inputEl.value = racer.name;
        this._wrapperEl.classList.add('racer-search--has-value');
        this._hideDropdown();
        this._updateURL(racer.key);
        if (this._onChangeCallback) this._onChangeCallback();
    },

    _hideDropdown() {
        if (this._dropdownEl) {
            this._dropdownEl.classList.add('hidden');
        }
        this._highlightIndex = -1;
    },

    _loadData(callback) {
        this._loading = true;
        fetch('data/racer_database.json')
            .then(resp => {
                if (!resp.ok) throw new Error('Failed to load racer database');
                return resp.json();
            })
            .then(data => {
                this._data = data;
                this._loaded = true;
                this._loading = false;
                if (callback) callback();
            })
            .catch(() => {
                this._loading = false;
                this._loaded = false;
            });
    },

    _updateURL(racerKey) {
        const url = new URL(window.location);
        if (racerKey) {
            url.searchParams.set('racer', racerKey);
        } else {
            url.searchParams.delete('racer');
        }
        history.replaceState(null, '', url);
    },

    _escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
};
