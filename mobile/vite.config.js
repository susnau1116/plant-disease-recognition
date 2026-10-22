import { defineConfig } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'

process.env.UNI_INPUT_DIR = process.env.UNI_INPUT_DIR || __dirname

export default defineConfig({
  plugins: [uni()],
  server: {
    host: '127.0.0.1',
    port: 5174
  }
})
