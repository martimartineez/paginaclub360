import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

const routes = [
  { path: '/', component: () => import('../views/Inicio.vue') },
  { path: '/login', component: () => import('../views/Login.vue') },
  { path: '/registro', component: () => import('../views/Registro.vue') },
  { path: '/clases', component: () => import('../views/Clases.vue') },
  { path: '/mis-reservas', component: () => import('../views/MisReservas.vue'), meta: { requiresAuth: true } },
  { path: '/perfil', component: () => import('../views/Perfil.vue'), meta: { requiresAuth: true } },
  // Admin
  { path: '/admin/clases', component: () => import('../views/admin/GestionClases.vue'), meta: { requiresAuth: true, roles: ['administrador'] } },
  { path: '/admin/usuarios', component: () => import('../views/admin/GestionUsuarios.vue'), meta: { requiresAuth: true, roles: ['administrador', 'empleado'] } },
  { path: '/admin/actividades', component: () => import('../views/admin/GestionActividades.vue'), meta: { requiresAuth: true, roles: ['administrador'] } },
  // Empleado
  { path: '/empleado/asistencia', component: () => import('../views/empleado/RegistroAsistencia.vue'), meta: { requiresAuth: true, roles: ['empleado', 'administrador'] } },
  { path: '/empleado/suspensiones', component: () => import('../views/empleado/Suspensiones.vue'), meta: { requiresAuth: true, roles: ['empleado', 'administrador'] } },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return next('/login')
  }
  if (to.meta.roles && !to.meta.roles.includes(auth.user?.rol)) {
    return next('/')
  }
  next()
})

export default router
