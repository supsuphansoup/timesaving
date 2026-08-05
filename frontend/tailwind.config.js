/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dongseo: {
          blue: '#002B66',
          gold: '#C5A059',
          light: '#F4F7FC',
          hover: '#003D99',
          accent: '#1E40AF',
        }
      }
    },
  },
  plugins: [],
}
