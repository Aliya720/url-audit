# PulseWatch - Audit & Trust System Design Specification

---
name: Audit & Trust System
colors:
  surface: '#fafaf4'
  surface-dim: '#dadad5'
  surface-bright: '#fafaf4'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f4f4ee'
  surface-container: '#eeeee9'
  surface-container-high: '#e8e8e3'
  surface-container-highest: '#e3e3dd'
  on-surface: '#1a1c19'
  on-surface-variant: '#434840'
  inverse-surface: '#2f312e'
  inverse-on-surface: '#f1f1ec'
  outline: '#73796f'
  outline-variant: '#c3c8bd'
  surface-tint: '#466642'
  primary: '#264525'
  on-primary: '#ffffff'
  primary-container: '#3d5d3a'
  on-primary-container: '#b0d4a8'
  inverse-primary: '#acd0a4'
  secondary: '#496545'
  on-secondary: '#ffffff'
  secondary-container: '#cbecc2'
  on-secondary-container: '#4f6c4b'
  tertiary: '#5d3042'
  on-tertiary: '#ffffff'
  tertiary-container: '#774759'
  on-tertiary-container: '#f8b9cf'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#c7edbf'
  primary-fixed-dim: '#acd0a4'
  on-primary-fixed: '#032105'
  on-primary-fixed-variant: '#2f4e2d'
  secondary-fixed: '#cbecc2'
  secondary-fixed-dim: '#afcfa8'
  on-secondary-fixed: '#072107'
  on-secondary-fixed-variant: '#324d2f'
  tertiary-fixed: '#ffd9e4'
  tertiary-fixed-dim: '#f4b5ca'
  on-tertiary-fixed: '#330e1f'
  on-tertiary-fixed-variant: '#66394a'
  background: '#fafaf4'
  on-background: '#1a1c19'
  surface-variant: '#e3e3dd'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-base:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-caps:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  mono-data:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base_unit: 8px
  container_max_width: 1280px
  gutter: 24px
  margin_desktop: 40px
  margin_mobile: 16px
  stack_sm: 8px
  stack_md: 16px
  stack_lg: 32px
---

## Brand & Style
The design system is engineered for high-stakes environments where precision, reliability, and technical authority are paramount. It targets IT professionals, SEO specialists, and web administrators who require a stable, low-friction interface to manage complex site health metrics.

The visual style is **Corporate / Modern** with a strong lean toward **Data-Centric Minimalism**. It prioritizes clarity over decoration, using a structured hierarchy and ample whitespace to reduce cognitive load when viewing dense audit logs. The aesthetic is "technical-grade"—clean, systematic, and intentional, evoking the feeling of a high-performance diagnostic tool.

## Colors
The palette is built on a foundation of "Trust Neutrals" punctuated by organic, professional greens that signal stability and growth.

- **Primary Structure**: Deep Forest Green (`#264525`) is used for primary interactive elements and global navigation to establish a sense of grounded authority.
- **Secondary Accents**: Muted Sage Green (`#496545`) is utilized for secondary UI elements and supporting structural components, providing a professional visual bridge across the interface.
- **Status Indicators**: A traffic-light system (Green, Amber, Red) is used with high saturation to provide immediate visual feedback on audit results. These colors must maintain high contrast against both white and light-gray backgrounds.

## Typography
This design system uses **Inter** for its exceptional legibility in UI contexts. The scale is designed to create a clear "scan-path" for the user.

- **Headlines**: Use tight letter-spacing and semi-bold weights to anchor page sections.
- **Data Display**: For specific technical outputs (IP addresses, code snippets, or raw audit logs), the system introduces **JetBrains Mono** to distinguish machine-readable data from UI labels.
- **Labels**: Small, uppercase labels are used for table headers and metadata to provide structure without competing with primary content.

## Layout & Spacing
The layout follows a **Fixed-Fluid Hybrid Grid**. The main content area is capped at 1280px to ensure line lengths remain readable on ultra-wide monitors, while the sidebars and internal dashboards scale fluidly.

- **The 8px Rhythm**: All margins, paddings, and component heights must be multiples of 8px.
- **Data Density**: In table-heavy views, vertical padding is reduced (8px/12px) to maximize the amount of information visible on one screen. In marketing or overview screens, spacing is increased (32px+) to provide visual breathing room.
- **Mobile Reflow**: On mobile, 12-column grids collapse into a single vertical stack. Metric cards that appear side-by-side on desktop (4 columns each) transition to a swipeable horizontal carousel or a single-column list.

## Elevation & Depth
Depth is conveyed through **Tonal Layering** and **Low-Contrast Outlines** rather than heavy shadows.

- **Surface 0**: The main background (Light Neutral Gray `#fafaf4`).
- **Surface 1**: Primary cards and content containers (Pure White `#ffffff`) with a 1px border.
- **Surface 2**: Floating elements like tooltips or dropdowns. These use a "Soft Ambient Shadow": `0px 4px 12px rgba(15, 23, 42, 0.08)`.
- **Active State**: Use a subtle inner-glow or a thicker 2px border in the Primary Forest Green to indicate focus or selection.

## Shapes
The design system uses a **Soft** shape language. This provides a modern feel while maintaining a professional, geometric rigor. 

- **Components**: Standard buttons, input fields, and status badges use a `0.25rem` (4px) corner radius.
- **Large Containers**: Metric cards and modal windows use `0.5rem` (8px) or `0.75rem` (12px). 
- **Icons**: Icons should follow a 2px stroke width with slightly rounded terminals to match the font's characteristics.

## Components
- **Metric Cards**: White background, 1px border, featuring a large "Display-LG" number. A small trend indicator (e.g., +12% in success green) should sit in the top-right corner.
- **Status Badges**: Small, pill-shaped indicators with a light tinted background (10% opacity of the status color) and dark text of the same hue.
- **Data Tables**: Minimalist design. No vertical lines; only subtle horizontal dividers. The header row should use the `label-caps` typography style with a light gray background.
- **Primary Buttons**: Solid Forest Green with white text. No gradients. On hover, darken the green by 10%.
- **Input Fields**: 1px Neutral border, turning Forest Green on focus. Labels sit clearly above the field in `body-sm` bold.
- **Audit Logs**: Use a "Monospace Stripe" layout where technical data is displayed in `mono-data` typography to distinguish it from the user interface.
