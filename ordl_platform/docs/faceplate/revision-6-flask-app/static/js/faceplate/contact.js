/**
 * Contact Page JavaScript
 */

(function() {
  'use strict';

  // Department selection from URL
  const DepartmentSelect = {
    init() {
      const params = new URLSearchParams(window.location.search);
      const dept = params.get('dept');
      
      if (dept) {
        const select = document.getElementById('department');
        if (select) {
          select.value = dept;
        }
      }
    }
  };

  document.addEventListener('DOMContentLoaded', () => {
    DepartmentSelect.init();
  });
})();