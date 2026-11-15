import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  pickLanAddress,
  mainCheckoutFromGitCommonDir,
  findFreePort,
  buildApkUrl,
  contentTypeFor,
  needsInstall,
} from './phone-lib.mjs'

const iface = (address, extra = {}) => ({ address, family: 'IPv4', internal: false, ...extra })

test('pickLanAddress prefers en0 over other interfaces', () => {
  const ip = pickLanAddress({
    en5: [iface('10.0.0.5')],
    en0: [{ address: 'fe80::1', family: 'IPv6', internal: false }, iface('192.168.1.20')],
  })
  assert.equal(ip, '192.168.1.20')
})

test('pickLanAddress falls back to another non-internal IPv4', () => {
  const ip = pickLanAddress({
    lo0: [iface('127.0.0.1', { internal: true })],
    en7: [iface('172.16.4.9')],
  })
  assert.equal(ip, '172.16.4.9')
})

test('pickLanAddress skips link-local addresses and handles numeric family', () => {
  const ip = pickLanAddress({
    en3: [iface('169.254.10.10')],
    en4: [{ address: '192.168.8.8', family: 4, internal: false }],
  })
  assert.equal(ip, '192.168.8.8')
})

test('pickLanAddress ignores VPN tunnels and VM bridges', () => {
  assert.equal(pickLanAddress({ utun3: [iface('10.8.0.2')], bridge100: [iface('192.168.64.1')] }), undefined)
})

test('pickLanAddress returns undefined when there is no LAN address', () => {
  assert.equal(pickLanAddress({ lo0: [iface('127.0.0.1', { internal: true })] }), undefined)
  assert.equal(pickLanAddress({}), undefined)
})

test('mainCheckoutFromGitCommonDir returns the parent of an absolute common dir', () => {
  assert.equal(
    mainCheckoutFromGitCommonDir('/Users/me/projects/spanish-app/.git', '/Users/me/.herdr/worktrees/x'),
    '/Users/me/projects/spanish-app',
  )
})

test('mainCheckoutFromGitCommonDir resolves a relative common dir against cwd', () => {
  assert.equal(mainCheckoutFromGitCommonDir('.git', '/Users/me/projects/spanish-app'), '/Users/me/projects/spanish-app')
  assert.equal(mainCheckoutFromGitCommonDir('../repo/.git', '/Users/me/wt'), '/Users/me/repo')
})

test('findFreePort returns the start port when free', async () => {
  assert.equal(await findFreePort(8787, async () => true), 8787)
})

test('findFreePort falls through to the next free port', async () => {
  const taken = new Set([8787, 8788])
  assert.equal(await findFreePort(8787, async (p) => !taken.has(p)), 8789)
})

test('findFreePort gives up after maxAttempts', async () => {
  await assert.rejects(findFreePort(8787, async () => false, 3), /No free port/)
})

test('buildApkUrl builds the install URL', () => {
  assert.equal(buildApkUrl('192.168.1.20', 8787), 'http://192.168.1.20:8787/spanish-app.apk')
})

test('contentTypeFor serves apk, png and falls back to octet-stream', () => {
  assert.equal(contentTypeFor('spanish-app.apk'), 'application/vnd.android.package-archive')
  assert.equal(contentTypeFor('qr.png'), 'image/png')
  assert.equal(contentTypeFor('mystery.bin'), 'application/octet-stream')
})

test('needsInstall is true without node_modules or without qrcode', () => {
  assert.equal(needsInstall(() => false), true)
  assert.equal(needsInstall((p) => p === 'node_modules'), true)
})

test('needsInstall is false when qrcode is installed', () => {
  assert.equal(needsInstall(() => true), false)
})
