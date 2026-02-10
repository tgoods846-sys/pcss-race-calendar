const EventModal = {
    init() {
        document.getElementById('modal-backdrop').addEventListener('click', () => this.close());
        document.getElementById('modal-close').addEventListener('click', () => this.close());
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') this.close();
        });
    },

    open(event) {
        this._currentEvent = event;
        document.getElementById('modal-body').innerHTML = this._render(event);
        document.getElementById('event-modal').classList.remove('hidden');
        document.getElementById('modal-backdrop').classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    },

    close() {
        document.getElementById('event-modal').classList.add('hidden');
        document.getElementById('modal-backdrop').classList.add('hidden');
        document.body.style.overflow = '';
    },

    _render(event) {
        const statusColors = {
            upcoming: 'var(--color-status-upcoming)',
            in_progress: 'var(--color-status-inprogress)',
            completed: 'var(--color-status-completed)',
            canceled: 'var(--color-status-canceled)',
        };
        const statusLabels = {
            upcoming: 'Upcoming',
            in_progress: 'In Progress',
            completed: 'Completed',
            canceled: 'Canceled',
        };

        let html = '';

        // Status badge
        const statusColor = statusColors[event.status] || statusColors.upcoming;
        const statusLabel = statusLabels[event.status] || 'Upcoming';
        html += `<span class="modal__status-badge" style="background:${statusColor}">${this._esc(statusLabel)}</span>`;
        if (event.pcss_confirmed) {
            html += ` <span class="modal__status-badge" style="background:var(--color-pcss)">PCSS Confirmed</span>`;
        }

        // Name
        html += `<h2 class="modal__name">${this._esc(event.name)}</h2>`;

        // Metadata grid
        html += '<div class="modal__meta">';

        html += `<span class="modal__meta-label">Dates</span>
                 <span>${this._esc(event.dates.display)}</span>`;

        const countdownText = DateUtils.getCountdownText(event.dates.start, event.dates.end, event.status);
        if (countdownText) {
            html += `<span class="modal__meta-label"></span>
                     <span class="event-card__countdown">${this._esc(countdownText)}</span>`;
        }

        if (event.venue) {
            html += `<span class="modal__meta-label">Venue</span>
                     <span>${this._esc(event.venue)}${event.state ? ', ' + this._esc(event.state) : ''}</span>`;
        }

        if (event.disciplines && event.disciplines.length > 0) {
            const discBadges = event.disciplines.map(d =>
                `<span class="badge badge--${d.toLowerCase()}">${d}</span>`
            ).join(' ');
            let countInfo = '';
            if (event.discipline_counts) {
                const parts = Object.entries(event.discipline_counts)
                    .map(([k, v]) => `${v}x ${k}`);
                if (parts.length) countInfo = ` <small style="color:var(--color-text-secondary)">(${parts.join(', ')})</small>`;
            }
            html += `<span class="modal__meta-label">Disciplines</span>
                     <span>${discBadges}${countInfo}</span>`;
        }

        html += `<span class="modal__meta-label">Circuit</span>
                 <span><span class="badge badge--circuit">${this._esc(event.circuit)}</span>
                 ${event.series && event.series !== event.circuit ? ' <small>' + this._esc(event.series) + '</small>' : ''}</span>`;

        if (event.age_groups && event.age_groups.length > 0) {
            const ageBadges = event.age_groups.map(a =>
                `<span class="badge badge--age">${a}</span>`
            ).join(' ');
            html += `<span class="modal__meta-label">Age Groups</span>
                     <span>${ageBadges}</span>`;
        }

        if (event.td_name) {
            html += `<span class="modal__meta-label">TD</span>
                     <span>${this._esc(event.td_name)}</span>`;
        }

        html += '</div>';

        // Description
        if (event.description && event.description.trim()) {
            html += `<div class="modal__description">${this._esc(event.description)}</div>`;
        }

        // Action buttons (always rendered — calendar buttons are always available)
        html += '<div class="modal__actions">';
        if (event.source_url) {
            html += `<a href="${this._esc(event.source_url)}" target="_blank" rel="noopener"
                        class="modal__action-btn modal__action-btn--primary">View on IMD</a>`;
        }
        if (event.blog_recap_url) {
            html += `<a href="${this._esc(event.blog_recap_url)}" target="_blank" rel="noopener"
                        class="modal__action-btn modal__action-btn--secondary">View Recap</a>`;
        }
        if (event.results_url) {
            html += `<a href="${this._esc(event.results_url)}" target="_blank" rel="noopener"
                        class="modal__action-btn modal__action-btn--secondary">View Results</a>`;
        }
        // Calendar export buttons
        const calIcon = '<svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" style="vertical-align:-2px;margin-right:4px"><rect x="2" y="3" width="12" height="11" rx="1.5"/><line x1="2" y1="6.5" x2="14" y2="6.5"/><line x1="5.5" y1="1.5" x2="5.5" y2="4.5"/><line x1="10.5" y1="1.5" x2="10.5" y2="4.5"/></svg>';
        html += `<a href="${this._esc(CalendarExport.googleCalendarUrl(event))}" target="_blank" rel="noopener"
                    class="modal__action-btn modal__action-btn--secondary">${calIcon}Google Cal</a>`;
        html += `<button onclick="CalendarExport.downloadIcs(EventModal._currentEvent)"
                    class="modal__action-btn modal__action-btn--secondary">${calIcon}Download .ics</button>`;
        html += '</div>';

        return html;
    },

    _esc(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
};
