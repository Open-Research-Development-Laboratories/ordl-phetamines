/**
 * ORDL Governance - Seats Page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize governance API
    const api = window.governanceApi || (typeof governanceApi !== 'undefined' ? governanceApi : null);
    const ui = window.ORDL?.ui;

    // Create Seat button
    document.querySelector('[data-action="create-seat"]')?.addEventListener('click', function() {
        openSeatModal();
    });

    // Bulk Assign button
    document.querySelector('[data-action="bulk-assign"]')?.addEventListener('click', async function() {
        const selectedSeats = Array.from(document.querySelectorAll('.seat-checkbox:checked')).map(cb => cb.value);
        
        if (selectedSeats.length === 0) {
            ui?.showToast?.('Please select at least one seat', 'warning');
            return;
        }
        
        const occupant = prompt('Enter occupant ID or name:');
        if (!occupant) return;
        
        const confirmed = await ui?.confirmDialog?.(
            `Assign ${occupant} to ${selectedSeats.length} selected seat(s)?`,
            { title: 'Bulk Assign', confirmText: 'Assign' }
        );
        
        if (!confirmed) return;
        
        const btn = this;
        const hideSpinner = ui?.showSpinner?.(btn, 'Assigning...');
        
        try {
            await api.bulkAssignSeats(selectedSeats, occupant);
            ui?.showToast?.(`Assigned ${occupant} to ${selectedSeats.length} seat(s)`, 'success');
            ui?.refreshData?.();
        } catch (error) {
            ui?.handleError?.(error, 'Failed to assign seats');
        } finally {
            hideSpinner?.();
        }
    });

    // Edit Matrix button
    document.querySelector('[data-action="edit-matrix"]')?.addEventListener('click', async function() {
        const btn = this;
        const hideSpinner = ui?.showSpinner?.(btn, 'Loading...');
        
        try {
            const matrix = await api.getPositionGroupMatrix();
            openMatrixModal(matrix);
        } catch (error) {
            ui?.handleError?.(error, 'Failed to load matrix');
        } finally {
            hideSpinner?.();
        }
    });

    // Edit Seat buttons
    document.querySelectorAll('[data-action="edit-seat"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const seatId = this.dataset.seat;
            const hideSpinner = ui?.showSpinner?.(this, 'Loading...');
            
            try {
                const seat = await api.getSeat(seatId);
                openSeatModal(seat);
            } catch (error) {
                ui?.handleError?.(error, 'Failed to load seat');
            } finally {
                hideSpinner?.();
            }
        });
    });

    // Assign Seat buttons
    document.querySelectorAll('[data-action="assign-seat"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const seatId = this.dataset.seat;
            const occupant = prompt('Enter occupant ID or name:');
            
            if (!occupant) return;
            
            const hideSpinner = ui?.showSpinner?.(this, 'Assigning...');
            
            try {
                await api.assignSeat(seatId, occupant);
                ui?.showToast?.('Seat assigned successfully', 'success');
                ui?.refreshData?.();
            } catch (error) {
                ui?.handleError?.(error, 'Failed to assign seat');
            } finally {
                hideSpinner?.();
            }
        });
    });

    // Vacate Seat buttons
    document.querySelectorAll('[data-action="vacate-seat"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const seatId = this.dataset.seat;
            
            const confirmed = await ui?.confirmDialog?.(
                `Vacate seat ${seatId}? The current occupant will be removed.`,
                { title: 'Vacate Seat', confirmText: 'Vacate', confirmClass: 'danger' }
            );
            
            if (!confirmed) return;
            
            const hideSpinner = ui?.showSpinner?.(this, 'Vacating...');
            
            try {
                await api.vacateSeat(seatId);
                ui?.showToast?.('Seat vacated successfully', 'success');
                ui?.refreshData?.();
            } catch (error) {
                ui?.handleError?.(error, 'Failed to vacate seat');
            } finally {
                hideSpinner?.();
            }
        });
    });

    // Seat History buttons
    document.querySelectorAll('[data-action="seat-history"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const seatId = this.dataset.seat;
            const hideSpinner = ui?.showSpinner?.(this, 'Loading...');
            
            try {
                const history = await api.getSeatHistory(seatId);
                openHistoryModal(history, seatId);
            } catch (error) {
                ui?.handleError?.(error, 'Failed to load seat history');
            } finally {
                hideSpinner?.();
            }
        });
    });

    // Select All checkbox
    const selectAll = document.getElementById('selectAll');
    if (selectAll) {
        selectAll.addEventListener('change', function() {
            document.querySelectorAll('.seat-checkbox').forEach(cb => {
                cb.checked = this.checked;
            });
        });
    }

    // Filters
    const stateFilter = document.getElementById('stateFilter');
    if (stateFilter) {
        stateFilter.addEventListener('change', filterSeats);
    }

    const projectFilter = document.getElementById('projectFilter');
    if (projectFilter) {
        projectFilter.addEventListener('change', filterSeats);
    }

    async function filterSeats() {
        const state = document.getElementById('stateFilter')?.value;
        const project = document.getElementById('projectFilter')?.value;
        
        const hideSpinner = ui?.showGlobalLoading?.('Filtering...');
        
        try {
            const result = await api.getSeats({ state, projectId: project, page: 1 });
            updateSeatsList(result.items || []);
        } catch (error) {
            // Fallback to client-side filtering
            document.querySelectorAll('.seat-row').forEach(row => {
                let show = true;
                if (state && !row.classList.contains(state)) show = false;
                if (project && row.dataset.project !== project) show = false;
                row.style.display = show ? '' : 'none';
            });
        } finally {
            hideSpinner?.();
        }
    }

    function updateSeatsList(seats) {
        // FIXME: backend gap - implement full seats list rendering
        ui?.showToast?.('Seat list updated from API', 'info');
        console.log('Seats to render:', seats);
    }

    function openSeatModal(seat = null) {
        const isEdit = !!seat;
        const modalHtml = `
            <div id="seat-modal" class="modal" style="display: block; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 1000;">
                <div style="background: #1a1a1a; max-width: 500px; margin: 50px auto; padding: 24px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5;">
                    <h3>${isEdit ? 'Edit' : 'Create'} Seat</h3>
                    <form id="seat-form">
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Project</label>
                            <input type="text" name="project" value="${escapeHtml(seat?.project || '')}" ${isEdit ? 'readonly' : ''} style="width: 100%; padding: 8px; background: ${isEdit ? '#141414' : '#0d0d0d'}; border: 1px solid rgba(255,255,255,0.1); color: ${isEdit ? '#a8a39c' : '#faf8f5'}; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Role</label>
                            <input type="text" name="role" value="${escapeHtml(seat?.role || '')}" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Position</label>
                            <input type="text" name="position" value="${escapeHtml(seat?.position || '')}" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Group</label>
                            <input type="text" name="group" value="${escapeHtml(seat?.group || '')}" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">Clearance Level</label>
                            <select name="clearance" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                                <option value="">None</option>
                                <option value="L1">L1 - Restricted</option>
                                <option value="L2">L2 - Standard</option>
                                <option value="L3">L3 - Confidential</option>
                                <option value="L4">L4 - Secret</option>
                                <option value="L5">L5 - Top Secret</option>
                            </select>
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 4px; color: #d4cfc7;">State</label>
                            <select name="state" style="width: 100%; padding: 8px; background: #0d0d0d; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; border-radius: 4px;">
                                <option value="vacant">Vacant</option>
                                <option value="filled">Filled</option>
                                <option value="reserved">Reserved</option>
                                <option value="suspended">Suspended</option>
                            </select>
                        </div>
                        <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px;">
                            ${isEdit ? `<button type="button" class="delete-btn" style="padding: 8px 16px; background: #dc2626; border: none; color: white; border-radius: 4px; cursor: pointer; margin-right: auto;">Delete</button>
                            ` : ''}
                            <button type="button" class="cancel-btn" style="padding: 8px 16px; background: transparent; border: 1px solid rgba(255,255,255,0.2); color: #d4cfc7; border-radius: 4px; cursor: pointer;">Cancel</button>
                            <button type="submit" style="padding: 8px 16px; background: #f59e0b; border: none; color: #0d0d0d; border-radius: 4px; cursor: pointer; font-weight: 500;">${isEdit ? 'Update' : 'Create'} Seat</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = document.getElementById('seat-modal');
        const form = document.getElementById('seat-form');
        
        if (seat?.clearance) form.querySelector('[name="clearance"]').value = seat.clearance;
        if (seat?.state) form.querySelector('[name="state"]').value = seat.state;
        
        modal.querySelector('.cancel-btn')?.addEventListener('click', () => {
            modal.remove();
        });
        
        modal.querySelector('.delete-btn')?.addEventListener('click', async () => {
            const confirmed = await ui?.confirmDialog?.(
                `Delete seat ${seat.id}?`,
                { title: 'Delete Seat', confirmText: 'Delete', confirmClass: 'danger' }
            );
            
            if (!confirmed) return;
            
            const hideSpinner = ui?.showSpinner?.(modal.querySelector('.delete-btn'), 'Deleting...');
            
            try {
                await api.deleteSeat(seat.id);
                ui?.showToast?.('Seat deleted successfully', 'success');
                modal.remove();
                ui?.refreshData?.();
            } catch (error) {
                ui?.handleError?.(error, 'Failed to delete seat');
            } finally {
                hideSpinner?.();
            }
        });
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = form.querySelector('button[type="submit"]');
            const hideSpinner = ui?.showSpinner?.(submitBtn, isEdit ? 'Updating...' : 'Creating...');
            
            try {
                const formData = new FormData(form);
                const data = {
                    project: formData.get('project'),
                    role: formData.get('role'),
                    position: formData.get('position'),
                    group: formData.get('group'),
                    clearance: formData.get('clearance'),
                    state: formData.get('state')
                };
                
                if (isEdit) {
                    await api.updateSeat(seat.id, data);
                    ui?.showToast?.('Seat updated successfully', 'success');
                } else {
                    await api.createSeat(data);
                    ui?.showToast?.('Seat created successfully', 'success');
                }
                
                modal.remove();
                ui?.refreshData?.();
            } catch (error) {
                ui?.handleError?.(error, isEdit ? 'Failed to update seat' : 'Failed to create seat');
            } finally {
                hideSpinner?.();
            }
        });
    }

    function openMatrixModal(matrix) {
        ui?.showToast?.('Position/Group matrix editor - FIXME: backend gap PUT /v1/seats/matrix', 'warning');
        console.log('Matrix editor:', matrix);
    }

    function openHistoryModal(history, seatId) {
        const modalHtml = `
            <div id="history-modal" class="modal" style="display: block; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 1000;">
                <div style="background: #1a1a1a; max-width: 600px; margin: 50px auto; padding: 24px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); color: #faf8f5; max-height: 80vh; overflow-y: auto;">
                    <h3>Seat ${seatId} History</h3>
                    <div style="margin-top: 16px;">
                        ${(history || []).length === 0 ? '<p style="color: #a8a39c;">No history available</p>' : `
                            <div style="border-left: 2px solid rgba(245,158,11,0.3); padding-left: 16px;">
                                ${history.map((entry, i) => `
                                    <div style="margin-bottom: 16px; position: relative;">
                                        <div style="position: absolute; left: -21px; top: 4px; width: 8px; height: 8px; background: #f59e0b; border-radius: 50%;"></div>
                                        <div style="color: #a8a39c; font-size: 12px;">${escapeHtml(entry.timestamp || 'Unknown date')}</div>
                                        <div>${escapeHtml(entry.action || 'Unknown action')}</div>
                                        ${entry.occupant ? `<div style="color: #d4cfc7; font-size: 14px;">Occupant: ${escapeHtml(entry.occupant)}</div>` : ''}
                                    </div>
                                `).join('')}
                            </div>
                        `}
                    </div>
                    <div style="display: flex; justify-content: flex-end; margin-top: 20px;">
                        <button type="button" class="close-btn" style="padding: 8px 16px; background: transparent; border: 1px solid rgba(255,255,255,0.2); color: #d4cfc7; border-radius: 4px; cursor: pointer;">Close</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = document.getElementById('history-modal');
        modal.querySelector('.close-btn').addEventListener('click', () => {
            modal.remove();
        });
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});
