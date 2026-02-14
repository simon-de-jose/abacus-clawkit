// Table rendering helpers

function formatCurrency(amount) {
    const abs = Math.abs(amount);
    const formatted = `$${abs.toFixed(2)}`;
    return amount < 0 ? formatted : `+${formatted}`;
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function createTransactionRow(transaction, onCategoryChange) {
    const row = document.createElement('tr');
    const isNegative = transaction.amount < 0;
    
    row.innerHTML = `
        <td>${formatDate(transaction.transaction_date)}</td>
        <td>
            ${transaction.merchant || transaction.description}
            ${transaction.needs_review ? '<span class="badge needs-review">Needs Review</span>' : ''}
        </td>
        <td>
            <span class="editable category-edit" data-id="${transaction.id}" data-current="${transaction.category || ''}" data-group="${transaction.category_group || ''}">
                ${transaction.category || '—'}
            </span>
        </td>
        <td class="amount ${isNegative ? 'negative' : 'positive'}">
            ${formatCurrency(transaction.amount)}
        </td>
        <td style="font-size: 0.875rem; color: var(--gray-text);">
            ${transaction.account_id}
        </td>
    `;
    
    // Add click handler for category edit
    const categoryCell = row.querySelector('.category-edit');
    if (categoryCell && onCategoryChange) {
        categoryCell.addEventListener('click', () => {
            const currentCategory = categoryCell.dataset.current;
            const transactionId = categoryCell.dataset.id;
            showCategoryPicker(transactionId, currentCategory, onCategoryChange);
        });
    }
    
    return row;
}

function showCategoryPicker(transactionId, currentCategory, onSave) {
    // Fetch categories and show picker
    fetch('/api/categories')
        .then(r => r.json())
        .then(data => {
            const categories = data.categories;
            const select = document.createElement('select');
            select.className = 'category-picker';
            
            select.innerHTML = `
                <option value="">— Select Category —</option>
                ${categories.map(cat => `
                    <option value="${cat.category}" data-group="${cat.category_group}" ${cat.category === currentCategory ? 'selected' : ''}>
                        ${cat.category_group} → ${cat.category}
                    </option>
                `).join('')}
            `;
            
            select.addEventListener('change', async () => {
                const selectedOption = select.options[select.selectedIndex];
                const category = selectedOption.value;
                const categoryGroup = selectedOption.dataset.group;
                
                if (category) {
                    // Save to backend
                    const response = await fetch(`/api/transactions/${transactionId}/category`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ category, category_group: categoryGroup })
                    });
                    
                    if (response.ok) {
                        onSave();
                    } else {
                        alert('Failed to update category');
                    }
                }
            });
            
            // Show as modal
            const modal = document.createElement('div');
            modal.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000;';
            
            const modalContent = document.createElement('div');
            modalContent.style.cssText = 'background: white; padding: 2rem; border-radius: 12px; min-width: 400px;';
            modalContent.innerHTML = '<h3 style="margin-bottom: 1rem;">Change Category</h3>';
            modalContent.appendChild(select);
            
            const cancelBtn = document.createElement('button');
            cancelBtn.textContent = 'Cancel';
            cancelBtn.className = 'btn-secondary';
            cancelBtn.style.marginTop = '1rem';
            cancelBtn.onclick = () => document.body.removeChild(modal);
            modalContent.appendChild(cancelBtn);
            
            modal.appendChild(modalContent);
            modal.onclick = (e) => {
                if (e.target === modal) document.body.removeChild(modal);
            };
            
            document.body.appendChild(modal);
        });
}

// Phase 3: Mobile transaction card layout
function createMobileTransactionCard(transaction, onCategoryChange) {
    const card = document.createElement('div');
    card.className = 'mobile-transaction-card';
    const isNegative = transaction.amount < 0;
    
    card.innerHTML = `
        <div class="mobile-txn-line1">
            <div class="mobile-txn-merchant">
                ${transaction.merchant || transaction.description}
                ${transaction.needs_review ? '<span class="badge needs-review">Review</span>' : ''}
            </div>
            <div class="mobile-txn-amount ${isNegative ? 'negative' : 'positive'}">
                ${formatCurrency(transaction.amount)}
            </div>
        </div>
        <div class="mobile-txn-line2">
            <div class="mobile-txn-category">
                <span class="editable category-edit" data-id="${transaction.id}" data-current="${transaction.category || ''}" data-group="${transaction.category_group || ''}">
                    ${transaction.category || 'Uncategorized'}
                </span>
            </div>
            <div class="mobile-txn-date">
                ${formatDate(transaction.transaction_date)}
            </div>
        </div>
    `;
    
    // Add click handler for category edit
    const categoryCell = card.querySelector('.category-edit');
    if (categoryCell && onCategoryChange) {
        categoryCell.addEventListener('click', (e) => {
            e.stopPropagation();
            const currentCategory = categoryCell.dataset.current;
            const transactionId = categoryCell.dataset.id;
            showCategoryPicker(transactionId, currentCategory, onCategoryChange);
        });
    }
    
    return card;
}

function createPagination(currentPage, totalPages, onPageChange) {
    const pagination = document.createElement('div');
    pagination.className = 'pagination';
    
    // Previous button
    const prevBtn = document.createElement('button');
    prevBtn.textContent = '←';
    prevBtn.disabled = currentPage === 1;
    prevBtn.onclick = () => onPageChange(currentPage - 1);
    pagination.appendChild(prevBtn);
    
    // Page numbers
    const maxButtons = 7;
    let startPage = Math.max(1, currentPage - Math.floor(maxButtons / 2));
    let endPage = Math.min(totalPages, startPage + maxButtons - 1);
    
    if (endPage - startPage < maxButtons - 1) {
        startPage = Math.max(1, endPage - maxButtons + 1);
    }
    
    for (let i = startPage; i <= endPage; i++) {
        const pageBtn = document.createElement('button');
        pageBtn.textContent = i;
        pageBtn.className = i === currentPage ? 'active' : '';
        pageBtn.onclick = () => onPageChange(i);
        pagination.appendChild(pageBtn);
    }
    
    // Next button
    const nextBtn = document.createElement('button');
    nextBtn.textContent = '→';
    nextBtn.disabled = currentPage === totalPages;
    nextBtn.onclick = () => onPageChange(currentPage + 1);
    pagination.appendChild(nextBtn);
    
    return pagination;
}
