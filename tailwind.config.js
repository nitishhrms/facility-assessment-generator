/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sf: [
          '-apple-system',
          'BlinkMacSystemFont',
          'SF Pro Text',
          'SF Pro Display',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'Arial',
          'sans-serif',
        ],
      },
      colors: {
        // Apple-style neutral system palette
        canvas: '#f5f5f7',
        ink: '#1d1d1f',
        subtle: '#6e6e73',
        hairline: '#d2d2d7',
        accent: {
          DEFAULT: '#0071e3', // Apple system blue
          hover: '#0077ed',
        },
        // Medelite brand — used ONLY in the mandatory INFINITE banner
        brand: {
          pink: '#e6007e',
          blue: '#1b3a8b',
        },
      },
      boxShadow: {
        card: '0 1px 3px rgba(0,0,0,0.06), 0 8px 24px rgba(0,0,0,0.05)',
      },
      borderRadius: {
        xl2: '18px',
      },
    },
  },
  plugins: [],
};
