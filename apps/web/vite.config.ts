import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
const port = Number(process.env.HIS_PORT || 8000)
if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new Error('HIS_PORT must be a loopback development port')
export default defineConfig({ plugins:[react()], server:{host:'127.0.0.1',port:5173,strictPort:true,proxy:{'/api/v2':{target:`http://127.0.0.1:${port}`,changeOrigin:false},'/health':{target:`http://127.0.0.1:${port}`,changeOrigin:false}}}, preview:{host:'127.0.0.1'}})
