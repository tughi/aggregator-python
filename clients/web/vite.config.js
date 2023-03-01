import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import autoprefixer from 'autoprefixer'

export default defineConfig({
   css: {
      postcss: {
         plugins: [autoprefixer]
      }
   },
   plugins: [react()],
   server: {
      port: 3000,
      proxy: {
         '/graphql': {
            target: 'http://localhost:8000',
            changeOrigin: true,
         }
      }
   },
})
