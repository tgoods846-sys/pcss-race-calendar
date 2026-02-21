const URLParams = {
    parse() {
        const params = new URLSearchParams(window.location.search);
        return {
            embed: params.get('embed') === 'true',
            view: params.get('view') || 'month',
            discipline: params.get('discipline') ? params.get('discipline').split(',') : [],
            circuit: params.get('circuit') ? params.get('circuit').split(',') : [],
            age: params.get('age') ? params.get('age').split(',') : [],
            pcss: params.get('pcss') === 'true',
            past: params.get('past') === 'true',
            racer: params.get('racer') || '',
        };
    }
};
