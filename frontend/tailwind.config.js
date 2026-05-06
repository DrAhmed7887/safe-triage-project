/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        'arabic': ['Cairo', 'sans-serif'],
        'sans': ['Inter', 'system-ui', 'sans-serif'],
        'mono': ['IBM Plex Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      colors: {
        triage: {
          1: '#ef4444', // Red       — ESI 1 Resuscitation
          2: '#f97316', // Orange    — ESI 2 Emergent
          3: '#eab308', // Yellow    — ESI 3 Urgent
          4: '#22c55e', // Green     — ESI 4 Less Urgent
          5: '#3b82f6', // Blue      — ESI 5 Non-Urgent
        }
      }
    },
  },
  plugins: [],
}
