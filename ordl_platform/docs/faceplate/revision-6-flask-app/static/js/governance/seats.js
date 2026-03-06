/**
 * ORDL Governance - Seats Page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Create Seat button
    document.querySelector('[data-action="create-seat"]')?.addEventListener('click', function() {
        console.log('Create seat');
        // TODO: Implement seat creation modal
    });

    // Bulk Assign button
    document.querySelector('[data-action="bulk-assign"]')?.addEventListener('click', function() {
        console.log('Bulk assign seats');
        // TODO: Implement bulk assignment
    });

    // Edit Matrix button
    document.querySelector('[data-action="edit-matrix"]')?.addEventListener('click', function() {
        console.log('Edit position/group matrix');
        // TODO: Implement matrix editing
    });

    // Edit Seat buttons
    document.querySelectorAll('[data-action="edit-seat"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const seatId = this.dataset.seat;
            console.log('Edit seat:', seatId);
        });
    });

    // Assign Seat buttons
    document.querySelectorAll('[data-action="assign-seat"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const seatId = this.dataset.seat;
            console.log('Assign seat:', seatId);
        });
    });

    // Vacate Seat buttons
    document.querySelectorAll('[data-action="vacate-seat"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const seatId = this.dataset.seat;
            if (confirm(`Vacate seat ${seatId}?`)) {
                console.log('Vacate seat:', seatId);
            }
        });
    });

    // Seat History buttons
    document.querySelectorAll('[data-action="seat-history"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const seatId = this.dataset.seat;
            console.log('View seat history:', seatId);
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

    function filterSeats() {
        const state = document.getElementById('stateFilter')?.value;
        const project = document.getElementById('projectFilter')?.value;
        
        document.querySelectorAll('.seat-row').forEach(row => {
            let show = true;
            if (state && !row.classList.contains(state)) show = false;
            // TODO: Add project filtering logic
            row.style.display = show ? '' : 'none';
        });
    }
});
