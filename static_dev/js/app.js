class ITMonitoringApp {
    constructor() {
        this.feedData = [];
        this.currentPage = 1;
        this.itemsPerPage = 20;
        this.filters = {
            categories: [],
            types: ['announcements', 'commits', 'releases']
        };
        this.currentView = 'grid';
        this.isLoading = false;

        this.init();
    }

    async init() {
        this.showLoadingScreen();
        await this.setupEventListeners();
        await this.loadInitialData();
        this.hideLoadingScreen();
        this.setupAnimations();
    }

    showLoadingScreen() {
        const loadingScreen = document.getElementById('loading-screen');
        const loadingContent = loadingScreen.querySelector('.loading-content');
        const loadingProgress = loadingScreen.querySelector('.loading-progress');

        gsap.to(loadingContent, {
            opacity: 1,
            duration: 0.5,
            ease: "power2.out"
        });

        gsap.to(loadingProgress, {
            width: "100%",
            duration: 2,
            ease: "power2.inOut"
        });
    }

    hideLoadingScreen() {
        const loadingScreen = document.getElementById('loading-screen');
        const mainContainer = document.getElementById('main-container');

        gsap.to(loadingScreen, {
            opacity: 0,
            duration: 0.5,
            ease: "power2.out",
            onComplete: () => {
                loadingScreen.style.display = 'none';
            }
        });

        gsap.to(mainContainer, {
            opacity: 1,
            y: 0,
            duration: 0.8,
            ease: "power2.out",
            delay: 0.2
        });
    }

    setupAnimations() {
        // Animate stats cards
        gsap.from('.stat-card', {
            y: 30,
            opacity: 0,
            duration: 0.6,
            stagger: 0.1,
            ease: "power2.out",
            delay: 0.5
        });

        // Animate sidebar
        gsap.from('.sidebar', {
            x: -50,
            opacity: 0,
            duration: 0.8,
            ease: "power2.out",
            delay: 0.7
        });

        // Animate section header
        gsap.from('.section-header', {
            y: 20,
            opacity: 0,
            duration: 0.6,
            ease: "power2.out",
            delay: 0.9
        });
    }

    setupEventListeners() {
        // Refresh button
        const refreshBtn = document.getElementById('refresh-btn');
        refreshBtn.addEventListener('click', () => this.forceRefresh());

        // View controls
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.changeView(e.target.dataset.view));
        });

        // Load more button
        const loadMoreBtn = document.getElementById('load-more-btn');
        loadMoreBtn.addEventListener('click', () => this.loadMore());

        // Modal controls
        const modalOverlay = document.getElementById('modal-overlay');
        const modalClose = document.getElementById('modal-close');
        modalOverlay.addEventListener('click', () => this.closeModal());
        modalClose.addEventListener('click', () => this.closeModal());

        // Filter controls
        document.addEventListener('change', (e) => {
            if (e.target.type === 'checkbox') {
                this.handleFilterChange(e);
            }
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') this.closeModal();
            if (e.key === 'r' && e.ctrlKey) {
                e.preventDefault();
                this.forceRefresh();
            }
        });
    }

    async loadInitialData() {
        try {
            await Promise.all([
                this.loadStats(),
                this.loadCategories(),
                this.loadFeeds()
            ]);
            this.updateStatusIndicator(true);
        } catch (error) {
            console.error('Error loading initial data:', error);
            this.updateStatusIndicator(false);
            this.showErrorMessage('Erreur lors du chargement des données');
        }
    }

    async loadStats() {
        try {
            const response = await fetch('/api/feeds/status');
            const data = await response.json();

            if (data.success) {
                const stats = data.status;
                this.updateStatCard('stat-categories', stats.total_categories);
                this.updateStatCard('stat-feeds', stats.total_feeds);
                this.updateStatCard('stat-entries', stats.total_entries);
                this.updateStatCard('stat-update', this.formatDate(stats.last_update));
            }
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }

    async loadCategories() {
        try {
            const response = await fetch('/api/feeds/categories');
            const data = await response.json();

            if (data.success) {
                this.renderCategoryFilters(data.categories);
            }
        } catch (error) {
            console.error('Error loading categories:', error);
        }
    }

    async loadFeeds() {
        if (this.isLoading) return;
        this.isLoading = true;

        try {
            const response = await fetch(`/api/feeds/latest?limit=${this.itemsPerPage * this.currentPage}`);
            const data = await response.json();

            if (data.success) {
                this.feedData = data.entries;
                this.renderFeeds();
            }
        } catch (error) {
            console.error('Error loading feeds:', error);
            this.showErrorMessage('Erreur lors du chargement des flux');
        } finally {
            this.isLoading = false;
        }
    }

    updateStatCard(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            const currentValue = element.textContent;
            if (currentValue !== value.toString()) {
                gsap.to(element, {
                    scale: 1.1,
                    duration: 0.2,
                    yoyo: true,
                    repeat: 1,
                    ease: "power2.inOut",
                    onComplete: () => {
                        element.textContent = value;
                    }
                });
            }
        }
    }

    renderCategoryFilters(categories) {
        const container = document.getElementById('category-filters');
        container.innerHTML = '';

        Object.keys(categories).forEach(key => {
            const category = categories[key];
            const label = document.createElement('label');
            label.className = 'filter-checkbox';
            label.innerHTML = `
                <input type="checkbox" name="category" value="${key}" checked>
                <span class="checkmark"></span>
                <i class="fas fa-layer-group"></i> ${category.name}
            `;
            container.appendChild(label);
            this.filters.categories.push(key);
        });

        gsap.from(container.children, {
            x: -20,
            opacity: 0,
            duration: 0.4,
            stagger: 0.1,
            ease: "power2.out"
        });
    }

    renderFeeds() {
        const container = document.getElementById('feed-container');
        const filteredFeeds = this.getFilteredFeeds();

        container.innerHTML = '';

        filteredFeeds.forEach((feed, index) => {
            const feedElement = this.createFeedElement(feed);
            container.appendChild(feedElement);

            // Animate new items
            gsap.from(feedElement, {
                y: 30,
                opacity: 0,
                duration: 0.6,
                delay: index * 0.05,
                ease: "power2.out"
            });
        });

        // Update load more button visibility
        const loadMoreBtn = document.getElementById('load-more-btn');
        loadMoreBtn.style.display = filteredFeeds.length >= this.itemsPerPage * this.currentPage ? 'block' : 'none';
    }

    createFeedElement(feed) {
        const article = document.createElement('article');
        article.className = 'feed-item';
        article.innerHTML = `
            <div class="feed-header">
                <div class="feed-category">
                    <i class="fas fa-tag"></i>
                    ${feed.category}
                </div>
                <div class="feed-type ${feed.feed_type}">
                    ${this.getTypeIcon(feed.feed_type)} ${feed.feed_type}
                </div>
            </div>
            <h3 class="feed-title">${feed.title}</h3>
            <div class="feed-summary">${feed.summary || 'Aucun résumé disponible'}</div>
            <div class="feed-footer">
                <div class="feed-meta">
                    <span><i class="fas fa-calendar"></i> ${this.formatDate(feed.published)}</span>
                    <span><i class="fas fa-rss"></i> ${feed.feed_name}</span>
                </div>
                <div class="feed-actions">
                    <button class="action-btn" onclick="window.open('${feed.link}', '_blank')" title="Ouvrir le lien">
                        <i class="fas fa-external-link-alt"></i>
                    </button>
                    <button class="action-btn" onclick="app.showFeedDetail('${feed.id}')" title="Voir les détails">
                        <i class="fas fa-eye"></i>
                    </button>
                </div>
            </div>
        `;

        return article;
    }

    getTypeIcon(type) {
        const icons = {
            announcements: '<i class="fas fa-bullhorn"></i>',
            commits: '<i class="fas fa-code-branch"></i>',
            releases: '<i class="fas fa-tag"></i>'
        };
        return icons[type] || '<i class="fas fa-file"></i>';
    }

    getFilteredFeeds() {
        return this.feedData.filter(feed => {
            const categoryMatch = this.filters.categories.length === 0 ||
                                this.filters.categories.some(cat => feed.category.toLowerCase().includes(cat.toLowerCase()));
            const typeMatch = this.filters.types.includes(feed.feed_type);
            return categoryMatch && typeMatch;
        });
    }

    changeView(view) {
        this.currentView = view;
        const container = document.getElementById('feed-container');
        const viewBtns = document.querySelectorAll('.view-btn');

        viewBtns.forEach(btn => btn.classList.remove('active'));
        document.querySelector(`[data-view="${view}"]`).classList.add('active');

        if (view === 'list') {
            container.classList.add('list-view');
        } else {
            container.classList.remove('list-view');
        }

        gsap.from('.feed-item', {
            scale: 0.9,
            opacity: 0,
            duration: 0.4,
            stagger: 0.02,
            ease: "power2.out"
        });
    }

    handleFilterChange(event) {
        const { name, value, checked } = event.target;

        if (name === 'category') {
            if (checked) {
                this.filters.categories.push(value);
            } else {
                this.filters.categories = this.filters.categories.filter(cat => cat !== value);
            }
        } else if (name === 'type') {
            if (checked) {
                this.filters.types.push(value);
            } else {
                this.filters.types = this.filters.types.filter(type => type !== value);
            }
        }

        this.renderFeeds();
    }

    async loadMore() {
        this.currentPage++;
        await this.loadFeeds();
    }

    async forceRefresh() {
        const refreshBtn = document.getElementById('refresh-btn');
        refreshBtn.classList.add('loading');

        try {
            const response = await fetch('/api/admin/force-fetch', {
                method: 'POST'
            });
            const data = await response.json();

            if (data.success) {
                await this.loadInitialData();
                this.showSuccessMessage('Données mises à jour avec succès');
            } else {
                this.showErrorMessage('Erreur lors de la mise à jour');
            }
        } catch (error) {
            console.error('Error forcing refresh:', error);
            this.showErrorMessage('Erreur lors de la mise à jour');
        } finally {
            refreshBtn.classList.remove('loading');
        }
    }

    showFeedDetail(feedId) {
        const feed = this.feedData.find(f => f.id === feedId);
        if (!feed) return;

        const modal = document.getElementById('detail-modal');
        const modalTitle = document.getElementById('modal-title');
        const modalBody = document.getElementById('modal-body');

        modalTitle.textContent = feed.title;
        modalBody.innerHTML = `
            <div class="feed-detail">
                <div class="detail-header">
                    <div class="detail-meta">
                        <span class="detail-category">${feed.category}</span>
                        <span class="detail-type ${feed.feed_type}">${feed.feed_type}</span>
                    </div>
                    <div class="detail-info">
                        <p><i class="fas fa-calendar"></i> ${this.formatDate(feed.published)}</p>
                        <p><i class="fas fa-rss"></i> ${feed.feed_name}</p>
                        <p><i class="fas fa-user"></i> ${feed.author || 'Auteur inconnu'}</p>
                    </div>
                </div>
                <div class="detail-content">
                    <p>${feed.summary || 'Aucun contenu disponible'}</p>
                </div>
                <div class="detail-actions">
                    <a href="${feed.link}" target="_blank" class="detail-link">
                        <i class="fas fa-external-link-alt"></i> Voir l'article complet
                    </a>
                </div>
            </div>
        `;

        modal.classList.add('active');

        gsap.from('.modal-content', {
            scale: 0.8,
            opacity: 0,
            duration: 0.3,
            ease: "power2.out"
        });
    }

    closeModal() {
        const modal = document.getElementById('detail-modal');
        modal.classList.remove('active');
    }

    updateStatusIndicator(isOnline) {
        const indicator = document.getElementById('status-indicator');
        if (isOnline) {
            indicator.classList.add('online');
            indicator.classList.remove('offline');
            indicator.querySelector('span').textContent = 'Connecté';
        } else {
            indicator.classList.add('offline');
            indicator.classList.remove('online');
            indicator.querySelector('span').textContent = 'Déconnecté';
        }
    }

    showSuccessMessage(message) {
        this.showMessage(message, 'success');
    }

    showErrorMessage(message) {
        this.showMessage(message, 'error');
    }

    showMessage(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-triangle'}"></i>
            <span>${message}</span>
        `;

        document.body.appendChild(notification);

        gsap.from(notification, {
            x: 300,
            opacity: 0,
            duration: 0.3,
            ease: "power2.out"
        });

        setTimeout(() => {
            gsap.to(notification, {
                x: 300,
                opacity: 0,
                duration: 0.3,
                ease: "power2.in",
                onComplete: () => notification.remove()
            });
        }, 4000);
    }

    formatDate(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        const now = new Date();
        const diffTime = Math.abs(now - date);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

        if (diffDays === 1) {
            return 'Hier';
        } else if (diffDays < 7) {
            return `Il y a ${diffDays} jours`;
        } else if (diffDays < 30) {
            const weeks = Math.floor(diffDays / 7);
            return `Il y a ${weeks} semaine${weeks > 1 ? 's' : ''}`;
        } else {
            return date.toLocaleDateString('fr-FR', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
        }
    }
}

// CSS for notifications
const notificationStyles = `
    .notification {
        position: fixed;
        top: 100px;
        right: 20px;
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: var(--radius-md);
        padding: 1rem 1.5rem;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        z-index: 1001;
        min-width: 300px;
        box-shadow: var(--shadow-heavy);
    }

    .notification-success {
        border-left: 4px solid var(--success-color);
    }

    .notification-error {
        border-left: 4px solid var(--error-color);
    }

    .notification i {
        font-size: 1.25rem;
    }

    .notification-success i {
        color: var(--success-color);
    }

    .notification-error i {
        color: var(--error-color);
    }

    .detail-header {
        margin-bottom: 1.5rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid var(--border-color);
    }

    .detail-meta {
        display: flex;
        gap: 0.75rem;
        margin-bottom: 1rem;
    }

    .detail-category, .detail-type {
        padding: 0.25rem 0.75rem;
        border-radius: var(--radius-md);
        font-size: 0.75rem;
        font-weight: 500;
    }

    .detail-category {
        background: var(--bg-secondary);
        color: var(--text-secondary);
    }

    .detail-type {
        text-transform: uppercase;
    }

    .detail-info p {
        margin-bottom: 0.5rem;
        font-size: 0.875rem;
        color: var(--text-secondary);
    }

    .detail-content {
        margin-bottom: 1.5rem;
        line-height: 1.6;
    }

    .detail-link {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.75rem 1.5rem;
        background: var(--primary-color);
        color: white;
        text-decoration: none;
        border-radius: var(--radius-md);
        font-weight: 500;
        transition: all var(--transition-fast);
    }

    .detail-link:hover {
        background: var(--primary-dark);
        transform: translateY(-1px);
    }
`;

// Inject notification styles
const styleSheet = document.createElement('style');
styleSheet.textContent = notificationStyles;
document.head.appendChild(styleSheet);

// Initialize app when DOM is loaded
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new ITMonitoringApp();
});

// Auto-refresh every 5 minutes
setInterval(() => {
    if (app && !app.isLoading) {
        app.loadStats();
    }
}, 5 * 60 * 1000);