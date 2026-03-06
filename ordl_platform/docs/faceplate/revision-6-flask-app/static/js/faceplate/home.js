/**
 * Home Page JavaScript
 */

(function() {
  'use strict';

  // ============================================
  // ANIMATED COUNTERS
  // ============================================
  const AnimatedCounters = {
    init() {
      const counters = document.querySelectorAll('[data-count]');
      if (counters.length === 0) return;

      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            this.animate(entry.target);
            observer.unobserve(entry.target);
          }
        });
      }, { threshold: 0.5 });

      counters.forEach(counter => observer.observe(counter));
    },

    animate(element) {
      const target = parseFloat(element.dataset.count);
      const suffix = element.dataset.suffix || '';
      const prefix = element.dataset.prefix || '';
      const duration = 2000;
      const startTime = performance.now();
      const isDecimal = target % 1 !== 0;

      const update = (currentTime) => {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Easing function (ease-out)
        const easeOut = 1 - Math.pow(1 - progress, 3);
        const current = target * easeOut;
        
        if (isDecimal) {
          element.textContent = `${prefix}${current.toFixed(1)}${suffix}`;
        } else {
          element.textContent = `${prefix}${Math.floor(current)}${suffix}`;
        }

        if (progress < 1) {
          requestAnimationFrame(update);
        }
      };

      requestAnimationFrame(update);
    }
  };

  // ============================================
  // NAVBAR SCROLL EFFECT
  // ============================================
  const NavbarScroll = {
    init() {
      const navbar = document.querySelector('.fp-navbar');
      if (!navbar) return;

      let lastScroll = 0;
      
      window.addEventListener('scroll', () => {
        const currentScroll = window.scrollY;
        
        if (currentScroll > 100) {
          navbar.style.backgroundColor = 'rgba(10, 10, 10, 0.98)';
          navbar.style.boxShadow = '0 1px 3px rgba(0, 0, 0, 0.5)';
        } else {
          navbar.style.backgroundColor = 'rgba(10, 10, 10, 0.95)';
          navbar.style.boxShadow = 'none';
        }
        
        lastScroll = currentScroll;
      }, { passive: true });
    }
  };

  // ============================================
  // INITIALIZE
  // ============================================
  document.addEventListener('DOMContentLoaded', () => {
    AnimatedCounters.init();
    NavbarScroll.init();
  });
})();