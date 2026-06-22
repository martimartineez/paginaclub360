<template>
  <div>
    <div class="page-header">
      <h2>MIS CLASES</h2>
      <p>Consultá tus clases y presentá el QR para registrar asistencia</p>
    </div>

    <div class="alert alert-error" v-if="error">{{ error }}</div>
    <div class="alert alert-success" v-if="mensaje">{{ mensaje }}</div>

    <div v-if="loading" class="loading-text">Cargando...</div>

    <div v-else-if="reservas.length === 0 && listaEspera.length === 0" class="empty-state">
      <p style="font-size:48px">🎯</p>
      <p>No tenés reservas activas.</p>
      <router-link to="/clases" class="btn btn-primary" style="margin-top:16px">Ver clases disponibles</router-link>
    </div>

    <div v-else class="reservas-grid">
      <!-- Reservas normales -->
      <div v-for="r in reservas" :key="'r-' + r.id" class="reserva-card card" :class="{ 'cancelada': r.estado === 'cancelada' }">
        <div class="reserva-header">
          <span class="sport-emoji">{{ sportEmoji(r.clase?.actividad) }}</span>
          <div class="reserva-info">
            <h3 style="color:inherit">{{ r.clase?.actividad }}</h3>
            <p>{{ r.clase?.dia_semana }} — {{ r.clase?.hora_inicio }} hs</p>
          </div>
          <div class="reserva-badges">
            <span class="badge" :class="tipoBadge(r.tipo)">{{ r.tipo === 'abonado' ? 'Mensual' : 'Clase suelta' }}</span>
            <span v-if="r.asistida" class="badge badge-green">✓ Asistida</span>
            <span v-if="r.estado === 'suspendida'" class="badge badge-yellow">Suspendida</span>
          </div>
        </div>

        <div class="reserva-detalles">
          <div class="detalle">
            <span class="label">Fecha</span>
            <span>{{ r.clase?.fecha }}</span>
          </div>
          <div class="detalle">
            <span class="label">Total</span>
            <span>${{ r.monto_total?.toLocaleString() }}</span>
          </div>
          <div class="detalle">
            <span class="label">Pagado</span>
            <span :class="{ 'text-green': r.monto_pagado >= r.monto_total, 'text-warning': r.monto_pagado < r.monto_total }">
              ${{ r.monto_pagado?.toLocaleString() }}
            </span>
          </div>
          <div class="detalle" v-if="r.tipo === 'no_abonado'">
            <span class="label">Seña</span>
            <span :class="r.senia_pagada ? 'text-green' : 'text-danger'">
              {{ r.senia_pagada ? '✓ Pagada' : '✗ Pendiente' }}
            </span>
          </div>
        </div>

        <!-- QR Code -->
        <div class="reserva-actions" v-if="r.estado !== 'cancelada'">
          <button class="btn btn-outline btn-sm" @click="toggleQR(r)">
            {{ qrVisible === r.id ? 'Ocultar QR' : 'Ver QR' }}
          </button>
          <button
            v-if="r.estado === 'activa' && esReservaFutura(r)"
            class="btn btn-danger btn-sm"
            @click="confirmarCancelar(r)"
          >
            Cancelar reserva
          </button>
        </div>
        <div v-else class="reserva-actions">
          <span class="badge badge-red">Cancelada</span>
        </div>
        <div v-if="r.estado !== 'cancelada' && qrVisible === r.id" class="qr-section">
          <p class="qr-label">Tu código QR de asistencia</p>
          <img
            v-if="r.qr_code"
            :src="`data:image/png;base64,${r.qr_code}`"
            :alt="`QR de asistencia para la reserva ${r.id}`"
            class="qr-img"
          />
          <p v-else class="text-danger">No se pudo generar el QR de esta clase.</p>
          <p class="qr-help">El empleado validará el pago y las suspensiones al escanearlo.</p>
        </div>
      </div>

      <!-- Entradas en lista de espera -->
      <div v-for="e in listaEspera" :key="'e-' + e.id" class="reserva-card card espera-card">
        <div class="reserva-header">
          <span class="sport-emoji">{{ sportEmoji(e.clase?.actividad) }}</span>
          <div class="reserva-info">
            <h3 style="color:inherit">{{ e.clase?.actividad }}</h3>
            <p>{{ e.clase?.dia_semana }} — {{ e.clase?.hora_inicio }} hs · {{ formatFecha(e.clase?.fecha) }}</p>
          </div>
          <div class="reserva-badges">
            <span class="badge" :class="tipoBadge(e.tipo_preferencia)">{{ e.tipo_preferencia === 'abonado' ? 'Mensual' : 'Clase suelta' }}</span>
            <span class="badge badge-yellow">⏳ En lista de espera</span>
          </div>
        </div>

        <div class="espera-info-banner">
          <span>⏳ Estás en lista de espera para esta clase. Te avisaremos si se libera un cupo.</span>
        </div>

        <div class="reserva-detalles">
          <div class="detalle">
            <span class="label">Fecha</span>
            <span>{{ e.clase?.fecha}}</span>
          </div>
          <div class="detalle">
            <span class="label">Inscripto</span>
            <span>{{ formatFecha(e.fecha_inscripcion?.slice(0,10)) }}</span>
          </div>
          <div class="detalle">
            <span class="label">Costo</span>
            <span class="text-warning">Sin cargo</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal Pago -->
    <div class="modal-overlay" v-if="pagoModal" @click.self="pagoModal = null">
      <div class="modal card">
        <h3>💳 Registrar Pago Online</h3>
        <p style="color:var(--text-muted);font-size:13px;margin-bottom:20px">
          Reserva: {{ pagoModal.clase?.actividad }} — {{ pagoModal.clase?.dia_semana }}
        </p>
        <div class="input-group">
          <label>Monto a pagar</label>
          <input v-model.number="pagoForm.monto" type="number" :max="pagoModal.monto_total - pagoModal.monto_pagado" />
        </div>
        <div class="input-group">
          <label>Tipo de tarjeta</label>
          <select v-model="pagoForm.tipo_pago">
            <option value="senia">Seña (50%)</option>
            <option value="mensualidad">Mensualidad completa</option>
          </select>
        </div>
        <p style="font-size:12px;color:var(--text-muted);margin-bottom:16px">⚠️ Solo se acepta tarjeta de crédito para pagos online</p>
        <div style="display:flex;gap:10px">
          <button class="btn btn-primary" @click="realizarPago" :disabled="pagoLoading">
            {{ pagoLoading ? 'Procesando...' : 'Confirmar pago' }}
          </button>
          <button class="btn btn-outline" @click="pagoModal = null">Cancelar</button>
        </div>
      </div>
    </div>

    <!-- Modal confirmar cancelación -->
    <div class="modal-overlay" v-if="cancelarModal" @click.self="cancelarModal = null">
      <div class="modal card">
        <h3>⚠️ Cancelar reserva</h3>
        <p style="color:var(--text-muted);margin:12px 0">
          ¿Estás seguro? Recordá las políticas de cancelación:
        </p>
        <ul style="font-size:13px;color:var(--text-muted);margin-bottom:20px;padding-left:20px">
          <li v-if="cancelarModal.tipo === 'abonado'">Abonado: crédito a favor si cancelás con 48hs de anticipación</li>
          <li v-else>No abonado: recuperás la seña si cancelás con 24hs de anticipación</li>
          <li>Fuera del plazo: perdés el dinero abonado</li>
        </ul>
        <div style="display:flex;gap:10px">
          <button class="btn btn-danger" @click="ejecutarCancelacion" :disabled="cancelandoLoading">
            {{ cancelandoLoading ? 'Cancelando...' : 'Sí, cancelar' }}
          </button>
          <button class="btn btn-outline" @click="cancelarModal = null">Volver</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api.js'

const reservas = ref([])
const listaEspera = ref([])
const loading = ref(false)
const error = ref('')
const mensaje = ref('')
const qrVisible = ref(null)
const pagoModal = ref(null)
const pagoForm = ref({ monto: 0, tipo_pago: 'mensualidad' })
const pagoLoading = ref(false)
const cancelarModal = ref(null)
const cancelandoLoading = ref(false)

function sportEmoji(nombre) {
  const map = { 'Fútbol': '⚽', 'Pádel': '🎾', 'Básquet': '🏀', 'Vóley': '🏐' }
  return map[nombre] || '🏃'
}
function tipoBadge(tipo) { return tipo === 'abonado' ? 'badge-green' : 'badge-blue' }
function formatFecha(f) {
  if (!f) return ''
  const [y, m, d] = f.split('-')
  return `${d}/${m}/${y}`
}

function toggleQR(r) {
  qrVisible.value = qrVisible.value === r.id ? null : r.id
}

function abrirPago(r) {
  pagoModal.value = r
  pagoForm.value.monto = r.monto_total - r.monto_pagado
}

function confirmarCancelar(r) {
  cancelarModal.value = r
}

function esReservaFutura(r) {
  if (!r?.clase?.fecha || !r?.clase?.hora_inicio) return false
  return new Date(`${r.clase.fecha}T${r.clase.hora_inicio}:00`) > new Date()
}

function mensajeCancelacion(data) {
  const partes = [data.mensaje || 'Reserva cancelada']
  if (data.info) partes.push(data.info)
  if (data.credito_generado > 0) partes.push(`Credito generado: $${data.credito_generado.toLocaleString()}`)
  if (data.descuento_aplicado > 0) partes.push(`Descuento aplicado: $${data.descuento_aplicado.toLocaleString()}`)
  if (data.devolucion_senia > 0) partes.push(`Senia a devolver: $${data.devolucion_senia.toLocaleString()}`)
  if (data.advertencia) partes.push(data.advertencia)
  return partes.join(' - ')
}

async function realizarPago() {
  pagoLoading.value = true
  try {
    await api.post(`/reservas/${pagoModal.value.id}/pagar`, {
      metodo: 'tarjeta_credito',
      monto: pagoForm.value.monto,
      tipo_pago: pagoForm.value.tipo_pago
    })
    mensaje.value = 'Pago registrado correctamente'
    pagoModal.value = null
    await fetchReservas()
  } catch (e) {
    error.value = e.response?.data?.error || 'Error al procesar el pago'
  } finally {
    pagoLoading.value = false
  }
}

async function ejecutarCancelacion() {
  cancelandoLoading.value = true
  try {
    const { data } = await api.post(`/reservas/${cancelarModal.value.id}/cancelar`)
    mensaje.value = mensajeCancelacion(data)
    cancelarModal.value = null
    await fetchReservas()
  } catch (e) {
    error.value = e.response?.data?.error || 'Error al cancelar'
  } finally {
    cancelandoLoading.value = false
  }
}

async function fetchReservas() {
  loading.value = true
  try {
    const [resReservas, resEspera] = await Promise.all([
      api.get('/reservas/'),
      api.get('/reservas/mis-lista-espera')
    ])
    reservas.value = resReservas.data
    listaEspera.value = resEspera.data
  } catch (e) {
    error.value = 'Error al cargar reservas'
  } finally {
    loading.value = false
  }
}

onMounted(fetchReservas)
</script>

<style scoped>
.reservas-grid { display: flex; flex-direction: column; gap: 16px; }
.reserva-card { transition: border-color 0.2s; }
.reserva-card.cancelada { opacity: 0.5; }
.espera-card { border-color: rgba(234,179,8,0.5) !important; background: rgba(234,179,8,0.04); }
.espera-info-banner { background: rgba(234,179,8,0.1); border: 1px solid rgba(234,179,8,0.35); border-radius: 8px; padding: 10px 14px; font-size: 13px; color: var(--warning); margin-bottom: 14px; }
.badge-yellow { background: rgba(234,179,8,0.15); color: #ca8a04; border: 1px solid rgba(234,179,8,0.4); }
.reserva-header { display: flex; align-items: center; gap: 14px; margin-bottom: 16px; }
.sport-emoji { font-size: 32px; }
.reserva-info { flex: 1; }
.reserva-info h3 { font-size: 20px; font-family: 'Bebas Neue', sans-serif; }
.reserva-info p { font-size: 14px; color: var(--text-muted); text-transform: capitalize; }
.reserva-badges { display: flex; gap: 6px; flex-wrap: wrap; }
.reserva-detalles { display: flex; gap: 24px; padding: 12px 0; border-top: 1px solid var(--border); border-bottom: 1px solid var(--border); margin-bottom: 14px; }
.detalle { display: flex; flex-direction: column; gap: 4px; }
.label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.text-green { color: var(--success); font-weight: 600; }
.text-warning { color: var(--warning); font-weight: 600; }
.text-danger { color: var(--danger); font-weight: 600; }
.qr-section { text-align: center; padding: 16px; background: var(--dark-3); border-radius: 8px; margin-bottom: 14px; }
.qr-label { font-size: 12px; color: var(--text-muted); margin-bottom: 10px; }
.qr-img { width: 160px; height: 160px; border-radius: 8px; }
.qr-help { max-width: 360px; margin: 10px auto 0; font-size: 12px; color: var(--text-muted); }
.reserva-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.loading-text, .empty-state { text-align: center; padding: 60px; color: var(--text-muted); }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 200; }
.modal { max-width: 440px; width: 100%; }
.modal h3 { font-size: 22px; margin-bottom: 8px; }
</style>
