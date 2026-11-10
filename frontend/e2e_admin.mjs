import puppeteer from 'puppeteer-core'
import fs from 'fs'

const API = 'http://127.0.0.1:8000/api/v1'
const BASE = 'http://localhost:5173'
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
const SHOT = 'D:/Desktop/wanho/Python_code/103hanchao/eshop/.tmp/shots_admin'
fs.mkdirSync(SHOT, { recursive: true })

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const results = []
function check(name, ok, extra = '') {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'} - ${name}${extra ? ' | ' + extra : ''}`)
}

async function api(path, method = 'GET', body = null, token = null) {
  const res = await fetch(API + path, {
    method,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: 'Bearer ' + token } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  })
  return res.json()
}

async function clickByText(page, text, tag = 'button') {
  const handle = await page.evaluateHandle(
    (t, g) => [...document.querySelectorAll(g)].find((e) => (e.textContent || '').trim().includes(t)) || null,
    text, tag
  )
  const el = handle.asElement()
  if (!el) throw new Error('未找到可点击元素: ' + text)
  await el.click()
}

async function main() {
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: 'new',
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  })
  const page = await browser.newPage()
  await page.setViewport({ width: 1440, height: 900 })

  const errors = []
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message))
  page.on('console', (m) => {
    if (m.type() === 'error') {
      const t = m.text()
      if (!t.includes('favicon')) errors.push('console: ' + t)
    }
  })

  // ---- 1. 商家登录 ----
  await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle2' })
  await page.screenshot({ path: `${SHOT}/01-login.png` })
  check('打开商家登录页', (await page.content()).includes('商家后台'))

  await clickByText(page, '登')
  await sleep(1500)
  const urlAfter = page.url()
  check('登录后跳转到 /admin', urlAfter.includes('/admin') && !urlAfter.includes('login'), urlAfter)
  await page.screenshot({ path: `${SHOT}/02-dashboard.png` })

  // ---- 2. 概览 ----
  const dash = await page.content()
  check('概览显示 GMV 卡片', dash.includes('累计 GMV'))
  check('概览显示商品/SKU 卡片', dash.includes('商品 / SKU'))
  check('商家后台隐藏买家端导航', !dash.includes('我的订单'))

  // ---- 3. 商家 token 生效（API 侧）----
  const token = await page.evaluate(() => localStorage.getItem('admin_token'))
  check('admin_token 已写入 localStorage', !!token)
  const st = await api('/admin/stats', 'GET', null, token)
  check('概览接口返回数据', st && st.code === 0 && typeof st.data.gmv === 'number', 'GMV=' + (st.data || {}).gmv)

  // ---- 4. 订单管理：发货 + 推进物流 ----
  await page.goto(BASE + '/admin/orders?status=1', { waitUntil: 'networkidle2' })
  await sleep(1200)
  await page.screenshot({ path: `${SHOT}/03-orders.png` })
  const before = await api('/admin/stats', 'GET', null, token)
  const waitBefore = before.data.orders_wait_ship
  const ordersBefore = await api('/admin/orders?status=1', 'GET', null, token)
  const beforeItems = ordersBefore.data.items || []
  check('存在待发货订单', beforeItems.length > 0, '待发货=' + beforeItems.length)

  if (beforeItems.length > 0) {
    await clickByText(page, '发货')
    await sleep(1500)
    const after = await api('/admin/stats', 'GET', null, token)
    check('点击发货后待发货数 -1', after.data.orders_wait_ship === waitBefore - 1,
      `${waitBefore} -> ${after.data.orders_wait_ship}`)

    await page.goto(BASE + '/admin/orders?status=2', { waitUntil: 'networkidle2' })
    await sleep(1200)
    await clickByText(page, '推进物流')
    await sleep(1500)
    const shipList = await api('/admin/orders?status=2', 'GET', null, token)
    const advanced = (shipList.data.items || []).some((o) => o.shipment && o.shipment.ship_status >= 2)
    check('点击推进物流后状态前进', advanced)
    await page.screenshot({ path: `${SHOT}/04-orders-advanced.png` })
  }

  // ---- 5. 其余页面巡检 ----
  for (const [p, key, name] of [
    ['/admin/products', '商品管理', '商品管理'],
    ['/admin/aftersales', '售后管理', '售后管理'],
    ['/admin/members', '会员管理', '会员管理'],
    ['/admin/coupons', '优惠券管理', '优惠券管理'],
  ]) {
    await page.goto(BASE + p, { waitUntil: 'networkidle2' })
    await sleep(1000)
    const c = await page.content()
    check(`${name}页正常渲染`, c.includes(key))
    await page.screenshot({ path: `${SHOT}/05${p.replace(/\//g, '-')}.png` })
  }

  // ---- 6. 无 JS 报错 ----
  check('无 JS 运行时错误', errors.length === 0, errors.slice(0, 3).join(' ; '))

  await browser.close()

  const failed = results.filter((r) => !r.ok)
  console.log(`\n==== ${results.length - failed.length}/${results.length} 通过 ====`)
  if (failed.length) {
    console.log('失败项: ' + failed.map((f) => f.name).join(', '))
    process.exit(1)
  }
}

main().catch((e) => { console.error('E2E 异常:', e.message); process.exit(1) })
