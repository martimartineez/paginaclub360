<template>
  <section class="result-page">
    <div class="result-card">
      <div class="result-icon" :class="result.tone">
        {{ result.icon }}
      </div>

      <p class="result-kicker">Lista de espera</p>
      <h1>{{ result.title }}</h1>
      <p class="result-message">{{ result.message }}</p>

      <div class="result-actions">
        <router-link v-if="auth.isAuthenticated" to="/mis-reservas" class="btn btn-outline">
          Mis reservas
        </router-link>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

const route = useRoute()
const auth = useAuthStore()

const results = {
  ok: {
    icon: '✓',
    tone: 'success',
    title: 'Cupo rechazado',
    message: 'Ya liberamos tu lugar para ofrecérselo a la siguiente persona de la lista de espera.'
  },
  ya_rechazado: {
    icon: '✓',
    tone: 'success',
    title: 'Este cupo ya fue rechazado',
    message: 'No tenés que hacer nada más. El lugar ya fue ofrecido a la siguiente persona.'
  },
  ya_reservado: {
    icon: '!',
    tone: 'warning',
    title: 'Ya reservaste esta clase',
    message: 'El enlace no realizó cambios porque ya tenés una reserva activa para esta clase.'
  },
  no_pendiente: {
    icon: 'i',
    tone: 'warning',
    title: 'La invitación ya no está pendiente',
    message: 'El estado de tu lugar en la lista de espera cambió y este enlace ya no puede utilizarse.'
  },
  expirado: {
    icon: '!',
    tone: 'error',
    title: 'El enlace venció',
    message: 'Los enlaces para rechazar un cupo duran 7 días. Podés revisar tus reservas para ver el estado actual.'
  },
  invalido: {
    icon: '×',
    tone: 'error',
    title: 'El enlace no es válido',
    message: 'No pudimos verificar este enlace. Revisá que esté completo o consultá el estado desde tu cuenta.'
  }
}

const result = computed(() => results[route.query.estado] || results.invalido)
</script>

<style scoped>
.result-page {
  min-height: calc(100vh - 64px);
  display: grid;
  place-items: center;
  padding: 32px 20px;
}

.result-card {
  width: min(100%, 560px);
  padding: 42px;
  text-align: center;
  background: var(--dark-2);
  border: 1px solid var(--border);
  border-radius: 18px;
}

.result-icon {
  width: 64px;
  height: 64px;
  display: grid;
  place-items: center;
  margin: 0 auto 20px;
  border-radius: 50%;
  font-size: 34px;
  font-weight: 700;
}

.result-icon.success {
  color: var(--verde-claro);
  background: rgba(46, 204, 113, 0.12);
}

.result-icon.warning {
  color: #f5c451;
  background: rgba(245, 196, 81, 0.12);
}

.result-icon.error {
  color: #ff7373;
  background: rgba(255, 115, 115, 0.12);
}

.result-kicker {
  margin: 0 0 8px;
  color: var(--verde-claro);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

h1 {
  margin: 0 0 14px;
  font-size: clamp(28px, 5vw, 38px);
}

.result-message {
  margin: 0 auto;
  max-width: 450px;
  color: var(--text-muted);
  line-height: 1.65;
}

.result-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 30px;
}

@media (max-width: 520px) {
  .result-card {
    padding: 32px 22px;
  }

  .result-actions {
    flex-direction: column;
  }
}
</style>
