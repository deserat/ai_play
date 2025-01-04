class WikiAPI {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }

    /**
     * Get a list of all wiki entries (summary view)
     * @returns {Promise<Array>} Array of entry summaries with id, title, and modified_at
     */
    async listEntries() {
        try {
            const response = await fetch(`${this.baseUrl}/wiki-entries/`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const entries = await response.json();
            return entries;
        } catch (error) {
            console.error('Error fetching wiki entries:', error);
            throw error;
        }
    }

    /**
     * Get a single wiki entry by ID (detailed view)
     * @param {number} id - The ID of the wiki entry
     * @returns {Promise<Object>} Full entry details including markdown content
     */
    async getEntry(id) {
        try {
            const response = await fetch(`${this.baseUrl}/wiki-entries/${id}`);
            if (response.status === 404) {
                throw new Error('Entry not found');
            }
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const entry = await response.json();
            return entry;
        } catch (error) {
            console.error(`Error fetching wiki entry ${id}:`, error);
            throw error;
        }
    }
}
