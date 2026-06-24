<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-header">
        <h2>CLUB 360</h2>
        <p>Creá tu nueva contraseña</p>
      </div>

      <div v-if="!tokenValido">
        <div class="alert alert-error">
          {{ errorToken || 'Link inválido o expirado. Solicitá uno nuevo.' }}
        </div>
        <p class="auth-footer">
          <router-link to="/recuperar-password">Solicitar nuevo link</router-link>
        </p>
      </div>

      <div v-else-if="!cambiado">
        <div class="alert alert-error" v-if="error">{{ error }}</div>
        <div class="input-group">
          <label>Nueva contraseña</label>
          <input v-model="form.nueva" type="password" placeholder="Mínimo 8 caracteres" />
        </div>
        <div class="input-group">
          <label>Confirmá la contraseña</label>
          <input v-model="form.confirmar" type="password" placeholder="Repetí la contraseña" />
        </div>
        <button class="btn btn-primary" style="width:100%;margin-top:8px" :disabled="loading" @click="cambiar">
          {{ loading ? 'Guardando...' : 'Guardar nueva contraseña' }}
        </button>
      </div>

      <div v-else>
        <div class="alert alert-success">
          ¡Contraseña actualizada! Ya podés iniciar sesión con tu nueva contraseña.
        </div>
        <router-link to="/login" class="btn btn-primary" style="display:block;text-align:center;margin-top:16px">
          Ir al inicio de sesión
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api.js'

const route = useRoute()
const token = route.query.token || ''
const tokenValido = ref(false)
const errorToken = ref('')
const cambiado = ref(false)
const error = ref('')
const loading = ref(false)
const form = ref({ nueva: '', confirmar: '' })

onMounted(() => {
  // Validación básica local: si no hay token directamente mostramos error
  if (!token) {
    errorToken.value = 'No se encontró el token de recuperación.'
  } else {
    tokenValido.value = true
  }
})

async function cambiar() {
  error.value = ''
  if (form.value.nueva.length < 8) {
    error.value = 'La contraseña debe tener al menos 8 caracteres'
    return
  }
  if (form.value.nueva !== form.value.confirmar) {
    error.value = 'Las contraseñas no coinciden'
    return
  }
  loading.value = true
  try {
    await api.post('/auth/reset-password', {
      token,
      nueva_password: form.value.nueva,
      confirmar_password: form.value.confirmar
    })
    cambiado.value = true
  } catch (e) {
    const msg = e.response?.data?.error || 'Error al cambiar la contraseña'
    // Si el backend dice que el token expiró, lo mostramos en el bloque de error de token
    if (e.response?.status === 400 && msg.includes('expiró')) {
      tokenValido.value = false
      errorToken.value = msg
    } else {
      error.value = msg
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page { min-height:100vh;display:flex;align-items:center;justify-content:center;background:radial-gradient(ellipse at center,#0a1628 0%,var(--dark) 70%); }
.auth-card { background:var(--dark-2);border:1px solid var(--border);border-radius:16px;padding:40px;width:100%;max-width:420px;box-shadow:var(--shadow); }
.auth-header { text-align:center;margin-bottom:32px; }
.auth-header h2 { font-size:32px; }
.auth-header p { color:var(--text-muted);margin-top:4px; }
.auth-footer { text-align:center;margin-top:20px;font-size:14px; }
.auth-footer a { color:var(--verde-claro); }
</style>