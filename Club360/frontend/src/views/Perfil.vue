<template>
<div>
    <div class="page-header">
      <h2>MI PERFIL</h2>
    </div>

    <div class="perfil-layout">
      <div>
        <div class="card" style="margin-bottom:20px">
          <h3>Datos personales</h3>
          
          <div class="alert alert-success" v-if="msg">{{ msg }}</div>
          <div class="alert alert-error" v-if="err">{{ err }}</div>
          
          <div class="input-group">
            <label>Nombre</label>
            <input v-model="form.nombre" placeholder="Tu nombre" />
            <p v-if="errorNombre" class="field-error">{{ errorNombre }}</p>
          </div>
          
          <div class="input-group">
            <label>Apellido</label>
            <input v-model="form.apellido" placeholder="Tu apellido" />
            <p v-if="errorApellido" class="field-error">{{ errorApellido }}</p>
          </div>
          
          <div class="input-group">
            <label>Email</label>
            <input v-model="form.email" type="email" placeholder="tu@email.com" disabled style="opacity:0.4"/>
            <p v-if="errorEmail" class="field-error">{{ errorEmail }}</p>
          </div>

          <div class="input-group">
            <label>DNI</label>
            <input :value="auth.user?.dni" disabled style="opacity:0.4" />
          </div>
          <div class="input-group" v-if="auth.user?.fecha_nacimiento">
            <label>Fecha de nacimiento</label>
            <input :value="formatFecha(auth.user?.fecha_nacimiento)" disabled style="opacity:0.4" />
          </div>

          <div style="display:flex;gap:10px;flex-wrap:wrap">
            <button 
              class="btn btn-primary" 
              @click="guardar" 
              :disabled="guardando || !isFormValido"
            >
              {{ guardando ? 'Guardando...' : 'Guardar cambios' }}
            </button>
            <button class="btn btn-outline" @click="modalPass = true">
              🔑 Cambiar contraseña
            </button>
          </div>
        </div>

        <!-- Sección tarjetas (solo clientes) -->
        <div class="card" v-if="auth.isCliente">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
            <h3>💳 Mis tarjetas de crédito</h3>
            <button class="btn btn-outline btn-sm" @click="mostrarFormTarjeta = !mostrarFormTarjeta">
              {{ mostrarFormTarjeta ? 'Cancelar' : '+ Agregar tarjeta' }}
            </button>
          </div>

          <!-- Tarjetas existentes -->
          <div v-if="tarjetas.length === 0 && !mostrarFormTarjeta" class="empty-tarjetas">
            <p>No tenés tarjetas registradas.</p>
            <p style="font-size:12px">Agregá una para poder pagar clases online.</p>
          </div>

          <div v-for="t in tarjetas" :key="t.id" class="tarjeta-item">
            <div style="display:flex;align-items:center;gap:12px">
              <span style="font-size:24px">💳</span>
              <div>
                <p style="font-weight:600">•••• •••• •••• {{ t.ultimos_4 }}</p>
                <p style="font-size:12px;color:var(--text-muted)">{{ t.titular }} · Vence {{ t.vencimiento }}</p>
              </div>
            </div>
            <button class="btn btn-danger btn-sm" @click="eliminarTarjeta(t.id)">Eliminar</button>
          </div>

          <!-- Formulario nueva tarjeta -->
          <div v-if="mostrarFormTarjeta" style="margin-top:16px;padding-top:16px;border-top:1px solid var(--border)">
            <FormTarjeta
              label-boton="Guardar tarjeta"
              @guardada="onTarjetaGuardada"
              @cancelar="mostrarFormTarjeta = false"
            />
          </div>
        </div>

        <div class="card danger-zone">
          <h3>Cuenta</h3>
          <p>Si eliminás tu cuenta, se borrarán todos tus datos y no podrás recuperarla.</p>
          <button class="btn btn-danger" @click="modalEliminarCuenta = true">
            Eliminar mi cuenta
          </button>
        </div>
      </div>

      <!-- Info de cuenta -->
      <div class="card cuenta-info">
        <div class="avatar-perfil">{{ auth.user?.nombre?.charAt(0) }}</div>
        <h3>{{ auth.user?.nombre }} {{ auth.user?.apellido }}</h3>
        <p class="email-text">{{ auth.user?.email }}</p>
        <!-- <span class="badge" :class="rolBadge">{{ auth.user?.rol }}</span> -->
        <div class="info-extra">
          <div class="info-row">
            <span class="label">DNI</span>
            <span>{{ auth.user?.dni }}</span>
          </div>
          <div class="info-row" v-if="auth.user?.fecha_nacimiento">
            <span class="label">Nacimiento</span>
            <span>{{ formatFecha(auth.user?.fecha_nacimiento) }}</span>
          </div>
          <div class="info-row" v-if="auth.isCliente">
            <span class="label">Tarjetas</span>
            <span>{{ tarjetas.length }} registrada(s)</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal cambiar contraseña -->
    <div class="modal-overlay" v-if="modalPass" @click.self="cerrarModalPass">
      <div class="modal card">
        <h3>🔑 Cambiar contraseña</h3>
        <div class="alert alert-success" v-if="passMsg">{{ passMsg }}</div>
        <div class="alert alert-error" v-if="passErr">{{ passErr }}</div>
        <div class="input-group">
          <label>Contraseña actual</label>
          <div class="input-eye">
            <input v-model="passForm.password_actual" :type="verActual ? 'text' : 'password'" placeholder="••••••••" />
            <button class="eye-btn" @click="verActual = !verActual">{{ verActual ? '🙈' : '👁️' }}</button>
          </div>
        </div>
        <div class="input-group">
          <label>Nueva contraseña</label>
          <div class="input-eye">
            <input v-model="passForm.nueva_password" :type="verNueva ? 'text' : 'password'" placeholder="Mínimo 8 caracteres" />
            <button class="eye-btn" @click="verNueva = !verNueva">{{ verNueva ? '🙈' : '👁️' }}</button>
          </div>
        </div>
        <div class="input-group">
          <label>Confirmar nueva contraseña</label>
          <div class="input-eye">
            <input v-model="passForm.confirmar" :type="verConfirmar ? 'text' : 'password'" placeholder="Repetí la nueva contraseña" />
            <button class="eye-btn" @click="verConfirmar = !verConfirmar">{{ verConfirmar ? '🙈' : '👁️' }}</button>
          </div>
          <p v-if="passForm.confirmar && passForm.nueva_password !== passForm.confirmar" class="mismatch-msg">
            ⚠️ Las contraseñas no coinciden
          </p>
        </div>
        <div v-if="passForm.nueva_password" class="strength-bar-wrap">
          <div class="strength-bar" :style="{ width: fortaleza.pct + '%', background: fortaleza.color }"></div>
          <span class="strength-label" :style="{ color: fortaleza.color }">{{ fortaleza.label }}</span>
        </div>
        <div style="display:flex;gap:10px;margin-top:8px">
          <button
            class="btn btn-primary"
            @click="cambiarPass"
            :disabled="cambiando || passForm.nueva_password !== passForm.confirmar || !passForm.nueva_password"
          >
            {{ cambiando ? 'Cambiando...' : 'Confirmar cambio' }}
          </button>
          <button class="btn btn-outline" @click="cerrarModalPass">Cancelar</button>
        </div>
      </div>
    </div>

    <div class="modal-overlay" v-if="modalEliminarCuenta" @click.self="cerrarModalEliminarCuenta">
      <div class="modal card">
        <h3>Eliminar mi cuenta</h3>
        <div class="alert alert-error" v-if="eliminarCuentaErr">{{ eliminarCuentaErr }}</div>
        <p class="modal-copy">
          Tu cuenta quedará eliminada.
        </p>
        <div class="modal-actions">
          <button class="btn btn-danger" @click="eliminarMiCuenta" :disabled="eliminandoCuenta">
            {{ eliminandoCuenta ? 'Eliminando...' : 'Eliminar cuenta' }}
          </button>
          <button class="btn btn-outline" @click="cerrarModalEliminarCuenta" :disabled="eliminandoCuenta">
            Cancelar
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import FormTarjeta from '../components/FormTarjeta.vue'
import api from '../api.js'

const auth = useAuthStore()
const router = useRouter()
const form = ref({ nombre: '', apellido: '', email: '' })
const msg = ref(''), err = ref('')
const guardando = ref(false)

const modalPass = ref(false)
const passForm = ref({ password_actual: '', nueva_password: '', confirmar: '' })
const passMsg = ref(''), passErr = ref('')
const cambiando = ref(false)
const verActual = ref(false), verNueva = ref(false), verConfirmar = ref(false)

const tarjetas = ref([])
const mostrarFormTarjeta = ref(false)
const modalEliminarCuenta = ref(false)
const eliminandoCuenta = ref(false)
const eliminarCuentaErr = ref('')

const errorNombre = computed(() => {
  if (!form.value.nombre) return ''
  if (form.value.nombre.trim() === '') return 'El nombre no puede ser solo espacios'
  if (/\d/.test(form.value.nombre)) return 'El nombre no debe contener números'
  return ''
})

const errorApellido = computed(() => {
  if (!form.value.apellido) return ''
  if (form.value.apellido.trim() === '') return 'El apellido no puede ser solo espacios'
  if (/\d/.test(form.value.apellido)) return 'El apellido no debe contener números'
  return ''
})

const errorEmail = computed(() => {
  if (!form.value.email) return ''
  const emailRegex = /^[^@\s]+@[^@\s]+$/
  if (!emailRegex.test(form.value.email)) return 'Debes colocar texto antes del @, incluir el @, y texto luego del @'
  return ''
})

const isFormValido = computed(() => {
  return (
    form.value.nombre.trim() !== '' &&
    form.value.apellido.trim() !== '' &&
    form.value.email.trim() !== '' &&
    !errorNombre.value &&
    !errorApellido.value &&
    !errorEmail.value
  )
})

const rolBadge = computed(() => ({
  'badge-green': auth.user?.rol === 'administrador',
  'badge-blue': auth.user?.rol === 'empleado',
  'badge-yellow': auth.user?.rol === 'cliente'
}))

const fortaleza = computed(() => {
  const p = passForm.value.nueva_password
  if (!p) return { pct: 0, color: '#da3633', label: '' }
  let score = 0
  if (p.length >= 8) score++
  if (p.length >= 10) score++
  if (/[A-Z]/.test(p)) score++
  if (/[0-9]/.test(p)) score++
  if (/[^A-Za-z0-9]/.test(p)) score++
  const map = [
    { pct: 20, color: '#da3633', label: 'Muy débil' },
    { pct: 40, color: '#d29922', label: 'Débil' },
    { pct: 60, color: '#d29922', label: 'Regular' },
    { pct: 80, color: '#3fb950', label: 'Fuerte' },
    { pct: 100, color: '#3fb950', label: 'Muy fuerte' },
  ]
  return map[score - 1] || map[0]
})

onMounted(async () => {
  form.value = { nombre: auth.user?.nombre || '', apellido: auth.user?.apellido || '', email: auth.user?.email || '' }
  if (auth.isCliente) fetchTarjetas()
})

async function fetchTarjetas() {
  try {
    const { data } = await api.get('/auth/tarjetas')
    tarjetas.value = data
  } catch {}
}

async function guardar() {
  if (!isFormValido.value) return
  guardando.value = true; err.value = ''
  try {
    await api.put(`/usuarios/${auth.user.id}`, form.value)
    await auth.refreshUser()
    msg.value = 'Perfil actualizado correctamente'
  } catch (e) { err.value = e.response?.data?.error || 'Error al guardar' }
  finally { guardando.value = false }
}

// viejo
// async function guardar() {
//   guardando.value = true; err.value = ''
//   try {
//     await api.put(`/usuarios/${auth.user.id}`, form.value)
//     await auth.refreshUser()
//     msg.value = 'Perfil actualizado correctamente'
//   } catch (e) { err.value = e.response?.data?.error || 'Error al guardar' }
//   finally { guardando.value = false }
// }

async function cambiarPass() {
  if (passForm.value.nueva_password !== passForm.value.confirmar) return
  cambiando.value = true; passErr.value = ''
  try {
    await api.put('/auth/change-password', { password_actual: passForm.value.password_actual, nueva_password: passForm.value.nueva_password })
    passMsg.value = '✅ Contraseña cambiada correctamente'
    passForm.value = { password_actual: '', nueva_password: '', confirmar: '' }
    setTimeout(() => { modalPass.value = false; passMsg.value = '' }, 1500)
  } catch (e) { passErr.value = e.response?.data?.error || 'Error al cambiar contraseña' }
  finally { cambiando.value = false }
}

function cerrarModalPass() {
  modalPass.value = false
  passForm.value = { password_actual: '', nueva_password: '', confirmar: '' }
  passMsg.value = ''; passErr.value = ''
}

function onTarjetaGuardada(tarjeta) {
  tarjetas.value.push(tarjeta)
  mostrarFormTarjeta.value = false
}

function formatFecha(iso) {
  if (!iso) return ''
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}

async function eliminarTarjeta(id) {
  await api.delete(`/auth/tarjetas/${id}`)
  tarjetas.value = tarjetas.value.filter(t => t.id !== id)
}

function cerrarModalEliminarCuenta() {
  if (eliminandoCuenta.value) return
  modalEliminarCuenta.value = false
  eliminarCuentaErr.value = ''
}

async function eliminarMiCuenta() {
  eliminandoCuenta.value = true
  eliminarCuentaErr.value = ''
  try {
    await api.delete('/auth/me')
    auth.logout()
    router.push('/login')
  } catch (e) {
    eliminarCuentaErr.value = e.response?.data?.error || 'No se pudo eliminar la cuenta'
  } finally {
    eliminandoCuenta.value = false
  }
}
</script>

<style scoped>
.perfil-layout { display: grid; grid-template-columns: 1fr 300px; gap: 24px; align-items: start; }
.card h3 { font-size: 20px; margin-bottom: 20px; }
.cuenta-info { display: flex; flex-direction: column; align-items: center; text-align: center; gap: 10px; padding: 32px 24px; position: sticky; top: 80px; }
.avatar-perfil { width: 72px; height: 72px; background: linear-gradient(135deg, var(--verde), var(--azul)); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 28px; font-weight: 700; margin-bottom: 4px; }
.cuenta-info h3 { font-size: 22px; margin: 0; }
.email-text { color: var(--text-muted); font-size: 14px; }
.info-extra { width: 100%; margin-top: 16px; border-top: 1px solid var(--border); padding-top: 16px; }
.info-row { display: flex; justify-content: space-between; font-size: 14px; padding: 6px 0; }
.label { color: var(--text-muted); }
/* Tarjetas */
.empty-tarjetas { padding: 20px; text-align: center; color: var(--text-muted); font-size: 14px; background: var(--dark-3); border-radius: 8px; }
.tarjeta-item { display: flex; align-items: center; justify-content: space-between; padding: 12px 14px; background: var(--dark-3); border-radius: 8px; margin-bottom: 8px; border: 1px solid var(--border); }
.danger-zone { margin-top: 20px; border-color: rgba(218, 54, 51, 0.45); }
.danger-zone p { color: var(--text-muted); font-size: 14px; margin-bottom: 16px; }
/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 200; }
.modal { max-width: 440px; width: 100%; }
.modal h3 { font-size: 22px; margin-bottom: 20px; }
.modal-copy { color: var(--text-muted); font-size: 14px; line-height: 1.5; margin-bottom: 18px; }
.modal-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.input-eye { position: relative; }
.input-eye input { width: 100%; padding-right: 40px; }
.eye-btn { position: absolute; right: 10px; top: 50%; transform: translateY(-50%); background: none; border: none; cursor: pointer; font-size: 16px; padding: 0; }
.mismatch-msg { font-size: 12px; color: var(--danger); margin-top: 4px; }
.strength-bar-wrap { margin-bottom: 12px; }
.strength-bar { height: 4px; border-radius: 2px; transition: all 0.3s; margin-bottom: 4px; }
.strength-label { font-size: 12px; }
@media (max-width: 768px) { .perfil-layout { grid-template-columns: 1fr; } }
.field-error { font-size: 12px; color: var(--danger); margin-top: 4px; }
</style>
