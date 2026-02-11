const CalendarExport = {
    /**
     * Build a Google Calendar "create event" URL for an all-day race event.
     * Opens in a new tab — no API key needed.
     */
    googleCalendarUrl(event) {
        const start = event.dates.start.replace(/-/g, '');
        const end = this._addOneDay(event.dates.end).replace(/-/g, '');
        const params = new URLSearchParams({
            action: 'TEMPLATE',
            text: event.name,
            dates: `${start}/${end}`,
            details: this._buildDescription(event),
            location: this._buildLocation(event),
        });
        return `https://calendar.google.com/calendar/render?${params.toString()}`;
    },

    /**
     * Generate and trigger download of an .ics file for Apple Calendar / Outlook.
     */
    downloadIcs(event) {
        const ics = this._generateIcs(event);
        const blob = new Blob([ics], { type: 'text/calendar;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = this._sanitizeFilename(event.name) + '.ics';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    },

    /**
     * Add one day to an ISO date string "YYYY-MM-DD".
     * Needed because our end dates are inclusive but iCal/Google use exclusive DTEND.
     */
    _addOneDay(isoDate) {
        const d = new Date(isoDate + 'T00:00:00');
        d.setDate(d.getDate() + 1);
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return `${y}-${m}-${day}`;
    },

    _buildLocation(event) {
        if (!event.venue) return '';
        return event.state ? `${event.venue}, ${event.state}` : event.venue;
    },

    _buildDescription(event) {
        const parts = [];
        if (event.disciplines && event.disciplines.length) {
            parts.push('Disciplines: ' + event.disciplines.join(', '));
        }
        if (event.circuit) {
            parts.push('Circuit: ' + event.circuit);
        }
        if (event.source_url) {
            parts.push(event.source_url);
        }
        return parts.join('\n');
    },

    /**
     * Generate an RFC 5545 VCALENDAR string for an all-day event.
     */
    _generateIcs(event) {
        const start = event.dates.start.replace(/-/g, '');
        const end = this._addOneDay(event.dates.end).replace(/-/g, '');
        const now = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '');
        const uid = event.id + '@sim.sports';
        const lines = [
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//Sim.Sports//Race Calendar//EN',
            'BEGIN:VEVENT',
            `UID:${uid}`,
            `DTSTAMP:${now}`,
            `DTSTART;VALUE=DATE:${start}`,
            `DTEND;VALUE=DATE:${end}`,
            `SUMMARY:${this._escIcs(event.name)}`,
            `LOCATION:${this._escIcs(this._buildLocation(event))}`,
            `DESCRIPTION:${this._escIcs(this._buildDescription(event))}`,
            'BEGIN:VALARM',
            'TRIGGER:-P1D',
            'ACTION:DISPLAY',
            `DESCRIPTION:${this._escIcs(event.name)} starts tomorrow`,
            'END:VALARM',
            'END:VEVENT',
            'END:VCALENDAR',
        ];
        return lines.join('\r\n');
    },

    /**
     * Escape text for iCalendar per RFC 5545 §3.3.11.
     */
    _escIcs(str) {
        if (!str) return '';
        return str
            .replace(/\\/g, '\\\\')
            .replace(/;/g, '\\;')
            .replace(/,/g, '\\,')
            .replace(/\n/g, '\\n');
    },

    /**
     * Sanitize a string for use as a filename.
     */
    _sanitizeFilename(name) {
        return (name || 'event')
            .replace(/[^a-zA-Z0-9 _-]/g, '')
            .replace(/\s+/g, '_')
            .substring(0, 80);
    },
};
