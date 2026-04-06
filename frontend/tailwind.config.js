/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html","./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        'sbg': '#080d1a',
        'ssurface': '#0d1526',
        'scard': '#111c30',
        'sborder': '#1a2d4a',
        'scyan': '#00e5ff',
        'spurple': '#a855f7',
        'sgreen': '#00ffa3',
        'sred': '#ff4444',
      },
    },
  },
  plugins: [],
}
