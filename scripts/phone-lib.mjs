// Pure helpers for scripts/phone.mjs. No I/O here so they can be unit-tested.
import path from 'node:path'

export const APK_NAME = 'spanish-app.apk'
export const DEFAULT_PORT = 8787

const isIPv4 = (entry) => entry.family === 'IPv4' || entry.family === 4
const isLinkLocal = (address) => address.startsWith('169.254.')

// Choose the Mac's Wi-Fi/LAN IPv4 from os.networkInterfaces() output: prefer en0,
// otherwise the first other en* (Ethernet/Wi-Fi) interface. VPN tunnels and VM bridges
// (utun*, bridge*, docker...) are never chosen: the phone could not reach them.
export function pickLanAddress(interfaces) {
  const usable = (name) =>
    (interfaces[name] ?? []).find((e) => isIPv4(e) && !e.internal && !isLinkLocal(e.address))
  const preferred = usable('en0')
  if (preferred) return preferred.address
  for (const name of Object.keys(interfaces).filter((n) => /^en\d+$/.test(n))) {
    const found = usable(name)
    if (found) return found.address
  }
  return undefined
}

// `git rev-parse --git-common-dir` points at the main checkout's .git directory
// (relative to cwd when run in the main checkout itself); its parent is the checkout.
export function mainCheckoutFromGitCommonDir(commonDir, cwd) {
  return path.dirname(path.resolve(cwd, commonDir))
}

// First port >= start for which `isFree(port)` resolves true.
export async function findFreePort(start, isFree, maxAttempts = 50) {
  for (let i = 0; i < maxAttempts; i++) {
    const port = start + i
    if (await isFree(port)) return port
  }
  throw new Error(`No free port found in ${start}-${start + maxAttempts - 1}`)
}

export function buildApkUrl(ip, port) {
  return `http://${ip}:${port}/${APK_NAME}`
}

const CONTENT_TYPES = {
  '.apk': 'application/vnd.android.package-archive',
  '.png': 'image/png',
  '.html': 'text/html; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8',
}

export function contentTypeFor(file) {
  return CONTENT_TYPES[path.extname(file).toLowerCase()] ?? 'application/octet-stream'
}
