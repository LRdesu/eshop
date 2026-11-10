import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/Login.vue') },
  { path: '/register', name: 'register', component: () => import('../views/Register.vue') },
  { path: '/', name: 'home', component: () => import('../views/Home.vue'), meta: { auth: true } },
  { path: '/list', name: 'list', component: () => import('../views/ProductList.vue'), meta: { auth: true } },
  { path: '/seckill', name: 'seckill', component: () => import('../views/Seckill.vue'), meta: { auth: true } },
  { path: '/product/:id', name: 'product', component: () => import('../views/ProductDetail.vue'), meta: { auth: true } },
  { path: '/shop/:id', name: 'shop', component: () => import('../views/Shop.vue'), meta: { auth: true } },
  { path: '/cart', name: 'cart', component: () => import('../views/Cart.vue'), meta: { auth: true } },
  { path: '/checkout', name: 'checkout', component: () => import('../views/Checkout.vue'), meta: { auth: true } },
  { path: '/pay/:orderId', name: 'pay', component: () => import('../views/Pay.vue'), meta: { auth: true } },
  { path: '/orders', name: 'orders', component: () => import('../views/OrderList.vue'), meta: { auth: true } },
  { path: '/order/:id', name: 'order-detail', component: () => import('../views/OrderDetail.vue'), meta: { auth: true } },
  { path: '/shipment/:orderId', name: 'shipment', component: () => import('../views/Shipment.vue'), meta: { auth: true } },
  { path: '/aftersale', name: 'aftersale', component: () => import('../views/AfterSale.vue'), meta: { auth: true } },
  { path: '/coupon-center', name: 'coupon-center', component: () => import('../views/CouponCenter.vue'), meta: { auth: true } },
  { path: '/member', name: 'member', component: () => import('../views/Member.vue'), meta: { auth: true } },
  { path: '/member-center', name: 'member-center', component: () => import('../views/MemberCenter.vue'), meta: { auth: true } },

  // ---- 商家后台（与买家端共用同一站点，独立登录态）----
  { path: '/admin/login', name: 'admin-login', component: () => import('../views/admin/AdminLogin.vue') },
  {
    path: '/admin',
    component: () => import('../views/admin/AdminLayout.vue'),
    meta: { admin: true },
    children: [
      { path: '', name: 'admin-dashboard', component: () => import('../views/admin/Dashboard.vue') },
      { path: 'products', name: 'admin-products', component: () => import('../views/admin/AdminProducts.vue') },
      { path: 'orders', name: 'admin-orders', component: () => import('../views/admin/AdminOrders.vue') },
      { path: 'aftersales', name: 'admin-aftersales', component: () => import('../views/admin/AdminAfterSales.vue') },
      { path: 'activities', name: 'admin-activities', component: () => import('../views/admin/AdminActivities.vue') },
      { path: 'shops', name: 'admin-shops', component: () => import('../views/admin/AdminShops.vue') },
      { path: 'members', name: 'admin-members', component: () => import('../views/admin/AdminMembers.vue') },
      { path: 'coupons', name: 'admin-coupons', component: () => import('../views/admin/AdminCoupons.vue') },
    ],
  },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  if (to.meta.auth && !localStorage.getItem('token')) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.admin && !localStorage.getItem('admin_token')) {
    return { name: 'admin-login' }
  }
})

export default router
