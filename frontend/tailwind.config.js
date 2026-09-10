/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'sentinel': {
          'bg': '#0d1117',
          'card': '#161b22',
          'border': '#30363d',
          'text': '#e6edf3',
          'text-secondary': '#8b949e',
          'cyan': '#00d4ff',
          'purple': '#a371f7',
          'critical': '#f85149',
          'high': '#d29922',
          'medium': '#a371f7',
          'low': '#3fb950',
        },
      },
      animation: {
        'pulse-critical': 'pulse-critical 2s infinite',
      },
      keyframes: {
        'pulse-critical': {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.5 },
        },
      },
    },
  },
  plugins: [],
}