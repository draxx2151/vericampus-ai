/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: '#1a2332',
          light: '#243044',
          dark: '#121824',
        },
        teal: {
          DEFAULT: '#2d8b8b',
          hover: '#247070',
          light: '#e6f3f3',
        },
        seafoam: {
          DEFAULT: '#a8dadc',
          light: '#eaf6f6',
          dark: '#7fb7b9',
        },
        cream: {
          DEFAULT: '#f1faee',
          dark: '#e3f2e1',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
