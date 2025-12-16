/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Semantic naming for "The Alchemist" palette
        brand: {
          bg: '#0C0A09',      // Obsidian
          surface: '#1C1917', // Basalt
          border: '#44403C',  // Iron
          primary: '#F59E0B', // Molten
          text: '#E7E5E4',    // Parchment
          muted: '#A8A29E',   // Ash
        },
        // Error colors (warm rose tones)
        error: {
          bg: '#9F1239',      // Rose-900
          text: '#FECDD3',    // Rose-200
        }
      }
    },
  },
  plugins: [],
}

