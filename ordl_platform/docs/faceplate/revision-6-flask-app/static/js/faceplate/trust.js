/**
 * Trust Page JavaScript
 */

(function() {
  'use strict';

  // Region map interactivity
  const RegionMap = {
    init() {
      this.points = document.querySelectorAll('.region-point');
      if (this.points.length === 0) return;

      this.bindEvents();
    },

    bindEvents() {
      this.points.forEach(point => {
        point.addEventListener('mouseenter', () => {
          this.points.forEach(p => p.classList.remove('active'));
          point.classList.add('active');
        });
      });
    }
  };

  document.addEventListener('DOMContentLoaded', () => {
    RegionMap.init();
  });
})();