/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'inc-primary': '#0f172a',
        'inc-secondary': '#1e293b',
        'inc-accent': '#3b82f6',
        'inc-accent-light': '#60a5fa',
        'inc-success': '#22c55e',
        'inc-warning': '#eab308',
        'inc-danger': '#ef4444',
        'inc-muted': '#64748b',
        'inc-border': '#334155',
        'inc-surface': '#1e293b',
        'inc-surface-light': '#2d3a4f',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
};

