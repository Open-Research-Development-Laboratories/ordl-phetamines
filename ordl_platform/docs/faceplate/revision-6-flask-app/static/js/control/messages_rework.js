/**
 * Messages Rework JavaScript
 * Handles message lifecycle board and drag-drop functionality
 */

let draggedCard = null;
let selectedMessages = new Set();

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    initMessagesRework();
});

function initMessagesRework() {
    setupDragAndDrop();
    setupEventListeners();
}

// Drag and Drop
function setupDragAndDrop() {
    // Allow drop on columns
    document.querySelectorAll('.column-content').forEach(column => {
        column.addEventListener('dragover', handleDragOver);
        column.addEventListener('drop', handleDrop);
        column.addEventListener('dragleave', handleDragLeave);
    });
}

function drag(ev) {
    draggedCard = ev.target;
    ev.target.classList.add('dragging');
    ev.dataTransfer.effectAllowed = 'move';
    ev.dataTransfer.setData('text/plain', ev.target.dataset.id);
}

function allowDrop(ev) {
    ev.preventDefault();
}

function handleDragOver(ev) {
    ev.preventDefault();
    ev.dataTransfer.dropEffect = 'move';
    this.classList.add('drag-over');
}

function handleDragLeave(ev) {
    this.classList.remove('drag-over');
}

function handleDrop(ev) {
    ev.preventDefault();
    this.classList.remove('drag-over');
    
    if (draggedCard) {
        const messageId = draggedCard.dataset.id;
        const newStatus = this.dataset.status;
        
        // Move card to new column
        this.appendChild(draggedCard);
        draggedCard.classList.remove('dragging');
        
        // Update message status
        updateMessageStatus(messageId, newStatus);
        
        draggedCard = null;
        updateColumnCounts();
    }
}

function updateMessageStatus(messageId, newStatus) {
    console.log(`Moving message ${messageId} to status: ${newStatus}`);
    // API call to update message status
}

function updateColumnCounts() {
    document.querySelectorAll('.lifecycle-column').forEach(column => {
        const count = column.querySelectorAll('.message-card').length;
        const countEl = column.querySelector('.column-count');
        if (countEl) {
            countEl.textContent = count;
        }
    });
}

// Event listeners
function setupEventListeners() {
    // Message card checkboxes (if implemented)
}

// Message actions
function createMessage() {
    console.log('Create new message');
    // Open create message modal
}

function editMessage(messageId) {
    console.log('Edit message:', messageId);
    // Open edit modal
}

function submitForReview(messageId) {
    console.log('Submit for review:', messageId);
    moveMessageToColumn(messageId, 'review');
}

function viewDetails(messageId) {
    console.log('View details:', messageId);
    showMessageDetailModal(messageId);
}

function approveMessage(messageId) {
    console.log('Approve message:', messageId);
    moveMessageToColumn(messageId, 'approved');
}

function dispatchMessage(messageId) {
    console.log('Dispatch message:', messageId);
    moveMessageToColumn(messageId, 'dispatched');
}

function revokeApproval(messageId) {
    console.log('Revoke approval:', messageId);
    moveMessageToColumn(messageId, 'draft');
}

function trackMessage(messageId) {
    console.log('Track message:', messageId);
    // Open tracking view
}

function cancelMessage(messageId) {
    if (confirm('Are you sure you want to cancel this message?')) {
        console.log('Cancel message:', messageId);
        moveMessageToColumn(messageId, 'draft');
    }
}

function viewResults(messageId) {
    console.log('View results:', messageId);
    // Show results modal
}

function archiveMessage(messageId) {
    console.log('Archive message:', messageId);
    moveMessageToColumn(messageId, 'superseded');
}

function viewHistory(messageId) {
    console.log('View history:', messageId);
    showMessageDetailModal(messageId);
}

function deleteMessage(messageId) {
    if (confirm('Are you sure you want to delete this message?')) {
        console.log('Delete message:', messageId);
        const card = document.querySelector(`[data-id="${messageId}"]`);
        if (card) {
            card.remove();
            updateColumnCounts();
        }
    }
}

function moveMessageToColumn(messageId, targetStatus) {
    const card = document.querySelector(`[data-id="${messageId}"]`);
    const targetColumn = document.querySelector(`.column-content[data-status="${targetStatus}"]`);
    
    if (card && targetColumn) {
        targetColumn.appendChild(card);
        updateColumnCounts();
    }
}

// Modal functions
function showMessageDetailModal(messageId) {
    const modal = document.getElementById('messageDetailModal');
    if (modal) {
        modal.classList.add('active');
    }
}

function closeMessageModal() {
    const modal = document.getElementById('messageDetailModal');
    if (modal) {
        modal.classList.remove('active');
    }
}

// Bulk actions
function bulkMove(targetStatus) {
    if (selectedMessages.size === 0) {
        alert('Please select messages to move');
        return;
    }
    
    selectedMessages.forEach(messageId => {
        moveMessageToColumn(messageId, targetStatus);
    });
    
    selectedMessages.clear();
    updateBulkActionsUI();
}

function bulkApprove() {
    if (selectedMessages.size === 0) {
        alert('Please select messages to approve');
        return;
    }
    
    selectedMessages.forEach(messageId => {
        moveMessageToColumn(messageId, 'approved');
    });
    
    selectedMessages.clear();
    updateBulkActionsUI();
}

function bulkDispatch() {
    if (selectedMessages.size === 0) {
        alert('Please select messages to dispatch');
        return;
    }
    
    selectedMessages.forEach(messageId => {
        moveMessageToColumn(messageId, 'dispatched');
    });
    
    selectedMessages.clear();
    updateBulkActionsUI();
}

function bulkDelete() {
    if (selectedMessages.size === 0) {
        alert('Please select messages to delete');
        return;
    }
    
    if (confirm(`Are you sure you want to delete ${selectedMessages.size} messages?`)) {
        selectedMessages.forEach(messageId => {
            const card = document.querySelector(`[data-id="${messageId}"]`);
            if (card) {
                card.remove();
            }
        });
        
        selectedMessages.clear();
        updateBulkActionsUI();
        updateColumnCounts();
    }
}

function updateBulkActionsUI() {
    const bulkActions = document.getElementById('bulkActions');
    const countEl = bulkActions?.querySelector('strong');
    
    if (bulkActions && countEl) {
        if (selectedMessages.size > 0) {
            bulkActions.classList.add('visible');
            countEl.textContent = selectedMessages.size;
        } else {
            bulkActions.classList.remove('visible');
        }
    }
}
