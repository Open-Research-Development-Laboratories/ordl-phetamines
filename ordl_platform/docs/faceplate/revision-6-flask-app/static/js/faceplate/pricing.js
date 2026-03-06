/**
 * Pricing Page JavaScript
 */

(function() {
  'use strict';

  const PricingToggle = {
    init() {
      this.toggle = document.getElementById('billingToggle');
      this.prices = document.querySelectorAll('.price-amount');
      this.isAnnual = false;

      if (!this.toggle) return;

      this.bindEvents();
    },

    bindEvents() {
      this.toggle.addEventListener('click', () => {
        this.isAnnual = !this.isAnnual;
        this.toggle.setAttribute('data-annual', this.isAnnual);
        this.updatePrices();
        this.updateLabels();
      });
    },

    updatePrices() {
      this.prices.forEach(price => {
        const monthly = price.dataset.monthly;
        const annual = price.dataset.annual;
        
        if (monthly && annual) {
          const newValue = this.isAnnual ? annual : monthly;
          this.animatePrice(price, parseInt(newValue));
        }
      });
    },

    animatePrice(element, target) {
      const start = parseInt(element.textContent);
      const duration = 300;
      const startTime = performance.now();

      const update = (currentTime) => {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const easeOut = 1 - Math.pow(1 - progress, 3);
        const current = Math.floor(start + (target - start) * easeOut);
        
        element.textContent = current;

        if (progress < 1) {
          requestAnimationFrame(update);
        }
      };

      requestAnimationFrame(update);
    },

    updateLabels() {
      document.querySelectorAll('.billing-label').forEach((label, index) => {
        const isActive = this.isAnnual ? index === 1 : index === 0;
        label.setAttribute('data-active', isActive);
      });
    }
  };

  document.addEventListener('DOMContentLoaded', () => {
    PricingToggle.init();
  });
})();