/**
 * Docs Page JavaScript
 */

(function() {
  'use strict';

  const DocsSearch = {
    init() {
      this.input = document.getElementById('docsSearch');
      if (!this.input) return;

      this.bindEvents();
    },

    bindEvents() {
      // Focus search on Cmd/Ctrl+K
      document.addEventListener('keydown', (e) => {
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
          e.preventDefault();
          this.input.focus();
        }
      });

      // Simple search highlighting
      this.input.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        if (query.length > 0) {
          this.input.parentElement.classList.add('has-query');
        } else {
          this.input.parentElement.classList.remove('has-query');
        }
      });
    }
  };

  document.addEventListener('DOMContentLoaded', () => {
    DocsSearch.init();
  });
})();