/**
 * Changelog Page JavaScript
 */

(function() {
  'use strict';

  // Filter tabs
  const FilterTabs = {
    init() {
      this.tabs = document.querySelectorAll('.filter-tab');
      if (this.tabs.length === 0) return;

      this.bindEvents();
    },

    bindEvents() {
      this.tabs.forEach(tab => {
        tab.addEventListener('click', () => {
          this.tabs.forEach(t => t.classList.remove('active'));
          tab.classList.add('active');
        });
      });
    }
  };

  document.addEventListener('DOMContentLoaded', () => {
    FilterTabs.init();
  });
})();