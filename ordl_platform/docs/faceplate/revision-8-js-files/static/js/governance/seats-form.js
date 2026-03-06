/**
 * ORDL Governance Seats Assignment Form Handler
 * Role/position validation, clearance tier checks, conflict detection
 */

(function() {
  'use strict';

  const SeatsForm = {
    form: null,
    userSelect: null,
    roleSelect: null,
    positionInput: null,
    clearanceSelect: null,
    startDate: null,
    endDate: null,

    // State
    currentAssignments: new Map(),
    conflicts: [],

    /**
     * Initialize the seats form
     */
    init() {
      this.form = document.querySelector('.seats-form, .assignment-form');
      if (!this.form) return;

      this.bindFields();
      this.bindEvents();
      this.setupValidation();
      this.loadCurrentAssignments();
    },

    /**
     * Bind field references
     */
    bindFields() {
      this.userSelect = document.getElementById('user');
      this.roleSelect = document.getElementById('role');
      this.positionInput = document.getElementById('position');
      this.clearanceSelect = document.getElementById('clearance_tier');
      this.startDate = document.getElementById('start_date');
      this.endDate = document.getElementById('end_date');
    },

    /**
     * Bind event listeners
     */
    bindEvents() {
      // Form submission
      this.form.addEventListener('submit', (e) => this.handleSubmit(e));

      // User selection change
      if (this.userSelect) {
        this.userSelect.addEventListener('change', () => this.handleUserChange());
      }

      // Role selection change
      if (this.roleSelect) {
        this.roleSelect.addEventListener('change', () => this.handleRoleChange());
      }

      // Clearance validation
      if (this.clearanceSelect) {
        this.clearanceSelect.addEventListener('change', () => this.validateClearance());
      }

      // Date validation
      if (this.startDate && this.endDate) {
        this.startDate.addEventListener('change', () => this.validateDates());
        this.endDate.addEventListener('change', () => this.validateDates());
      }

      // Real-time conflict checking
      this.form.querySelectorAll('select, input').forEach(field => {
        field.addEventListener('change', () => this.checkConflicts());
      });

      // Remove assignment buttons
      document.querySelectorAll('.remove-assignment').forEach(btn => {
        btn.addEventListener('click', (e) => this.handleRemoveAssignment(e));
      });
    },

    /**
     * Setup validation
     */
    setupValidation() {
      if (window.ORDL?.Validation) {
        // Add custom rules
        window.ORDL.Validation.addRule('futureDate', (value) => {
          if (!value) return true;
          const date = new Date(value);
          const today = new Date();
          today.setHours(0, 0, 0, 0);
          return date >= today;
        }, 'Date must be today or in the future');

        window.ORDL.Validation.addRule('dateAfterStart', (value) => {
          if (!value || !this.startDate?.value) return true;
          return new Date(value) > new Date(this.startDate.value);
        }, 'End date must be after start date');

        // Initialize validation
        window.ORDL.Validation.init(this.form, {
          validateOnBlur: true,
          validateOnChange: true
        });
      }
    },

    /**
     * Load current seat assignments
     */
    async loadCurrentAssignments() {
      try {
        const response = await fetch('/api/governance/seats');
        const data = await response.json();

        if (data.assignments) {
          this.renderAssignments(data.assignments);
          this.currentAssignments = new Map(
            data.assignments.map(a => [a.user_id, a])
          );
        }
      } catch (error) {
        console.error('Failed to load assignments:', error);
      }
    },

    /**
     * Render current assignments
     */
    renderAssignments(assignments) {
      const container = document.querySelector('.current-assignments');
      if (!container) return;

      if (assignments.length === 0) {
        container.innerHTML = '<p class="no-data">No current assignments</p>';
        return;
      }

      container.innerHTML = `
        <table class="assignments-table">
          <thead>
            <tr>
              <th>User</th>
              <th>Role</th>
              <th>Position</th>
              <th>Clearance</th>
              <th>Period</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${assignments.map(a => `
              <tr data-assignment-id="${a.id}">
                <td>${a.user_name}</td>
                <td><span class="role-badge role-${a.role}">${a.role}</span></td>
                <td>${a.position || '-'}</td>
                <td><span class="clearance-${a.clearance_tier}">${a.clearance_tier}</span></td>
                <td>${this.formatDateRange(a.start_date, a.end_date)}</td>
                <td>
                  <button class="btn-icon remove-assignment" data-id="${a.id}" title="Remove">🗑</button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;
    },

    /**
     * Handle user selection change
     */
    async handleUserChange() {
      const userId = this.userSelect?.value;
      if (!userId) return;

      // Fetch user details
      try {
        const response = await fetch(`/api/users/${userId}/clearance`);
        const data = await response.json();

        // Update clearance options based on user's max clearance
        this.updateClearanceOptions(data.max_clearance);

        // Show user info
        this.showUserInfo(data);

        // Check for existing assignment
        if (this.currentAssignments.has(userId)) {
          this.showExistingAssignmentWarning(userId);
        }
      } catch (error) {
        console.error('Failed to load user clearance:', error);
      }
    },

    /**
     * Update clearance tier options
     */
    updateClearanceOptions(maxClearance) {
      if (!this.clearanceSelect) return;

      const tiers = ['public', 'internal', 'confidential', 'secret', 'top_secret'];
      const maxIndex = tiers.indexOf(maxClearance);

      this.clearanceSelect.querySelectorAll('option').forEach(option => {
        const tierIndex = tiers.indexOf(option.value);
        option.disabled = tierIndex > maxIndex;
      });
    },

    /**
     * Show user information panel
     */
    showUserInfo(data) {
      let infoPanel = document.querySelector('.user-info-panel');
      
      if (!infoPanel) {
        infoPanel = document.createElement('div');
        infoPanel.className = 'user-info-panel';
        this.userSelect.parentElement.appendChild(infoPanel);
      }

      infoPanel.innerHTML = `
        <div class="user-info-header">
          <strong>${data.name}</strong>
          <span class="user-clearance">Max: ${data.max_clearance}</span>
        </div>
        <div class="user-info-details">
          <span>${data.department || 'No department'}</span>
          ${data.current_assignments > 0 ? `<span class="warning">${data.current_assignments} current assignment(s)</span>` : ''}
        </div>
      `;

      infoPanel.classList.add('is-visible');
    },

    /**
     * Show warning for existing assignment
     */
    showExistingAssignmentWarning(userId) {
      const existing = this.currentAssignments.get(userId);
      
      this.showWarning(
        `${existing.user_name} already has a ${existing.role} assignment. ` +
        `This will replace their current assignment.`
      );
    },

    /**
     * Handle role selection change
     */
    handleRoleChange() {
      const role = this.roleSelect?.value;
      if (!role) return;

      // Update position options based on role
      this.updatePositionOptions(role);

      // Check role-specific requirements
      this.checkRoleRequirements(role);
    },

    /**
     * Update position options based on role
     */
    updatePositionOptions(role) {
      if (!this.positionInput) return;

      const positions = {
        'admin': ['System Administrator', 'Security Administrator', 'Network Administrator'],
        'analyst': ['Security Analyst', 'Data Analyst', 'Operations Analyst'],
        'auditor': ['Compliance Auditor', 'Security Auditor', 'Financial Auditor'],
        'manager': ['Project Manager', 'Security Manager', 'Operations Manager'],
        'viewer': ['Read-only Viewer', 'Report Viewer']
      };

      // If using datalist
      let datalist = document.getElementById('position-suggestions');
      if (!datalist) {
        datalist = document.createElement('datalist');
        datalist.id = 'position-suggestions';
        this.positionInput.setAttribute('list', 'position-suggestions');
        this.positionInput.parentElement.appendChild(datalist);
      }

      datalist.innerHTML = (positions[role] || [])
        .map(p => `<option value="${p}">`)
        .join('');
    },

    /**
     * Check role-specific requirements
     */
    checkRoleRequirements(role) {
      const requirements = {
        'admin': { minClearance: 'secret', requiresApproval: true },
        'analyst': { minClearance: 'internal', requiresApproval: false },
        'auditor': { minClearance: 'confidential', requiresApproval: true },
        'manager': { minClearance: 'secret', requiresApproval: true },
        'viewer': { minClearance: 'public', requiresApproval: false }
      };

      const req = requirements[role];
      if (req) {
        this.showRoleRequirements(req);
      }
    },

    /**
     * Show role requirements
     */
    showRoleRequirements(requirements) {
      let reqPanel = document.querySelector('.role-requirements');
      
      if (!reqPanel) {
        reqPanel = document.createElement('div');
        reqPanel.className = 'role-requirements';
        this.roleSelect.parentElement.appendChild(reqPanel);
      }

      reqPanel.innerHTML = `
        <div class="requirement-item ${requirements.requiresApproval ? 'required' : ''}">
          <span class="req-icon">${requirements.requiresApproval ? '⚠' : '✓'}</span>
          <span>${requirements.requiresApproval ? 'Requires approval' : 'No approval needed'}</span>
        </div>
        <div class="requirement-item">
          <span class="req-icon">🔒</span>
          <span>Minimum clearance: ${requirements.minClearance}</span>
        </div>
      `;

      reqPanel.classList.add('is-visible');
    },

    /**
     * Validate clearance tier
     */
    validateClearance() {
      const selectedTier = this.clearanceSelect?.value;
      const userId = this.userSelect?.value;

      if (!selectedTier || !userId) return true;

      // Get user's max clearance
      const userOption = this.userSelect.querySelector(`option[value="${userId}"]`);
      const maxClearance = userOption?.dataset.maxClearance;

      if (maxClearance) {
        const tiers = ['public', 'internal', 'confidential', 'secret', 'top_secret'];
        if (tiers.indexOf(selectedTier) > tiers.indexOf(maxClearance)) {
          this.showFieldError(
            this.clearanceSelect, 
            `User's clearance (${maxClearance}) is insufficient for this tier`
          );
          return false;
        }
      }

      this.clearFieldError(this.clearanceSelect);
      return true;
    },

    /**
     * Validate date range
     */
    validateDates() {
      const start = this.startDate?.value;
      const end = this.endDate?.value;

      if (start && end) {
        if (new Date(end) <= new Date(start)) {
          this.showFieldError(this.endDate, 'End date must be after start date');
          return false;
        }
      }

      this.clearFieldError(this.endDate);
      return true;
    },

    /**
     * Check for conflicts
     */
    async checkConflicts() {
      const data = this.getFormData();
      
      if (!data.user || !data.start_date) return;

      try {
        const response = await fetch('/api/governance/seats/check-conflicts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data)
        });

        const result = await response.json();

        if (result.conflicts?.length > 0) {
          this.conflicts = result.conflicts;
          this.showConflicts(result.conflicts);
        } else {
          this.clearConflicts();
        }
      } catch (error) {
        console.error('Conflict check failed:', error);
      }
    },

    /**
     * Show conflict warnings
     */
    showConflicts(conflicts) {
      let conflictPanel = document.querySelector('.conflict-panel');
      
      if (!conflictPanel) {
        conflictPanel = document.createElement('div');
        conflictPanel.className = 'conflict-panel';
        this.form.insertBefore(conflictPanel, this.form.firstChild);
      }

      conflictPanel.innerHTML = `
        <div class="conflict-header">
          <span class="conflict-icon">⚠</span>
          <strong>Potential Conflicts Detected</strong>
        </div>
        <ul class="conflict-list">
          ${conflicts.map(c => `
            <li>
              <strong>${c.type}:</strong> ${c.description}
              ${c.canOverride 
                ? '<button class="override-btn" data-conflict-id="${c.id}">Override</button>' 
                : ''}
            </li>
          `).join('')}
        </ul>
      `;

      conflictPanel.classList.add('is-visible');

      // Bind override buttons
      conflictPanel.querySelectorAll('.override-btn').forEach(btn => {
        btn.addEventListener('click', () => this.overrideConflict(btn.dataset.conflictId));
      });
    },

    /**
     * Clear conflict display
     */
    clearConflicts() {
      this.conflicts = [];
      const conflictPanel = document.querySelector('.conflict-panel');
      if (conflictPanel) {
        conflictPanel.classList.remove('is-visible');
      }
    },

    /**
     * Override a conflict
     */
    overrideConflict(conflictId) {
      const conflict = this.conflicts.find(c => c.id === conflictId);
      if (conflict) {
        conflict.overridden = true;
        
        // Add hidden input for override
        let overrideInput = this.form.querySelector(`input[name="override_${conflictId}"]`);
        if (!overrideInput) {
          overrideInput = document.createElement('input');
          overrideInput.type = 'hidden';
          overrideInput.name = `override_${conflictId}`;
          this.form.appendChild(overrideInput);
        }
        overrideInput.value = 'true';

        // Update UI
        this.checkConflicts();
      }
    },

    /**
     * Handle form submission
     */
    async handleSubmit(e) {
      e.preventDefault();

      // Validate all fields
      if (!this.validateForm()) return;

      // Check for unresolved conflicts
      const unresolved = this.conflicts.filter(c => !c.overridden && !c.canAutoResolve);
      if (unresolved.length > 0) {
        this.showWarning('Please resolve all conflicts before submitting');
        return;
      }

      // Confirm if replacing existing assignment
      const userId = this.userSelect?.value;
      if (this.currentAssignments.has(userId)) {
        const confirmed = await this.confirmReplace(userId);
        if (!confirmed) return;
      }

      // Submit
      this.setLoading(true);

      try {
        const response = await this.assignSeat();
        this.handleSuccess(response);
      } catch (error) {
        this.handleError(error);
      } finally {
        this.setLoading(false);
      }
    },

    /**
     * Validate entire form
     */
    validateForm() {
      let isValid = true;

      // Required fields
      const required = ['user', 'role', 'clearance_tier', 'start_date'];
      required.forEach(fieldName => {
        const field = this.form.querySelector(`[name="${fieldName}"]`);
        if (!field?.value) {
          this.showFieldError(field, 'This field is required');
          isValid = false;
        }
      });

      // Custom validations
      if (!this.validateClearance()) isValid = false;
      if (!this.validateDates()) isValid = false;

      return isValid;
    },

    /**
     * Confirm replacing existing assignment
     */
    async confirmReplace(userId) {
      const existing = this.currentAssignments.get(userId);
      
      if (window.ORDL?.confirmDialog) {
        return await window.ORDL.confirmDialog(
          `Replace existing ${existing.role} assignment for ${existing.user_name}?`,
          { title: 'Confirm Replacement', confirmText: 'Replace' }
        );
      }
      
      return confirm(`Replace existing assignment for ${existing.user_name}?`);
    },

    /**
     * Get form data
     */
    getFormData() {
      const formData = new FormData(this.form);
      return Object.fromEntries(formData);
    },

    /**
     * Submit assignment
     */
    async assignSeat() {
      const data = this.getFormData();

      const response = await fetch('/api/governance/seats', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(data)
      });

      const result = await response.json();

      if (!response.ok) {
        const error = new Error(result.message || 'Assignment failed');
        error.errors = result.errors;
        throw error;
      }

      return result;
    },

    /**
     * Handle successful assignment
     */
    handleSuccess(response) {
      // Show toast
      if (window.ORDL?.showToast) {
        window.ORDL.showToast('Seat assigned successfully', 'success');
      }

      // Reload assignments
      this.loadCurrentAssignments();

      // Reset form
      this.form.reset();
      this.clearConflicts();

      // Hide info panels
      document.querySelectorAll('.user-info-panel, .role-requirements').forEach(el => {
        el.classList.remove('is-visible');
      });

      // Dispatch event
      document.dispatchEvent(new CustomEvent('seats:assigned', { detail: response }));
    },

    /**
     * Handle assignment error
     */
    handleError(error) {
      if (error.errors) {
        Object.entries(error.errors).forEach(([field, message]) => {
          const fieldEl = this.form.querySelector(`[name="${field}"]`);
          if (fieldEl) {
            this.showFieldError(fieldEl, Array.isArray(message) ? message[0] : message);
          }
        });
      } else {
        this.showWarning(error.message || 'Failed to assign seat');
      }

      document.dispatchEvent(new CustomEvent('seats:error', { detail: error }));
    },

    /**
     * Handle remove assignment
     */
    async handleRemoveAssignment(e) {
      const assignmentId = e.target.dataset.id;
      
      const confirmed = window.ORDL?.confirmDialog 
        ? await window.ORDL.confirmDialog('Remove this assignment?', { confirmText: 'Remove' })
        : confirm('Remove this assignment?');

      if (!confirmed) return;

      try {
        const response = await fetch(`/api/governance/seats/${assignmentId}`, {
          method: 'DELETE'
        });

        if (response.ok) {
          this.loadCurrentAssignments();
          
          if (window.ORDL?.showToast) {
            window.ORDL.showToast('Assignment removed', 'success');
          }
        }
      } catch (error) {
        this.showWarning('Failed to remove assignment');
      }
    },

    /**
     * Show field error
     */
    showFieldError(field, message) {
      if (window.ORDL?.Validation) {
        window.ORDL.Validation.showError(field, message);
      } else {
        field.classList.add('is-invalid');
        
        let errorEl = field.parentElement.querySelector('.field-error');
        if (!errorEl) {
          errorEl = document.createElement('span');
          errorEl.className = 'field-error';
          field.parentElement.appendChild(errorEl);
        }
        errorEl.textContent = message;
      }
    },

    /**
     * Clear field error
     */
    clearFieldError(field) {
      if (window.ORDL?.Validation) {
        window.ORDL.Validation.clearError(field);
      } else {
        field.classList.remove('is-invalid');
        const errorEl = field.parentElement.querySelector('.field-error');
        if (errorEl) errorEl.remove();
      }
    },

    /**
     * Show warning message
     */
    showWarning(message) {
      if (window.ORDL?.showToast) {
        window.ORDL.showToast(message, 'warning');
      } else {
        alert(message);
      }
    },

    /**
     * Set loading state
     */
    setLoading(loading) {
      const submitBtn = this.form.querySelector('[type="submit"]');
      if (submitBtn) {
        submitBtn.disabled = loading;
        submitBtn.classList.toggle('is-loading', loading);
        
        if (loading) {
          submitBtn.dataset.originalText = submitBtn.textContent;
          submitBtn.textContent = 'Assigning...';
        } else {
          submitBtn.textContent = submitBtn.dataset.originalText || 'Assign Seat';
        }
      }
    },

    /**
     * Format date range for display
     */
    formatDateRange(start, end) {
      const formatDate = (d) => new Date(d).toLocaleDateString();
      return end ? `${formatDate(start)} - ${formatDate(end)}` : formatDate(start) + ' - Ongoing';
    }
  };

  // Initialize on DOM ready
  document.addEventListener('DOMContentLoaded', () => {
    SeatsForm.init();
  });

  // Export
  window.ORDL = window.ORDL || {};
  window.ORDL.SeatsForm = SeatsForm;

})();