<template>
  <div class="inicio">
    <div class="hero">
      <div class="hero-content">
        <h1>CLUB <span class="gradient-text">360</span></h1>
        <p class="hero-subtitle">Tu centro deportivo en Buenos Aires. Fútbol, Pádel, Básquet y Vóley.</p>
        <div class="hero-actions">
          <template v-if="auth.isAdmin || auth.isEmpleado">
            <router-link to="/clases" class="btn btn-primary">Ver Clases Disponibles</router-link>
          </template>
          <template v-if="auth.isCliente">
            <router-link to="/clases" class="btn btn-primary">Reservar Clase</router-link>
          </template>
          <router-link to="/registro" class="btn btn-outline" v-if="!auth.isAuthenticated">Registrarse</router-link>
        </div>
      </div>
      <div class="hero-sports">
        <div class="sport-card" v-for="s in sports" :key="s.name">
          <span class="sport-icon">{{ s.icon }}</span>
          <span>{{ s.name }}</span>
        </div>
      </div>
    </div>

    <div class="info-section">
      <div class="grid-3">
        <div class="card info-card">
          <div class="info-icon">🕐</div>
          <h3>Horario</h3>
          <p>Lunes a Sábados</p>
          <p class="highlight">8:00 - 22:00 hs</p>
          <p class="note">Cerrado feriados nacionales</p>
        </div>
        <div class="card info-card">
          <div class="info-icon">📍</div>
          <h3>Ubicación</h3>
          <p>Provincia de Buenos Aires</p>
          <p class="highlight">Sede única</p>
        </div>
        <div class="card info-card">
          <div class="info-icon">💳</div>
          <h3>Pagos</h3>
          <p>Tarjeta de crédito online</p>
          <p class="highlight">Efectivo en sede</p>
        </div>
      </div>
    </div>

    <div class="features-section">
      <h2>¿Cómo funciona?</h2>
      <div class="grid-2" style="margin-top:20px">
        <div class="card feature">
          <h3>🗓️ Inscripción Mensual</h3>
          <p>Abonás el mes completo y tenés tu lugar asegurado cada semana. Con <strong>20% de descuento</strong> si te sumás a mitad de mes.</p>
        </div>
        <div class="card feature">
          <h3>🎯 Clase Individual</h3>
          <p>Reservá clases sueltas pagando una seña del <strong>50%</strong>. Flexible y sin compromisos.</p>
        </div>
        <div class="card feature">
          <h3>📲 Control QR</h3>
          <p>Al llegar, escaneá tu QR para registrar tu asistencia de forma rápida y digital.</p>
        </div>
        <div class="card feature">
          <h3>⏳ Lista de Espera</h3>
          <p>Si un turno está lleno, te anotamos automáticamente y te notificamos cuando se libere un cupo.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useAuthStore } from '../stores/auth.js'
const auth = useAuthStore()
const sports = [
  { name: 'Fútbol', icon: '⚽' },
  { name: 'Pádel', icon: '🎾' },
  { name: 'Básquet', icon: '🏀' },
  { name: 'Vóley', icon: '🏐' }
]
</script>

<style scoped>
.hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 80px 0 60px;
  gap: 40px;
}
.hero h1 { font-size: 96px; line-height: 1; margin-bottom: 16px; }
.gradient-text {
  background: linear-gradient(135deg, var(--verde-claro), var(--azul-claro));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.hero-subtitle { font-size: 18px; color: var(--text-muted); max-width: 440px; margin-bottom: 32px; line-height: 1.6; }
.hero-actions { display: flex; gap: 12px; }
.hero-sports {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  flex-shrink: 0;
}
.sport-card {
  background: var(--dark-2);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px;
  text-align: center;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.2s;
}
.sport-card:hover { border-color: var(--verde); transform: translateY(-2px); }
.sport-icon { display: block; font-size: 32px; margin-bottom: 8px; }
.info-section { margin: 40px 0; }
.info-card { text-align: center; }
.info-card h3 { font-size: 20px; margin: 12px 0 8px; }
.info-card p { color: var(--text-muted); font-size: 14px; }
.info-icon { font-size: 32px; }
.highlight { color: var(--verde-claro); font-weight: 600; font-size: 16px !important; margin: 4px 0; }
.note { font-size: 12px !important; color: var(--text-muted); margin-top: 4px; }
.features-section { margin-top: 40px; }
.features-section h2 { font-size: 36px; margin-bottom: 4px; }
.feature h3 { margin-bottom: 10px; font-size: 16px; }
.feature p { color: var(--text-muted); font-size: 14px; line-height: 1.6; }
</style>
