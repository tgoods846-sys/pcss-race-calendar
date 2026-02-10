const DateUtils = {
    MONTH_SHORT: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
    MONTH_LONG: ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'],
    DAY_SHORT: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],

    parseISO(str) {
        const [y, m, d] = str.split('-').map(Number);
        return new Date(y, m - 1, d);
    },

    formatMonthYear(year, month) {
        return `${this.MONTH_LONG[month]} ${year}`;
    },

    today() {
        const now = new Date();
        return new Date(now.getFullYear(), now.getMonth(), now.getDate());
    },

    isSameDay(a, b) {
        return a.getFullYear() === b.getFullYear() &&
               a.getMonth() === b.getMonth() &&
               a.getDate() === b.getDate();
    },

    daysInMonth(year, month) {
        return new Date(year, month + 1, 0).getDate();
    },

    firstDayOfWeek(year, month) {
        return new Date(year, month, 1).getDay();
    },

    getCountdownText(startISO, endISO, status) {
        if (status === 'completed' || status === 'canceled') return '';
        const today = this.today();
        const start = this.parseISO(startISO);
        const end = this.parseISO(endISO);
        if (today >= start && today <= end) return 'Happening now';
        if (this.isSameDay(today, start)) return 'Starting today';
        const msPerDay = 86400000;
        const daysAway = Math.round((start - today) / msPerDay);
        if (daysAway < 0) return '';
        if (daysAway === 1) return 'Tomorrow';
        if (daysAway <= 6) return `In ${daysAway} days`;
        if (daysAway <= 13) return 'In 1 week';
        if (daysAway <= 27) return `In ${Math.floor(daysAway / 7)} weeks`;
        return '';
    },

    getUrgencyLevel(startISO, endISO, status) {
        if (status === 'completed' || status === 'canceled') return null;
        const today = this.today();
        const start = this.parseISO(startISO);
        const end = this.parseISO(endISO);
        if (today > end) return null;
        const msPerDay = 86400000;
        const daysAway = Math.round((start - today) / msPerDay);
        if (status === 'in_progress' || daysAway <= 0) return { level: 'race-day', label: 'RACE DAY' };
        if (daysAway === 1) return { level: 'tomorrow', label: 'TOMORROW' };
        if (daysAway <= 6) return { level: 'this-week', label: 'THIS WEEK' };
        if (daysAway <= 13) return { level: 'next-week', label: 'NEXT WEEK' };
        return null;
    }
};
