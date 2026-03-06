/**
 * Topology JavaScript
 * D3.js visualization for network topology
 */

// Configuration
const CONFIG = {
    nodeSize: { coordinator: 18, worker: 14, gateway: 16 },
    colors: {
        coordinator: '#f59e0b',
        worker: '#06b6d4',
        gateway: '#8b5cf6',
        cream: '#f5f5dc',
        error: '#ef4444'
    },
    packetSpeed: 2000,
    refreshRate: 50
};

// State
let simulation;
let svg, g, link, node, packet;
let zoom;
let selectedNode = null;
let isolatedNode = null;
let filters = { coordinator: true, worker: true, gateway: true };
let packets = [];
let contextMenuTarget = null;

// Initialize on load
document.addEventListener('DOMContentLoaded', function() {
    initTopology();
});

function initTopology() {
    initVisualization();
    initEventListeners();
}

// Generate sample data
function generateData() {
    const nodes = [];
    const links = [];
    
    // Coordinators
    for (let i = 0; i < 2; i++) {
        nodes.push({
            id: `coord-${i}`,
            role: 'coordinator',
            status: Math.random() > 0.1 ? 'active' : 'idle',
            uptime: Math.floor(Math.random() * 86400 * 30),
            throughput: Math.floor(Math.random() * 10000),
            x: 400 + i * 200,
            y: 300,
            org: 'acme',
            project: 'platform'
        });
    }
    
    // Gateways
    for (let i = 0; i < 4; i++) {
        nodes.push({
            id: `gw-${i}`,
            role: 'gateway',
            status: Math.random() > 0.15 ? 'active' : 'idle',
            uptime: Math.floor(Math.random() * 86400 * 14),
            throughput: Math.floor(Math.random() * 5000),
            x: 200 + (i % 2) * 400,
            y: 150 + Math.floor(i / 2) * 300,
            org: i % 2 === 0 ? 'acme' : 'globex',
            project: 'ml-inference'
        });
    }
    
    // Workers
    for (let i = 0; i < 12; i++) {
        nodes.push({
            id: `worker-${i}`,
            role: 'worker',
            status: Math.random() > 0.1 ? 'active' : 'error',
            uptime: Math.floor(Math.random() * 86400 * 7),
            throughput: Math.floor(Math.random() * 2000),
            x: 100 + Math.random() * 600,
            y: 100 + Math.random() * 400,
            org: ['acme', 'globex', 'initech'][i % 3],
            project: ['platform', 'ml-inference', 'data-pipeline'][i % 3]
        });
    }
    
    // Create connections
    const coordinators = nodes.filter(n => n.role === 'coordinator');
    const gateways = nodes.filter(n => n.role === 'gateway');
    const workers = nodes.filter(n => n.role === 'worker');
    
    // Connect coordinators to gateways
    coordinators.forEach((coord) => {
        gateways.forEach((gw) => {
            if (Math.random() > 0.3) {
                links.push({
                    source: coord.id,
                    target: gw.id,
                    throughput: Math.floor(Math.random() * 1000)
                });
            }
        });
    });
    
    // Connect gateways to workers
    gateways.forEach((gw) => {
        workers.forEach((worker) => {
            if (Math.random() > 0.6) {
                links.push({
                    source: gw.id,
                    target: worker.id,
                    throughput: Math.floor(Math.random() * 500)
                });
            }
        });
    });
    
    return { nodes, links };
}

// Initialize D3 visualization
function initVisualization() {
    const container = document.querySelector('.topology-canvas');
    const width = container.clientWidth;
    const height = container.clientHeight;
    
    svg = d3.select('#topology-svg')
        .attr('width', width)
        .attr('height', height);
    
    // Zoom behavior
    zoom = d3.zoom()
        .scaleExtent([0.1, 4])
        .on('zoom', (event) => {
            g.attr('transform', event.transform);
        });
    
    svg.call(zoom);
    
    // Main group
    g = svg.append('g');
    
    const data = generateData();
    
    // Force simulation
    simulation = d3.forceSimulation(data.nodes)
        .force('link', d3.forceLink(data.links).id(d => d.id).distance(100))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(40));
    
    // Links
    link = g.append('g')
        .attr('class', 'links')
        .selectAll('line')
        .data(data.links)
        .enter().append('line')
        .attr('class', 'link')
        .attr('stroke-width', d => Math.max(1, Math.log(d.throughput + 1) / 2));
    
    // Packets group
    const packetGroup = g.append('g').attr('class', 'packets');
    
    // Nodes
    node = g.append('g')
        .attr('class', 'nodes')
        .selectAll('g')
        .data(data.nodes)
        .enter().append('g')
        .attr('class', 'node')
        .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended));
    
    // Node shapes
    node.each(function(d) {
        const el = d3.select(this);
        const size = CONFIG.nodeSize[d.role];
        
        if (d.role === 'coordinator') {
            el.append('rect')
                .attr('width', size * 1.5)
                .attr('height', size * 1.5)
                .attr('x', -size * 0.75)
                .attr('y', -size * 0.75)
                .attr('transform', 'rotate(45)')
                .attr('fill', CONFIG.colors.coordinator)
                .attr('class', d.status === 'error' ? 'glow-error' : 'glow-coordinator');
        } else if (d.role === 'gateway') {
            const hexPath = [];
            for (let i = 0; i < 6; i++) {
                const angle = (i * 60 - 30) * Math.PI / 180;
                const x = size * Math.cos(angle);
                const y = size * Math.sin(angle);
                hexPath.push(`${i === 0 ? 'M' : 'L'} ${x} ${y}`);
            }
            hexPath.push('Z');
            
            el.append('path')
                .attr('d', hexPath.join(' '))
                .attr('fill', CONFIG.colors.gateway)
                .attr('class', d.status === 'error' ? 'glow-error' : 'glow-gateway');
        } else {
            el.append('circle')
                .attr('r', size)
                .attr('fill', CONFIG.colors.worker)
                .attr('class', d.status === 'error' ? 'glow-error' : 'glow-worker');
        }
        
        // Label
        el.append('text')
            .attr('class', 'node-label')
            .attr('dy', size + 15)
            .text(d.id);
    });
    
    // Node interactions
    node.on('click', (event, d) => {
        event.stopPropagation();
        selectNode(d);
    });
    
    node.on('dblclick', (event, d) => {
        event.stopPropagation();
        isolateNode(d);
    });
    
    node.on('contextmenu', (event, d) => {
        event.preventDefault();
        showContextMenu(event, d);
    });
    
    // Background click
    svg.on('click', () => {
        clearSelection();
    });
    
    // Simulation tick
    simulation.on('tick', () => {
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);
        
        node.attr('transform', d => `translate(${d.x},${d.y})`);
    });
    
    // Start packet animation
    setInterval(spawnPacket, 300);
    updateStats();
}

// Drag functions
function dragstarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
}

function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
}

function dragended(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
}

// Packet animation
function spawnPacket() {
    if (!link || link.empty()) return;
    
    const activeLinks = link.nodes().map(d => d.__data__).filter(l => {
        return filters[l.source.role] && filters[l.target.role];
    });
    
    if (activeLinks.length === 0) return;
    
    const randomLink = activeLinks[Math.floor(Math.random() * activeLinks.length)];
    // Packet visualization logic here
}

// Selection
function selectNode(d) {
    selectedNode = d;
    
    document.getElementById('selection-empty').style.display = 'none';
    document.getElementById('node-details').classList.add('active');
    
    document.getElementById('detail-id').textContent = d.id;
    document.getElementById('detail-role').textContent = d.role;
    
    const statusEl = document.getElementById('detail-status');
    statusEl.textContent = d.status;
    statusEl.className = `detail-value status-${d.status}`;
    
    document.getElementById('detail-uptime').textContent = formatUptime(d.uptime);
    document.getElementById('detail-connections').textContent = countConnections(d);
    document.getElementById('detail-throughput').textContent = `${d.throughput} req/s`;
    document.getElementById('detail-org').textContent = d.org;
    document.getElementById('detail-project').textContent = d.project;
    
    // Highlight node
    node.style('opacity', n => n.id === d.id ? 1 : 0.3);
    link.style('opacity', l => (l.source.id === d.id || l.target.id === d.id) ? 1 : 0.1);
}

function clearSelection() {
    selectedNode = null;
    
    document.getElementById('selection-empty').style.display = 'block';
    document.getElementById('node-details').classList.remove('active');
    
    if (!isolatedNode) {
        node.style('opacity', 1);
        link.style('opacity', 1);
    }
}

function countConnections(d) {
    return link.nodes().filter(l => 
        l.__data__.source.id === d.id || l.__data__.target.id === d.id
    ).length;
}

function formatUptime(seconds) {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    if (days > 0) return `${days}d ${hours}h`;
    return `${hours}h`;
}

// Isolation mode
function isolateNode(d) {
    if (isolatedNode === d) {
        isolatedNode = null;
        document.querySelector('.topology-canvas').classList.remove('isolated');
        return;
    }
    
    isolatedNode = d;
    document.querySelector('.topology-canvas').classList.add('isolated');
}

// Context menu
function showContextMenu(event, d) {
    contextMenuTarget = d;
    const menu = document.getElementById('contextMenu');
    menu.style.left = `${event.pageX}px`;
    menu.style.top = `${event.pageY}px`;
    menu.classList.add('active');
}

function hideContextMenu() {
    document.getElementById('contextMenu').classList.remove('active');
    contextMenuTarget = null;
}

// View controls
function zoomIn() {
    svg.transition().call(zoom.scaleBy, 1.3);
}

function zoomOut() {
    svg.transition().call(zoom.scaleBy, 0.7);
}

function resetView() {
    svg.transition().call(zoom.transform, d3.zoomIdentity);
    clearSelection();
}

function toggleFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen();
    } else {
        document.exitFullscreen();
    }
}

// Filters
function toggleFilter(el) {
    const filter = el.dataset.filter;
    filters[filter] = !filters[filter];
    el.classList.toggle('active');
    
    node.style('display', d => filters[d.role] ? 'block' : 'none');
    link.style('display', l => 
        filters[l.source.role] && filters[l.target.role] ? 'block' : 'none'
    );
    
    updateStats();
}

function toggleRoleOverlay(el, role) {
    el.classList.toggle('active');
    // Implement role overlay logic
}

// Role overlays
function updateStats() {
    const nodes = node ? node.nodes().map(n => n.__data__).filter(n => filters[n.role]) : [];
    document.getElementById('count-coordinator').textContent = 
        nodes.filter(n => n.role === 'coordinator').length;
    document.getElementById('count-worker').textContent = 
        nodes.filter(n => n.role === 'worker').length;
    document.getElementById('count-gateway').textContent = 
        nodes.filter(n => n.role === 'gateway').length;
}

// Context menu actions
function inspectNode() {
    if (contextMenuTarget) selectNode(contextMenuTarget);
    hideContextMenu();
}

function isolateNodeContext() {
    if (contextMenuTarget) isolateNode(contextMenuTarget);
    hideContextMenu();
}

function rerouteTraffic() {
    console.log('Reroute traffic for:', contextMenuTarget);
    hideContextMenu();
}

function drainNode() {
    console.log('Drain node:', contextMenuTarget);
    hideContextMenu();
}

function viewLogs() {
    console.log('View logs for:', contextMenuTarget);
    hideContextMenu();
}

// Event listeners
function initEventListeners() {
    // Hide context menu on click elsewhere
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.context-menu')) {
            hideContextMenu();
        }
    });
    
    // Physics sliders
    document.getElementById('gravity').addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        document.getElementById('gravity-value').textContent = val.toFixed(2);
        simulation.force('center', d3.forceCenter(
            svg.attr('width') / 2, 
            svg.attr('height') / 2
        ).strength(val * 10));
        simulation.alpha(0.3).restart();
    });
    
    document.getElementById('charge').addEventListener('input', (e) => {
        const val = parseInt(e.target.value);
        document.getElementById('charge-value').textContent = val;
        simulation.force('charge', d3.forceManyBody().strength(val));
        simulation.alpha(0.3).restart();
    });
    
    document.getElementById('distance').addEventListener('input', (e) => {
        const val = parseInt(e.target.value);
        document.getElementById('distance-value').textContent = val;
        simulation.force('link').distance(val);
        simulation.alpha(0.3).restart();
    });
    
    // Org/Project filters
    document.getElementById('orgFilter').addEventListener('change', filterByOrgProject);
    document.getElementById('projectFilter').addEventListener('change', filterByOrgProject);
}

function filterByOrgProject() {
    const org = document.getElementById('orgFilter').value;
    const project = document.getElementById('projectFilter').value;
    
    node.style('display', d => {
        const matchOrg = !org || d.org === org;
        const matchProject = !project || d.project === project;
        const matchRole = filters[d.role];
        return matchOrg && matchProject && matchRole ? 'block' : 'none';
    });
}
