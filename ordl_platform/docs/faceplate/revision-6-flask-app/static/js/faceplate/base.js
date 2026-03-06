/**
 * ORDL Faceplate - Base JavaScript
 * Shared functionality for public-facing pages
 */

(function() {
  'use strict';

  // ============================================
  // COMMAND PALETTE
  // ============================================
  const CommandPalette = {
    element: null,
    input: null,
    results: null,
    isOpen: false,
    selectedIndex: -1,
    
    commands: [
      { id: 'home', label: 'Home', shortcut: 'H', url: '/', section: 'Pages' },
      { id: 'pricing', label: 'Pricing', shortcut: 'P', url: '/pricing', section: 'Pages' },
      { id: 'docs', label: 'Documentation', shortcut: 'D', url: '/docs', section: 'Pages' },
      { id: 'trust', label: 'Trust Center', shortcut: 'T', url: '/trust', section: 'Pages' },
      { id: 'status', label: 'System Status', shortcut: 'S', url: '/status', section: 'Pages' },
      { id: 'contact', label: 'Contact', shortcut: 'C', url: '/contact', section: 'Pages' },
      { id: 'login', label: 'Sign In', shortcut: 'L', url: '/login', section: 'Account' },
      { id: 'signup', label: 'Get Started', shortcut: 'G', url: '/signup', section: 'Account' },
      { id: 'changelog', label: 'Changelog', shortcut: null, url: '/changelog', section: 'Resources' },
    ],

    init() {
      this.element = document.getElementById('commandPalette');
      if (!this.element) return;
      
      this.input = this.element.querySelector('.fp-command-input');
      this.results = document.getElementById('commandResults');
      
      this.bindEvents();
    },

    bindEvents() {
      // Keyboard shortcut to open (Cmd/Ctrl + K)
      document.addEventListener('keydown', (e) => {
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
          e.preventDefault();
          this.toggle();
        }
        if (e.key === 'Escape' && this.isOpen) {
          this.close();
        }
      });

      // Input handling
      if (this.input) {
        this.input.addEventListener('input', (e) => {
          this.filter(e.target.value);
        });

        this.input.addEventListener('keydown', (e) => {
          if (e.key === 'ArrowDown') {
            e.preventDefault();
            this.selectNext();
          } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            this.selectPrev();
          } else if (e.key === 'Enter') {
            e.preventDefault();
            this.executeSelected();
          }
        });
      }

      // Click outside to close
      this.element.addEventListener('click', (e) => {
        if (e.target === this.element || e.target.classList.contains('fp-command-backdrop')) {
          this.close();
        }
      });
    },

    toggle() {
      if (this.isOpen) {
        this.close();
      } else {
        this.open();
      }
    },

    open() {
      this.isOpen = true;
      this.element.setAttribute('aria-hidden', 'false');
      document.body.style.overflow = 'hidden';
      
      if (this.input) {
        setTimeout(() => this.input.focus(), 10);
      }
      
      this.renderResults(this.commands);
    },

    close() {
      this.isOpen = false;
      this.element.setAttribute('aria-hidden', 'true');
      document.body.style.overflow = '';
      this.selectedIndex = -1;
      
      if (this.input) {
        this.input.value = '';
      }
    },

    filter(query) {
      const normalizedQuery = query.toLowerCase().trim();
      
      if (!normalizedQuery) {
        this.renderResults(this.commands);
        return;
      }

      const filtered = this.commands.filter(cmd => 
        cmd.label.toLowerCase().includes(normalizedQuery) ||
        cmd.section.toLowerCase().includes(normalizedQuery)
      );
      
      this.renderResults(filtered, normalizedQuery);
    },

    renderResults(commands, highlightQuery = '') {
      if (!this.results) return;

      if (commands.length === 0) {
        this.results.innerHTML = `
          <div class="fp-command-empty">
            <p>No commands found</p>
          </div>
        `;
        return;
      }

      // Group by section
      const grouped = commands.reduce((acc, cmd) => {
        if (!acc[cmd.section]) acc[cmd.section] = [];
        acc[cmd.section].push(cmd);
        return acc;
      }, {});

      let html = '';
      Object.entries(grouped).forEach(([section, cmds]) => {
        html += `
          <div class="fp-command-section">
            <div class="fp-command-section-title">${section}</div>
            ${cmds.map((cmd, idx) => this.renderCommandItem(cmd, highlightQuery)).join('')}
          </div>
        `;
      });

      this.results.innerHTML = html;
      
      // Add click handlers
      this.results.querySelectorAll('.fp-command-item').forEach((item, idx) => {
        item.addEventListener('click', () => {
          const url = item.dataset.url;
          if (url) window.location.href = url;
        });
        item.addEventListener('mouseenter', () => {
          this.selectedIndex = idx;
          this.updateSelection();
        });
      });
    },

    renderCommandItem(cmd, highlightQuery) {
      let label = cmd.label;
      if (highlightQuery) {
        const regex = new RegExp(`(${highlightQuery})`, 'gi');
        label = label.replace(regex, '<span class="fp-command-item-match">$1</span>');
      }

      return `
        <div class="fp-command-item" data-url="${cmd.url}" data-id="${cmd.id}">
          <svg class="fp-command-item-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 12h18M3 6h18M3 18h18"></path>
          </svg>
          <span class="fp-command-item-text">${label}</span>
          ${cmd.shortcut ? `<span class="fp-command-item-shortcut">${cmd.shortcut}</span>` : ''}
        </div>
      `;
    },

    selectNext() {
      const items = this.results.querySelectorAll('.fp-command-item');
      if (items.length === 0) return;
      
      this.selectedIndex = (this.selectedIndex + 1) % items.length;
      this.updateSelection();
    },

    selectPrev() {
      const items = this.results.querySelectorAll('.fp-command-item');
      if (items.length === 0) return;
      
      this.selectedIndex = this.selectedIndex <= 0 ? items.length - 1 : this.selectedIndex - 1;
      this.updateSelection();
    },

    updateSelection() {
      const items = this.results.querySelectorAll('.fp-command-item');
      items.forEach((item, idx) => {
        item.classList.toggle('selected', idx === this.selectedIndex);
      });
      
      const selected = items[this.selectedIndex];
      if (selected) {
        selected.scrollIntoView({ block: 'nearest' });
      }
    },

    executeSelected() {
      const items = this.results.querySelectorAll('.fp-command-item');
      const selected = items[this.selectedIndex];
      
      if (selected) {
        const url = selected.dataset.url;
        if (url) window.location.href = url;
      }
    }
  };

  // ============================================
  // MOBILE MENU
  // ============================================
  const MobileMenu = {
    toggle: null,
    menu: null,
    isOpen: false,

    init() {
      this.toggle = document.getElementById('mobileMenuToggle');
      this.menu = document.getElementById('mobileMenu');
      
      if (!this.toggle || !this.menu) return;
      
      this.bindEvents();
    },

    bindEvents() {
      this.toggle.addEventListener('click', () => this.toggleMenu());
      
      // Close when clicking a link
      this.menu.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => this.close());
      });
      
      // Close on escape
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && this.isOpen) {
          this.close();
        }
      });
    },

    toggleMenu() {
      if (this.isOpen) {
        this.close();
      } else {
        this.open();
      }
    },

    open() {
      this.isOpen = true;
      this.toggle.setAttribute('aria-expanded', 'true');
      this.menu.setAttribute('aria-hidden', 'false');
      document.body.style.overflow = 'hidden';
    },

    close() {
      this.isOpen = false;
      this.toggle.setAttribute('aria-expanded', 'false');
      this.menu.setAttribute('aria-hidden', 'true');
      document.body.style.overflow = '';
    }
  };

  // ============================================
  // SCROLL EFFECTS
  // ============================================
  const ScrollEffects = {
    init() {
      this.handleScroll();
      window.addEventListener('scroll', this.throttle(() => this.handleScroll(), 100));
    },

    handleScroll() {
      const navbar = document.querySelector('.fp-navbar');
      if (navbar) {
        if (window.scrollY > 10) {
          navbar.classList.add('scrolled');
        } else {
          navbar.classList.remove('scrolled');
        }
      }
    },

    throttle(fn, wait) {
      let time = Date.now();
      return function() {
        if ((time + wait - Date.now()) < 0) {
          fn();
          time = Date.now();
        }
      };
    }
  };

  // ============================================
  // ANIMATIONS
  // ============================================
  const Animations = {
    init() {
      this.observeElements();
    },

    observeElements() {
      const animatedElements = document.querySelectorAll('[data-animate]');
      
      if (animatedElements.length === 0) return;
      
      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('fp-animate-fade-in-up');
            observer.unobserve(entry.target);
          }
        });
      }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
      });

      animatedElements.forEach(el => observer.observe(el));
    }
  };

  // ============================================
  // FORM VALIDATION
  // ============================================
  const FormValidation = {
    init() {
      document.querySelectorAll('form[data-validate]').forEach(form => {
        form.addEventListener('submit', (e) => this.handleSubmit(e, form));
      });
    },

    handleSubmit(e, form) {
      let isValid = true;
      
      form.querySelectorAll('[required]').forEach(field => {
        if (!field.value.trim()) {
          isValid = false;
          this.showError(field, 'This field is required');
        } else {
          this.clearError(field);
        }
      });

      // Email validation
      form.querySelectorAll('input[type="email"]').forEach(field => {
        if (field.value && !this.isValidEmail(field.value)) {
          isValid = false;
          this.showError(field, 'Please enter a valid email address');
        }
      });

      if (!isValid) {
        e.preventDefault();
      }
    },

    isValidEmail(email) {
      return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    },

    showError(field, message) {
      field.classList.add('fp-error');
      
      let errorEl = field.parentNode.querySelector('.fp-error-message');
      if (!errorEl) {
        errorEl = document.createElement('span');
        errorEl.className = 'fp-error-message';
        field.parentNode.appendChild(errorEl);
      }
      errorEl.textContent = message;
    },

    clearError(field) {
      field.classList.remove('fp-error');
      const errorEl = field.parentNode.querySelector('.fp-error-message');
      if (errorEl) errorEl.remove();
    }
  };

  // ============================================
  // COOKIE CONSENT
  // ============================================
  const CookieConsent = {
    init() {
      if (localStorage.getItem('cookieConsent')) return;
      
      this.showBanner();
    },

    showBanner() {
      const banner = document.createElement('div');
      banner.className = 'fp-cookie-banner';
      banner.innerHTML = `
        <div class="fp-cookie-content">
          <p>We use cookies to enhance your experience. By continuing, you agree to our use of cookies.</p>
          <div class="fp-cookie-actions">
            <button class="fp-btn fp-btn-ghost fp-btn-sm" data-action="reject">Reject</button>
            <button class="fp-btn fp-btn-primary fp-btn-sm" data-action="accept">Accept</button>
          </div>
        </div>
      `;
      
      document.body.appendChild(banner);
      
      // Animate in
      setTimeout(() => banner.classList.add('visible'), 100);
      
      // Handle actions
      banner.querySelectorAll('button').forEach(btn => {
        btn.addEventListener('click', () => {
          const action = btn.dataset.action;
          localStorage.setItem('cookieConsent', action);
          banner.classList.remove('visible');
          setTimeout(() => banner.remove(), 300);
        });
      });
    }
  };

  // ============================================
  // INITIALIZE
  // ============================================
  function init() {
    CommandPalette.init();
    MobileMenu.init();
    ScrollEffects.init();
    Animations.init();
    FormValidation.init();
    CookieConsent.init();
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Expose to global scope for page-specific scripts
  window.ORDL = {
    CommandPalette,
    MobileMenu,
    ScrollEffects,
    Animations
  };
})();