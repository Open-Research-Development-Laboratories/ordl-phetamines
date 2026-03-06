/**
 * Login Page JavaScript
 */

(function() {
  'use strict';

  // Password visibility toggle could be added here
  const LoginForm = {
    init() {
      this.form = document.querySelector('.auth-form');
      if (!this.form) return;

      this.bindEvents();
    },

    bindEvents() {
      this.form.addEventListener('submit', (e) => {
        // Form validation is handled by base.js
        // This is for any additional login-specific logic
      });
    }
  };

  document.addEventListener('DOMContentLoaded', () => {
    LoginForm.init();
  });
})();