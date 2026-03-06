/**
 * ORDL Security - Audit Page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize APIs
    const api = window.securityApi || (typeof securityApi !== 'undefined' ? securityApi : null);
    const auditApi = window.auditApi || (typeof auditApi !== 'undefined' ? auditApi : null);
    const ui = window.ORDL?.ui;

    // Create Evidence button
    document.querySelector('[data-action="create-evidence"]')?.addEventListener('click', function() {
        openEvidenceModal();
    });

    // New Export button
    document.querySelector('[data-action="new-export"]')?.addEventListener('click', function() {
        openExportModal();
    });

    // Package Evidence button
    document.querySelector('[data-action="package-evidence"]')?.addEventListener('click', async function() {
        const selectedEvents = Array.from(document.querySelectorAll('.audit-event-checkbox:checked')).map(cb => cb.value);
        
        if (selectedEvents.length === 0) {
            ui?.showToast?.('Please select at least one event', 'warning');
            return;
        }
        
        const name = prompt('Enter evidence package name:');
        if (!name) return;
        
        const btn = this;
        const hideSpinner = ui?.showSpinner?.(btn, 'Packaging...');
        
        try {
            await api.packageEvidence(selectedEvents, name);
            ui?.showToast?.(`Evidence package "${name}" created`, 'success');
            ui?.refreshData?.();
        } catch (error) {
            ui?.handleError?.(error, 'Failed to package evidence');
        } finally {
            hideSpinner?.();
        }
    });

    // Pause Stream button
    let streamPaused = false;
    document.querySelector('[data-action="pause-stream"]')?.addEventListener('click', function() {
        streamPaused = !streamPaused;
        this.textContent = streamPaused ? 'Resume' : 'Pause';
        ui?.showToast?.(streamPaused ? 'Audit stream paused' : 'Audit stream resumed', 'info');
    });

    // Jump to Now button
    document.querySelector('[data-action="jump-now"]')?.addEventListener('click', function() {
        const stream = document.getElementById('auditStream');
        if (stream) {
            stream.scrollTop = stream.scrollHeight;
        }
    });

    // Load More button
    document.querySelector('[data-action="load-more"]')?.addEventListener('click', async function() {
        const btn = this;
        const hideSpinner = ui?.showSpinner?.(btn, 'Loading...');
        
        try {
            const currentPage = parseInt(btn.dataset.page || '1');
            const result = await api.getAuditEvents({ page: currentPage + 1, limit: 50 });
            appendAuditEvents(result.items || []);
            btn.dataset.page = currentPage + 1;
            
            if (!result.hasNext) {
                btn.style.display = 'none';
            }
        } catch (error) {
            ui?.handleError?.(error, 'Failed to load more events');
        } finally {
            hideSpinner?.();
        }
    });

    // Export Filtered button
    document.querySelector('[data-action="export-filtered"]')?.addEventListener('click', async function() {
        const severity = document.getElementById('severityFilter')?.value;
        const category = document.getElementById('categoryFilter')?.value;
        
        const btn = this;
        const hideSpinner = ui?.showSpinner?.(btn, 'Exporting...');
        
        try {
            await auditApi.exportAudit({
                format: 'json',
                levels: severity ? [severity] : undefined,
                categories: category ? [category] : undefined
            });
            ui?.showToast?.('Filtered export started', 'success');
        } catch (error) {
            ui?.handleError?.(error, 'Failed to export');
        } finally {
            hideSpinner?.();
        }
    });

    // Download job buttons
    document.querySelectorAll('[data-action="download"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const jobId = this.dataset.job;
            const hideSpinner = ui?.showSpinner?.(this, 'Downloading...');
            
            try {
                const blob = await api.downloadExportJob(jobId);
                downloadBlob(blob, `audit-export-${jobId}.zip`);
                ui?.showToast?.('Download started', 'success');
            } catch (error) {
                ui?.handleError?.(error, 'Failed to download export');
            } finally {
                hideSpinner?.();
            }
        });
    });

    // Verify job buttons
    document.querySelectorAll('[data-action="verify"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const jobId = this.dataset.job;
            const hideSpinner = ui?.showSpinner?.(this, 'Verifying...');
            
            try {
                const result = await api.verifyExportJob(jobId);
                if (result.valid) {
                    ui?.showToast?.('Export verified successfully', 'success');
                } else {
                    ui?.showToast?.('Export verification failed', 'error');
                }
            } catch (error) {
                ui?.handleError?.(error, 'Failed to verify export');
            } finally {
                hideSpinner?.();
            }
        });
    });

    // Delete job buttons
    document.querySelectorAll('[data-action="delete-job"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const jobId = this.dataset.job;
            
            const confirmed = await ui?.confirmDialog?.(
                `Delete export job ${jobId}?`,
                { title: 'Delete Export', confirmText: 'Delete', confirmClass: 'danger' }
            );
            
            if (!confirmed) return;
            
            const hideSpinner = ui?.showSpinner?.(this, 'Deleting...');
            
            try {
                await api.deleteExportJob(jobId);
                ui?.showToast?.('Export job deleted', 'success');
                ui?.refreshData?.();
            } catch (error) {
                ui?.handleError?.(error, 'Failed to delete export');
            } finally {
                hideSpinner?.();
            }
        });
    });

    // Download package buttons
    document.querySelectorAll('[data-action="download-pkg"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const pkgId = this.dataset.pkg;
            const hideSpinner = ui?.showSpinner?.(this, 'Downloading...');
            
            try {
                const blob = await api.downloadEvidencePackage(pkgId);
                downloadBlob(blob, `evidence-${pkgId}.zip`);
                ui?.showToast?.('Download started', 'success');
            } catch (error) {
                ui?.handleError?.(error, 'Failed to download package');
            } finally {
                hideSpinner?.();
            }
        });
    });

    // View chain buttons
    document.querySelectorAll('[data-action="chain-pkg"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const pkgId = this.dataset.pkg;
            const hideSpinner = ui?.showSpinner?.(this, 'Loading...');
            
            try {
                const chain = await api.getEvidenceChain(pkgId);
                openChainModal(chain, pkgId);
            } catch (error) {
                ui?.handleError?.(error, 'Failed to load evidence chain');
            } finally {
                hideSpinner?.();
            }
        });
    });

    // Filters
    const severityFilter = document.getElementById('severityFilter');
    const categoryFilter = document.getElementById('categoryFilter');
    
    if (severityFilter) {
        severityFilter.addEventListener('change', filterEvents);
    }
    
    if (categoryFilter) {
        categoryFilter.addEventListener('change', filterEvents);
    }

    async function filterEvents() {
        const severity = severityFilter?.value;
        const category = categoryFilter?.value;
        
        const hideSpinner = ui?.showGlobalLoading?.('Filtering...');
        
        try {
            const result = await api.getAuditEvents({ 
                severity, 
                category, 
                page: 1, 
                limit: 50 
            });
            updateAuditEvents(result.items || []);
        } catch (error) {
            // Fallback to client-side filtering
            document.querySelectorAll('.audit-event').forEach(event => {
                let show = true;
                if (severity && !event.classList.contains(severity)) show = false;
                if (category && event.dataset.category !== category) show = false;
                event.style.display = show ? '' : 'none';
            });
        } finally {
            hideSpinner?.();
        }
    }

    function updateAuditEvents(events) {
        // FIXME: backend gap - implement full event list rendering
        ui?.showToast?.('Audit events updated from API', 'info');
        console.log('Events to render:', events);
    }

    function appendAuditEvents(events) {
        const container = document.getElementById('auditStream');
        if (!container) return;
        
        events.forEach(event => {
            const eventEl = document.createElement('div');
            eventEl.className = `audit-event ${event.severity}`;
            eventEl.dataset.category = event.category;
            eventEl.innerHTML = `
                <div class="timestamp">${escapeHtml(event.timestamp)}</div>
                <div class="severity ${event.severity}">${event.severity.toUpperCase()}</div>
                <div class="action">${escapeHtml(event.action)}</div>
            `;
            container.appendChild(eventEl);
        });
    }

    function openEvidenceModal() {
        const modalHtml = `
            <div id="evidence-modal" class="modal" style="display: block; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 1000;">
                <div style="background: #1a1a1a; max-width: 500px; margin: 50px auto; padding: 24px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5;">
                    <h3>Create Evidence Package</h3>
                    <form id="evidence-form">
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Package Name *</label>
                            <input type="text" name="name" required style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Case ID</label>
                            <input type="text" name="caseId" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Description</label>
                            <textarea name="description" rows="3" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px; resize: vertical;"></textarea>
                        </div>
                        <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px;">
                            <button type="button" class="cancel-btn" style="padding: 8px 16px; background: transparent; border: 1px solid rgba(255,255,255,0.2); color: #d4cfc7; border-radius: 4px; cursor: pointer;">Cancel</button>
                            <button type="submit" style="padding: 8px 16px; background: #f59e0b; border: none; color: #0d0d0d; border-radius: 4px; cursor: pointer; font-weight: 500;">Create Package</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = document.getElementById('evidence-modal');
        const form = document.getElementById('evidence-form');
        
        modal.querySelector('.cancel-btn').addEventListener('click', () => {
            modal.remove();
        });
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = form.querySelector('button[type="submit"]');
            const hideSpinner = ui?.showSpinner?.(submitBtn, 'Creating...');
            
            try {
                const formData = new FormData(form);
                await api.createEvidencePackage({
                    name: formData.get('name'),
                    caseId: formData.get('caseId'),
                    description: formData.get('description')
                });
                ui?.showToast?.('Evidence package created successfully', 'success');
                modal.remove();
                ui?.refreshData?.();
            } catch (error) {
                ui?.handleError?.(error, 'Failed to create evidence package');
            } finally {
                hideSpinner?.();
            }
        });
    }

    function openExportModal() {
        const modalHtml = `
            <div id="export-modal" class="modal" style="display: block; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 1000;">
                <div style="background: #1a1a1a; max-width: 500px; margin: 50px auto; padding: 24px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5;">
                    <h3>New Export Job</h3>
                    <form id="export-form">
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Start Date</label>
                            <input type="date" name="startDate" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">End Date</label>
                            <input type="date" name="endDate" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Severity Filter</label>
                            <select name="severity" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                                <option value="">All Severities</option>
                                <option value="critical">Critical</option>
                                <option value="high">High</option>
                                <option value="medium">Medium</option>
                                <option value="low">Low</option>
                                <option value="info">Info</option>
                            </select>
                        </div>
                        <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px;">
                            <button type="button" class="cancel-btn" style="padding: 8px 16px; background: transparent; border: 1px solid rgba(255,255,255,0.2); color: #d4cfc7; border-radius: 4px; cursor: pointer;">Cancel</button>
                            <button type="submit" style="padding: 8px 16px; background: #f59e0b; border: none; color: #0d0d0d; border-radius: 4px; cursor: pointer; font-weight: 500;">Create Export</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = document.getElementById('export-modal');
        const form = document.getElementById('export-form');
        
        modal.querySelector('.cancel-btn').addEventListener('click', () => {
            modal.remove();
        });
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = form.querySelector('button[type="submit"]');
            const hideSpinner = ui?.showSpinner?.(submitBtn, 'Creating...');
            
            try {
                const formData = new FormData(form);
                await api.createExportJob({
                    startDate: formData.get('startDate'),
                    endDate: formData.get('endDate'),
                    severity: formData.get('severity') || undefined
                });
                ui?.showToast?.('Export job created successfully', 'success');
                modal.remove();
                ui?.refreshData?.();
            } catch (error) {
                ui?.handleError?.(error, 'Failed to create export job');
            } finally {
                hideSpinner?.();
            }
        });
    }

    function openChainModal(chain, pkgId) {
        const modalHtml = `
            <div id="chain-modal" class="modal" style="display: block; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 1000;">
                <div style="background: #1a1a1a; max-width: 600px; margin: 50px auto; padding: 24px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; max-height: 80vh; overflow-y: auto;">
                    <h3>Evidence Chain - ${pkgId}</h3>
                    <div style="margin-top: 16px;">
                        <pre style="color: #d4cfc7; font-size: 12px; overflow-x: auto; background: rgba(0,0,0,0.3); padding: 16px; border-radius: 4px;">${escapeHtml(JSON.stringify(chain, null, 2))}</pre>
                    </div>
                    <div style="display: flex; justify-content: flex-end; margin-top: 20px;">
                        <button type="button" class="close-btn" style="padding: 8px 16px; background: transparent; border: 1px solid rgba(255,255,255,0.2); color: #d4cfc7; border-radius: 4px; cursor: pointer;">Close</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = document.getElementById('chain-modal');
        modal.querySelector('.close-btn').addEventListener('click', () => {
            modal.remove();
        });
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    }

    function downloadBlob(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Simulate live stream updates
    setInterval(() => {
        if (!streamPaused) {
            // In production, this would fetch new events
            // console.log('Checking for new events...');
        }
    }, 5000);
});
