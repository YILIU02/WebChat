import { createRouter, createWebHistory } from 'vue-router';
import AuthView from '../views/AuthView.vue';
import App from '../App.vue'; 

const router = createRouter({
  history: createWebHistory(),
  routes: [
    // 根路径对应App.vue（登录后显示的主页面）
    { path: '/', name: 'Main', component: App, meta: { requiresAuth: true } },
    // 登录注册页
    { path: '/auth', name: 'Auth', component: AuthView }
  ]
});

// 路由守卫：未登录时强制跳转至登录页（符合文档中登录后才能访问主页面的逻辑）
router.beforeEach((to, from, next) => {
  if (to.meta.requiresAuth && !localStorage.getItem('token')) {
    next('/auth'); // 未登录则跳转到登录页
  } else {
    next(); // 已登录或无需登录的页面直接放行
  }
});

export default router;