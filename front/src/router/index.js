import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/HomeView.vue')
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue')
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/RegisterView.vue')
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/ProfileView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/route',
    name: 'Route',
    component: () => import('@/views/RouteView.vue')
  },
  {
    path: '/community',
    name: 'Community',
    component: () => import('@/views/CommunityView.vue')
  },
  {
    path: '/community/write',
    name: 'PostWrite',
    component: () => import('@/views/PostWriteView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/community/notices',
    name: 'Notice',
    component: () => import('@/views/NoticeView.vue')
  },
  {
    path: '/community/notices/:id',
    name: 'NoticeDetail',
    component: () => import('@/views/NoticeDetailView.vue')
  },
  {
    path: '/community/:id',
    name: 'PostDetail',
    component: () => import('@/views/PostDetailView.vue')
  },
  {
    path: '/chatbot',
    name: 'Chatbot',
    component: () => import('@/views/ChatbotView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('@/views/AdminView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/kakao/callback',
    name: 'KakaoCallback',
    component: () => import('@/views/KakaoCallbackView.vue')
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFoundView.vue')
  },
  {
  path: '/kakao/profile',
  name: 'KakaoProfile',
  component: () => import('@/views/KakaoProfileView.vue'),
  meta: { requiresAuth: true }
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 인증 가드
router.beforeEach((to, _, next) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    next('/login')
  } else {
    next()
  }
})

export default router