import puppeteer from 'puppeteer-core'
import fs from 'fs'

const API = 'http://127.0.0.1:8000/api/v1'
const BASE = 'http://localhost:5173'
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
const SHOT = 'D:/Desktop/wanho/Python_code/103hanchao/eshop/.tmp/shots3'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const log = []

async function api(path, method = 'GET', body = null, token = null) {
  const res = await fetch(API + path, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: 'Bearer ' + token } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  })
  return res.json()
}

async function clickByText(page, text, tag = 'button') {
  const handle = await page.evaluateHandle(
    (t, g) => [...document.querySelectorAll(g)].find((e) => (e.textContent || '').trim().includes(t)) || null,
    text,
    tag
  )
  const el = handle.asElement()
  if (!el) throw new Error('未找到可点击元素: ' + text)
  await el.click()
  return el
}

const bodyHas = (page, s) => page.evaluate((t) => document.body.innerText.includes(t), s)

async function main() {
  fs.mkdirSync(SHOT, { recursive: true })

  // ---- 1. 用接口造一个「已支付待发货」订单 ----
  const login = await api('/auth/login', 'POST', { username: 'alice', password: 'alice123' })
  const token = login.data.token
  const prods = (await api('/products')).data
  const skuId = prods[0].skus[0].id

  const probe = (
    await api('/orders/preview', 'POST', { items: [{ sku_id: skuId, quantity: 1 }], address_id: 1 }, token)
  ).data
  const goods = probe.available_coupons || []
  const ships = probe.available_shipping_coupons || []
  const couponId = goods.length ? goods[0].coupon.id : null
  const shipCouponId = ships.length ? ships[0].coupon.id : null

  const order = (
    await api('/orders', 'POST', {
      items: [{ sku_id: skuId, quantity: 1 }],
      address_id: 1,
      coupon_id: couponId,
      shipping_coupon_id: shipCouponId,
    }, token)
  ).data
  const orderId = order.id
  const pay = (await api('/payments', 'POST', { order_id: orderId, channel: 'BALANCE' }, token)).data
  await api(`/payments/${pay.payment_no}/pay`, 'POST', { channel: 'BALANCE' })
  log.push(`STEP1 造单成功 order_id=${orderId} 实付=${order.pay_amount}（已支付待发货）`)

  // ---- 2. 浏览器：登录并进入订单详情 ----
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
  })
  const page = await browser.newPage()
  await page.setViewport({ width: 1280, height: 1000 })
  page.on('pageerror', (e) => log.push('[pageerror] ' + e.message))

  await page.goto(BASE + '/login', { waitUntil: 'networkidle2' })
  await page.waitForSelector('input[placeholder="用户名"]', { timeout: 10000 })
  await page.evaluate(() => {
    const setVal = (el, v) => {
      const desc = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el), 'value')
      desc.set.call(el, v)
      el.dispatchEvent(new Event('input', { bubbles: true }))
    }
    setVal(document.querySelector('input[placeholder="用户名"]'), 'alice')
    setVal(document.querySelector('input[placeholder="密码"]'), 'alice123')
  })
  await page.evaluate(() => document.querySelector('.auth-card button').click())
  await page.waitForFunction(() => location.pathname === '/', { timeout: 10000 })

  await page.goto(`${BASE}/order/${orderId}`, { waitUntil: 'networkidle2' })
  await sleep(1200)
  await page.screenshot({ path: SHOT + '/01-detail-pending.png' })
  log.push('STEP2 订单详情：收货地址含南京 = ' + (await bodyHas(page, '南京')))
  log.push('STEP2 显示「商家发货」按钮 = ' + (await page.evaluate(() =>
    [...document.querySelectorAll('button')].some((b) => b.textContent.includes('商家发货')))))

  // ---- 3. 商家发货 ----
  await clickByText(page, '商家发货')
  await sleep(1200)
  await page.screenshot({ path: SHOT + '/02-shipped.png' })
  log.push('STEP3 发货后路由 上海→南京 = ' + (await bodyHas(page, '上海 → 南京')))
  log.push('STEP3 首条轨迹「已发货」= ' + (await bodyHas(page, '已发货')))

  // ---- 4. 逐步推进物流 ----
  const stages = ['仓库拣货', '已揽收', '运输中', '派送中', '已签收']
  for (let i = 0; i < 5; i++) {
    await clickByText(page, '推进物流')
    await sleep(900)
    const ok = await bodyHas(page, stages[i])
    log.push(`STEP4 推进${i + 1} 出现「${stages[i]}」= ${ok}`)
  }
  await page.screenshot({ path: SHOT + '/03-full-trace.png' })
  const text = await page.evaluate(() => document.body.innerText)
  log.push('STEP4 轨迹含上海 = ' + text.includes('上海'))
  log.push('STEP4 轨迹含南京 = ' + text.includes('南京'))
  log.push('STEP4 含「快件已离开【上海转运中心】，发往【南京】」= ' +
    text.includes('快件已离开【上海转运中心】，发往【南京】'))

  // ---- 5. 确认收货 ----
  await clickByText(page, '确认收货')
  await sleep(1200)
  await page.screenshot({ path: SHOT + '/04-confirmed.png' })
  log.push('STEP5 确认收货后状态含「已完成」= ' + (await bodyHas(page, '已完成')))

  // ---- 6. 售后 ----
  await page.evaluate(() => {
    const el = [...document.querySelectorAll('input')].find((i) => i.placeholder === '如：商品破损')
    if (el) {
      const desc = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el), 'value')
      desc.set.call(el, '物流演示：包装破损')
      el.dispatchEvent(new Event('input', { bubbles: true }))
    }
  })
  await clickByText(page, '提交售后申请')
  await sleep(1500)
  await page.screenshot({ path: SHOT + '/05-aftersale.png' })
  log.push('STEP6 售后单号出现(AS开头) = ' + (await page.evaluate(() => /AS\d{14}/.test(document.body.innerText))))
  log.push('STEP6 售后状态含「申请中」= ' + (await bodyHas(page, '申请中')))

  await clickByText(page, '退款')
  await sleep(1500)
  await page.screenshot({ path: SHOT + '/06-refunded.png' })
  log.push('STEP6 退款后状态含「已完成」= ' + (await bodyHas(page, '已完成')))

  await browser.close()
  console.log(log.join('\n'))
  console.log('DONE')
}
main().catch((e) => { console.error('FATAL', e.message); console.log(log.join('\n')); process.exit(1) })
