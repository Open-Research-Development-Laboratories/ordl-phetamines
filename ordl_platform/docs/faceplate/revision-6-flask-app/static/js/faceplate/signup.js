/**
 * Signup Page JavaScript
 */

(function() {
  'use strict';

  const PasswordStrength = {
    init() {
      this.password = document.getElementById('password');
      this.strengthIndicator = document.getElementById('passwordStrength');
      
      if (!this.password || !this.strengthIndicator) return;

      this.password.addEventListener('input', () => this.checkStrength());
    },

    checkStrength() {
      const value = this.password.value;
      let strength = 0;

      if (value.length >= 8) strength++;
      if (/[a-z]/.test(value) && /[A-Z]/.test(value)) strength++;
      if (/[0-9]/.test(value)) strength++;
      if (/[^a-zA-Z0-9]/.test(value)) strength++;

      this.strengthIndicator.className = 'password-strength';
      
      if (value.length === 0) {
        this.strengthIndicator.querySelector('.strength-text').textContent = 'Password strength';
      } else if (strength <= 1) {
        this.strengthIndicator.classList.add('weak');
        this.strengthIndicator.querySelector('.strength-text').textContent = 'Weak password';
      } else if (strength === 2 || strength === 3) {
        this.strengthIndicator.classList.add('medium');
        this.strengthIndicator.querySelector('.strength-text').textContent = 'Medium strength';
      } else {
        this.strengthIndicator.classList.add('strong');
        this.strengthIndicator.querySelector('.strength-text').textContent = 'Strong password';
      }
    }
  };

  document.addEventListener('DOMContentLoaded', () => {
    PasswordStrength.init();
  });
})();