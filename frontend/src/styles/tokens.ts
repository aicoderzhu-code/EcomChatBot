/**
 * Design Token System
 * 统一的设计系统 Token 定义
 * 用于保持整个应用的视觉一致性
 */

// ============ 颜色系统 ============

// 品牌色 - Indigo 紫色系
export const brandColors = {
  50: '#EEF2FF',
  100: '#E0E7FF',
  200: '#C7D2FE',
  300: '#A5B4FC',
  400: '#818CF8',
  500: '#6366F1', // 主色
  600: '#4F46E5',
  700: '#4338CA',
  800: '#3730A3',
  900: '#312E81',
  950: '#1E1B4B',
} as const;

// 功能色
export const functionalColors = {
  success: {
    50: '#ECFDF5',
    100: '#D1FAE5',
    500: '#10B981',
    600: '#059669',
    700: '#047857',
  },
  warning: {
    50: '#FFFBEB',
    100: '#FEF3C7',
    500: '#F59E0B',
    600: '#D97706',
    700: '#B45309',
  },
  error: {
    50: '#FEF2F2',
    100: '#FEE2E2',
    500: '#EF4444',
    600: '#DC2626',
    700: '#B91C1C',
  },
  info: {
    50: '#EFF6FF',
    100: '#DBEAFE',
    500: '#3B82F6',
    600: '#2563EB',
    700: '#1D4ED8',
  },
} as const;

// 中性色
export const neutralColors = {
  50: '#F9FAFB',
  100: '#F3F4F6',
  200: '#E5E7EB',
  300: '#D1D5DB',
  400: '#9CA3AF',
  500: '#6B7280',
  600: '#4B5563',
  700: '#374151',
  800: '#1F2937',
  900: '#111827',
  950: '#030712',
} as const;

// 语义色
export const semanticColors = {
  background: {
    light: brandColors[50],
    dark: neutralColors[950],
  },
  foreground: {
    light: brandColors[950],
    dark: neutralColors[50],
  },
  card: {
    light: '#FFFFFF',
    dark: neutralColors[900],
  },
  border: {
    light: neutralColors[200],
    dark: neutralColors[700],
  },
  sidebar: {
    bg: brandColors[950],
    hover: '#2D2A5E',
    active: brandColors[500],
  },
} as const;

// ============ 间距系统 ============
// 基于 8px 基准

export const spacing = {
  0: '0',
  0.5: '0.125rem', // 2px
  1: '0.25rem',    // 4px
  1.5: '0.375rem', // 6px
  2: '0.5rem',     // 8px
  2.5: '0.625rem', // 10px
  3: '0.75rem',    // 12px
  3.5: '0.875rem', // 14px
  4: '1rem',       // 16px
  5: '1.25rem',    // 20px
  6: '1.5rem',     // 24px
  7: '1.75rem',    // 28px
  8: '2rem',       // 32px
  9: '2.25rem',    // 36px
  10: '2.5rem',    // 40px
  11: '2.75rem',   // 44px
  12: '3rem',      // 48px
  14: '3.5rem',    // 56px
  16: '4rem',      // 64px
  20: '5rem',      // 80px
  24: '6rem',      // 96px
  28: '7rem',      // 112px
  32: '8rem',      // 128px
} as const;

// ============ 圆角系统 ============

export const borderRadius = {
  none: '0',
  sm: '0.25rem',   // 4px
  base: '0.375rem', // 6px
  md: '0.5rem',    // 8px
  lg: '0.75rem',   // 12px
  xl: '1rem',      // 16px
  '2xl': '1.5rem', // 24px
  '3xl': '2rem',   // 32px
  full: '9999px',
} as const;

// ============ 阴影系统 ============
// 使用紫色系阴影

export const shadows = {
  xs: '0 1px 2px 0 rgba(99, 102, 241, 0.05)',
  sm: '0 1px 3px 0 rgba(99, 102, 241, 0.1), 0 1px 2px -1px rgba(99, 102, 241, 0.1)',
  base: '0 4px 6px -1px rgba(99, 102, 241, 0.1), 0 2px 4px -2px rgba(99, 102, 241, 0.1)',
  md: '0 10px 15px -3px rgba(99, 102, 241, 0.1), 0 4px 6px -4px rgba(99, 102, 241, 0.1)',
  lg: '0 20px 25px -5px rgba(99, 102, 241, 0.1), 0 8px 10px -6px rgba(99, 102, 241, 0.1)',
  xl: '0 25px 50px -12px rgba(99, 102, 241, 0.25)',
  '2xl': '0 25px 50px -12px rgba(99, 102, 241, 0.35)',
  inner: 'inset 0 2px 4px 0 rgba(99, 102, 241, 0.05)',
  none: 'none',
} as const;

// ============ 字体系统 ============

export const fontFamily = {
  sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'] as string[],
  mono: ['Fira Code', 'Consolas', 'Monaco', 'monospace'] as string[],
};

export const fontSize = {
  xs: ['0.75rem', { lineHeight: '1rem' }] as [string, { lineHeight: string }],
  sm: ['0.875rem', { lineHeight: '1.25rem' }] as [string, { lineHeight: string }],
  base: ['1rem', { lineHeight: '1.5rem' }] as [string, { lineHeight: string }],
  lg: ['1.125rem', { lineHeight: '1.75rem' }] as [string, { lineHeight: string }],
  xl: ['1.25rem', { lineHeight: '1.75rem' }] as [string, { lineHeight: string }],
  '2xl': ['1.5rem', { lineHeight: '2rem' }] as [string, { lineHeight: string }],
  '3xl': ['1.875rem', { lineHeight: '2.25rem' }] as [string, { lineHeight: string }],
  '4xl': ['2.25rem', { lineHeight: '2.5rem' }] as [string, { lineHeight: string }],
  '5xl': ['3rem', { lineHeight: '1' }] as [string, { lineHeight: string }],
};

export const fontWeight = {
  light: '300',
  normal: '400',
  medium: '500',
  semibold: '600',
  bold: '700',
} as const;

// ============ 动画系统 ============

export const animation = {
  duration: {
    fast: '150ms',
    base: '250ms',
    slow: '350ms',
    slower: '500ms',
  },
  easing: {
    linear: 'linear',
    ease: 'ease',
    easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
    easeOut: 'cubic-bezier(0, 0, 0.2, 1)',
    easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
    spring: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
  },
} as const;

// ============ Z-index 层级 ============

export const zIndex = {
  base: 0,
  dropdown: 1000,
  sticky: 1020,
  fixed: 1030,
  modalBackdrop: 1040,
  modal: 1050,
  popover: 1060,
  tooltip: 1070,
} as const;

// ============ 断点系统 ============

export const breakpoints = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
} as const;

// ============ 导出所有 Token ============

export const tokens = {
  colors: {
    brand: brandColors,
    functional: functionalColors,
    neutral: neutralColors,
    semantic: semanticColors,
  },
  spacing,
  borderRadius,
  shadows,
  fontFamily,
  fontSize,
  fontWeight,
  animation,
  zIndex,
  breakpoints,
} as const;

export default tokens;
