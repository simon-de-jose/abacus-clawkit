// Sidebar navigation component

function createSidebar(activePage) {
    const pages = [
        { name: 'Dashboard', path: '/', icon: '📊' },
        { name: 'Transactions', path: '/transactions', icon: '💳' },
        { name: 'Review', path: '/review', icon: '📋' },
        { name: 'Projects', path: '/projects', icon: '📁' },
        { name: 'Cash Flow', path: '/cashflow', icon: '💰' },
        { name: 'Reports', path: '/reports/cashflow', icon: '📈' },
        { name: 'Categories', path: '/categories', icon: '🏷️' },
        { name: 'Accounts', path: '/accounts', icon: '🏦' }
    ];
    
    const sidebar = document.createElement('div');
    sidebar.className = 'sidebar';
    sidebar.id = 'sidebar';
    
    sidebar.innerHTML = `
        <div class="sidebar-header">
            <h1>🧮 Abacus</h1>
            <p>Personal Finance</p>
        </div>
        <ul class="sidebar-nav">
            ${pages.map(page => `
                <li>
                    <a href="${page.path}" class="${activePage === page.name ? 'active' : ''}" data-nav-link>
                        <span class="icon">${page.icon}</span>
                        <span>${page.name}</span>
                    </a>
                </li>
            `).join('')}
        </ul>
    `;
    
    return sidebar;
}

function createMobileHeader(activePage) {
    const header = document.createElement('div');
    header.className = 'mobile-header';
    
    header.innerHTML = `
        <button class="hamburger-btn" id="hamburger-btn" aria-label="Toggle menu">
            ☰
        </button>
        <div class="mobile-header-title">
            🧮 Abacus
        </div>
    `;
    
    return header;
}

function createBackdrop() {
    const backdrop = document.createElement('div');
    backdrop.className = 'sidebar-backdrop';
    backdrop.id = 'sidebar-backdrop';
    return backdrop;
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const backdrop = document.getElementById('sidebar-backdrop');
    
    if (sidebar && backdrop) {
        sidebar.classList.toggle('open');
        backdrop.classList.toggle('visible');
    }
}

function closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    const backdrop = document.getElementById('sidebar-backdrop');
    
    if (sidebar && backdrop) {
        sidebar.classList.remove('open');
        backdrop.classList.remove('visible');
    }
}

// Initialize sidebar on page load
document.addEventListener('DOMContentLoaded', () => {
    const activePage = document.body.dataset.page || 'Dashboard';
    
    // Create and insert mobile header
    const mobileHeader = createMobileHeader(activePage);
    document.body.insertBefore(mobileHeader, document.body.firstChild);
    
    // Create and insert sidebar
    const sidebar = createSidebar(activePage);
    document.body.insertBefore(sidebar, document.body.firstChild);
    
    // Create and insert backdrop
    const backdrop = createBackdrop();
    document.body.insertBefore(backdrop, document.body.firstChild);
    
    // Hamburger button click handler
    const hamburgerBtn = document.getElementById('hamburger-btn');
    if (hamburgerBtn) {
        hamburgerBtn.addEventListener('click', toggleSidebar);
    }
    
    // Backdrop click handler (close sidebar)
    const backdropElement = document.getElementById('sidebar-backdrop');
    if (backdropElement) {
        backdropElement.addEventListener('click', closeSidebar);
    }
    
    // Close sidebar when any nav link is clicked
    const navLinks = document.querySelectorAll('[data-nav-link]');
    navLinks.forEach(link => {
        link.addEventListener('click', closeSidebar);
    });
});
