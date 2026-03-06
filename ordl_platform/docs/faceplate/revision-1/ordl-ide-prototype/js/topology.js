/**
 * ORDL IDE - Swarm Topology Visualization
 * Force-directed graph showing agent communication topology
 * Industrial, precise, deterministic aesthetic
 */

class SwarmTopology {
  constructor(containerId, options = {}) {
    this.containerId = containerId;
    this.container = document.getElementById(containerId);
    if (!this.container) {
      throw new Error(`Container #${containerId} not found`);
    }

    // Configuration
    this.config = {
      width: options.width || this.container.clientWidth || 800,
      height: options.height || this.container.clientHeight || 600,
      nodeRadius: options.nodeRadius || 20,
      linkDistance: options.linkDistance || 120,
      chargeStrength: options.chargeStrength || -400,
      collisionRadius: options.collisionRadius || 35,
      ...options
    };

    // Color palette - industrial, precise
    this.colors = {
      cream: '#F5F5DC',
      charcoal: '#36454F',
      amber: '#FFBF00',
      creamDim: '#C4C4B0',
      charcoalLight: '#4A5A64'
    };

    // State
    this.nodes = [];
    this.links = [];
    this.selectedNode = null;
    this.activeNodes = new Set();
    this.packetAnimations = [];
    this.eventListeners = {};

    this.init();
  }

  init() {
    this.setupSVG();
    this.setupDefs();
    this.setupSimulation();
    this.setupZoom();
    this.generateMockData();
    this.render();
    this.startAnimations();
  }

  setupSVG() {
    // Clear container
    this.container.innerHTML = '';

    // Create SVG with dark background
    this.svg = d3.select(this.container)
      .append('svg')
      .attr('width', this.config.width)
      .attr('height', this.config.height)
      .attr('viewBox', [0, 0, this.config.width, this.config.height])
      .style('background', '#1a1a1a')
      .style('border-radius', '4px');

    // Main group for zoom/pan
    this.g = this.svg.append('g');

    // Layers for z-ordering
    this.linkLayer = this.g.append('g').attr('class', 'links');
    this.packetLayer = this.g.append('g').attr('class', 'packets');
    this.nodeLayer = this.g.append('g').attr('class', 'nodes');
  }

  setupDefs() {
    const defs = this.svg.append('defs');

    // Glow filter for active nodes
    const glowFilter = defs.append('filter')
      .attr('id', 'glow')
      .attr('x', '-50%')
      .attr('y', '-50%')
      .attr('width', '200%')
      .attr('height', '200%');

    glowFilter.append('feGaussianBlur')
      .attr('stdDeviation', '4')
      .attr('result', 'coloredBlur');

    const feMerge = glowFilter.append('feMerge');
    feMerge.append('feMergeNode').attr('in', 'coloredBlur');
    feMerge.append('feMergeNode').attr('in', 'SourceGraphic');

    // Pulse animation gradient
    const pulseGradient = defs.append('radialGradient')
      .attr('id', 'pulse-gradient')
      .attr('cx', '50%')
      .attr('cy', '50%')
      .attr('r', '50%');

    pulseGradient.append('stop')
      .attr('offset', '0%')
      .attr('stop-color', this.colors.cream)
      .attr('stop-opacity', '0.8');

    pulseGradient.append('stop')
      .attr('offset', '100%')
      .attr('stop-color', this.colors.cream)
      .attr('stop-opacity', '0');

    // Selected node gradient
    const selectedGradient = defs.append('radialGradient')
      .attr('id', 'selected-gradient')
      .attr('cx', '50%')
      .attr('cy', '50%')
      .attr('r', '50%');

    selectedGradient.append('stop')
      .attr('offset', '0%')
      .attr('stop-color', this.colors.amber)
      .attr('stop-opacity', '0.6');

    selectedGradient.append('stop')
      .attr('offset', '100%')
      .attr('stop-color', this.colors.amber)
      .attr('stop-opacity', '0');
  }

  setupSimulation() {
    this.simulation = d3.forceSimulation()
      .force('link', d3.forceLink().id(d => d.id).distance(this.config.linkDistance))
      .force('charge', d3.forceManyBody().strength(this.config.chargeStrength))
      .force('center', d3.forceCenter(this.config.width / 2, this.config.height / 2))
      .force('collision', d3.forceCollide().radius(this.config.collisionRadius));
  }

  setupZoom() {
    this.zoom = d3.zoom()
      .scaleExtent([0.3, 4])
      .on('zoom', (event) => {
        this.g.attr('transform', event.transform);
      });

    this.svg.call(this.zoom);
  }

  generateMockData() {
    // Agent definitions - industrial naming convention
    const agentTypes = [
      { prefix: 'alpha', role: 'coordinator' },
      { prefix: 'beta', role: 'worker' },
      { prefix: 'gamma', role: 'worker' },
      { prefix: 'delta', role: 'processor' },
      { prefix: 'epsilon', role: 'processor' },
      { prefix: 'zeta', role: 'worker' },
      { prefix: 'eta', role: 'relay' },
      { prefix: 'theta', role: 'worker' },
      { prefix: 'iota', role: 'storage' },
      { prefix: 'kappa', role: 'monitor' }
    ];

    // Create nodes
    this.nodes = agentTypes.map((type, i) => ({
      id: `${type.prefix}-0${(i % 3) + 1}`,
      name: `${type.prefix}-0${(i % 3) + 1}`,
      role: type.role,
      status: Math.random() > 0.3 ? 'active' : 'idle',
      throughput: Math.floor(Math.random() * 1000) + 100,
      x: this.config.width / 2 + (Math.random() - 0.5) * 200,
      y: this.config.height / 2 + (Math.random() - 0.5) * 200
    }));

    // Mark some nodes as active for pulsing animation
    this.nodes.forEach(node => {
      if (node.status === 'active' && Math.random() > 0.5) {
        this.activeNodes.add(node.id);
      }
    });

    // Create links - mesh-like topology with some hierarchy
    const linkPatterns = [
      [0, 1], [0, 2], [0, 6],      // alpha connects to beta, gamma, eta
      [1, 3], [1, 4],              // beta connects to delta, epsilon
      [2, 5], [2, 7],              // gamma connects to zeta, theta
      [3, 8], [4, 8],              // delta, epsilon connect to iota (storage)
      [6, 9], [7, 9],              // eta, theta connect to kappa (monitor)
      [5, 6], [3, 6],              // cross connections
      [1, 7], [4, 5]               // additional redundancy
    ];

    this.links = linkPatterns.map(([source, target], i) => ({
      id: `link-${i}`,
      source: this.nodes[source].id,
      target: this.nodes[target].id,
      throughput: Math.floor(Math.random() * 500) + 50,
      active: Math.random() > 0.3
    }));
  }

  render() {
    this.renderLinks();
    this.renderNodes();
    this.updateSimulation();
  }

  renderLinks() {
    this.linkElements = this.linkLayer
      .selectAll('line.link')
      .data(this.links, d => d.id)
      .join('line')
      .attr('class', 'link')
      .attr('stroke', this.colors.creamDim)
      .attr('stroke-width', d => this.getLinkWidth(d))
      .attr('stroke-opacity', d => d.active ? 0.8 : 0.3)
      .attr('stroke-linecap', 'round');
  }

  renderNodes() {
    // Node groups
    this.nodeGroups = this.nodeLayer
      .selectAll('g.node-group')
      .data(this.nodes, d => d.id)
      .join('g')
      .attr('class', 'node-group')
      .style('cursor', 'pointer')
      .call(this.drag());

    // Pulse rings for active nodes
    this.pulseRings = this.nodeGroups
      .selectAll('circle.pulse-ring')
      .data(d => this.activeNodes.has(d.id) ? [d] : [])
      .join('circle')
      .attr('class', 'pulse-ring')
      .attr('r', this.config.nodeRadius)
      .attr('fill', 'url(#pulse-gradient)')
      .attr('opacity', 0);

    // Selection halo
    this.selectionHalos = this.nodeGroups
      .selectAll('circle.selection-halo')
      .data(d => d.id === this.selectedNode?.id ? [d] : [])
      .join('circle')
      .attr('class', 'selection-halo')
      .attr('r', this.config.nodeRadius + 8)
      .attr('fill', 'url(#selected-gradient)')
      .attr('opacity', 0.8);

    // Main node circles
    this.nodeCircles = this.nodeGroups
      .selectAll('circle.node')
      .data(d => [d])
      .join('circle')
      .attr('class', 'node')
      .attr('r', this.config.nodeRadius)
      .attr('fill', this.colors.charcoal)
      .attr('stroke', this.colors.cream)
      .attr('stroke-width', 2)
      .attr('filter', d => this.activeNodes.has(d.id) ? 'url(#glow)' : null);

    // Node labels
    this.nodeLabels = this.nodeGroups
      .selectAll('text.node-label')
      .data(d => [d])
      .join('text')
      .attr('class', 'node-label')
      .attr('dy', this.config.nodeRadius + 15)
      .attr('text-anchor', 'middle')
      .attr('fill', this.colors.cream)
      .attr('font-family', 'monospace')
      .attr('font-size', '10px')
      .attr('font-weight', '400')
      .text(d => d.name);

    // Role indicators (small dot)
    this.nodeGroups
      .selectAll('circle.role-indicator')
      .data(d => [d])
      .join('circle')
      .attr('class', 'role-indicator')
      .attr('r', 4)
      .attr('cx', this.config.nodeRadius - 6)
      .attr('cy', -this.config.nodeRadius + 6)
      .attr('fill', d => this.getRoleColor(d.role));

    // Click handlers
    this.nodeGroups.on('click', (event, d) => {
      event.stopPropagation();
      this.selectNode(d);
    });

    // Click background to deselect
    this.svg.on('click', () => {
      this.deselectNode();
    });
  }

  updateSimulation() {
    this.simulation
      .nodes(this.nodes)
      .on('tick', () => this.tick());

    this.simulation.force('link').links(this.links);
    this.simulation.alpha(1).restart();
  }

  tick() {
    // Update link positions
    this.linkElements
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y);

    // Update node positions
    this.nodeGroups
      .attr('transform', d => `translate(${d.x},${d.y})`);
  }

  drag() {
    return d3.drag()
      .on('start', (event, d) => {
        if (!event.active) this.simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on('drag', (event, d) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on('end', (event, d) => {
        if (!event.active) this.simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      });
  }

  // Animation system
  startAnimations() {
    this.animatePulses();
    this.spawnPackets();
  }

  animatePulses() {
    const pulseDuration = 2000;
    
    const pulse = () => {
      this.pulseRings
        .transition()
        .duration(pulseDuration)
        .ease(d3.easeCubicOut)
        .attr('r', this.config.nodeRadius * 2)
        .attr('opacity', 0)
        .on('end', function() {
          d3.select(this)
            .attr('r', this.config.nodeRadius)
            .attr('opacity', 0.6);
        }.bind(this));
    };

    // Continuous pulse animation
    setInterval(pulse, pulseDuration / 2);
    pulse();
  }

  spawnPackets() {
    // Spawn message packets traveling along edges
    const spawnInterval = 800;
    
    setInterval(() => {
      const activeLinks = this.links.filter(l => l.active);
      if (activeLinks.length === 0) return;

      // Select random active link
      const link = activeLinks[Math.floor(Math.random() * activeLinks.length)];
      this.createPacket(link);
    }, spawnInterval);
  }

  createPacket(link) {
    const packet = this.packetLayer
      .append('circle')
      .attr('class', 'packet')
      .attr('r', 3)
      .attr('fill', this.colors.cream)
      .attr('opacity', 0.9);

    const duration = 1500 + Math.random() * 1000;
    
    packet
      .attr('cx', link.source.x)
      .attr('cy', link.source.y)
      .transition()
      .duration(duration)
      .ease(d3.easeLinear)
      .attr('cx', link.target.x)
      .attr('cy', link.target.y)
      .on('end', function() {
        d3.select(this).remove();
      })
      .tween('progress', function() {
        return function(t) {
          // Update position during transition to follow moving nodes
          const x = link.source.x + (link.target.x - link.source.x) * t;
          const y = link.source.y + (link.target.y - link.source.y) * t;
          d3.select(this).attr('cx', x).attr('cy', y);
        };
      });
  }

  // Selection
  selectNode(node) {
    this.selectedNode = node;
    this.renderNodes(); // Re-render to show selection halo
    this.emit('nodeSelected', node);
  }

  deselectNode() {
    this.selectedNode = null;
    this.renderNodes();
    this.emit('nodeDeselected');
  }

  // Helpers
  getLinkWidth(link) {
    if (!link.active) return 1;
    return 1 + (link.throughput / 500) * 2;
  }

  getRoleColor(role) {
    const colors = {
      coordinator: '#FF6B6B',
      worker: '#4ECDC4',
      processor: '#45B7D1',
      relay: '#96CEB4',
      storage: '#FFEAA7',
      monitor: '#DDA0DD'
    };
    return colors[role] || this.colors.cream;
  }

  // Event system
  on(event, callback) {
    if (!this.eventListeners[event]) {
      this.eventListeners[event] = [];
    }
    this.eventListeners[event].push(callback);
  }

  emit(event, data) {
    if (this.eventListeners[event]) {
      this.eventListeners[event].forEach(cb => cb(data));
    }
  }

  // Public API
  setNodeActive(nodeId, active) {
    if (active) {
      this.activeNodes.add(nodeId);
    } else {
      this.activeNodes.delete(nodeId);
    }
    this.renderNodes();
  }

  updateThroughput(linkId, throughput) {
    const link = this.links.find(l => l.id === linkId);
    if (link) {
      link.throughput = throughput;
      this.renderLinks();
    }
  }

  getSelectedNode() {
    return this.selectedNode;
  }

  resize(width, height) {
    this.config.width = width;
    this.config.height = height;
    this.svg
      .attr('width', width)
      .attr('height', height)
      .attr('viewBox', [0, 0, width, height]);
    this.simulation.force('center', d3.forceCenter(width / 2, height / 2));
    this.simulation.alpha(0.3).restart();
  }

  destroy() {
    this.simulation.stop();
    this.svg.remove();
  }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { SwarmTopology };
}
