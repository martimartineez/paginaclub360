<template>
  <div>
    <div class="page-header">
      <h2>MI PERFIL</h2>
    </div>
    <div class="grid-2">
      <div class="card">
        <h3 style="margin-bottom:20px;font-size:20px">Datos personales</h3>
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
          <input :value="auth.user?.dni" disabled style="opacity:0.5" />
        </div>
        <div class="input-group">
          <label>Rol</label>
          <input :value="auth.user?.rol" disabled style="opacity:0.5;text-transform:capitalize" />
        </div>
        <button class="btn btn-primary" @click="guardar">Guardar cambios</button>
      </div>

      <div class="card">
        <h3 style="margin-bottom:20px;font-size:20px">Cambiar contraseña</h3>
        <div class="alert alert-success" v-if="passMsg">{{ passMsg }}</div>
        <div class="alert alert-error" v-if="passErr">{{ passErr }}</div>
        <div class="input-group">
          <label>Contraseña actual</label>
          <input v-model="passForm.password_actual" type="password" />
        </div>
        <div class="input-group">
          <label>Nueva contraseña</label>
          <input v-model="passForm.nueva_password" type="password" />
        </div>
        <button class="btn btn-secondary" @click="cambiarPass">Cambiar contraseña</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth.js'
import api from '../api.js'

const auth = useAuthStore()
const form = ref({ nombre: '', apellido: '', email: '' })
const passForm = ref({ password_actual: '', nueva_password: '' })
const msg = ref(''), err = ref(''), passMsg = ref(''), passErr = ref('')

onMounted(() => {
  form.value = {
    nombre: auth.user?.nombre || '',
    apellido: auth.user?.apellido || '',
    email: auth.user?.email || ''
  }
})

async function guardar() {
  err.value = ''
  try {
    await api.put(`/usuarios/${auth.user.id}`, form.value)
    await auth.refreshUser()
    msg.value = 'Perfil actualizado'
  } catch (e) { err.value = e.response?.data?.error || 'Error al guardar' }
}

async function cambiarPass() {
  passErr.value = ''
  try {
    await api.put('/auth/change-password', passForm.value)
    passMsg.value = 'Contraseña actualizada'
    passForm.value = { password_actual: '', nueva_password: '' }
  } catch (e) { passErr.value = e.response?.data?.error || 'Error' }
}
</script>
