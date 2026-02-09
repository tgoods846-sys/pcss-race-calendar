const CalendarList = {
    render(events) {
        const container = document.getElementById('list-container');
        container.innerHTML = '';

        if (events.length === 0) return;

        // Sort by start date
        const sorted = [...events].sort((a, b) => a.dates.start.localeCompare(b.dates.start));

        // Group by month
        let currentMonthKey = '';
        sorted.forEach(event => {
            const start = DateUtils.parseISO(event.dates.start);
            const monthKey = `${start.getFullYear()}-${start.getMonth()}`;

            if (monthKey !== currentMonthKey) {
                currentMonthKey = monthKey;
                const header = document.createElement('h3');
                header.className = 'list-month-header';
                header.textContent = DateUtils.formatMonthYear(start.getFullYear(), start.getMonth());
                container.appendChild(header);
            }

            container.appendChild(this._buildCard(event));
        });
    },

    _buildCard(event) {
        const card = document.createElement('div');
        card.className = 'event-card';
        if (event.status === 'canceled') card.classList.add('event-card--canceled');

        const start = DateUtils.parseISO(event.dates.start);
        const end = DateUtils.parseISO(event.dates.end);
        const isMultiDay = !DateUtils.isSameDay(start, end);

        // Date column
        const dateCol = document.createElement('div');
        dateCol.className = 'event-card__date';

        let dateHTML = `
            <div class="event-card__date-month">${DateUtils.MONTH_SHORT[start.getMonth()]}</div>
            <div class="event-card__date-day">${start.getDate()}</div>`;

        if (isMultiDay) {
            dateHTML += `<div class="event-card__date-range">\u2013 ${DateUtils.MONTH_SHORT[end.getMonth()]} ${end.getDate()}</div>`;
        }

        dateCol.innerHTML = dateHTML;

        // Details column
        const details = document.createElement('div');
        details.className = 'event-card__details';

        const name = document.createElement('div');
        name.className = 'event-card__name';
        name.textContent = event.name;

        const venue = document.createElement('div');
        venue.className = 'event-card__venue';
        venue.textContent = [event.venue, event.state].filter(Boolean).join(', ');

        const badges = document.createElement('div');
        badges.className = 'badge-row';

        // Discipline badges
        (event.disciplines || []).forEach(d => {
            const badge = document.createElement('span');
            badge.className = `badge badge--${d.toLowerCase()}`;
            badge.textContent = d;
            badges.appendChild(badge);
        });

        // Circuit badge
        if (event.circuit) {
            const cb = document.createElement('span');
            cb.className = 'badge badge--circuit';
            cb.textContent = event.circuit === 'Western Region' ? 'WR' : event.circuit;
            badges.appendChild(cb);
        }

        // Age group badges
        (event.age_groups || []).forEach(a => {
            const ab = document.createElement('span');
            ab.className = 'badge badge--age';
            ab.textContent = a;
            badges.appendChild(ab);
        });

        // Canceled badge
        if (event.status === 'canceled') {
            const cb = document.createElement('span');
            cb.className = 'badge badge--status-canceled';
            cb.textContent = 'CANCELED';
            badges.appendChild(cb);
        }

        details.appendChild(name);
        details.appendChild(venue);
        details.appendChild(badges);

        card.appendChild(dateCol);
        card.appendChild(details);

        card.addEventListener('click', () => EventModal.open(event));
        return card;
    }
};
