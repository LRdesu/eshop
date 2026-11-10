import puppeteer from 'puppeteer-core'
import fs from 'fs'

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
const BASE = 'http://localhost:5173'
const SHOT = 'D:/Desktop/wanho/Python_code/103hanchao/eshop/.tmp/shots'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function clickByText(page, text, tag = 'button') {
  const handle = await page.evaluateHandle(
    (t, g) => {
      const els = [...document.querySelectorAll(g)]
      return els.find((e) => (e.textContent || '').trim().includes(t)) || null
    },
    text,
    tag
  )
  const el = handle.asElement()
  if (!el) throw new Error('未找到可点击元素: ' + text)
  await el.click()
  return el
}

const log = []
async function main() {
  fs.mkdirSync(SHOT, { recursive: true })
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--window-size=1280,900'],
  })
  const page = await browser.newPage()
  await page.setViewport({ width: 1280, height: 900 })
  page.on('console', (m) => { if (m.type() === 'error') log.push('[console.error] ' + m.text()) })
  page.on('pageerror', (e) => log.push('[pageerror] ' + e.message))
  page.on('requestfailed', (r) => log.push('[reqfail] ' + r.url() + ' ' + (r.failure()?.errorText || '')))

  const bodyHas = async (s) => page.evaluate((t) => document.body.innerText.includes(t), s)

  // 1) login
  await page.goto(BASE + '/login', { waitUntil: 'networkidle2' })
  await page.waitForSelector('input[placeholder="用户名"]', { timeout: 10000 })
  await page.evaluate(() => {
    const setVal = (el, v) => {
      const proto = Object.getPrototypeOf(el)
      const desc = Object.getOwnPropertyDescriptor(proto, 'value')
      desc.set.call(el, v)
      el.dispatchEvent(new Event('input', { bubbles: true }))
    }
    setVal(document.querySelector('input[placeholder="用户名"]'), 'alice')
    setVal(document.querySelector('input[placeholder="密码"]'), 'alice123')
  })
  await page.screenshot({ path: SHOT + '/01-login.png' })
  await page.evaluate(() => {
    const card = document.querySelector('.auth-card')
    const btn = card && card.querySelector('button')
    if (btn) btn.click()
    else throw new Error('login button not found in .auth-card')
  })
  await sleep(2500)
  const diag = await page.evaluate(() => ({
    url: location.href,
    body: document.body.innerText.slice(0, 400),
    errToast: !!document.querySelector('.el-message--error'),
  }))
  log.push('DIAG after login click: ' + JSON.stringify(diag))
  await page.screenshot({ path: SHOT + '/01b-afterlogin.png' })
  try {
    await page.waitForFunction(() => location.pathname === '/', { timeout: 10000 })
  } catch (e) {
    log.push('WAIT FAIL: did not reach / ; dumping body:')
    log.push(await page.evaluate(() => document.body.innerText.slice(0, 600)))
    console.log(log.join('\n'))
    await browser.close()
    process.exit(2)
  }
  await sleep(800)
  await page.screenshot({ path: SHOT + '/02-products.png' })
  log.push('STEP2 商品列表含保温杯: ' + (await bodyHas('保温杯')))

  // 2) product detail
  await page.click('.p-card')
  await page.waitForFunction(() => location.pathname.startsWith('/product/'), { timeout: 10000 })
  await sleep(800)
  await page.screenshot({ path: SHOT + '/03-detail.png' })
  log.push('STEP3 详情含实时价¥: ' + (await page.evaluate(() => /¥/.test(document.body.innerText))))

  // 3) add to cart
  await clickByText(page, '加入购物车')
  await sleep(1200)
  await page.screenshot({ path: SHOT + '/04-after-add.png' })

  // 4) cart
  await page.goto(BASE + '/cart', { waitUntil: 'networkidle2' })
  await sleep(800)
  await page.screenshot({ path: SHOT + '/05-cart.png' })
  log.push('STEP5 购物车含保温杯: ' + (await bodyHas('保温杯')))

  // 5) checkout
  await clickByText(page, '去结算')
  await page.waitForFunction(() => location.pathname === '/checkout', { timeout: 10000 })
  await sleep(1500)
  await page.screenshot({ path: SHOT + '/06-checkout.png' })
  const coText = await page.evaluate(() => document.body.innerText)
  const m = coText.match(/实付[：:]\s*¥?([\d.]+)/)
  log.push('STEP6 结算预览实付金额: ' + (m ? m[1] : '(未解析到)'))
  log.push('STEP6 结算含提交订单按钮: ' + (await page.evaluate(() => [...document.querySelectorAll('button')].some(b => b.textContent.includes('提交订单')))))

  // 6) submit order -> pay page
  await clickByText(page, '提交订单')
  await page.waitForFunction(() => location.pathname.startsWith('/pay/'), { timeout: 12000 })
  await sleep(1000)
  await page.screenshot({ path: SHOT + '/07-pay.png' })
  log.push('STEP7 进入收银台路径: ' + (await page.evaluate(() => location.pathname)))

  // 7) pay
  await clickByText(page, '确认支付')
  await page.waitForFunction(() => location.pathname === '/orders', { timeout: 12000 })
  await sleep(1000)
  await page.screenshot({ path: SHOT + '/08-orders.png' })
  const ordText = await page.evaluate(() => document.body.innerText)
  log.push('STEP8 订单页含订单号/待发货/已支付: ' + (/(订单号|待发货|已支付|待付款)/.test(ordText)))

  await browser.close()
  console.log(log.join('\n'))
  console.log('DONE')
}
main().catch((e) => { console.error('FATAL', e); console.log(log.join('\n')); process.exit(1) })
