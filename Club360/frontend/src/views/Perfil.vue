<template>
  <div>
    <div class="page-header">
      <h2>MI PERFIL</h2>
    </div>

    <div class="perfil-layout">
      <!-- Datos personales -->
      <div class="card">
        <h3>Datos personales</h3>
        <div class="alert alert-success" v-if="msg">{{ msg }}</div>
        <div class="alert alert-error" v-if="err">{{ err }}</div>
        <div class="input-group">
          <label>Nombre</label>
          <input v-model="form.nombre" />
        </div>
        <div class="input-group">
          <label>Apellido</label>
          <input v-model="form.apellido" />
        </div>
        <div class="input-group">
          <label>Email</label>
          <input v-model="form.email" type="email" />
        </div>
        <div class="input-group">
          <label>DNI</label>
          <input :value="auth.user?.dni" disabled style="opacity:0.4" />
        </div>
        <div class="input-group">
          <label>Rol</label>
          <input :value="auth.user?.rol" disabled style="opacity:0.4;text-transform:capitalize" />
        </div>
        <div style="display:flex;gap:10px;flex-wrap:wrap">
          <button class="btn btn-primary" @click="guardar" :disabled="guardando">
            {{ guardando ? 'Guardando...' : 'Guardar cambios' }}
          </button>
          <button class="btn btn-outline" @click="modalPass = true">
            🔑 Cambiar contraseña
          </button>
        </div>
      </div>

      <!-- Info de cuenta -->
      <div class="card cuenta-info">
        <div class="avatar-perfil">{{ auth.user?.nombre?.charAt(0) }}</div>
        <h3>{{ auth.user?.nombre }} {{ auth.user?.apellido }}</h3>
        <p class="email-text">{{ auth.user?.email }}</p>
        <span class="badge" :class="rolBadge">{{ auth.user?.rol }}</span>
        <div class="info-extra">
          <div class="info-row">
            <span class="label">DNI</span>
            <span>{{ auth.user?.dni }}</span>
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
            <input v-model="passForm.nueva_password" :type="verNueva ? 'text' : 'password'" placeholder="Mínimo 6 caracteres" />
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

        <!-- Indicador de fortaleza -->
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth.js'
import api from '../api.js'

const auth = useAuthStore()
const form = ref({ nombre: '', apellido: '', email: '' })
const msg = ref(''), err = ref('')
const guardando = ref(false)

const modalPass = ref(false)
const passForm = ref({ password_actual: '', nueva_password: '', confirmar: '' })
const passMsg = ref(''), passErr = ref('')
const cambiando = ref(false)
const verActual = ref(false)
const verNueva = ref(false)
const verConfirmar = ref(false)

const rolBadge = computed(() => ({
  'badge-green': auth.user?.rol === 'administrador',
  'badge-blue': auth.user?.rol === 'empleado',
  'badge-yellow': auth.user?.rol === 'cliente'
}))

const fortaleza = computed(() => {
  const p = passForm.value.nueva_password
  if (!p) return { pct: 0, color: '#da3633', label: '' }
  let score = 0
  if (p.length >= 6) score++
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

onMounted(() => {
  form.value = {
    nombre: auth.user?.nombre || '',
    apellido: auth.user?.apellido || '',
    email: auth.user?.email || ''
  }
})

async function guardar() {
  guardando.value = true
  err.value = ''
  try {
    await api.put(`/usuarios/${auth.user.id}`, form.value)
    await auth.refreshUser()
    msg.value = 'Perfil actualizado correctamente'
  } catch (e) {
    err.value = e.response?.data?.error || 'Error al guardar'
  } finally {
    guardando.value = false
  }
}

async function cambiarPass() {
  if (passForm.value.nueva_password !== passForm.value.confirmar) return
  cambiando.value = true
  passErr.value = ''
  try {
    await api.put('/auth/change-password', {
      password_actual: passForm.value.password_actual,
      nueva_password: passForm.value.nueva_password
    })
    passMsg.value = '✅ Contraseña cambiada correctamente'
    passForm.value = { password_actual: '', nueva_password: '', confirmar: '' }
    setTimeout(() => { modalPass.value = false; passMsg.value = '' }, 1500)
  } catch (e) {
    passErr.value = e.response?.data?.error || 'Error al cambiar contraseña'
  } finally {
    cambiando.value = false
  }
}

function cerrarModalPass() {
  modalPass.value = false
  passForm.value = { password_actual: '', nueva_password: '', confirmar: '' }
  passMsg.value = ''
  passErr.value = ''
}
</script>

<style scoped>
.perfil-layout { display: grid; grid-template-columns: 1fr 320px; gap: 24px; }
.card h3 { font-size: 20px; margin-bottom: 20px; }
.cuenta-info { display: flex; flex-direction: column; align-items: center; text-align: center; gap: 10px; padding: 32px 24px; }
.avatar-perfil {
  width: 72px; height: 72px;
  background: linear-gradient(135deg, var(--verde), var(--azul));
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 28px; font-weight: 700;
  margin-bottom: 4px;
}
.cuenta-info h3 { font-size: 22px; margin: 0; }
.email-text { color: var(--text-muted); font-size: 14px; }
.info-extra { width: 100%; margin-top: 16px; border-top: 1px solid var(--border); padding-top: 16px; }
.info-row { display: flex; justify-content: space-between; font-size: 14px; padding: 6px 0; }
.label { color: var(--text-muted); }
/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 200; }
.modal { max-width: 440px; width: 100%; }
.modal h3 { font-size: 22px; margin-bottom: 20px; }
.input-eye { position: relative; }
.input-eye input { width: 100%; padding-right: 40px; }
.eye-btn {
  position: absolute; right: 10px; top: 50%; transform: translateY(-50%);
  background: none; border: none; cursor: pointer; font-size: 16px; padding: 0;
}
.mismatch-msg { font-size: 12px; color: var(--danger); margin-top: 4px; }
.strength-bar-wrap { margin-bottom: 12px; }
.strength-bar { height: 4px; border-radius: 2px; transition: all 0.3s; margin-bottom: 4px; }
.strength-label { font-size: 12px; }
@media (max-width: 768px) {
  .perfil-layout { grid-template-columns: 1fr; }
}
</style>
