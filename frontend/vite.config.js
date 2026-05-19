import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'node:fs'
import path from 'node:path'

// Hospital Lite Phase-1 must not ship the Firebase Cloud Messaging service
// worker — it is dead code in this mode (Firebase Auth is bypassed and no FCM
// token is requested), and its presence at /firebase-messaging-sw.js leaks the
// Firebase project config into the static bundle. This plugin removes the
// file from dist/ after build, but only when --mode hospital_lite is in effect.
function stripFirebaseMessagingInHospitalLite(mode) {
  return {
    name: 'safe-triage:strip-firebase-messaging-hospital-lite',
    apply: 'build',
    closeBundle() {
      if (mode !== 'hospital_lite') return
      const target = path.resolve('dist/firebase-messaging-sw.js')
      if (fs.existsSync(target)) {
        fs.rmSync(target)
        console.log('[hospital_lite] stripped dist/firebase-messaging-sw.js')
      }

      const assetsDir = path.resolve('dist/assets')
      if (fs.existsSync(assetsDir)) {
        for (const fileName of fs.readdirSync(assetsDir)) {
          if (fileName.startsWith('StandardApp-')) {
            fs.rmSync(path.join(assetsDir, fileName))
            console.log(`[hospital_lite] stripped dist/assets/${fileName}`)
          }
        }
      }
    },
  }
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [react(), stripFirebaseMessagingInHospitalLite(mode)],
}))
