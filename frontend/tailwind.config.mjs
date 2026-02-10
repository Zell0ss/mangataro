/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}'],
  theme: {
    extend: {
      colors: {
        ink: {
          950: 'rgb(var(--ink-950) / <alpha-value>)',
          900: 'rgb(var(--ink-900) / <alpha-value>)',
          850: 'rgb(var(--ink-850) / <alpha-value>)',
          800: 'rgb(var(--ink-800) / <alpha-value>)',
          700: 'rgb(var(--ink-700) / <alpha-value>)',
          600: 'rgb(var(--ink-600) / <alpha-value>)',
          500: 'rgb(var(--ink-500) / <alpha-value>)',
          400: 'rgb(var(--ink-400) / <alpha-value>)',
          300: 'rgb(var(--ink-300) / <alpha-value>)',
          200: 'rgb(var(--ink-200) / <alpha-value>)',
          100: 'rgb(var(--ink-100) / <alpha-value>)',
          50:  'rgb(var(--ink-50) / <alpha-value>)',
        },
        crimson: {
          50:  'rgb(var(--crimson-50) / <alpha-value>)',
          100: 'rgb(var(--crimson-100) / <alpha-value>)',
          200: 'rgb(var(--crimson-200) / <alpha-value>)',
          300: 'rgb(var(--crimson-300) / <alpha-value>)',
          400: 'rgb(var(--crimson-400) / <alpha-value>)',
          500: 'rgb(var(--crimson-500) / <alpha-value>)',
          600: 'rgb(var(--crimson-600) / <alpha-value>)',
          700: 'rgb(var(--crimson-700) / <alpha-value>)',
          800: 'rgb(var(--crimson-800) / <alpha-value>)',
          900: 'rgb(var(--crimson-900) / <alpha-value>)',
          950: 'rgb(var(--crimson-950) / <alpha-value>)',
        },
      },
      fontFamily: {
        display: ['"Bricolage Grotesque"', 'system-ui', 'sans-serif'],
        body: ['"Plus Jakarta Sans"', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
