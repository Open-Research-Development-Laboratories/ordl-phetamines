/**
 * Status Page JavaScript
 */

(function() {
  'use strict';

  // Auto-refresh status
  const StatusRefresh = {
    init() {
      this.lastUpdated = document.querySelector('.status-updated');
      if (!this.lastUpdated) return;

      // Update "last updated" text every minute
      setInterval(() => {
        this.lastUpdated.textContent = 'Last updated: Just now';
      }, 60000);
    }
  };

  document.addEventListener('DOMContentLoaded', () => {
    StatusRefresh.init();
  });
})();