<template>
  <div>
    <div class="page-header">
      <h2>REGISTRO DE ASISTENCIA</h2>
      <p>Escaneá el QR del cliente para registrar su asistencia</p>
    </div>

    <div class="grid-2">
      <div class="card">
        <h3 style="margin-bottom:20px;font-size:20px">Ingresar código QR</h3>
        <p style="font-size:13px;color:var(--text-muted);margin-bottom:16px">
          En producción se usaría la cámara del dispositivo. Ingresá el contenido del QR manualmente para simular:
        </p>
        <div class="input-group">
          <label>Contenido del QR</label>
          <input v-model="qrInput" placeholder="CLUB360-RESERVA-1" @keyup.enter="registrar" />
        </div>
        <p style="font-size:12px;color:var(--text-muted);margin-bottom:16px">Formato: CLUB360-RESERVA-{id}</p>
        <button class="btn btn-primary" @click="registrar" :disabled="loading || !qrInput">
          {{ loading ? 'Registrando...' : '📲 Registrar asistencia' }}
        </button>
      </div>

      <div class="card resultado" v-if="resultado">
        <h3 style="margin-bottom:16px;font-size:20px">
          {{ resultado.asistencia_registrada ? '✅ Asistencia registrada' : '❌ Error' }}
        </h3>
        <div class="cliente-info">
          <div class="avatar-lg">{{ resultado.nombre?.charAt(0) }}</div>
          <div>
            <p class="cliente-nombre">{{ resultado.nombre }}</p>
            <p style="font-size:13px;color:var(--text-muted)">
              {{ resultado.reserva?.clase?.actividad }} — {{ resultado.reserva?.clase?.dia_semana }} {{ resultado.reserva?.clase?.hora_inicio }} hs
            </p>
            <span class="badge" :class="resultado.reserva?.tipo === 'abonado' ? 'badge-green' : 'badge-blue'">
              {{ resultado.reserva?.tipo }}
            </span>
          </div>
        </div>

        <div v-if="resultado.alertas?.length" class="alertas-section">
          <p class="alerta-titulo">⚠️ Alertas del cliente:</p>
          <div v-for="(a, i) in resultado.alertas" :key="i" class="alert alert-warning">{{ a }}</div>
        </div>
        <div v-else class="alert alert-success">Cliente sin alertas pendientes</div>
      </div>

      <div class="card" v-else style="display:flex;align-items:center;justify-content:center;min-height:200px">
        <div style="text-align:center;color:var(--text-muted)">
          <p style="font-size:48px">📲</p>
          <p>El resultado aparecerá aquí</p>
        </div>
      </div>
    </div>

    <div class="alert alert-error" v-if="error" style="margin-top:16px">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import api from '../../api.js'

const qrInput = ref('')
const resultado = ref(null)
const loading = ref(false)
const error = ref('')

async function registrar() {
  if (!qrInput.value) return
  loading.value = true
  error.value = ''
  resultado.value = null
  try {
    const { data } = await api.post('/asistencia/registrar', { qr_data: qrInput.value })
    resultado.value = data
    qrInput.value = ''
  } catch (e) {
    error.value = e.response?.data?.error || 'Error al registrar asistencia'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.cliente-info { display:flex; align-items:center; gap:14px; margin-bottom:16px; }
.avatar-lg {
  width:52px; height:52px;
  background:linear-gradient(135deg, var(--verde), var(--azul));
  border-radius:50%;
  display:flex; align-items:center; justify-content:center;
  font-size:20px; font-weight:700; flex-shrink:0;
}
.cliente-nombre { font-size:18px; font-weight:600; margin-bottom:4px; }
.alerta-titulo { font-size:14px; font-weight:600; margin-bottom:10px; color:var(--warning); }
</style>
