/**
 * Fleet Operations JavaScript
 * Handles node management, bulk actions, and status updates
 */

// Sample node data
const sampleNodes = [
    { id: 'node-001', hostname: 'node-001.us-east.internal', ip: '10.0.1.15', status: 'online', role: 'coordinator', region: 'us-east', cpu: 34, memory: 42, gpu: 0, uptime: '45d 12h', updateStatus: 'up_to_date' },
    { id: 'node-002', hostname: 'node-002.us-east.internal', ip: '10.0.1.16', status: 'online', role: 'worker', region: 'us-east', cpu: 56, memory: 62, gpu: 85, uptime: '32d 8h', updateStatus: 'up_to_date' },
    { id: 'node-003', hostname: 'node-003.us-west.internal', ip: '10.0.2.23', status: 'online', role: 'gateway', region: 'us-west', cpu: 23, memory: 31, gpu: 0, uptime: '28d 4h', updateStatus: 'updating' },
    { id: 'node-004', hostname: 'node-004.eu-west.internal', ip: '10.0.3.42', status: 'cordoned', role: 'worker', region: 'eu-west', cpu: 89, memory: 85, gpu: 45, uptime: '31d 15h', updateStatus: 'pending' },
    { id: 'node-005', hostname: 'node-005.ap-southeast.internal', ip: '10.0.4.18', status: 'offline', role: 'worker', region: 'ap-southeast', cpu: 0, memory: 0, gpu: 0, uptime: '-', updateStatus: 'error' },
    { id: 'node-006', hostname: 'node-006.us-east.internal', ip: '10.0.1.24', status: 'draining', role: 'relay', region: 'us-east', cpu: 12, memory: 22, gpu: 0, uptime: '25d 18h', updateStatus: 'up_to_date' },
];

let nodes = [...sampleNodes];
let selectedNodes = new Set();
let currentSort = { column: 'id', direction: 'asc' };

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    initFleetOperations();
});

function initFleetOperations() {
    renderTable();
    setupEventListeners();
    updateStats();
}

function renderTable(data = nodes) {
    const tbody = document.getElementById('tableBody');
    if (!tbody) return;
    
    tbody.innerHTML = data.map(node => `
        <tr data-id="${node.id}" class="${selectedNodes.has(node.id) ? 'selected' : ''}"
            onclick="toggleRowSelection('${node.id}')">
            <td><input type="checkbox" class="checkbox node-checkbox" 
                data-id="${node.id}" ${selectedNodes.has(node.id) ? 'checked' : ''}
                onclick="event.stopPropagation(); toggleNodeSelection('${node.id}')"></td>
            <td>
                <div class="node-id">${node.id}</div>
                <div class="node-address">${node.ip}</div>
            </td>
            <td><span class="badge badge-${node.status}">${node.status}</span></td>
            <td><span class="role-tag role-${node.role}">${node.role}</span></td>
            <td>${node.region}</td>
            <td>
                <div class="resource-bar-container">
                    <div class="resource-bar">
                        <div class="resource-bar-fill cpu" style="width: ${node.cpu}%"></div>
                    </div>
                    <div class="resource-bar">
                        <div class="resource-bar-fill memory" style="width: ${node.memory}%"></div>
                    </div>
                    <div class="resource-labels">
                        <span>CPU ${node.cpu}%</span>
                        <span>MEM ${node.memory}%</span>
                    </div>
                </div>
            </td>
            <td>${node.uptime}</td>
            <td>${getUpdateStatusHtml(node.updateStatus)}</td>
            <td>
                <div class="table-actions">
                    <button class="action-btn-sm" onclick="event.stopPropagation(); reconnectNode('${node.id}')">Reconnect</button>
                    <button class="action-btn-sm warning" onclick="event.stopPropagation(); cordonNode('${node.id}')">Cordon</button>
                    <button class="action-btn-sm warning" onclick="event.stopPropagation(); drainNode('${node.id}')">Drain</button>
                </div>
            </td>
        </tr>
    `).join('');
}

function getUpdateStatusHtml(status) {
    switch(status) {
        case 'updating':
            return `
                <div class="update-status">
                    <div class="update-progress">
                        <div class="update-progress-fill" style="width: 65%;"></div>
                    </div>
                    <span class="update-text">65%</span>
                </div>`;
        case 'pending':
            return '<span class="update-text">Pending</span>';
        case 'error':
            return '<span class="update-text" style="color: var(--error);">Error</span>';
        default:
            return '<span class="update-text">Up to date</span>';
    }
}

function setupEventListeners() {
    // Sortable headers
    document.querySelectorAll('.node-table th.sortable').forEach(th => {
        th.addEventListener('click', () => sortNodes(th.dataset.sort));
    });
    
    // Select all checkbox
    const selectAll = document.getElementById('selectAll');
    if (selectAll) {
        selectAll.addEventListener('change', (e) => {
            const checkboxes = document.querySelectorAll('.node-checkbox');
            checkboxes.forEach(cb => {
                cb.checked = e.target.checked;
                const id = cb.dataset.id;
                if (e.target.checked) selectedNodes.add(id);
                else selectedNodes.delete(id);
            });
            updateSelectionUI();
        });
    }
    
    // Filters
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', filterNodes);
    }
    
    const regionFilter = document.getElementById('regionFilter');
    if (regionFilter) {
        regionFilter.addEventListener('change', filterNodes);
    }
    
    const statusFilter = document.getElementById('statusFilter');
    if (statusFilter) {
        statusFilter.addEventListener('change', filterNodes);
    }
    
    const roleFilter = document.getElementById('roleFilter');
    if (roleFilter) {
        roleFilter.addEventListener('change', filterNodes);
    }
}

function toggleNodeSelection(nodeId) {
    if (selectedNodes.has(nodeId)) {
        selectedNodes.delete(nodeId);
    } else {
        selectedNodes.add(nodeId);
    }
    updateSelectionUI();
}

function toggleRowSelection(nodeId) {
    toggleNodeSelection(nodeId);
}

function updateSelectionUI() {
    const bulkBar = document.getElementById('bulkActionsBar');
    const countSpan = document.getElementById('selectedCount');
    
    if (selectedNodes.size > 0) {
        bulkBar.classList.add('visible');
        countSpan.innerHTML = `<strong>${selectedNodes.size}</strong> node${selectedNodes.size !== 1 ? 's' : ''} selected`;
    } else {
        bulkBar.classList.remove('visible');
    }
    
    // Update row selections
    document.querySelectorAll('#tableBody tr').forEach(row => {
        row.classList.toggle('selected', selectedNodes.has(row.dataset.id));
    });
    
    // Update checkboxes
    document.querySelectorAll('.node-checkbox').forEach(cb => {
        cb.checked = selectedNodes.has(cb.dataset.id);
    });
}

function filterNodes() {
    const search = document.getElementById('searchInput')?.value.toLowerCase() || '';
    const region = document.getElementById('regionFilter')?.value || '';
    const status = document.getElementById('statusFilter')?.value || '';
    const role = document.getElementById('roleFilter')?.value || '';
    
    const filtered = nodes.filter(node => {
        const matchesSearch = !search || 
            node.id.toLowerCase().includes(search) ||
            node.hostname.toLowerCase().includes(search) ||
            node.ip.includes(search);
        const matchesRegion = !region || node.region === region;
        const matchesStatus = !status || node.status === status;
        const matchesRole = !role || node.role === role;
        return matchesSearch && matchesRegion && matchesStatus && matchesRole;
    });
    
    const emptyState = document.getElementById('emptyState');
    const tableContainer = document.querySelector('.table-container');
    
    if (emptyState && tableContainer) {
        emptyState.classList.toggle('visible', filtered.length === 0);
        tableContainer.style.display = filtered.length === 0 ? 'none' : 'block';
    }
    
    renderTable(filtered);
}

function sortNodes(column) {
    if (currentSort.column === column) {
        currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        currentSort.column = column;
        currentSort.direction = 'asc';
    }
    
    // Update sort indicators
    document.querySelectorAll('.node-table th').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
        if (th.dataset.sort === column) {
            th.classList.add(`sort-${currentSort.direction}`);
        }
    });
    
    // Sort data
    nodes.sort((a, b) => {
        let valA = a[column];
        let valB = b[column];
        if (typeof valA === 'string') valA = valA.toLowerCase();
        if (typeof valB === 'string') valB = valB.toLowerCase();
        if (valA < valB) return currentSort.direction === 'asc' ? -1 : 1;
        if (valA > valB) return currentSort.direction === 'asc' ? 1 : -1;
        return 0;
    });
    
    filterNodes();
}

function clearFilters() {
    const searchInput = document.getElementById('searchInput');
    const regionFilter = document.getElementById('regionFilter');
    const statusFilter = document.getElementById('statusFilter');
    const roleFilter = document.getElementById('roleFilter');
    
    if (searchInput) searchInput.value = '';
    if (regionFilter) regionFilter.value = '';
    if (statusFilter) statusFilter.value = '';
    if (roleFilter) roleFilter.value = '';
    
    filterNodes();
}

function updateStats() {
    // Update header stats
    const total = nodes.length;
    const online = nodes.filter(n => n.status === 'online').length;
    const cordoned = nodes.filter(n => n.status === 'cordoned').length;
    const offline = nodes.filter(n => n.status === 'offline').length;
    const draining = nodes.filter(n => n.status === 'draining').length;
    const updating = nodes.filter(n => n.updateStatus === 'updating').length;
    
    // Could update DOM elements here
}

// Action functions
function reconnectNode(nodeId) {
    console.log('Reconnecting node:', nodeId);
    showNotification(`Reconnecting ${nodeId}...`);
}

function cordonNode(nodeId) {
    console.log('Cordoning node:', nodeId);
    showNotification(`Cordoning ${nodeId}...`);
}

function drainNode(nodeId) {
    console.log('Draining node:', nodeId);
    showNotification(`Draining ${nodeId}...`);
}

// Bulk actions
function bulkAction(action) {
    const nodeIds = Array.from(selectedNodes);
    console.log(`Bulk ${action} on:`, nodeIds);
    
    if (nodeIds.length === 0) return;
    
    // Show confirmation modal
    showActionModal(action, nodeIds);
}

function showActionModal(action, nodeIds) {
    const modal = document.getElementById('actionModal');
    const title = document.getElementById('actionModalTitle');
    const text = document.getElementById('actionConfirmText');
    const list = document.getElementById('actionConfirmList');
    
    const actionNames = {
        reconnect: 'Reconnect',
        cordon: 'Cordon',
        drain: 'Drain',
        update: 'Update',
        delete: 'Delete'
    };
    
    title.textContent = `${actionNames[action]} Nodes`;
    text.textContent = `You are about to ${action.toLowerCase()} the following ${nodeIds.length} node(s):`;
    list.innerHTML = nodeIds.map(id => `
        <div class="action-confirm-item">${id}</div>
    `).join('');
    
    modal.classList.add('active');
}

function closeActionModal() {
    document.getElementById('actionModal').classList.remove('active');
}

function confirmBulkAction() {
    console.log('Confirmed bulk action');
    closeActionModal();
    selectedNodes.clear();
    updateSelectionUI();
}

function showAddNodeModal() {
    console.log('Show add node modal');
    // Open add node modal
}

function showNotification(message) {
    // Simple notification implementation
    console.log('Notification:', message);
}
