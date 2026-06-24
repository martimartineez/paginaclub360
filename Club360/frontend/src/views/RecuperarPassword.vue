<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-header">
        <h2>CLUB 360</h2>
        <p>Recuperá tu contraseña</p>
      </div>

      <div v-if="!enviado">
        <div class="alert alert-error" v-if="error">{{ error }}</div>
        <p style="font-size:14px;color:var(--text-muted);margin-bottom:20px">
          Ingresá tu email y te enviamos un link para crear una nueva contraseña.
        </p>
        <div class="input-group">
          <label>Email</label>
          <input v-model="email" type="email" placeholder="tu@email.com" @keyup.enter="enviar" />
        </div>
        <button class="btn btn-primary" style="width:100%" :disabled="loading" @click="enviar">
          {{ loading ? 'Enviando...' : 'Enviar link' }}
        </button>
      </div>

      <div v-else>
        <div class="alert alert-success">
          Si el email está registrado, vas a recibir un link en tu casilla en los próximos minutos.
        </div>
      </div>

      <p class="auth-footer">
        <router-link to="/login">← Volver al inicio de sesión</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import api from '../api.js'

const email = ref('')
const error = ref('')
const loading = ref(false)
const enviado = ref(false)

async function enviar() {
  if (!email.value.trim()) { error.value = 'Ingresá tu email'; return }
  loading.value = true
  error.value = ''
  try {
    await api.post('/auth/recuperar-password', { email: email.value.trim() })
    enviado.value = true
  } catch (e) {
    error.value = e.response?.data?.error || 'Error al enviar el mail'
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