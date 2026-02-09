const CalendarMonth = {
    _year: 0,
    _month: 0,

    init(params) {
        const today = DateUtils.today();
        this._year = today.getFullYear();
        this._month = today.getMonth();

        document.getElementById('month-prev').addEventListener('click', () => this._navigate(-1));
        document.getElementById('month-next').addEventListener('click', () => this._navigate(1));
        document.getElementById('month-today').addEventListener('click', () => {
            this._year = today.getFullYear();
            this._month = today.getMonth();
            App.render();
        });
    },

    _navigate(delta) {
        this._month += delta;
        if (this._month > 11) { this._month = 0; this._year++; }
        if (this._month < 0) { this._month = 11; this._year--; }
        App.render();
    },

    render(events) {
        document.getElementById('month-title').textContent =
            DateUtils.formatMonthYear(this._year, this._month);

        const body = document.getElementById('month-grid-body');
        body.innerHTML = '';

        const today = DateUtils.today();
        const days = this._buildDayGrid();

        // Group into weeks (arrays of 7)
        const weeks = [];
        for (let i = 0; i < days.length; i += 7) {
            weeks.push(days.slice(i, i + 7));
        }

        weeks.forEach(week => {
            body.appendChild(this._buildWeekRow(week, events, today));
        });
    },

    _buildDayGrid() {
        const daysInMonth = DateUtils.daysInMonth(this._year, this._month);
        const firstDay = DateUtils.firstDayOfWeek(this._year, this._month);
        const days = [];

        // Previous month trailing days
        const prevMonth = this._month === 0 ? 11 : this._month - 1;
        const prevYear = this._month === 0 ? this._year - 1 : this._year;
        const prevDays = DateUtils.daysInMonth(prevYear, prevMonth);

        for (let i = firstDay - 1; i >= 0; i--) {
            days.push({ year: prevYear, month: prevMonth, day: prevDays - i, outside: true });
        }

        // Current month days
        for (let d = 1; d <= daysInMonth; d++) {
            days.push({ year: this._year, month: this._month, day: d, outside: false });
        }

        // Next month fill
        const totalCells = firstDay + daysInMonth;
        const rows = Math.ceil(totalCells / 7);
        const remaining = rows * 7 - totalCells;
        const nextMonth = this._month === 11 ? 0 : this._month + 1;
        const nextYear = this._month === 11 ? this._year + 1 : this._year;

        for (let d = 1; d <= remaining; d++) {
            days.push({ year: nextYear, month: nextMonth, day: d, outside: true });
        }

        return days;
    },

    _dateKey(y, m, d) {
        return `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    },

    _buildWeekRow(week, events, today) {
        const weekRow = document.createElement('div');
        weekRow.className = 'week-row';

        const weekStartKey = this._dateKey(week[0].year, week[0].month, week[0].day);
        const weekEndKey = this._dateKey(week[6].year, week[6].month, week[6].day);

        // Day number cells (grid-row: 1)
        week.forEach((dayInfo, col) => {
            const dayCell = document.createElement('div');
            dayCell.className = 'week-row__day';
            if (dayInfo.outside) dayCell.classList.add('week-row__day--outside');
            if (col === 6) dayCell.classList.add('week-row__day--last');

            const cellDate = new Date(dayInfo.year, dayInfo.month, dayInfo.day);
            if (DateUtils.isSameDay(cellDate, today)) {
                dayCell.classList.add('week-row__day--today');
            }

            dayCell.style.gridColumn = String(col + 1);
            dayCell.style.gridRow = '1';

            const numEl = document.createElement('span');
            numEl.className = 'week-row__day-number';
            numEl.textContent = dayInfo.day;
            dayCell.appendChild(numEl);

            weekRow.appendChild(dayCell);
        });

        // Find events overlapping this week
        const segments = [];
        events.forEach(e => {
            const eStartKey = e.dates.start;
            const eEndKey = e.dates.end;

            // Check overlap: event overlaps week if eStart <= weekEnd AND eEnd >= weekStart
            if (eStartKey > weekEndKey || eEndKey < weekStartKey) return;

            let startCol = 1;
            let endCol = 8;
            let contLeft = false;
            let contRight = false;

            if (eStartKey >= weekStartKey) {
                for (let c = 0; c < 7; c++) {
                    if (this._dateKey(week[c].year, week[c].month, week[c].day) === eStartKey) {
                        startCol = c + 1;
                        break;
                    }
                }
            } else {
                contLeft = true;
            }

            if (eEndKey <= weekEndKey) {
                for (let c = 0; c < 7; c++) {
                    if (this._dateKey(week[c].year, week[c].month, week[c].day) === eEndKey) {
                        endCol = c + 2; // grid-column end is exclusive
                        break;
                    }
                }
            } else {
                contRight = true;
            }

            segments.push({ event: e, startCol, endCol, contLeft, contRight });
        });

        // Sort: earlier start first, then longer events first (for stable lane layout)
        segments.sort((a, b) => {
            if (a.startCol !== b.startCol) return a.startCol - b.startCol;
            return (b.endCol - b.startCol) - (a.endCol - a.startCol);
        });

        // Allocate lanes (greedy: first available row without overlap)
        const lanes = [];
        segments.forEach(seg => {
            let laneIdx = -1;
            for (let i = 0; i < lanes.length; i++) {
                const conflict = lanes[i].some(
                    other => !(seg.endCol <= other.startCol || seg.startCol >= other.endCol)
                );
                if (!conflict) { laneIdx = i; break; }
            }
            if (laneIdx === -1) {
                laneIdx = lanes.length;
                lanes.push([]);
            }
            lanes[laneIdx].push(seg);
            seg.lane = laneIdx;
        });

        // Render event banners
        segments.forEach(seg => {
            const banner = document.createElement('div');
            banner.className = 'event-banner';
            if (seg.event.status === 'canceled') banner.classList.add('event-banner--canceled');
            if (seg.event.pcss_confirmed) banner.classList.add('event-banner--pcss');
            if (seg.contLeft) banner.classList.add('event-banner--cont-left');
            if (seg.contRight) banner.classList.add('event-banner--cont-right');

            // Color based on first discipline
            const disc = (seg.event.disciplines || [])[0];
            if (disc) {
                banner.classList.add(`event-banner--${disc.toLowerCase()}`);
            }

            banner.style.gridColumn = `${seg.startCol} / ${seg.endCol}`;
            banner.style.gridRow = String(seg.lane + 2); // row 1 = day numbers

            // Discipline badges
            (seg.event.disciplines || []).forEach(d => {
                const b = document.createElement('span');
                b.className = `event-banner__disc badge--${d.toLowerCase()}`;
                b.textContent = d;
                banner.appendChild(b);
            });

            // Event name
            const nameSpan = document.createElement('span');
            nameSpan.className = 'event-banner__name';
            nameSpan.textContent = seg.event.name;
            banner.appendChild(nameSpan);

            banner.title = `${seg.event.name}\n${seg.event.venue} \u2014 ${seg.event.dates.display}`;
            banner.addEventListener('click', ev => {
                ev.stopPropagation();
                EventModal.open(seg.event);
            });

            weekRow.appendChild(banner);
        });

        return weekRow;
    }
};
