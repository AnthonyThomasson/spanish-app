// Herdr "Phone" button: build the Android APK, serve it on the LAN and show a QR code to install it.
import { execFileSync, spawnSync } from 'node:child_process'
import fs from 'node:fs'
import http from 'node:http'
import net from 'node:net'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import QRCode from 'qrcode'
import {
  APK_NAME,
  DEFAULT_PORT,
  buildApkUrl,
  contentTypeFor,
  findFreePort,
  mainCheckoutFromGitCommonDir,
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
if (!fs.existsSync('node_modules')) {
  console.log('phone: node_modules missing, running npm ci')
  if (!run('npm', ['ci'])) fail('npm ci failed')
}

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

// (d) LAN address
const ip = pickLanAddress(os.networkInterfaces())
if (!ip) fail('could not find a Wi-Fi/LAN IPv4 address. Connect the Mac to the same network as the phone.')

// (e) serve release/ over HTTP
const releaseDir = path.join(root, 'release')
const server = http.createServer((req, res) => {
  const requested = decodeURIComponent(new URL(req.url, 'http://x').pathname)
  const file = path.resolve(releaseDir, '.' + path.posix.normalize('/' + requested))
  if (!file.startsWith(releaseDir + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) {
    res.writeHead(404).end('Not found')
    return
  }
  res.writeHead(200, { 'Content-Type': contentTypeFor(file), 'Content-Length': fs.statSync(file).size })
  fs.createReadStream(file).pipe(res)
})

const isFree = (port) =>
  new Promise((resolve) => {
    const probe = net.createServer()
    probe.once('error', () => resolve(false))
    probe.listen(port, '0.0.0.0', () => probe.close(() => resolve(true)))
  })
const port = await findFreePort(DEFAULT_PORT, isFree)
await new Promise((resolve, reject) => {
  server.once('error', reject)
  server.listen(port, '0.0.0.0', resolve)
})

// (f) URL + QR
const url = buildApkUrl(ip, port)
await QRCode.toFile(path.join(releaseDir, 'qr.png'), url, { width: 512 })
console.log(`\nScan to install on the phone (same Wi-Fi):\n`)
console.log(await QRCode.toString(url, { type: 'terminal', small: true }))
console.log(`${url}\n`)
console.log('QR image: release/qr.png')
console.log('Serving release/ — press Ctrl+C to stop.')

// (g) serve until Ctrl+C
const stop = () => server.close(() => process.exit(0))
process.on('SIGINT', stop)
process.on('SIGTERM', stop)
