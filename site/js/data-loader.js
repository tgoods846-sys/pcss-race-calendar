const DataLoader = {
    async load() {
        try {
            const resp = await fetch('data/race_database.json');
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            return await resp.json();
        } catch (err) {
            console.error('Failed to load race database:', err);
            return null;
        }
    }
};
