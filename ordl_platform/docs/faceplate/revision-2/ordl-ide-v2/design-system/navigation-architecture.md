# ORDL IDE Navigation Architecture
## Design Specification v1.0

> **Design Philosophy:** Industrial precision meets fluid interaction. Every transition feels like machinery engaging—deliberate, satisfying, purposeful.

---

## Table of Contents

1. [Design Principles](#1-design-principles)
2. [Navigation Architecture](#2-navigation-architecture)
3. [Main Views & Screens](#3-main-views--screens)
4. [Page Transition System](#4-page-transition-system)
5. [Keyboard Navigation](#5-keyboard-navigation)
6. [Wireframe Specifications](#6-wireframe-specifications)
7. [Interaction Patterns](#7-interaction-patterns)

---

## 1. Design Principles

### Core Tenets

| Principle | Description | Implementation |
|-----------|-------------|----------------|
| **Mechanical Precision** | Every interaction has weight and feedback | Spring physics, tactile responses |
| **Context Preservation** | Users never lose their place | Breadcrumbs, state retention, deep linking |
| **Keyboard-First** | Power users never need a mouse | Vim bindings, command palette, shortcuts |
| **Progressive Disclosure** | Complexity reveals itself as needed | Collapsible sections, detail drawers |
| **Spatial Consistency** | Elements stay where expected | Fixed zones, predictable layouts |

### Visual Language

```
┌─────────────────────────────────────────────────────────────────┐
│  INDUSTRIAL AESTHETIC                                            │
├─────────────────────────────────────────────────────────────────┤
│  • Dark substrate (#0D0D0D base)                                 │
│  • Signal colors: Amber (#FFB800), Cyan (#00D4AA), Red (#FF3366) │
│  • Grid overlays (subtle 8px base grid)                          │
│  • Status indicators as illuminated ports                        │
│  • Transitions feel like mechanical actuation                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Navigation Architecture

### 2.1 Spatial Zones

The IDE is divided into persistent zones that maintain their state across navigation:

```
┌─────────────────────────────────────────────────────────────────────┐
│ ZONE 0: TOP BAR (Fixed, 48px)                                       │
│ [≡ Menu]  [Breadcrumbs →]                    [System Status] [👤]   │
├──────────┬──────────────────────────────────────────────────────────┤
│          │                                                          │
│ ZONE 1:  │              ZONE 2: MAIN CANVAS                         │
│ SIDEBAR  │              (Dynamic content area)                      │
│ (64px    │                                                          │
│  collapsed│              ┌─────────────────────────────┐             │
│  240px   │              │    VIEW CONTENT             │             │
│  expanded)│              │    (contextual)             │             │
│          │              └─────────────────────────────┘             │
│ [Icons]  │                                                          │
│ +        │              ZONE 3: CONTEXT PANEL                       │
│ [Labels] │              (Collapsible, 320px default)                │
│          │                                                          │
│          │                                                          │
├──────────┴──────────────────────────────────────────────────────────┤
│ ZONE 4: COMMAND PALETTE (Overlay, triggered)                        │
│ ZONE 5: TOAST/NOTIFICATION ZONE (Floating)                          │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Navigation Hierarchy

```
ORDL IDE
├── Fleet Dashboard [g d]
│   ├── Agent Grid View
│   ├── List View
│   └── Topology View
├── Agent Workshop [g a]
│   ├── Editor Canvas
│   ├── Behavior Tree
│   ├── State Machine
│   └── Properties Panel
├── Deployment Pipeline [g p]
│   ├── Pipeline Overview
│   ├── Build Stages
│   ├── Deployment History
│   └── Environment Manager
├── System Settings [g s]
│   ├── General
│   ├── Integrations
│   ├── Security
│   └── Advanced
└── Onboarding [g o] (or auto-triggered)
    ├── Welcome
    ├── Quick Start
    ├── Tutorial Library
    └── Documentation
```

### 2.3 Sidebar Navigation

#### Collapsed State (64px)
- Icon-only navigation
- Hover reveals tooltip with shortcut hint
- Active state: illuminated amber indicator + subtle glow

#### Expanded State (240px)
- Full labels visible
- Nested sections collapsible
- Drag-to-reorder for custom organization
- Recent items section (last 5 visited contexts)

#### Sidebar Items

```
┌──────────────────────────────────────┐
│  ≡  [Hamburger - toggle expand]      │
├──────────────────────────────────────┤
│  ◈  Dashboard        [g d]           │
│  ⚙  Agent Workshop   [g a] ← active  │
│  ⏵  Deployment       [g p]           │
│  ◉  Settings         [g s]           │
├──────────────────────────────────────┤
│  ─  Recent Contexts                  │
│     └─ agent-7-debug                 │
│     └─ production-deploy             │
├──────────────────────────────────────┤
│  ?  Help & Onboard   [g o]           │
└──────────────────────────────────────┘
```

### 2.4 Breadcrumb System

Breadcrumbs serve dual purpose: navigation AND context hierarchy.

```
Fleet Dashboard ▸ Production Environment ▸ agent-node-7 ▸ Behavior Editor
│                 │                          │             │
│                 │                          │             └── Deep context
│                 │                          └── Instance/Resource
│                 └── Environment/Namespace
└── Root section
```

**Interaction Patterns:**
- Click any segment to jump to that level
- Right-click for context menu (open in new tab, copy path, etc.)
- Each segment shows loading state when children are fetching
- Truncation with "..." for deep paths, hover to expand

---

## 3. Main Views & Screens

### 3.1 Fleet Dashboard

**Purpose:** Operational overview of all agents and system health.

**Primary Function:** Monitor, filter, and access agents at scale.

#### Layout Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│ [Fleet Dashboard]                              [+ New Agent] [⚙️]   │
├─────────────────────────────────────────────────────────────────────┤
│ View: [Grid ▼] | Filter: [All Agents ▼] | Search: [________] [🔍]  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │
│  │ ● Agent-1   │  │ ● Agent-2   │  │ ◌ Agent-3   │  │  + Add    │  │
│  │   [preview] │  │   [preview] │  │   [preview] │  │   New     │  │
│  │             │  │             │  │             │  │           │  │
│  │ ▓▓▓▓░░ 80%  │  │ ▓▓▓▓▓▓ 95% │  │ ▓▓░░░░ 40%  │  │           │  │
│  │ 🟢 Running  │  │ 🟡 Warning  │  │ 🔴 Error    │  │           │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │ ◉ Agent-4   │  │ ◎ Agent-5   │  │ ◎ Agent-6   │                  │
│  │   [preview] │  │   [preview] │  │   [preview] │                  │
│  │             │  │             │  │             │                  │
│  │ ▓▓▓▓▓▓ 100% │  │ ▓▓▓▓▓░ 85% │  │ ▓▓▓░░░ 60%  │                  │
│  │ ⚪ Standby  │  │ 🟢 Running  │  │ 🟢 Running  │                  │
│  └─────────────┘  └─────────────┘  └─────────────┘                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### Key Interactions

| Action | Method | Result |
|--------|--------|--------|
| Open Agent | Click card | Navigate to Agent Workshop with agent loaded |
| Quick Actions | Hover card | Reveal action bar (start/stop/restart/logs) |
| Multi-select | Cmd/Ctrl + Click | Select multiple for batch operations |
| Context Menu | Right-click card | Full agent options menu |
| View Toggle | Grid/List icons | Switch between visual and dense list views |
| Filter | Search bar | Real-time filtering by name, status, tags |

#### State Visualization

Each agent card displays:
- **Status indicator:** Illuminated port (green/amber/red/white)
- **Health bar:** Horizontal progress showing resource utilization
- **Activity sparkline:** Mini graph of recent activity (last 60s)
- **Quick stats:** 2-3 key metrics (CPU, memory, active tasks)

---

### 3.2 Agent Workshop

**Purpose:** Deep editing and debugging of individual agents.

**Primary Function:** Visual programming environment for agent behavior.

#### Layout Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│ [←] [Agent-7] [● Saved]                    [Debug ▶] [Deploy ⏵]     │
├──────────┬────────────────────────────────────────────┬─────────────┤
│          │                                            │             │
│ PALETTE  │           CANVAS AREA                      │ PROPERTIES  │
│          │           (Infinite pan/zoom)              │ PANEL       │
│ ┌──────┐ │                                            │             │
│ │Nodes │ │    ┌─────┐         ┌─────┐                │ ┌─────────┐ │
│ ├──────┤ │    │Input│────────▶│Process│              │ │Name:    │ │
│ │Input │ │    └──┬──┘         └──┬──┘                │ │[Agent-7]│ │
│ │Logic │ │       │               │                   │ ├─────────┤ │
│ │Action│ │       ▼               ▼                   │ │Type:    │ │
│ │AI    │ │    ┌─────┐         ┌─────┐                │ │[Worker] │ │
│ └──────┘ │    │Validate       │Store│                │ ├─────────┤ │
│          │    └─────┘         └─────┘                │ │Config   │ │
│ [Layers] │                                            │ │[Edit ↓] │ │
│ ▓ Canvas │    ┌─────────────────────────┐            │ │         │ │
│ ▒ Overlay│    │  Selection Info         │            │ │[Apply]  │ │
│          │    │  3 nodes selected       │            │ └─────────┘ │
│          │    └─────────────────────────┘            │             │
│          │                                            │ [Inspector] │
│          │                                            │ [Debug Log] │
│          │                                            │             │
└──────────┴────────────────────────────────────────────┴─────────────┘
```

#### Panel Structure

**Left Panel - Node Palette (200px, collapsible)**
- Categorized node types (Input, Logic, Action, AI)
- Search/filter nodes
- Favorites section
- Drag to canvas to instantiate

**Center - Canvas (Fluid)**
- Infinite canvas with grid snap
- Zoom: 25% - 400%
- Mini-map in bottom-right corner
- Multi-select with marquee or Cmd+click
- Pan with middle-mouse or Space+drag

**Right Panel - Properties (320px, collapsible)**
- Context-aware based on selection
- Empty state: Workspace-level properties
- Single selection: Node properties
- Multi-selection: Batch operations
- Tabs: Properties | Inspector | Debug Log

#### Key Interactions

| Action | Shortcut | Description |
|--------|----------|-------------|
| Create Node | Double-click canvas | Open node creation palette |
| Connect Nodes | Drag from port to port | Create data/action flow |
| Pan Canvas | Space + Drag | Move around workspace |
| Zoom | Ctrl/Cmd + Scroll | Zoom in/out |
| Select All | Cmd/Ctrl + A | Select all nodes |
| Delete | Delete/Backspace | Remove selected |
| Group | Cmd/Ctrl + G | Create compound node |
| Ungroup | Cmd/Ctrl + Shift + G | Expand compound node |
| Debug | F5 | Start debugging session |
| Breakpoint | F9 | Toggle breakpoint on node |

---

### 3.3 Deployment Pipeline

**Purpose:** Manage build, test, and deployment workflows.

**Primary Function:** CI/CD visualization and control for agent deployment.

#### Layout Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│ [Deployment Pipeline]                        [+ New Pipeline] [⚙️]  │
├─────────────────────────────────────────────────────────────────────┤
│ Pipeline: [Production Agents ▼]  Branch: main  Last run: 2m ago     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐      │
│  │  BUILD   │───▶│   TEST   │───▶│  STAGE   │───▶│ PRODUCTION│      │
│  │  ─────   │    │  ─────   │    │  ─────   │    │  ─────   │      │
│  │  ✓ 45s   │    │  ✓ 2m    │    │  ▶ 1m    │    │  ○ --    │      │
│  │  12 jobs │    │  8 jobs  │    │  3 jobs  │    │  2 jobs  │      │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘      │
│       │               │               │               │            │
│    [details]       [details]       [details]       [details]       │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│ RECENT RUNS                    │  STAGE DETAILS: TEST               │
│ ───────────                    │  ──────────────────────────────    │
│ ◉ #284  main  ✓ Success  2m ago│  Job              Status   Time    │
│ ○ #283  dev   ✗ Failed   1h ago│  ──────────────────────────────    │
│ ○ #282  main  ✓ Success  3h ago│  Unit Tests       ✓ Pass   45s    │
│ ○ #281  dev   ✓ Success  5h ago│  Integration      ✓ Pass   32s    │
│ ○ #280  main  ✓ Success  1d ago│  Lint             ✓ Pass   12s    │
│                                │  Security Scan    ✓ Pass   28s    │
│                                │  Performance      ✓ Pass   18s    │
│                                │                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### Pipeline Visualization

- **Horizontal flow:** Left-to-right stage progression
- **Stage status:** Color-coded (gray=pending, blue=running, green=success, red=failed)
- **Progress indicator:** Animated pulse for active stages
- **Connection lines:** Data flow between stages, animated for active transfers
- **Stage cards:** Expandable for detailed job view

#### Key Interactions

| Action | Method | Result |
|--------|--------|--------|
| View Run | Click pipeline run | Load full run details |
| Stage Details | Click stage card | Expand job breakdown |
| Job Logs | Click job row | Open log viewer |
| Rerun Stage | Hover + Rerun icon | Restart from this stage |
| Cancel Run | Active run menu | Stop current execution |
| Compare Runs | Multi-select | Side-by-side comparison |

---

### 3.4 System Settings

**Purpose:** Configure IDE and system-wide preferences.

**Primary Function:** Personalization, integrations, and advanced configuration.

#### Layout Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│ [System Settings]                                                   │
├──────────────┬──────────────────────────────────────────────────────┤
│              │                                                      │
│  NAVIGATION  │              SETTINGS CONTENT                        │
│              │                                                      │
│  ◉ General   │  ┌────────────────────────────────────────────────┐  │
│  ○ Editor    │  │  APPEARANCE                                    │  │
│  ○ Agents    │  │                                                │  │
│  ○ Keyboard  │  │  Theme: [Dark Industrial ▼]                    │  │
│  ○ Integrations│ │  Density: [Comfortable ▼]                      │  │
│  ○ Security  │  │  Animations: [ON ▼]                            │  │
│  ○ Advanced  │  │                                                │  │
│              │  │  ┌────────────────────────────────────────┐    │  │
│ ───────────  │  │  │  ◐  Accent Color                       │    │  │
│              │  │  │     ◉ Amber  ○ Cyan  ○ Custom          │    │  │
│              │  │  │     [________] #FFB800                 │    │  │
│              │  │  └────────────────────────────────────────┘    │  │
│              │  │                                                │  │
│              │  │  [Save Changes]        [Reset to Defaults]     │  │
│              │  └────────────────────────────────────────────────┘  │
│              │                                                      │
│              │                                                      │
└──────────────┴──────────────────────────────────────────────────────┘
```

#### Settings Categories

1. **General:** Theme, language, notifications, startup behavior
2. **Editor:** Grid settings, snap behavior, zoom defaults, auto-save
3. **Agents:** Default templates, runtime preferences, debug settings
4. **Keyboard:** Shortcut customization, Vim mode toggle, chord bindings
5. **Integrations:** Git, cloud providers, API keys, webhooks
6. **Security:** Authentication, encryption, audit logging
7. **Advanced:** Performance tuning, experimental features, debug mode

#### Key Interactions

- **Search:** Global search across all settings
- **Modified indicator:** Dot appears on modified sections
- **Revert:** Individual setting reset or section-wide
- **Import/Export:** Settings as JSON for sharing/backup
- **Validation:** Real-time validation with inline errors

---

### 3.5 Onboarding

**Purpose:** Welcome new users and guide them to productivity.

**Primary Function:** Progressive education without blocking experienced users.

#### Layout Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│ [Welcome to ORDL IDE]                          [Skip Tour] [✕]     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│                    ┌─────────────────────┐                          │
│                    │                     │                          │
│                    │    [HERO GRAPHIC]   │                          │
│                    │   Agent ecosystem   │                          │
│                    │     visualization   │                          │
│                    │                     │                          │
│                    └─────────────────────┘                          │
│                                                                     │
│              Build, deploy, and orchestrate AI agents               │
│                                                                     │
│         ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│         │  Quick      │  │  Browse     │  │  Import     │          │
│         │  Start      │  │  Templates  │  │  Project    │          │
│         │  [▶]        │  │  [◈]        │  │  [⬉]        │          │
│         └─────────────┘  └─────────────┘  └─────────────┘          │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│ RECENT DOCUMENTATION                                                │
│ ┌────────────────┐ ┌────────────────┐ ┌────────────────┐           │
│ │ Getting Started│ │ Agent Basics   │ │ Deployment     │           │
│ │ Guide          │ │                │ │ Guide          │           │
│ └────────────────┘ └────────────────┘ └────────────────┘           │
└─────────────────────────────────────────────────────────────────────┘
```

#### Onboarding Flow

1. **Welcome Screen:** Hero + primary actions
2. **Quick Start Wizard:** 
   - Choose template or blank
   - Configure basic settings
   - First agent walkthrough
3. **Interactive Tutorial:** 
   - Contextual tooltips
   - Guided actions with highlights
   - Progress tracking
4. **Documentation Hub:**
   - Searchable docs
   - Video tutorials
   - API reference

#### Smart Onboarding Behavior

- **First launch:** Full welcome experience
- **Return after 7 days:** "What's New" highlights
- **Feature discovery:** Contextual hints for unused features
- **Skip permanently:** "Don't show again" with re-enable in settings

---

## 4. Page Transition System

### 4.1 Transition Philosophy

Transitions should feel like mechanical components engaging—precise, weighted, and satisfying.

### 4.2 Transition Types

#### Standard Navigation (Sidebar/Breadcrumbs)

```
Duration: 300ms
Easing: cubic-bezier(0.4, 0.0, 0.2, 1)

Exit:  Current view slides left 20px + fades to 0.7 opacity
Enter: New view slides from right 20px + fades from 0.7 to 1.0

Visual: Like sliding a mechanical panel, slight resistance at start
```

#### Deep Navigation (Agent → Workshop)

```
Duration: 400ms
Easing: cubic-bezier(0.0, 0.0, 0.2, 1)

Exit:  Current view scales down to 0.95 + fades
Enter: New view scales up from 0.95 + fades in
       + Content stagger animation (50ms delay per section)

Visual: Zooming into a detail panel
```

#### Modal/Overlay Open

```
Duration: 250ms
Easing: cubic-bezier(0.0, 0.0, 0.2, 1)

Backdrop: Fade from 0 to 0.7 opacity black
Content:  Scale from 0.9 + fade in + slight upward translate (10px)

Visual: Like a gauge or meter swinging into position
```

#### Context Panel Slide

```
Duration: 200ms
Easing: cubic-bezier(0.4, 0.0, 1, 1)

Action: Slide from right edge, content reveals with mask

Visual: Like a drawer sliding out, mechanical precision
```

### 4.3 Stagger Patterns

When multiple elements animate:

```
List Items:    30ms stagger (top to bottom)
Grid Items:    40ms stagger (left-to-right, top-to-bottom)
Panel Sections: 50ms stagger (priority order)
```

### 4.4 Loading States

#### Skeleton Loading

```
Pulse animation on placeholder blocks
Duration: 1.5s loop
Easing: ease-in-out

┌─────────────────────────────────────────┐
│ ▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░ │ ← Shimmer sweep left-to-right
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░ │
│ ▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└─────────────────────────────────────────┘
```

#### Progress Indicators

- **Determinate:** Filling progress bar with mechanical tick marks
- **Indeterminate:** Back-and-forth scanning animation (like a sensor)
- **Spinner:** Rotating gear/segment (not a simple circle)

### 4.5 Micro-interactions

| Interaction | Animation | Duration |
|-------------|-----------|----------|
| Button Hover | Scale 1.02 + glow intensify | 150ms |
| Button Press | Scale 0.98 + shadow reduce | 100ms |
| Toggle Switch | Slide + background color | 200ms |
| Checkbox | Checkmark draw + scale bounce | 200ms |
| Tooltip | Fade + translate Y -4px | 150ms |
| Error Shake | Horizontal wobble (3 cycles) | 300ms |
| Success Pulse | Scale ripple + color flash | 400ms |

---

## 5. Keyboard Navigation

### 5.1 Vim-Style Navigation

#### Global Shortcuts

| Key | Action |
|-----|--------|
| `g` then `d` | Go to Dashboard |
| `g` then `a` | Go to Agent Workshop |
| `g` then `p` | Go to Deployment Pipeline |
| `g` then `s` | Go to System Settings |
| `g` then `o` | Go to Onboarding/Help |
| `g` then `h` | Go to Home (Dashboard) |

#### Canvas Navigation (Agent Workshop)

| Key | Action |
|-----|--------|
| `h` / `j` / `k` / `l` | Pan left/down/up/right |
| `Shift + h/j/k/l` | Pan faster |
| `+` / `-` | Zoom in/out |
| `0` | Reset zoom to 100% |
| `Shift + 0` | Fit to screen |
| `gg` | Go to top-left of canvas |
| `Shift + g` | Go to bottom-right of canvas |

#### Selection & Editing

| Key | Action |
|-----|--------|
| `Tab` | Select next node |
| `Shift + Tab` | Select previous node |
| `Esc` | Deselect all / close panel |
| `d` then `d` | Delete selected node(s) |
| `y` then `y` | Copy selected node(s) |
| `p` | Paste |
| `u` | Undo |
| `Ctrl + r` | Redo |
| `>` / `<` | Indent/outdent (if applicable) |

### 5.2 Command Palette

Triggered by `Cmd/Ctrl + K` or `Cmd/Ctrl + Shift + P`

```
┌─────────────────────────────────────────────────────────────────────┐
│ █                                                                   │
├─────────────────────────────────────────────────────────────────────┤
│ ⚡ Quick Actions                                                     │
│    New Agent                    [⌘ N]                               │
│    Open Recent                  [⌘ R]                               │
│    Save                         [⌘ S]                               │
│                                                                     │
│ 🧭 Navigation                                                       │
│    Go to Dashboard              [g d]                               │
│    Go to Agent Workshop         [g a]                               │
│    Go to Deployment Pipeline    [g p]                               │
│                                                                     │
│ ⚙️  Settings                                                        │
│    Toggle Theme                 [⌘ Shift T]                         │
│    Keyboard Shortcuts           [⌘ K]                               │
│                                                                     │
│ 🔍 Recently Opened                                                  │
│    Agent-7 (Production)                                             │
│    Deployment #284                                                  │
│    Behavior Tree: Customer Support                                  │
└─────────────────────────────────────────────────────────────────────┘
```

#### Command Palette Features

- **Fuzzy search:** Type any part of command name
- **Recent commands:** Top section shows last 5 used
- **Context-aware:** Different commands shown based on current view
- **Keyboard-only:** Arrow keys to navigate, Enter to execute
- **Shortcuts display:** Shows associated shortcut for learning

### 5.3 Shortcut Cheat Sheet

Accessible via `?` or `Cmd/Ctrl + /`

Displays overlay with all shortcuts organized by category:
- Global
- Navigation
- Canvas/Editor
- Agent Workshop
- Deployment
- Settings

### 5.4 Accessibility Shortcuts

| Key | Action |
|-----|--------|
| `Tab` | Navigate focusable elements |
| `Shift + Tab` | Reverse focus navigation |
| `Enter` / `Space` | Activate focused element |
| `Esc` | Close modal/overlay/dropdown |
| `F6` | Cycle through main regions |
| `Alt + 1-5` | Jump to specific view |

---

## 6. Wireframe Specifications

### 6.1 Responsive Breakpoints

| Breakpoint | Width | Layout Changes |
|------------|-------|----------------|
| Compact | < 768px | Sidebar collapses, stack panels |
| Standard | 768-1440px | Default layout |
| Wide | 1440-1920px | Expanded context panel |
| Ultra-wide | > 1920px | Multi-pane support |

### 6.2 Z-Index Layers

```
1000: Modals / Dialogs
 900: Command Palette
 800: Dropdowns / Tooltips
 700: Notifications / Toasts
 600: Sidebar (expanded overlay on mobile)
 500: Context Panels
 400: Fixed headers
 100: Content layers
   0: Base layer
```

### 6.3 Spacing System

```
Base unit: 4px

4px   - xs (tight spacing, icon padding)
8px   - sm (component internal padding)
16px  - md (card padding, section gaps)
24px  - lg (panel padding)
32px  - xl (section separation)
48px  - 2xl (major section breaks)
64px  - 3xl (page-level spacing)
```

### 6.4 Component Specifications

#### Sidebar Icon Button

```
Size: 48px × 48px
Icon: 20px × 20px, centered
Active indicator: 3px amber line, left edge
Hover: Background #1A1A1A
Active: Background #1A1A1A + glow
```

#### Breadcrumb Segment

```
Height: 32px
Padding: 0 12px
Separator: "▸" character, muted color
Hover: Text color brighten + underline
Active: Current segment, no hover state
```

#### Command Palette Input

```
Height: 56px
Font: 18px mono
Padding: 0 20px
Placeholder: "Type a command or search..."
Icon: Search left, ⌘K hint right
```

---

## 7. Interaction Patterns

### 7.1 Context Preservation

**Problem:** Users lose work context when navigating.

**Solution:**
- URL-based state (deep linking)
- Session restoration on re-open
- "Recent contexts" in sidebar
- Tabbed interface for multiple agents
- Split-view for side-by-side comparison

### 7.2 Progressive Disclosure

**Pattern:** Complexity reveals as user demonstrates intent.

**Examples:**
- Basic agent config → Advanced options (collapsed)
- Simple deployment → Custom pipeline stages
- Default keyboard shortcuts → Custom bindings

### 7.3 Feedback Loops

Every action produces visible feedback:

| Action | Feedback |
|--------|----------|
| Save | Toast: "Saved" + timestamp |
| Error | Shake + red highlight + inline message |
| Long operation | Progress indicator + cancel option |
| Background task | Status bar indicator |
| State change | Smooth transition + color change |

### 7.4 Error Recovery

**Graceful Degradation:**
- Network failure → Offline mode indicator + retry queue
- Canvas error → Fallback to list view
- Permission denied → Inline upgrade prompt

**Undo/Redo:**
- Global undo stack (Cmd/Ctrl + Z)
- Critical actions: Confirm dialog
- Destructive actions: Soft delete (recoverable)

### 7.5 Performance Patterns

**Virtualization:**
- Large agent lists: Virtual scrolling
- Canvas: LOD (level of detail) for distant nodes
- Timeline: Temporal virtualization

**Lazy Loading:**
- Images and previews on viewport entry
- Panel content on first expand
- Historical data on scroll

**Optimistic Updates:**
- UI updates immediately, syncs in background
- Rollback on failure with notification
- Conflict resolution UI

---

## 8. Design Rationale

### Why This Navigation Architecture?

1. **Sidebar + Breadcrumbs:** Balances quick access (sidebar) with context awareness (breadcrumbs)
2. **5 Main Views:** Covers complete agent lifecycle without overwhelming
3. **Mechanical Transitions:** Reinforces industrial brand while aiding spatial orientation
4. **Vim Shortcuts:** Appeals to power users without sacrificing mouse usability
5. **Command Palette:** Universal escape hatch for any action

### Success Metrics

- Time to first agent created: < 2 minutes
- Navigation efficiency: < 3 clicks to any view
- Keyboard coverage: 90% of actions accessible via keyboard
- User retention: 80% return within 7 days

---

## Appendix: Quick Reference

### Default Key Bindings

```
Global:
  ⌘ K          Open Command Palette
  ⌘ /          Show Shortcuts
  g d          Go to Dashboard
  g a          Go to Agent Workshop
  g p          Go to Pipeline
  g s          Go to Settings
  ?            Show Help

Canvas:
  h j k l      Pan
  +/-          Zoom
  0            Reset zoom
  Space+drag   Pan
  Tab          Next selection
  Esc          Deselect

Editing:
  ⌘ S          Save
  ⌘ Z          Undo
  ⌘ ⇧ Z        Redo
  ⌘ C/X/V      Copy/Cut/Paste
  Delete       Remove selection
  F5           Debug
  F9           Toggle breakpoint
```

### View Navigation Map

```
Dashboard ─────┬─── Agent Workshop ──── Agent Details
               │
               ├─── Deployment Pipeline ──── Run Details
               │
               ├─── System Settings ──── [various panels]
               │
               └─── Onboarding ──── [wizard flow]
```

---

*Document Version: 1.0*
*Last Updated: 2026-03-06*
*Status: Design Specification*
