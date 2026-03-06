// NEXUS COMMAND v4.0.0 - Enhanced Frontend with ALL Systems
// Additional data and methods for complete functionality

const NEXUS_ENHANCEMENTS = {
    // Additional navigation items
    extraNavItems: [
        { id: 'tools', label: 'Tools & Code', icon: 'fas fa-tools' },
        { id: 'mcp', label: 'MCP Servers', icon: 'fas fa-plug' },
        { id: 'knowledge', label: 'Knowledge Base', icon: 'fas fa-brain' },
        { id: 'files', label: 'File Uploads', icon: 'fas fa-folder-open' },
        { id: 'conversations', label: 'Conversations', icon: 'fas fa-history' }
    ],
    
    // Additional data properties
    extraData() {
        return {
            // Tools System
            tools: { list: [], viewingTool: null, editingTool: false },
            newTool: { name: '', description: '', code: '', language: 'python' },
            codeExecution: { code: '', result: null, loading: false },
            
            // MCP Servers
            mcpServers: { list: [], viewingServer: null },
            newMcpServer: { name: '', endpoint: '', type: 'http', auth_token: '' },
            
            // Knowledge Base
            knowledgeBase: { entries: [], viewingEntry: null, editingEntry: false },
            newKnowledgeEntry: { title: '', content: '', category: 'general', tags: '' },
            kbSearchQuery: '',
            kbSearchResults: [],
            
            // Files
            files: { list: [], viewingFile: null },
            fileUploadProgress: 0,
            
            // Conversations
            conversations: { list: [], viewingConversation: null },
            
            // Enhanced Research
            researchActions: {
                continueUrl: '',
                shareData: null
            },
            
            // Enhanced Agent View
            agentFilter: 'all',
            
            // System Events
            systemEvents: [],
            showSystemEvents: false
        };
    },
    
    // Additional methods
    extraMethods: {
        // ============ TOOLS API ============
        async fetchTools() {
            try {
                const response = await fetch('/api/tools', {
                    headers: { 'Authorization': `Bearer ${this.authForm.token}` }
                });
                if (response.ok) {
                    const data = await response.json();
                    this.tools.list = data.tools || [];
                }
            } catch (e) {}
        },
        
        async createTool() {
            try {
                const response = await fetch('/api/tools', {
                    method: 'POST',
                    headers: { 
                        'Authorization': `Bearer ${this.authForm.token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(this.newTool)
                });
                if (response.ok) {
                    this.tools.editingTool = false;
                    this.newTool = { name: '', description: '', code: '', language: 'python' };
                    await this.fetchTools();
                }
            } catch (e) {
                alert('Failed to create tool: ' + e.message);
            }
        },
        
        async deleteTool(toolId) {
            if (!confirm('Delete this tool?')) return;
            try {
                await fetch(`/api/tools/${toolId}`, {
                    method: 'DELETE',
                    headers: { 'Authorization': `Bearer ${this.authForm.token}` }
                });
                await this.fetchTools();
            } catch (e) {}
        },
        
        async executeCode() {
            if (!this.codeExecution.code.trim()) return;
            this.codeExecution.loading = true;
            this.codeExecution.result = null;
            
            try {
                const response = await fetch('/api/tools/code_execution', {
                    method: 'POST',
                    headers: { 
                        'Authorization': `Bearer ${this.authForm.token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ code: this.codeExecution.code })
                });
                this.codeExecution.result = await response.json();
            } catch (e) {
                this.codeExecution.result = { success: false, error: e.message };
            }
            this.codeExecution.loading = false;
        },
        
        // ============ MCP SERVERS ============
        async fetchMcpServers() {
            try {
                const response = await fetch('/api/mcp/servers', {
                    headers: { 'Authorization': `Bearer ${this.authForm.token}` }
                });
                if (response.ok) {
                    const data = await response.json();
                    this.mcpServers.list = data.servers || [];
                }
            } catch (e) {}
        },
        
        async createMcpServer() {
            try {
                const response = await fetch('/api/mcp/servers', {
                    method: 'POST',
                    headers: { 
                        'Authorization': `Bearer ${this.authForm.token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(this.newMcpServer)
                });
                if (response.ok) {
                    this.newMcpServer = { name: '', endpoint: '', type: 'http', auth_token: '' };
                    await this.fetchMcpServers();
                }
            } catch (e) {
                alert('Failed to create MCP server: ' + e.message);
            }
        },
        
        async connectMcpServer(serverId) {
            try {
                await fetch(`/api/mcp/servers/${serverId}/connect`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${this.authForm.token}` }
                });
                await this.fetchMcpServers();
            } catch (e) {}
        },
        
        async deleteMcpServer(serverId) {
            if (!confirm('Delete this MCP server?')) return;
            try {
                await fetch(`/api/mcp/servers/${serverId}`, {
                    method: 'DELETE',
                    headers: { 'Authorization': `Bearer ${this.authForm.token}` }
                });
                await this.fetchMcpServers();
            } catch (e) {}
        },
        
        // ============ KNOWLEDGE BASE ============
        async fetchKnowledgeBase() {
            try {
                const response = await fetch('/api/knowledge', {
                    headers: { 'Authorization': `Bearer ${this.authForm.token}` }
                });
                if (response.ok) {
                    const data = await response.json();
                    this.knowledgeBase.entries = data.entries || [];
                }
            } catch (e) {}
        },
        
        async searchKnowledgeBase() {
            if (!this.kbSearchQuery.trim()) return;
            try {
                const response = await fetch('/api/knowledge/search', {
                    method: 'POST',
                    headers: { 
                        'Authorization': `Bearer ${this.authForm.token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ query: this.kbSearchQuery })
                });
                if (response.ok) {
                    this.kbSearchResults = await response.json();
                }
            } catch (e) {}
        },
        
        async createKnowledgeEntry() {
            try {
                const response = await fetch('/api/knowledge', {
                    method: 'POST',
                    headers: { 
                        'Authorization': `Bearer ${this.authForm.token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        ...this.newKnowledgeEntry,
                        tags: this.newKnowledgeEntry.tags.split(',').map(t => t.trim()).filter(t => t)
                    })
                });
                if (response.ok) {
                    this.knowledgeBase.editingEntry = false;
                    this.newKnowledgeEntry = { title: '', content: '', category: 'general', tags: '' };
                    await this.fetchKnowledgeBase();
                }
            } catch (e) {}
        },
        
        async deleteKnowledgeEntry(entryId) {
            if (!confirm('Delete this knowledge entry?')) return;
            try {
                await fetch(`/api/knowledge/${entryId}`, {
                    method: 'DELETE',
                    headers: { 'Authorization': `Bearer ${this.authForm.token}` }
                });
                await this.fetchKnowledgeBase();
            } catch (e) {}
        },
        
        // ============ FILES ============
        async fetchFiles() {
            try {
                const response = await fetch('/api/files', {
                    headers: { 'Authorization': `Bearer ${this.authForm.token}` }
                });
                if (response.ok) {
                    const data = await response.json();
                    this.files.list = data.files || [];
                }
            } catch (e) {}
        },
        
        async uploadFile(event) {
            const file = event.target.files[0];
            if (!file) return;
            
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const response = await fetch('/api/files/upload', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${this.authForm.token}` },
                    body: formData
                });
                if (response.ok) {
                    await this.fetchFiles();
                    event.target.value = '';
                }
            } catch (e) {
                alert('Upload failed: ' + e.message);
            }
        },
        
        async deleteFile(fileId) {
            if (!confirm('Delete this file?')) return;
            try {
                await fetch(`/api/files/${fileId}`, {
                    method: 'DELETE',
                    headers: { 'Authorization': `Bearer ${this.authForm.token}` }
                });
                await this.fetchFiles();
            } catch (e) {}
        },
        
        async analyzeFile(fileId) {
            try {
                const response = await fetch('/api/tools/file_analysis', {
                    method: 'POST',
                    headers: { 
                        'Authorization': `Bearer ${this.authForm.token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ file_id: fileId })
                });
                if (response.ok) {
                    const analysis = await response.json();
                    this.files.viewingFile = { ...this.files.viewingFile, analysis };
                }
            } catch (e) {}
        },
        
        // ============ CONVERSATIONS ============
        async fetchConversations() {
            try {
                const response = await fetch('/api/conversations', {
                    headers: { 'Authorization': `Bearer ${this.authForm.token}` }
                });
                if (response.ok) {
                    const data = await response.json();
                    this.conversations.list = data.conversations || [];
                }
            } catch (e) {}
        },
        
        async loadConversation(convId) {
            try {
                const response = await fetch(`/api/conversations/${convId}`, {
                    headers: { 'Authorization': `Bearer ${this.authForm.token}` }
                });
                if (response.ok) {
                    this.conversations.viewingConversation = await response.json();
                }
            } catch (e) {}
        },
        
        async deleteConversation(convId) {
            if (!confirm('Delete this conversation?')) return;
            try {
                await fetch(`/api/conversations/${convId}`, {
                    method: 'DELETE',
                    headers: { 'Authorization': `Bearer ${this.authForm.token}` }
                });
                await this.fetchConversations();
            } catch (e) {}
        },
        
        // ============ ENHANCED RESEARCH ACTIONS ============
        async continueResearch(taskId, url) {
            if (!url) return;
            try {
                await fetch(`/api/research/tasks/${taskId}/action`, {
                    method: 'POST',
                    headers: { 
                        'Authorization': `Bearer ${this.authForm.token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ action: 'continue', url })
                });
                this.researchActions.continueUrl = '';
                await this.fetchResearchTasks();
            } catch (e) {}
        },
        
        async dropResearch(taskId) {
            if (!confirm('Drop this research task?')) return;
            try {
                await fetch(`/api/research/tasks/${taskId}/action`, {
                    method: 'POST',
                    headers: { 
                        'Authorization': `Bearer ${this.authForm.token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ action: 'drop' })
                });
                await this.fetchResearchTasks();
            } catch (e) {}
        },
        
        async shareResearch(taskId) {
            try {
                const response = await fetch(`/api/research/tasks/${taskId}/action`, {
                    method: 'POST',
                    headers: { 
                        'Authorization': `Bearer ${this.authForm.token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ action: 'share' })
                });
                if (response.ok) {
                    const data = await response.json();
                    this.researchActions.shareData = data.task?.share_data;
                }
            } catch (e) {}
        },
        
        // ============ AGENT ENHANCEMENTS ============
        async assignTaskToAgent(agentId) {
            const task = prompt('Enter task description:');
            if (!task) return;
            
            try {
                const response = await fetch(`/api/agents/${agentId}/assign`, {
                    method: 'POST',
                    headers: { 
                        'Authorization': `Bearer ${this.authForm.token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ type: 'direct', description: task })
                });
                if (response.ok) {
                    const data = await response.json();
                    alert('Task completed! Check the response below:\n\n' + data.result.substring(0, 500) + '...');
                    await this.fetchAgents();
                }
            } catch (e) {}
        },
        
        // ============ TRAINING ENHANCEMENTS ============
        async deployModel(modelId) {
            if (!confirm('Deploy this model to production?')) return;
            try {
                await fetch(`/api/models/custom/${modelId}/deploy`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${this.authForm.token}` }
                });
                await this.fetchCustomModels();
            } catch (e) {}
        },
        
        // ============ SYSTEM EVENTS ============
        async fetchSystemEvents() {
            try {
                const response = await fetch('/api/system/events?limit=50', {
                    headers: { 'Authorization': `Bearer ${this.authForm.token}` }
                });
                if (response.ok) {
                    const data = await response.json();
                    this.systemEvents = data.events || [];
                }
            } catch (e) {}
        },
        
        // ============ NETWORK ENHANCEMENTS ============
        async startPacketCapture() {
            try {
                const response = await fetch('/api/network/capture', {
                    method: 'POST',
                    headers: { 
                        'Authorization': `Bearer ${this.authForm.token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ interface: 'eth0' })
                });
                if (response.ok) {
                    this.network.capturing = true;
                }
            } catch (e) {}
        },
        
        // ============ UTILITY ============
        formatBytes(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
    }
};

// Export for use in main app
window.NEXUS_ENHANCEMENTS = NEXUS_ENHANCEMENTS;
