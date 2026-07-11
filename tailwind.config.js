/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f5f6ff',
          100: '#ebedff',
          200: '#dcdfff',
          300: '#c4c8ff',
          400: '#a3a7ff',
          500: '#7a7eff',
          600: '#4f46e5', // indigo-600 baseline
          700: '#4338ca',
          800: '#3730a3',
          900: '#312e81',
        }
      }
    },
  },
  plugins: [],
}
