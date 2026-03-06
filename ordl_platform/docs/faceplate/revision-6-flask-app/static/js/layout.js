/**
 * ORDL Layout JavaScript
 * Global interactions and shell behavior
 */

(function() {
  'use strict';

  // ============================================
  // State Management
  // ============================================

  const state = {
    sidebarExpanded: false,
    sidebarMobileOpen: false,
    contextVisible: false,
    commandPaletteOpen: false,
    activeNavItem: null,
    commandPaletteSelectedIndex: 0,
    commandPaletteFilter: ''
  };

  // ============================================
  // DOM Elements
  // ============================================

  const appShell = document.querySelector('.app-shell');
  const sidebarToggle = document.querySelector('.sidebar-toggle');
  const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
  const commandEntry = document.querySelector('.command-entry');
  const commandPalette = document.querySelector('.command-palette');
  const commandPaletteInput = document.querySelector('.command-palette-input');
  const commandPaletteClose = document.querySelector('.command-palette-close');
  const contextRailClose = document.querySelector('.context-rail-close');
  const navLinks = document.querySelectorAll('.nav-link');

  // ============================================
  // Sidebar Toggle
  // ============================================

  function toggleSidebar() {
    state.sidebarExpanded = !state.sidebarExpanded;
    updateSidebarState();
    
    // Persist preference
    localStorage.setItem('ordl_sidebar_expanded', state.sidebarExpanded);
  }

  function updateSidebarState() {
    if (state.sidebarExpanded) {
      appShell.classList.add('sidebar-expanded');
    } else {
      appShell.classList.remove('sidebar-expanded');
    }
  }

  // ============================================
  // Mobile Menu
  // ============================================

  function toggleMobileMenu() {
    state.sidebarMobileOpen = !state.sidebarMobileOpen;
    updateMobileMenuState();
  }

  function updateMobileMenuState() {
    if (state.sidebarMobileOpen) {
      appShell.classList.add('sidebar-mobile-open');
      document.body.style.overflow = 'hidden';
    } else {
      appShell.classList.remove('sidebar-mobile-open');
      document.body.style.overflow = '';
    }
  }

  function closeMobileMenu() {
    state.sidebarMobileOpen = false;
    updateMobileMenuState();
  }

  // ============================================
  // Context Rail
  // ============================================

  function toggleContextRail() {
    state.contextVisible = !state.contextVisible;
    updateContextRailState();
  }

  function showContextRail() {
    state.contextVisible = true;
    updateContextRailState();
  }

  function hideContextRail() {
    state.contextVisible = false;
    updateContextRailState();
  }

  function updateContextRailState() {
    if (state.contextVisible) {
      appShell.classList.add('context-visible');
    } else {
      appShell.classList.remove('context-visible');
    }
  }

  // ============================================
  // Command Palette
  // ============================================

  function openCommandPalette() {
    state.commandPaletteOpen = true;
    state.commandPaletteSelectedIndex = 0;
    state.commandPaletteFilter = '';
    updateCommandPaletteState();
    
    // Focus input after transition
    setTimeout(() => {
      if (commandPaletteInput) {
        commandPaletteInput.focus();
        commandPaletteInput.value = '';
      }
    }, 50);
  }

  function closeCommandPalette() {
    state.commandPaletteOpen = false;
    updateCommandPaletteState();
  }

  function updateCommandPaletteState() {
    if (state.commandPaletteOpen) {
      commandPalette.classList.add('open');
      document.body.style.overflow = 'hidden';
    } else {
      commandPalette.classList.remove('open');
      document.body.style.overflow = '';
    }
  }

  function handleCommandPaletteInput(e) {
    state.commandPaletteFilter = e.target.value.toLowerCase();
    filterCommandPaletteResults();
  }

  function filterCommandPaletteResults() {
    const items = document.querySelectorAll('.command-palette-item');
    const filter = state.commandPaletteFilter;
    let visibleCount = 0;

    items.forEach((item, index) => {
      const title = item.querySelector('.command-palette-item-title')?.textContent.toLowerCase() || '';
      const subtitle = item.querySelector('.command-palette-item-subtitle')?.textContent.toLowerCase() || '';
      
      const matches = title.includes(filter) || subtitle.includes(filter);
      
      if (matches) {
        item.style.display = 'flex';
        item.classList.toggle('selected', visibleCount === state.commandPaletteSelectedIndex);
        item.dataset.visibleIndex = visibleCount;
        visibleCount++;
      } else {
        item.style.display = 'none';
        item.classList.remove('selected');
        delete item.dataset.visibleIndex;
      }
    });
  }

  function navigateCommandPalette(direction) {
    const visibleItems = document.querySelectorAll('.command-palette-item[data-visible-index]');
    const maxIndex = visibleItems.length - 1;

    if (maxIndex < 0) return;

    state.commandPaletteSelectedIndex += direction;
    
    if (state.commandPaletteSelectedIndex < 0) {
      state.commandPaletteSelectedIndex = maxIndex;
    } else if (state.commandPaletteSelectedIndex > maxIndex) {
      state.commandPaletteSelectedIndex = 0;
    }

    visibleItems.forEach(item => {
      item.classList.remove('selected');
    });

    const selectedItem = visibleItems[state.commandPaletteSelectedIndex];
    if (selectedItem) {
      selectedItem.classList.add('selected');
      selectedItem.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }

  function executeSelectedCommand() {
    const selectedItem = document.querySelector('.command-palette-item.selected');
    if (selectedItem) {
      const href = selectedItem.dataset.href;
      if (href) {
        window.location.href = href;
      } else {
        selectedItem.click();
      }
      closeCommandPalette();
    }
  }

  // ============================================
  // Navigation Active State
  // ============================================

  function setActiveNavItem(path) {
    const currentPath = path || window.location.pathname;
    
    navLinks.forEach(link => {
      const linkPath = link.getAttribute('href');
      
      if (linkPath === currentPath || 
          (linkPath !== '/' && currentPath.startsWith(linkPath))) {
        link.classList.add('active');
      } else {
        link.classList.remove('active');
      }
    });
  }

  // ============================================
  // Keyboard Navigation
  // ============================================

  function handleKeyDown(e) {
    // Command Palette: Cmd/Ctrl + K
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      if (state.commandPaletteOpen) {
        closeCommandPalette();
      } else {
        openCommandPalette();
      }
      return;
    }

    // Command Palette: Escape to close
    if (e.key === 'Escape' && state.commandPaletteOpen) {
      e.preventDefault();
      closeCommandPalette();
      return;
    }

    // Command Palette: Arrow navigation
    if (state.commandPaletteOpen) {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          navigateCommandPalette(1);
          break;
        case 'ArrowUp':
          e.preventDefault();
          navigateCommandPalette(-1);
          break;
        case 'Enter':
          e.preventDefault();
          executeSelectedCommand();
          break;
      }
      return;
    }

    // Global shortcuts
    switch (e.key) {
      case '[':
        if (e.metaKey || e.ctrlKey) {
          e.preventDefault();
          toggleSidebar();
        }
        break;
      case ']':
        if (e.metaKey || e.ctrlKey) {
          e.preventDefault();
          toggleContextRail();
        }
        break;
    }
  }

  // ============================================
  // Touch/Swipe Gestures (Mobile)
  // ============================================

  let touchStartX = 0;
  let touchEndX = 0;
  const SWIPE_THRESHOLD = 100;

  function handleTouchStart(e) {
    touchStartX = e.changedTouches[0].screenX;
  }

  function handleTouchEnd(e) {
    touchEndX = e.changedTouches[0].screenX;
    handleSwipe();
  }

  function handleSwipe() {
    const swipeDistance = touchEndX - touchStartX;

    // Swipe right from left edge - open sidebar
    if (swipeDistance > SWIPE_THRESHOLD && touchStartX < 50) {
      state.sidebarMobileOpen = true;
      updateMobileMenuState();
    }

    // Swipe left - close sidebar
    if (swipeDistance < -SWIPE_THRESHOLD && state.sidebarMobileOpen) {
      closeMobileMenu();
    }

    // Swipe left from right edge - open context rail
    if (swipeDistance < -SWIPE_THRESHOLD && touchStartX > window.innerWidth - 50) {
      showContextRail();
    }
  }

  // ============================================
  // Click Outside to Close
  // ============================================

  function handleClickOutside(e) {
    // Close mobile sidebar when clicking outside
    if (state.sidebarMobileOpen && 
        !e.target.closest('.sidebar') && 
        !e.target.closest('.mobile-menu-toggle')) {
      closeMobileMenu();
    }

    // Close context rail when clicking overlay
    if (e.target.classList.contains('context-overlay')) {
      hideContextRail();
    }

    // Close command palette when clicking backdrop
    if (e.target === commandPalette) {
      closeCommandPalette();
    }
  }

  // ============================================
  // Initialization
  // ============================================

  function init() {
    // Restore sidebar state from localStorage
    const savedSidebarState = localStorage.getItem('ordl_sidebar_expanded');
    if (savedSidebarState !== null) {
      state.sidebarExpanded = savedSidebarState === 'true';
      updateSidebarState();
    }

    // Set initial active nav item
    setActiveNavItem();

    // Event Listeners
    if (sidebarToggle) {
      sidebarToggle.addEventListener('click', toggleSidebar);
    }

    if (mobileMenuToggle) {
      mobileMenuToggle.addEventListener('click', toggleMobileMenu);
    }

    if (commandEntry) {
      commandEntry.addEventListener('click', openCommandPalette);
    }

    if (commandPaletteClose) {
      commandPaletteClose.addEventListener('click', closeCommandPalette);
    }

    if (contextRailClose) {
      contextRailClose.addEventListener('click', hideContextRail);
    }

    if (commandPaletteInput) {
      commandPaletteInput.addEventListener('input', handleCommandPaletteInput);
    }

    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyDown);

    // Touch gestures
    document.addEventListener('touchstart', handleTouchStart, { passive: true });
    document.addEventListener('touchend', handleTouchEnd, { passive: true });

    // Click outside
    document.addEventListener('click', handleClickOutside);

    // Handle popstate for SPA-like navigation
    window.addEventListener('popstate', () => {
      setActiveNavItem();
    });

    console.log('ORDL Layout initialized');
  }

  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // ============================================
  // Public API
  // ============================================

  window.ORDL = {
    // State getters
    get isSidebarExpanded() { return state.sidebarExpanded; },
    get isContextVisible() { return state.contextVisible; },
    get isCommandPaletteOpen() { return state.commandPaletteOpen; },

    // Actions
    toggleSidebar,
    toggleContextRail,
    showContextRail,
    hideContextRail,
    openCommandPalette,
    closeCommandPalette,
    setActiveNavItem,

    // Utility
    init
  };

})();
