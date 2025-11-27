class ITMonitoring {
    constructor() {
        this.feeds = [];
        this.categoryMap = {};
        this.filters = this.loadFilters();
        this.readArticles = this.loadReadArticles();
        this.lastSeenIds = this.loadLastSeenIds();
        this.loading = false;
        this.newCount = 0;

        this.init();
    }

    // ==================== LocalStorage ====================

    loadFilters() {
        const saved = localStorage.getItem('itm_filters');
        if (saved) {
            return JSON.parse(saved);
        }
        return {
            categories: [],
            types: ['announcements', 'releases']
        };
    }

    saveFilters() {
        localStorage.setItem('itm_filters', JSON.stringify(this.filters));
    }

    loadReadArticles() {
        const saved = localStorage.getItem('itm_read');
        return saved ? JSON.parse(saved) : [];
    }

    saveReadArticles() {
        const trimmed = this.readArticles.slice(-1000);
        localStorage.setItem('itm_read', JSON.stringify(trimmed));
    }

    loadLastSeenIds() {
        const saved = localStorage.getItem('itm_last_seen');
        return saved ? JSON.parse(saved) : [];
    }

    saveLastSeenIds() {
        const currentIds = this.feeds.slice(0, 100).map(f => f.id);
        localStorage.setItem('itm_last_seen', JSON.stringify(currentIds));
    }

    isArticleRead(id) {
        return this.readArticles.includes(id);
    }

    markAsRead(id) {
        if (!this.readArticles.includes(id)) {
            this.readArticles.push(id);
            this.saveReadArticles();
        }
    }

    markAllAsRead() {
        const filtered = this.getFilteredFeeds();
        filtered.forEach(f => {
            if (!this.readArticles.includes(f.id)) {
                this.readArticles.push(f.id);
            }
        });
        this.saveReadArticles();
        this.render();
        this.updateNewCount();
    }

    // ==================== Init ====================

    async init() {
        this.bindEvents();
        await this.loadInitialData();
        this.checkUrlArticle();
    }

    checkUrlArticle() {
        const params = new URLSearchParams(window.location.search);
        const articleId = params.get('article');

        if (articleId) {
            // Trouver et ouvrir l'article
            setTimeout(() => {
                const item = document.querySelector(`.feed-item[data-id="${CSS.escape(articleId)}"]`);
                if (item) {
                    // Scroll vers l'article
                    item.scrollIntoView({ behavior: 'smooth', block: 'center' });

                    // Attendre la fin du scroll puis expand
                    setTimeout(() => {
                        item.classList.add('expanded', 'read');
                        this.markAsRead(articleId);
                        item.querySelector('.tag-new')?.remove();
                        this.updateNewCount();

                        // Highlight temporaire
                        item.style.boxShadow = '0 0 0 2px var(--accent), 0 0 20px rgba(88, 166, 255, 0.4)';
                        setTimeout(() => {
                            item.style.boxShadow = '';
                        }, 2000);
                    }, 500);
                }

                // Nettoyer l'URL
                window.history.replaceState({}, '', window.location.pathname);
            }, 300);
        }
    }

    bindEvents() {
        document.getElementById('refresh-btn').addEventListener('click', () => this.refresh());
        document.getElementById('mark-all-read')?.addEventListener('click', () => this.markAllAsRead());

        document.addEventListener('change', (e) => {
            if (e.target.type === 'checkbox') {
                this.handleFilterChange(e.target);
            }
        });
    }

    // ==================== Data Loading ====================

    async loadInitialData() {
        try {
            await Promise.all([
                this.loadStats(),
                this.loadCategories(),
                this.loadAllFeeds(),
            ]);
            this.setStatus(true);
            this.checkNewArticles();
        } catch (error) {
            console.error('Error loading data:', error);
            this.setStatus(false);
            this.showToast('Erreur de chargement', 'error');
        }
    }

    async loadStats() {
        const res = await fetch('/api/feeds/status');
        const data = await res.json();

        if (data.success) {
            const s = data.status;
            document.getElementById('stat-categories').textContent = s.total_categories;
            document.getElementById('stat-feeds').textContent = s.total_feeds;
            document.getElementById('stat-entries').textContent = s.total_entries;
            document.getElementById('stat-update').textContent = this.formatDateShort(s.last_update);
        }
    }

    async loadCategories() {
        const res = await fetch('/api/feeds/categories');
        const data = await res.json();

        if (data.success) {
            const container = document.getElementById('category-filters');
            container.innerHTML = '';
            this.categoryMap = {};

            const savedCategories = this.filters.categories;
            const allKeys = Object.keys(data.categories);

            if (savedCategories.length === 0) {
                this.filters.categories = allKeys;
            }

            Object.entries(data.categories).forEach(([key, cat]) => {
                this.categoryMap[key] = cat.name;

                const isChecked = this.filters.categories.includes(key);
                const label = document.createElement('label');
                label.innerHTML = `<input type="checkbox" name="category" value="${key}" ${isChecked ? 'checked' : ''}> ${cat.name}`;
                container.appendChild(label);
            });

            document.querySelectorAll('#type-filters input[type="checkbox"]').forEach(cb => {
                cb.checked = this.filters.types.includes(cb.value);
            });
        }
    }

    async loadAllFeeds() {
        if (this.loading) return;

        this.loading = true;

        try {
            const res = await fetch('/api/feeds/latest?limit=500');
            const data = await res.json();

            if (data.success) {
                this.feeds = data.entries;
                this.render();
            }
        } catch (error) {
            console.error('Error loading feeds:', error);
        } finally {
            this.loading = false;
        }
    }

    // ==================== New Articles ====================

    checkNewArticles() {
        const currentIds = this.feeds.slice(0, 100).map(f => f.id);
        const newIds = currentIds.filter(id => !this.lastSeenIds.includes(id) && !this.isArticleRead(id));

        this.newCount = newIds.length;
        this.updateNewCount();

        this.saveLastSeenIds();
    }

    updateNewCount() {
        const filtered = this.getFilteredFeeds();
        const unreadCount = filtered.filter(f => !this.isArticleRead(f.id)).length;

        const badge = document.getElementById('new-count');
        if (badge) {
            if (unreadCount > 0) {
                badge.textContent = unreadCount;
                badge.style.display = 'inline-flex';
            } else {
                badge.style.display = 'none';
            }
        }

        if (unreadCount > 0) {
            document.title = `(${unreadCount}) IT Monitoring`;
        } else {
            document.title = 'IT Monitoring';
        }
    }

    // ==================== Rendering ====================

    render() {
        const container = document.getElementById('feed-container');
        const filtered = this.getFilteredFeeds();

        if (filtered.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-inbox"></i>
                    <p>Aucun article trouvé</p>
                </div>
            `;
            return;
        }

        container.innerHTML = filtered.map((feed, index) => this.renderFeedItem(feed, index)).join('');

        // Animate items on load
        container.querySelectorAll('.feed-item').forEach((item, i) => {
            item.style.animationDelay = `${i * 0.03}s`;
        });

        // Add click listeners
        container.querySelectorAll('.feed-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (e.target.closest('a')) return;

                const id = item.dataset.id;
                this.markAsRead(id);
                item.classList.add('read');
                item.querySelector('.tag-new')?.remove();
                item.classList.toggle('expanded');
                this.updateNewCount();
            });
        });

        this.updateNewCount();
    }

    renderFeedItem(feed, index) {
        const date = this.formatDate(feed.published);
        const isRead = this.isArticleRead(feed.id);
        const typeIcon = this.getTypeIcon(feed.feed_type);

        return `
            <article class="feed-item ${isRead ? 'read' : ''}" data-index="${index}" data-id="${feed.id}">
                <div class="feed-item-header">
                    <div class="feed-item-tags">
                        <span class="tag tag-category">
                            <i class="fas fa-folder"></i>
                            ${this.escapeHtml(feed.category)}
                        </span>
                        <span class="tag tag-type ${feed.feed_type}">
                            <i class="${typeIcon}"></i>
                            ${this.getTypeLabel(feed.feed_type)}
                        </span>
                        ${!isRead ? '<span class="tag tag-new"><i class="fas fa-sparkles"></i> Nouveau</span>' : ''}
                    </div>
                    <span class="feed-item-date">
                        <i class="far fa-clock"></i>
                        ${date}
                    </span>
                </div>
                <h3 class="feed-item-title">
                    <a href="${this.escapeHtml(feed.link)}" target="_blank" rel="noopener">
                        ${this.escapeHtml(feed.title)}
                        <i class="fas fa-external-link-alt"></i>
                    </a>
                </h3>
                <p class="feed-item-preview">${this.getPreview(feed.summary)}</p>
                <div class="feed-item-content">
                    <div class="feed-item-body">
                        ${feed.summary || '<p>Pas de contenu disponible.</p>'}
                    </div>
                </div>
                <div class="feed-item-footer">
                    <span class="feed-source">
                        <i class="fas fa-rss"></i>
                        ${this.escapeHtml(feed.feed_name)}
                    </span>
                    ${feed.author ? `<span class="feed-author"><i class="fas fa-user"></i>${this.escapeHtml(feed.author)}</span>` : ''}
                    <span class="feed-item-expand">
                        <i class="fas fa-chevron-down"></i>
                        <span class="expand-text">Détails</span>
                    </span>
                </div>
            </article>
        `;
    }

    // ==================== Filtering ====================

    getFilteredFeeds() {
        return this.feeds.filter(feed => {
            if (this.filters.categories.length > 0) {
                const feedCategoryKey = feed.category_key || this.getCategoryKeyByName(feed.category);
                if (!this.filters.categories.includes(feedCategoryKey)) {
                    return false;
                }
            }

            if (this.filters.types.length === 0) {
                return false;
            }
            if (!this.filters.types.includes(feed.feed_type)) {
                return false;
            }

            return true;
        });
    }

    getCategoryKeyByName(name) {
        for (const [key, catName] of Object.entries(this.categoryMap)) {
            if (catName === name) {
                return key;
            }
        }
        return name.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '');
    }

    handleFilterChange(checkbox) {
        const { name, value, checked } = checkbox;

        if (name === 'category') {
            if (checked) {
                if (!this.filters.categories.includes(value)) {
                    this.filters.categories.push(value);
                }
            } else {
                this.filters.categories = this.filters.categories.filter(c => c !== value);
            }
        } else if (name === 'type') {
            if (checked) {
                if (!this.filters.types.includes(value)) {
                    this.filters.types.push(value);
                }
            } else {
                this.filters.types = this.filters.types.filter(t => t !== value);
            }
        }

        this.saveFilters();
        this.render();
    }

    // ==================== Actions ====================

    async refresh() {
        const btn = document.getElementById('refresh-btn');
        btn.classList.add('loading');

        try {
            this.feeds = [];
            await this.loadAllFeeds();
            await this.loadStats();
            this.checkNewArticles();
            this.showToast('Données actualisées', 'success');
        } catch (error) {
            console.error('Refresh error:', error);
        } finally {
            btn.classList.remove('loading');
        }
    }

    setStatus(online) {
        const status = document.getElementById('status');
        if (online) {
            status.classList.remove('offline');
            status.innerHTML = '<i class="fas fa-circle"></i> Connecté';
        } else {
            status.classList.add('offline');
            status.innerHTML = '<i class="fas fa-circle"></i> Déconnecté';
        }
    }

    showToast(message, type = 'info') {
        const existing = document.querySelector('.toast');
        if (existing) existing.remove();

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
            <span>${message}</span>
        `;
        document.body.appendChild(toast);

        requestAnimationFrame(() => toast.classList.add('show'));

        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // ==================== Utilities ====================

    formatDate(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return dateString;

        const now = new Date();
        const diff = now - date;
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);

        if (minutes < 60) {
            return `Il y a ${minutes}min`;
        } else if (hours < 24) {
            return `Il y a ${hours}h`;
        } else if (days < 7) {
            return `Il y a ${days}j`;
        }

        return date.toLocaleDateString('fr-FR', {
            day: 'numeric',
            month: 'short',
            year: 'numeric'
        });
    }

    formatDateShort(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return '-';

        return date.toLocaleDateString('fr-FR', {
            day: 'numeric',
            month: 'short',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    getTypeLabel(type) {
        const labels = {
            announcements: 'Annonce',
            releases: 'Release',
            commits: 'Commit'
        };
        return labels[type] || type;
    }

    getTypeIcon(type) {
        const icons = {
            announcements: 'fas fa-bullhorn',
            releases: 'fas fa-tag',
            commits: 'fas fa-code-commit'
        };
        return icons[type] || 'fas fa-rss';
    }

    getPreview(html) {
        if (!html) return '';
        // Strip HTML tags and get plain text
        const temp = document.createElement('div');
        temp.innerHTML = html;
        const text = temp.textContent || temp.innerText || '';
        // Truncate to ~150 chars
        const truncated = text.trim().substring(0, 150);
        if (text.length > 150) {
            return truncated + '...';
        }
        return truncated;
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ITMonitoring();
});

// Auto-refresh every 5 minutes
setInterval(() => {
    if (window.app && !window.app.loading) {
        window.app.refresh();
    }
}, 5 * 60 * 1000);
