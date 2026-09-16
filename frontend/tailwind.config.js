/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          900: '#0b0d13',
          800: '#121620',
          700: '#1e2530',
          600: '#273142',
        },
        primary: {
          DEFAULT: '#00e5ff',
          hover: '#00bccc',
        },
        text: {
          muted: '#64748b',
          secondary: '#94a3b8',
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        display: ['Outfit', 'sans-serif'],
        mono: ['Fira Code', 'monospace'],
      }
    },
  },
  plugins: [],
}
