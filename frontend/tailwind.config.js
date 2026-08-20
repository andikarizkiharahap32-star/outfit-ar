/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Syne"', 'sans-serif'],
        body: ['"DM Sans"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },

      // === EFEK ANIMASI & HOVER PREMIUM ===
      animation: {
        'fade-up': 'fadeUp 0.5s ease forwards',
        'glow-pulse': 'glowPulse 2s ease-in-out infinite',
        'scan': 'scan 2s linear infinite',
        'float': 'float 3s ease-in-out infinite',
        'pulse-fast': 'pulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        fadeUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' }
        },
        glowPulse: {
          '0%, 100%': { boxShadow: '0 0 20px rgba(168,85,247,0.3)', borderColor: 'rgba(168,85,247,0.2)' },
          '50%': { boxShadow: '0 0 40px rgba(168,85,247,0.7)', borderColor: 'rgba(168,85,247,0.6)' }
        },
        scan: {
          '0%': { top: '0%', opacity: '0' },
          '50%': { opacity: '1' },
          '100%': { top: '100%', opacity: '0' }
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-15px)' }
        }
      },

      colors: {
        brand: {
          50: '#fdf4ff',
          100: '#fae8ff',
          400: '#c084fc', // Tambahan untuk aksen teks ringan
          500: '#a855f7',
          600: '#9333ea',
          700: '#7e22ce',
          900: '#3b0764',
        },
        surface: {
          DEFAULT: '#0a0a0f',
          card: '#13131a',
          hover: '#1c1c28',
          border: '#2a2a3a',
        },
      },

      // === TAMBAHAN UNTUK UI AR & SKIN TONE ===
      boxShadow: {
        'glow-brand': '0 0 20px rgba(168, 85, 247, 0.4)',
        'glow-cyan': '0 0 20px rgba(34, 211, 238, 0.4)',
      },
      backgroundImage: {
        'glass-gradient': 'linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0) 100%)',
      }
    },
  },
  plugins: [],
}