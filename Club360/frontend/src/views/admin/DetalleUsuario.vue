<template>
  <div v-if="usuario">
    <div class="page-header">
      <router-link to="/admin/usuarios" class="back-link">← Volver a usuarios</router-link>
      <div style="display:flex;align-items:center;gap:16px;margin-top:12px">
        <div class="avatar-xl">{{ usuario.nombre?.charAt(0) }}</div>
        <div>
          <h2>{{ usuario.nombre }} {{ usuario.apellido }}</h2>
          <p style="color:var(--text-muted);font-size:14px">{{ usuario.email }}</p>
          <div style="display:flex;gap:8px;margin-top:6px">
            <span class="badge" :class="rolBadge(usuario.rol)">{{ usuario.rol }}</span>
            <span v-if="usuario.suspensiones_activas?.length" class="badge badge-red">
              {{ usuario.suspensiones_activas.length }} suspensión(es) activa(s)
            </span>
          </div>
        </div>
      </div>
    </div>

    <div class="alert alert-success" v-if="msg">{{ msg }}</div>
    <div class="alert alert-error" v-if="err">{{ err }}</div>

    <!-- Datos básicos -->
    <div class="card" style="margin-bottom:24px">
      <h3 style="font-size:18px;margin-bottom:16px">Información básica</h3>
      <div class="grid-2">
        <div class="detalle-item"><span class="label">Nombre completo</span><span>{{ usuario.nombre }} {{ usuario.apellido }}</span></div>
        <div class="detalle-item"><span class="label">DNI</span><span>{{ usuario.dni }}</span></div>
        <div class="detalle-item"><span class="label">Email</span><span>{{ usuario.email }}</span></div>
        <div class="detalle-item"><span class="label">Miembro desde</span><span>{{ new Date(usuario.fecha_registro).toLocaleDateString() }}</span></div>
      </div>
    </div>

    <!-- Acciones rápidas (solo para clientes) -->
    <div class="card acciones-card" style="margin-bottom:24px" v-if="usuario.rol === 'cliente'">
      <h3 style="font-size:18px;margin-bottom:16px">Acciones</h3>
      <div class="acciones-grid">
        <button class="accion-btn" @click="tab = 'reservas'; fetchReservas()">
          <span class="accion-icon">📋</span>
          <span>Ver reservas</span>
        </button>
        <button class="accion-btn" @click="tab = 'inscribir'">
          <span class="accion-icon">➕</span>
          <span>Inscribir a clase</span>
        </button>
        <button class="accion-btn" @click="tab = 'suspensiones'; fetchSuspensiones()" v-if="usuario.suspensiones_activas?.length">
          <span class="accion-icon">🔓</span>
          <span>Cancelar suspensión</span>
        </button>
      </div>
    </div>

    <!-- Tab: Reservas del usuario -->
    <div class="card" style="margin-bottom:24px" v-if="tab === 'reservas'">
      <h3 style="font-size:18px;margin-bottom:16px">📋 Reservas de {{ usuario.nombre }}</h3>
      <div v-if="loadingReservas" style="color:var(--text-muted);font-size:14px">Cargando...</div>
      <div v-else-if="reservas.length === 0" style="color:var(--text-muted);font-size:14px">Sin reservas.</div>
      <table v-else>
        <thead>
          <tr><th>Clase</th><th>Fecha</th><th>Tipo</th><th>Estado</th><th>Seña</th><th>Acciones</th></tr>
        </thead>
        <tbody>
          <tr v-for="r in reservas" :key="r.id">
            <td>{{ r.clase?.actividad }}</td>
            <td style="font-size:13px">{{ formatFecha(r.clase?.fecha) }} {{ r.clase?.hora_inicio }}</td>
            <td><span class="badge" :class="r.tipo === 'abonado' ? 'badge-green' : 'badge-blue'">{{ r.tipo }}</span></td>
            <td><span class="badge" :class="estadoBadge(r.estado)">{{ r.estado }}</span></td>
            <td>
              <span v-if="r.tipo === 'no_abonado'" :class="r.senia_pagada ? 'text-green' : 'text-danger'">
                {{ r.senia_pagada ? '✓ Pagada' : '✗ Pendiente' }}
              </span>
              <span v-else style="color:var(--text-muted)">—</span>
            </td>
            <td>
              <button
                v-if="r.tipo === 'no_abonado' && !r.senia_pagada && r.estado === 'activa'"
                class="btn btn-primary btn-sm"
                @click="abrirPagoSenia(r)"
              >
                💳 Pagar seña
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Tab: Inscribir a clase -->
    <div class="card" style="margin-bottom:24px" v-if="tab === 'inscribir'">
      <h3 style="font-size:18px;margin-bottom:16px">➕ Inscribir a {{ usuario.nombre }} en una clase</h3>
      <div class="grid-2" style="margin-bottom:16px">
        <div class="input-group" style="margin:0">
          <label>Actividad</label>
          <select v-model="inscribirForm.actividad_id" @change="fetchClasesDisponibles">
            <option value="">Seleccioná una actividad</option>
            <option v-for="a in actividades" :key="a.id" :value="a.id">{{ a.nombre }}</option>
          </select>
        </div>
        <div class="input-group" style="margin:0">
          <label>Tipo de inscripción</label>
          <select v-model="inscribirForm.tipo">
            <option value="abonado">Abonado (mensual)</option>
            <option value="no_abonado">Clase suelta</option>
          </select>
        </div>
      </div>

      <div v-if="clasesDisponibles.length > 0">
        <p style="font-size:13px;color:var(--text-muted);margin-bottom:12px">Seleccioná la clase:</p>
        <div class="clases-lista">
          <div
            v-for="c in clasesDisponibles"
            :key="c.id"
            class="clase-opcion"
            :class="{ 'selected': inscribirForm.clase_id === c.id, 'sin-cupo': c.cupos_disponibles === 0 }"
            @click="inscribirForm.clase_id = c.id"
          >
            <div style="display:flex;align-items:center;gap:10px">
              <span>{{ sportEmoji(c.actividad) }}</span>
              <div>
                <p style="font-weight:600;font-size:14px">{{ c.dia_semana }} {{ formatFecha(c.fecha) }}</p>
                <p style="font-size:12px;color:var(--text-muted)">{{ c.hora_inicio }} hs — {{ c.cupos_disponibles }} cupos</p>
              </div>
            </div>
            <span class="badge" :class="c.cupos_disponibles > 0 ? 'badge-green' : 'badge-yellow'">
              {{ c.cupos_disponibles > 0 ? 'Con cupo' : 'Lista espera' }}
            </span>
          </div>
        </div>
      </div>

      <button
        class="btn btn-primary"
        style="margin-top:16px"
        @click="inscribirCliente"
        :disabled="!inscribirForm.clase_id || inscribiendo"
      >
        {{ inscribiendo ? 'Inscribiendo...' : 'Confirmar inscripción' }}
      </button>
      <button class="btn btn-outline" style="margin-top:16px;margin-left:10px" @click="tab = null">Cancelar</button>
    </div>

    <!-- Tab: Suspensiones activas -->
    <div class="card" style="margin-bottom:24px" v-if="tab === 'suspensiones'">
      <h3 style="font-size:18px;margin-bottom:16px">🔓 Suspensiones activas de {{ usuario.nombre }}</h3>
      <div v-if="suspensiones.length === 0" style="color:var(--text-muted);font-size:14px">Sin suspensiones activas.</div>
      <div v-for="s in suspensiones" :key="s.id" class="suspension-item">
        <div>
          <span class="badge badge-red">{{ s.tipo }}</span>
          <p style="font-size:13px;color:var(--text-muted);margin-top:4px">{{ s.motivo || 'Sin motivo especificado' }}</p>
          <p style="color:var(--warning);font-weight:600;margin-top:4px">Deuda: ${{ s.monto_deuda?.toLocaleString() }}</p>
        </div>
        <div style="display:flex;gap:8px;align-items:center">
          <select v-model="metodoLevantamiento" style="background:var(--dark-3);border:1px solid var(--border);border-radius:8px;padding:6px 10px;color:var(--text);font-size:13px">
            <option value="efectivo">Efectivo</option>
            <option value="tarjeta_credito">Tarjeta</option>
          </select>
          <button class="btn btn-primary btn-sm" @click="levantarSuspension(s)" :disabled="levantando === s.id">
            {{ levantando === s.id ? 'Procesando...' : 'Levantar' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Modal pago seña -->
    <div class="modal-overlay" v-if="pagoSeniaModal" @click.self="pagoSeniaModal = null">
      <div class="modal card">
        <h3>💳 Registrar seña</h3>
        <p style="color:var(--text-muted);font-size:14px;margin-bottom:16px">
          {{ pagoSeniaModal.clase?.actividad }} — {{ formatFecha(pagoSeniaModal.clase?.fecha) }}
        </p>
        <div class="alert alert-warning">
          Monto de seña (50%): <strong>${{ (pagoSeniaModal.monto_total * 0.5).toLocaleString() }}</strong>
        </div>
        <div class="input-group" style="margin-top:16px">
          <label>Método de pago</label>
          <select v-model="metodoPagoSenia">
            <option value="efectivo">Efectivo</option>
            <option value="tarjeta_credito">Tarjeta de crédito</option>
          </select>
        </div>
        <div style="display:flex;gap:10px;margin-top:8px">
          <button class="btn btn-primary" @click="pagarSenia" :disabled="pagandoSenia">
            {{ pagandoSenia ? 'Procesando...' : 'Confirmar pago' }}
          </button>
          <button class="btn btn-outline" @click="pagoSeniaModal = null">Cancelar</button>
        </div>
      </div>
    </div>
  </div>

  <div v-else-if="loading" class="loading-text">Cargando usuario...</div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../../stores/auth.js'
import api from '../../api.js'

const auth = useAuthStore()
const route = useRoute()

const usuario = ref(null)
const loading = ref(true)
const tab = ref(null)
const msg = ref(''), err = ref('')

const reservas = ref([])
const loadingReservas = ref(false)

const actividades = ref([])
const clasesDisponibles = ref([])
const inscribirForm = ref({ actividad_id: '', clase_id: null, tipo: 'abonado' })
const inscribiendo = ref(false)

const suspensiones = ref([])
const metodoLevantamiento = ref('efectivo')
const levantando = ref(null)

const pagoSeniaModal = ref(null)
const metodoPagoSenia = ref('efectivo')
const pagandoSenia = ref(false)

function rolBadge(rol) {
  return { 'administrador': 'badge-green', 'empleado': 'badge-blue', 'cliente': 'badge-yellow' }[rol] || 'badge-yellow'
}
function estadoBadge(estado) {
  return { 'activa': 'badge-green', 'cancelada': 'badge-red', 'suspendida': 'badge-yellow' }[estado] || 'badge-yellow'
}
function sportEmoji(nombre) {
  const map = { 'Fútbol': '⚽', 'Pádel': '🎾', 'Básquet': '🏀', 'Vóley': '🏐' }
  return map[nombre] || '🏃'
}
function formatFecha(fechaStr) {
  if (!fechaStr) return ''
  const [y, m, d] = fechaStr.split('-')
  return `${d}/${m}/${y}`
}

async function fetchUsuario() {
  loading.value = true
  try {
    const { data } = await api.get(`/usuarios/${route.params.id}`)
    usuario.value = data
  } catch (e) {
    err.value = 'No se pudo cargar el usuario'
  } finally {
    loading.value = false
  }
}

async function fetchReservas() {
  loadingReservas.value = true
  try {
    const { data } = await api.get(`/usuarios/${route.params.id}/reservas`)
    reservas.value = data
  } finally {
    loadingReservas.value = false
  }
}

async function fetchSuspensiones() {
  try {
    const { data } = await api.get('/suspensiones/', { params: { activas: true } })
    suspensiones.value = data.filter(s => s.usuario_id === parseInt(route.params.id))
  } catch {}
}

async function fetchClasesDisponibles() {
  if (!inscribirForm.value.actividad_id) return
  inscribirForm.value.clase_id = null
  const { data } = await api.get('/clases/', { params: { actividad_id: inscribirForm.value.actividad_id, solo_activas: true } })
  clasesDisponibles.value = data
}

async function inscribirCliente() {
  inscribiendo.value = true
  err.value = ''
  try {
    const { data } = await api.post(`/usuarios/${route.params.id}/inscribir`, {
      clase_id: inscribirForm.value.clase_id,
      tipo: inscribirForm.value.tipo
    })
    if (data.en_espera) {
      msg.value = `${usuario.value.nombre} fue añadido a la lista de espera`
    } else {
      msg.value = `${usuario.value.nombre} inscripto correctamente`
    }
    tab.value = 'reservas'
    await fetchReservas()
  } catch (e) {
    err.value = e.response?.data?.error || 'Error al inscribir'
  } finally {
    inscribiendo.value = false
  }
}

async function levantarSuspension(s) {
  levantando.value = s.id
  err.value = ''
  try {
    await api.post(`/suspensiones/solicitar-retiro/${s.id}`, { metodo: metodoLevantamiento.value })
    msg.value = 'Suspensión levantada'
    await fetchUsuario()
    await fetchSuspensiones()
  } catch (e) {
    err.value = e.response?.data?.error || 'Error al levantar suspensión'
  } finally {
    levantando.value = null
  }
}

function abrirPagoSenia(r) {
  pagoSeniaModal.value = r
  metodoPagoSenia.value = 'efectivo'
}

async function pagarSenia() {
  pagandoSenia.value = true
  err.value = ''
  try {
    await api.post(`/usuarios/${route.params.id}/pagar-senia/${pagoSeniaModal.value.id}`, {
      metodo: metodoPagoSenia.value
    })
    msg.value = 'Seña registrada correctamente'
    pagoSeniaModal.value = null
    await fetchReservas()
  } catch (e) {
    err.value = e.response?.data?.error || 'Error al registrar seña'
  } finally {
    pagandoSenia.value = false
  }
}

onMounted(async () => {
  const { data } = await api.get('/actividades/')
  actividades.value = data
  await fetchUsuario()
})
</script>

<style scoped>
.back-link { font-size: 13px; color: var(--text-muted); transition: color 0.2s; }
.back-link:hover { color: var(--verde-claro); }
.avatar-xl {
  width: 64px; height: 64px;
  background: linear-gradient(135deg, var(--verde), var(--azul));
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 26px; font-weight: 700; flex-shrink: 0;
}
.detalle-item { display: flex; flex-direction: column; gap: 4px; margin-bottom: 16px; }
.label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.acciones-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
.accion-btn {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 20px 12px;
  background: var(--dark-3); border: 1px solid var(--border);
  border-radius: 10px; cursor: pointer; color: var(--text);
  font-family: 'DM Sans', sans-serif; font-size: 14px; font-weight: 500;
  transition: all 0.2s;
}
.accion-btn:hover { border-color: var(--verde); color: var(--verde-claro); transform: translateY(-2px); }
.accion-icon { font-size: 28px; }
.clases-lista { display: flex; flex-direction: column; gap: 8px; }
.clase-opcion {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px;
  background: var(--dark-3); border: 1px solid var(--border);
  border-radius: 8px; cursor: pointer; transition: all 0.2s;
}
.clase-opcion:hover { border-color: var(--verde); }
.clase-opcion.selected { border-color: var(--verde-claro); background: rgba(46,125,50,0.1); }
.clase-opcion.sin-cupo { opacity: 0.7; }
.suspension-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px; background: var(--dark-3); border-radius: 8px; margin-bottom: 10px;
  border: 1px solid rgba(218,54,51,0.2);
}
.text-green { color: var(--success); font-weight: 600; }
.text-danger { color: var(--danger); font-weight: 600; }
.loading-text { text-align: center; padding: 60px; color: var(--text-muted); }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 200; }
.modal { max-width: 440px; width: 100%; }
.modal h3 { font-size: 22px; margin-bottom: 8px; }
</style>
