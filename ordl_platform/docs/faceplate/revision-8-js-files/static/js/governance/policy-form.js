/**
 * ORDL Governance Policy Simulation Form Handler
 * Rule input validation, test data validation, results display
 */

(function() {
  'use strict';

  const PolicyForm = {
    form: null,
    ruleEditor: null,
    testDataInput: null,
    resultsPanel: null,

    // State
    currentPolicy: null,
    testResults: null,
    editorInstance: null,

    /**
     * Initialize the policy form
     */
    init() {
      this.form = document.querySelector('.policy-form, .simulation-form');
      if (!this.form) return;

      this.bindFields();
      this.bindEvents();
      this.setupEditor();
      this.setupValidation();
      this.loadPolicyTemplates();
    },

    /**
     * Bind field references
     */
    bindFields() {
      this.ruleEditor = document.getElementById('ruleEditor') || document.getElementById('policy_rules');
      this.testDataInput = document.getElementById('testData') || document.getElementById('test_data');
      this.resultsPanel = document.querySelector('.simulation-results');
    },

    /**
     * Bind event listeners
     */
    bindEvents() {
      // Form submission
      this.form.addEventListener('submit', (e) => this.handleSubmit(e));

      // Simulate button
      const simulateBtn = document.getElementById('simulateBtn');
      if (simulateBtn) {
        simulateBtn.addEventListener('click', () => this.runSimulation());
      }

      // Validate button
      const validateBtn = document.getElementById('validateBtn');
      if (validateBtn) {
        validateBtn.addEventListener('click', () => this.validateRules());
      }

      // Template selection
      const templateSelect = document.getElementById('policyTemplate');
      if (templateSelect) {
        templateSelect.addEventListener('change', () => this.loadTemplate(templateSelect.value));
      }

      // Format buttons
      document.querySelectorAll('[data-action="format"]').forEach(btn => {
        btn.addEventListener('click', () => this.formatCode());
      });

      // Import test data
      const importBtn = document.getElementById('importTestData');
      if (importBtn) {
        importBtn.addEventListener('click', () => this.importTestData());
      }

      // Clear results
      const clearBtn = document.getElementById('clearResults');
      if (clearBtn) {
        clearBtn.addEventListener('click', () => this.clearResults());
      }
    },

    /**
     * Setup code editor
     */
    setupEditor() {
      if (!this.ruleEditor) return;

      // Check if Monaco or CodeMirror is available
      if (window.monaco) {
        this.setupMonacoEditor();
      } else if (window.CodeMirror) {
        this.setupCodeMirror();
      } else {
        // Fallback to textarea with syntax highlighting hints
        this.setupTextareaEditor();
      }
    },

    /**
     * Setup Monaco Editor
     */
    setupMonacoEditor() {
      this.editorInstance = monaco.editor.create(this.ruleEditor, {
        value: this.getDefaultPolicy(),
        language: 'json',
        theme: 'vs-dark',
        minimap: { enabled: false },
        automaticLayout: true,
        scrollBeyondLastLine: false,
        fontSize: 14,
        tabSize: 2,
        insertSpaces: true,
        formatOnPaste: true,
        formatOnType: true
      });
    },

    /**
     * Setup CodeMirror Editor
     */
    setupCodeMirror() {
      this.editorInstance = CodeMirror.fromTextArea(this.ruleEditor, {
        mode: 'application/json',
        theme: 'default',
        lineNumbers: true,
        tabSize: 2,
        autoCloseBrackets: true,
        matchBrackets: true,
        foldGutter: true,
        gutters: ['CodeMirror-linenumbers', 'CodeMirror-foldgutter']
      });

      this.editorInstance.setValue(this.getDefaultPolicy());
    },

    /**
     * Setup enhanced textarea
     */
    setupTextareaEditor() {
      this.ruleEditor.classList.add('code-editor');
      this.ruleEditor.value = this.getDefaultPolicy();
      this.ruleEditor.spellcheck = false;

      // Add simple auto-indent
      this.ruleEditor.addEventListener('keydown', (e) => {
        if (e.key === 'Tab') {
          e.preventDefault();
          const start = this.ruleEditor.selectionStart;
          const end = this.ruleEditor.selectionEnd;
          this.ruleEditor.value = this.ruleEditor.value.substring(0, start) + 
                                 '  ' + 
                                 this.ruleEditor.value.substring(end);
          this.ruleEditor.selectionStart = this.ruleEditor.selectionEnd = start + 2;
        }
      });
    },

    /**
     * Get default policy template
     */
    getDefaultPolicy() {
      return JSON.stringify({
        version: '1.0',
        name: 'New Policy',
        description: 'Policy description',
        rules: [
          {
            id: 'rule_1',
            name: 'Example Rule',
            condition: {
              field: 'user.role',
              operator: 'equals',
              value: 'admin'
            },
            action: 'allow',
            priority: 1
          }
        ],
        defaultAction: 'deny'
      }, null, 2);
    },

    /**
     * Setup validation
     */
    setupValidation() {
      if (window.ORDL?.Validation) {
        window.ORDL.Validation.init(this.form, {
          validateOnBlur: true,
          validateOnInput: false
        });
      }

      // Real-time validation for test data
      if (this.testDataInput) {
        this.testDataInput.addEventListener('blur', () => this.validateTestData());
      }
    },

    /**
     * Load policy templates
     */
    async loadPolicyTemplates() {
      try {
        const response = await fetch('/api/governance/policy-templates');
        const templates = await response.json();

        const select = document.getElementById('policyTemplate');
        if (select) {
          select.innerHTML = `
            <option value="">Select a template...</option>
            ${templates.map(t => `<option value="${t.id}">${t.name}</option>`).join('')}
          `;
        }
      } catch (error) {
        console.error('Failed to load templates:', error);
      }
    },

    /**
     * Load policy template
     */
    async loadTemplate(templateId) {
      if (!templateId) return;

      try {
        const response = await fetch(`/api/governance/policy-templates/${templateId}`);
        const template = await response.json();

        const policyJson = JSON.stringify(template.policy, null, 2);
        
        if (this.editorInstance) {
          if (window.monaco) {
            this.editorInstance.setValue(policyJson);
          } else if (window.CodeMirror) {
            this.editorInstance.setValue(policyJson);
          }
        } else if (this.ruleEditor) {
          this.ruleEditor.value = policyJson;
        }

        // Update form fields
        const nameField = document.getElementById('policyName');
        if (nameField) nameField.value = template.name;

        const descField = document.getElementById('policyDescription');
        if (descField) descField.value = template.description || '';

      } catch (error) {
        this.showError('Failed to load template');
      }
    },

    /**
     * Get current rule content
     */
    getRuleContent() {
      if (this.editorInstance) {
        if (window.monaco) {
          return this.editorInstance.getValue();
        } else if (window.CodeMirror) {
          return this.editorInstance.getValue();
        }
      }
      return this.ruleEditor?.value || '';
    },

    /**
     * Set rule content
     */
    setRuleContent(content) {
      if (this.editorInstance) {
        if (window.monaco) {
          this.editorInstance.setValue(content);
        } else if (window.CodeMirror) {
          this.editorInstance.setValue(content);
        }
      } else if (this.ruleEditor) {
        this.ruleEditor.value = content;
      }
    },

    /**
     * Validate policy rules
     */
    validateRules() {
      const content = this.getRuleContent();
      
      try {
        const policy = JSON.parse(content);
        const errors = this.validatePolicyStructure(policy);

        if (errors.length === 0) {
          this.showValidationSuccess('Policy is valid');
          this.currentPolicy = policy;
          return true;
        } else {
          this.showValidationErrors(errors);
          return false;
        }
      } catch (parseError) {
        this.showValidationErrors([{
          line: this.getErrorLine(parseError),
          message: `JSON Parse Error: ${parseError.message}`
        }]);
        return false;
      }
    },

    /**
     * Validate policy structure
     */
    validatePolicyStructure(policy) {
      const errors = [];

      // Required fields
      if (!policy.version) {
        errors.push({ field: 'version', message: 'Version is required' });
      }

      if (!policy.name) {
        errors.push({ field: 'name', message: 'Policy name is required' });
      }

      if (!Array.isArray(policy.rules)) {
        errors.push({ field: 'rules', message: 'Rules must be an array' });
      } else {
        // Validate each rule
        policy.rules.forEach((rule, index) => {
          if (!rule.id) {
            errors.push({ field: `rules[${index}].id`, message: 'Rule ID is required' });
          }
          if (!rule.condition) {
            errors.push({ field: `rules[${index}].condition`, message: 'Rule condition is required' });
          }
          if (!['allow', 'deny', 'audit'].includes(rule.action)) {
            errors.push({ field: `rules[${index}].action`, message: 'Action must be allow, deny, or audit' });
          }
        });
      }

      // Check for duplicate rule IDs
      const ruleIds = policy.rules?.map(r => r.id) || [];
      const duplicates = ruleIds.filter((id, i) => ruleIds.indexOf(id) !== i);
      if (duplicates.length > 0) {
        errors.push({ message: `Duplicate rule IDs: ${[...new Set(duplicates)].join(', ')}` });
      }

      return errors;
    },

    /**
     * Get line number from parse error
     */
    getErrorLine(error) {
      const match = error.message.match(/line\s+(\d+)/i);
      return match ? parseInt(match[1], 10) : null;
    },

    /**
     * Validate test data
     */
    validateTestData() {
      const content = this.testDataInput?.value;
      if (!content) return true;

      try {
        JSON.parse(content);
        this.clearFieldError(this.testDataInput);
        return true;
      } catch (error) {
        this.showFieldError(this.testDataInput, `Invalid JSON: ${error.message}`);
        return false;
      }
    },

    /**
     * Format code in editor
     */
    formatCode() {
      try {
        const content = this.getRuleContent();
        const formatted = JSON.stringify(JSON.parse(content), null, 2);
        this.setRuleContent(formatted);
      } catch (error) {
        this.showError('Cannot format invalid JSON');
      }
    },

    /**
     * Import test data
     */
    async importTestData() {
      // Create file input
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = '.json';
      
      input.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        try {
          const content = await file.text();
          // Validate JSON
          JSON.parse(content);
          
          if (this.testDataInput) {
            this.testDataInput.value = content;
          }
          
          this.showSuccess(`Imported ${file.name}`);
        } catch (error) {
          this.showError('Invalid JSON file');
        }
      });

      input.click();
    },

    /**
     * Run policy simulation
     */
    async runSimulation() {
      // Validate inputs
      if (!this.validateRules()) return;
      if (!this.validateTestData()) return;

      const testData = this.testDataInput?.value;
      if (!testData) {
        this.showError('Please provide test data');
        return;
      }

      this.setLoading(true, 'simulate');

      try {
        const response = await this.sendSimulationRequest();
        this.displayResults(response);
      } catch (error) {
        this.showError(error.message || 'Simulation failed');
      } finally {
        this.setLoading(false, 'simulate');
      }
    },

    /**
     * Send simulation request
     */
    async sendSimulationRequest() {
      const policy = JSON.parse(this.getRuleContent());
      const testData = JSON.parse(this.testDataInput.value);

      const response = await fetch('/api/governance/policies/simulate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({ policy, testData })
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.message || 'Simulation failed');
      }

      return result;
    },

    /**
     * Display simulation results
     */
    displayResults(results) {
      this.testResults = results;

      if (!this.resultsPanel) {
        this.resultsPanel = document.createElement('div');
        this.resultsPanel.className = 'simulation-results';
        this.form.appendChild(this.resultsPanel);
      }

      const passed = results.passed || 0;
      const failed = results.failed || 0;
      const total = passed + failed;

      this.resultsPanel.innerHTML = `
        <div class="results-header">
          <h4>Simulation Results</h4>
          <div class="results-summary">
            <span class="result-passed">${passed} passed</span>
            <span class="result-failed">${failed} failed</span>
            <span class="result-total">${total} total</span>
          </div>
        </div>
        
        <div class="results-details">
          ${results.results?.map((r, i) => `
            <div class="result-item ${r.passed ? 'passed' : 'failed'}">
              <div class="result-header">
                <span class="result-number">#${i + 1}</span>
                <span class="result-status">${r.passed ? '✓ PASSED' : '✗ FAILED'}</span>
                <span class="result-action">Action: ${r.action}</span>
              </div>
              <div class="result-details">
                <div class="result-matched-rule">
                  Matched: ${r.matchedRule || 'None (default action)'}
                  ${r.matchedCondition ? `<pre>${JSON.stringify(r.matchedCondition, null, 2)}</pre>` : ''}
                </div>
                ${!r.passed ? `
                  <div class="result-expected">
                    Expected: ${r.expectedAction}
                  </div>
                ` : ''}
              </div>
            </div>
          `).join('') || '<p>No results</p>'}
        </div>
        
        <div class="results-actions">
          <button class="btn btn-secondary" onclick="PolicyForm.exportResults()">Export Results</button>
          <button class="btn btn-secondary" id="clearResults">Clear</button>
        </div>
      `;

      // Re-bind clear button
      this.resultsPanel.querySelector('#clearResults')?.addEventListener('click', () => {
        this.clearResults();
      });

      this.resultsPanel.classList.add('is-visible');

      // Dispatch event
      document.dispatchEvent(new CustomEvent('simulation:complete', { detail: results }));
    },

    /**
     * Clear results
     */
    clearResults() {
      this.testResults = null;
      if (this.resultsPanel) {
        this.resultsPanel.innerHTML = '';
        this.resultsPanel.classList.remove('is-visible');
      }
    },

    /**
     * Export results
     */
    exportResults() {
      if (!this.testResults) return;

      const blob = new Blob([JSON.stringify(this.testResults, null, 2)], {
        type: 'application/json'
      });

      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `simulation-results-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },

    /**
     * Handle form submission (save policy)
     */
    async handleSubmit(e) {
      e.preventDefault();

      if (!this.validateRules()) return;

      this.setLoading(true, 'save');

      try {
        const response = await this.savePolicy();
        this.handleSaveSuccess(response);
      } catch (error) {
        this.handleSaveError(error);
      } finally {
        this.setLoading(false, 'save');
      }
    },

    /**
     * Save policy
     */
    async savePolicy() {
      const policy = JSON.parse(this.getRuleContent());
      
      // Add metadata
      policy.name = document.getElementById('policyName')?.value || policy.name;
      policy.description = document.getElementById('policyDescription')?.value || '';

      const response = await fetch('/api/governance/policies', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(policy)
      });

      const result = await response.json();

      if (!response.ok) {
        const error = new Error(result.message || 'Save failed');
        error.errors = result.errors;
        throw error;
      }

      return result;
    },

    /**
     * Handle successful save
     */
    handleSaveSuccess(response) {
      if (window.ORDL?.showToast) {
        window.ORDL.showToast('Policy saved successfully', 'success');
      }

      // Update URL if new policy
      if (response.id && !window.location.pathname.includes(response.id)) {
        window.history.replaceState({}, '', `/governance/policies/${response.id}`);
      }

      document.dispatchEvent(new CustomEvent('policy:saved', { detail: response }));
    },

    /**
     * Handle save error
     */
    handleSaveError(error) {
      if (error.errors) {
        this.showValidationErrors(error.errors.map(e => ({
          field: e.field,
          message: e.message
        })));
      } else {
        this.showError(error.message || 'Failed to save policy');
      }
    },

    /**
     * Show validation success
     */
    showValidationSuccess(message) {
      let successPanel = document.querySelector('.validation-success');
      
      if (!successPanel) {
        successPanel = document.createElement('div');
        successPanel.className = 'validation-success';
        this.form.insertBefore(successPanel, this.form.firstChild);
      }

      successPanel.innerHTML = `✓ ${message}`;
      successPanel.classList.add('is-visible');

      setTimeout(() => {
        successPanel.classList.remove('is-visible');
      }, 3000);
    },

    /**
     * Show validation errors
     */
    showValidationErrors(errors) {
      let errorPanel = document.querySelector('.validation-errors');
      
      if (!errorPanel) {
        errorPanel = document.createElement('div');
        errorPanel.className = 'validation-errors';
        this.form.insertBefore(errorPanel, this.form.firstChild);
      }

      errorPanel.innerHTML = `
        <div class="error-header">Validation Errors:</div>
        <ul>
          ${errors.map(e => `
            <li>
              ${e.line ? `Line ${e.line}: ` : ''}
              ${e.field ? `${e.field}: ` : ''}
              ${e.message}
            </li>
          `).join('')}
        </ul>
      `;

      errorPanel.classList.add('is-visible');
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
     * Show success message
     */
    showSuccess(message) {
      if (window.ORDL?.showToast) {
        window.ORDL.showToast(message, 'success');
      }
    },

    /**
     * Show error message
     */
    showError(message) {
      if (window.ORDL?.showToast) {
        window.ORDL.showToast(message, 'error');
      } else {
        alert(message);
      }
    },

    /**
     * Set loading state
     */
    setLoading(loading, type) {
      const btn = type === 'simulate' 
        ? document.getElementById('simulateBtn')
        : this.form.querySelector('[type="submit"]');

      if (btn) {
        btn.disabled = loading;
        btn.classList.toggle('is-loading', loading);
        
        if (loading) {
          btn.dataset.originalText = btn.textContent;
          btn.textContent = type === 'simulate' ? 'Simulating...' : 'Saving...';
        } else {
          btn.textContent = btn.dataset.originalText || (type === 'simulate' ? 'Simulate' : 'Save Policy');
        }
      }
    }
  };

  // Initialize on DOM ready
  document.addEventListener('DOMContentLoaded', () => {
    PolicyForm.init();
  });

  // Export
  window.ORDL = window.ORDL || {};
  window.ORDL.PolicyForm = PolicyForm;

})();