/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        navy: { DEFAULT: '#2B2D6E', dark: '#23255a', light: '#3b3e8f' },
        accent: { DEFAULT: '#FF3D7F', light: '#FF6B9D', dark: '#E02D6B' },
        surface: { DEFAULT: '#F5F5F8', secondary: '#F0EFF8' },
        success: { 50: '#f0fdfa', 100: '#ccfbf1', 400: '#2dd4bf', 500: '#14b8a6', 600: '#0d9488', 700: '#0f766e' },
        warning: { 50: '#fffbeb', 100: '#fef3c7', 500: '#f59e0b', 600: '#d97706', 700: '#b45309' },
        danger: { 50: '#fef2f2', 100: '#fee2e2', 400: '#f87171', 500: '#ef4444', 600: '#dc2626', 700: '#b91c1c' },
        info: { 50: '#eff6ff', 100: '#dbeafe', 500: '#3b82f6', 600: '#2563eb', 700: '#1d4ed8' },
      },
      fontFamily: {
        sans: ['DM Sans', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        // Bumped 1 step from defaults (RNT-025):
        //   micro: 11→12px  |  xs: 12→13px  |  sm: 14→15px
        micro: ['12px', { lineHeight: '17px', fontWeight: '500' }],
        xs:    ['13px', { lineHeight: '18px' }],
        sm:    ['15px', { lineHeight: '22px' }],
      },
      // Keep pink-brand as alias for backwards compat in logo
      textColor: {
        'pink-brand': '#FF3D7F',
      },
    },
  },
  plugins: [],
}
