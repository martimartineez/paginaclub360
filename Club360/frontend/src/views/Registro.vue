<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-header">
        <span class="auth-logo">⚽</span>
        <h2>CLUB 360</h2>
        <p>Creá tu cuenta (mayores de 18 años)</p>
      </div>

      <div class="alert alert-error" v-if="error">{{ error }}</div>
      <div class="alert alert-success" v-if="success">{{ success }}</div>

      <form @submit.prevent="handleRegister">
        <div class="grid-2">
          <div class="input-group">
            <label>Nombre</label>
            <input v-model="form.nombre" placeholder="Juan" required />
          </div>
          <div class="input-group">
            <label>Apellido</label>
            <input v-model="form.apellido" placeholder="Pérez" required />
          </div>
        </div>
        <div class="input-group">
          <label>DNI</label>
          <input v-model="form.dni" placeholder="12345678" required />
        </div>
        <div class="input-group">
          <label>Email</label>
          <input v-model="form.email" type="email" placeholder="tu@email.com" required />
        </div>
        <div class="input-group">
          <label>Contraseña</label>
          <input v-model="form.password" type="password" placeholder="Mínimo 6 caracteres" required minlength="6" />
        </div>
        <button class="btn btn-primary" style="width:100%" :disabled="loading">
          {{ loading ? 'Registrando...' : 'Crear cuenta' }}
        </button>
      </form>

      <p class="auth-footer">
        ¿Ya tenés cuenta? <router-link to="/login">Ingresá</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

const auth = useAuthStore()
const router = useRouter()
const form = ref({ nombre: '', apellido: '', dni: '', email: '', password: '' })
const error = ref('')
const success = ref('')
const loading = ref(false)

async function handleRegister() {
  loading.value = true
  error.value = ''
  try {
    await auth.register(form.value)
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.error || 'Error al registrarse'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(ellipse at center, #0a1628 0%, var(--dark) 70%);
}
.auth-card {
  background: var(--dark-2);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 40px;
  width: 100%;
  max-width: 460px;
  box-shadow: var(--shadow);
}
.auth-header { text-align: center; margin-bottom: 28px; }
.auth-logo { font-size: 40px; display: block; margin-bottom: 12px; }
.auth-header h2 { font-size: 32px; }
.auth-header p { color: var(--text-muted); margin-top: 4px; font-size: 14px; }
.auth-footer { text-align: center; margin-top: 20px; font-size: 14px; color: var(--text-muted); }
.auth-footer a { color: var(--verde-claro); }
</style>
