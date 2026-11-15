// Herdr "Phone" button: build the Android APK, serve it on the LAN and show a QR code to install it.
import { execFileSync, spawnSync } from 'node:child_process'
import fs from 'node:fs'
import http from 'node:http'
import os from 'node:os'
import path from 'node:path'
import { pipeline } from 'node:stream'
import { fileURLToPath } from 'node:url'
import {
  APK_NAME,
  DEFAULT_PORT,
  buildApkUrl,
  contentTypeFor,
  findFreePort,
  mainCheckoutFromGitCommonDir,
  needsInstall,
  pickLanAddress,
} from './phone-lib.mjs'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
process.chdir(root)

const fail = (message) => {
  console.error(`\nphone: ${message}`)
  process.exit(1)
}

const run = (command, args) => {
  const result = spawnSync(command, args, { stdio: 'inherit', cwd: root })
  return result.status === 0
}

// (a) dependencies
if (needsInstall(fs.existsSync)) {
  console.log('phone: node_modules or qrcode missing, running npm ci')
  if (!run('npm', ['ci'])) fail('npm ci failed')
}

// Fail fast, before the multi-minute build: qrcode must load and the Mac needs a LAN address.
const { default: QRCode } = await import('qrcode')

const ip = pickLanAddress(os.networkInterfaces())
if (!ip) fail('could not find a Wi-Fi/LAN IPv4 address. Connect the Mac to the same network as the phone.')

// (b) vocabulary (gitignored, copied from the main checkout when this is a worktree)
const vocab = path.join('data', 'vocab.json')
if (!fs.existsSync(vocab)) {
  let source
  try {
    const commonDir = execFileSync('git', ['rev-parse', '--git-common-dir'], { cwd: root, encoding: 'utf8' }).trim()
    const candidate = path.join(mainCheckoutFromGitCommonDir(commonDir, root), vocab)
    if (fs.existsSync(candidate)) source = candidate
  } catch {
    // not a git checkout: fall through to the error below
  }
  if (!source) {
    fail(
      'data/vocab.json is missing here and in the main checkout. ' +
        'Generate it first: uv run scripts/extract_vocab.py "/path/to/book.pdf"',
    )
  }
  fs.mkdirSync('data', { recursive: true })
  fs.copyFileSync(source, vocab)
  console.log(`phone: copied vocabulary from ${source}`)
}

// (c) build
if (!run('npm', ['run', 'android:apk'])) fail('npm run android:apk failed')

// (e) serve release/ over HTTP (only the APK and QR image, nothing else in the folder)
const releaseDir = path.join(root, 'release')
const servable = new Set([APK_NAME, 'qr.png'])
const server = http.createServer((req, res) => {
  let name
  try {
    name = decodeURIComponent(new URL(req.url, 'http://x').pathname).replace(/^\//, '')
  } catch {
    res.writeHead(400).end('Bad request')
    return
  }
  const file = path.join(releaseDir, name)
  let size
  try {
    size = servable.has(name) ? fs.statSync(file).size : undefined
  } catch {
    size = undefined
  }
  if (size === undefined) {
    res.writeHead(404).end('Not found')
    return
  }
  res.writeHead(200, { 'Content-Type': contentTypeFor(file), 'Content-Length': size })
  pipeline(fs.createReadStream(file), res, () => {})
})

// Bind for real on each candidate port, so a port taken by another worktree (even a
// moment ago) just moves us on to the next one.
const tryListen = (port) =>
  new Promise((resolve, reject) => {
    const onError = (err) => (err.code === 'EADDRINUSE' ? resolve(false) : reject(err))
    server.once('error', onError)
    server.listen(port, '0.0.0.0', () => {
      server.off('error', onError)
      resolve(true)
    })
  })
const port = await findFreePort(DEFAULT_PORT, tryListen)

// (f) URL + QR
const url = buildApkUrl(ip, port)
await QRCode.toFile(path.join(releaseDir, 'qr.png'), url, { width: 512 })
console.log(`\nScan to install on the phone (same Wi-Fi as ${ip}):\n`)
console.log(await QRCode.toString(url, { type: 'terminal', small: true }))
console.log(`${url}\n`)
console.log('QR image: release/qr.png')
console.log('Serving release/ — press Ctrl+C to stop.')

// (g) serve until Ctrl+C
const stop = () => {
  server.closeAllConnections()
  server.close(() => process.exit(0))
  setTimeout(() => process.exit(0), 1000).unref()
}
process.on('SIGINT', stop)
process.on('SIGTERM', stop)
