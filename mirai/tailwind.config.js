/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './**/templates/**/*.html',
    './**/static/**/*.js',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Outfit', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
