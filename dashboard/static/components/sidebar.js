// Sidebar navigation component

function createSidebar(activePage) {
    const pages = [
        { name: 'Dashboard', path: 'index.html', icon: '📊' },
        { name: 'Transactions', path: 'transactions.html', icon: '💳' },
        { name: 'Cash Flow', path: 'cashflow.html', icon: '💰' },
        { name: 'Reports', path: 'reports.html', icon: '📈' },
        { name: 'Accounts', path: 'accounts.html', icon: '🏦' }
    ];
    
    const sidebar = document.createElement('div');
    sidebar.className = 'sidebar';
    
    sidebar.innerHTML = `
        <div class="sidebar-header">
            <h1>🧮 Abacus</h1>
            <p>Personal Finance</p>
        </div>
        <ul class="sidebar-nav">
            ${pages.map(page => `
                <li>
                    <a href="${page.path}" class="${activePage === page.name ? 'active' : ''}">
                        <span class="icon">${page.icon}</span>
                        <span>${page.name}</span>
                    </a>
                </li>
            `).join('')}
        </ul>
    `;
    
    return sidebar;
}

// Initialize sidebar on page load
document.addEventListener('DOMContentLoaded', () => {
    const activePage = document.body.dataset.page || 'Dashboard';
    document.body.insertBefore(createSidebar(activePage), document.body.firstChild);
});
