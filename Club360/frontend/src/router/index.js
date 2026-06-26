import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

const routes = [
  { path: '/', component: () => import('../views/Inicio.vue') },
  { path: '/login', component: () => import('../views/Login.vue') },
  { path: '/registro', component: () => import('../views/Registro.vue') },
  { path: '/clases', component: () => import('../views/Clases.vue') },
  { path: '/clases/:id', component: () => import('../views/DetalleClase.vue') },
  { path: '/recuperar-password', component: () => import('../views/RecuperarPassword.vue') },
  { path: '/reset-password', component: () => import('../views/ResetPassword.vue') },
  { path: '/lista-espera/rechazo', component: () => import('../views/RechazoListaEspera.vue') },
  { path: '/mis-reservas', component: () => import('../views/MisReservas.vue'), meta: { requiresAuth: true } },
  { path: '/mis-pagos', component: () => import('../views/MisPagos.vue'), meta: { requiresAuth: true, roles: ['cliente'] } },
  { path: '/perfil', component: () => import('../views/Perfil.vue'), meta: { requiresAuth: true } },
  // Admin
  { path: '/admin/turnos', component: () => import('../views/admin/GestionTurnos.vue'), meta: { requiresAuth: true, roles: ['administrador'] } },
  { path: '/admin/usuarios', component: () => import('../views/admin/GestionUsuarios.vue'), meta: { requiresAuth: true, roles: ['administrador', 'empleado'] } },
  { path: '/admin/actividades', component: () => import('../views/admin/GestionActividades.vue'), meta: { requiresAuth: true, roles: ['administrador'] } },
  { path: '/usuarios/:id', component: () => import('../views/admin/DetalleUsuario.vue'), meta: { requiresAuth: true, roles: ['administrador', 'empleado'] } },
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
    return next({ path: '/login', query: { redirect: to.fullPath } })
  }
  if (to.path.startsWith('/clases/') && to.query.lista_token && !auth.isAuthenticated) {
    return next({ path: '/login', query: { redirect: to.fullPath } })
  }
  if (to.meta.roles && !to.meta.roles.includes(auth.user?.rol)) {
    return next('/')
  }
  next()
})

export default router
