/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        serif: ['Instrument Serif', 'Georgia', 'serif'],
        mono: ['DM Mono', 'monospace'],
        sans: ['DM Sans', 'system-ui', 'sans-serif'],
      },
      colors: {
        brand: {
          50:  '#EEEDFE',
          100: '#D5D3FD',
          200: '#AFA9EC',
          500: '#534AB7',
          600: '#3C3489',
          700: '#2A2460',
        },
        surface: {
          0: '#FAFAF8',
          1: '#F3F2EE',
          2: '#ECEAE4',
        },
        border: {
          DEFAULT: '#E0DDD6',
          strong:  '#C8C5BC',
        }
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-up': 'fadeUp 0.4s ease both',
      },
      keyframes: {
        fadeUp: {
          from: { opacity: 0, transform: 'translateY(8px)' },
          to:   { opacity: 1, transform: 'translateY(0)' },
        }
      }
    },
  },
  plugins: [],
}
