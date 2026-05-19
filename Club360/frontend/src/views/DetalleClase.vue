<template>
  <div v-if="clase">
    <div class="page-header" style="display:flex;align-items:flex-start;justify-content:space-between;gap:16px">
      <div>
        <router-link v-if="auth.isCliente" to="/clases" class="back-link">← Volver</router-link>
      <router-link v-else to="/clases" class="back-link">← Volver a clases</router-link>
        <h2 style="margin-top:8px">{{ sportEmoji(clase.actividad) }} {{ clase.actividad }}</h2>
        <p v-if="clase.turno_id" style="font-size:13px;color:var(--text-muted);margin-top:4px">
          Turno recurrente · {{ clase.dia_semana }} {{ clase.hora_inicio }} hs
        </p>
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:6px">
          <span class="dia-badge">{{ clase.dia_semana }}</span>
          <span class="dia-badge fecha-badge">{{ formatFecha(clase.fecha) }}</span>
          <span class="dia-badge">🕐 {{ clase.hora_inicio }} hs</span>
          <span v-if="clase.cancelada" class="badge badge-red">Cancelada</span>
        </div>
      </div>
      <!-- Botones admin: editar cupo y cancelar clase -->
      <div v-if="auth.isAdmin && !clase.cancelada" style="display:flex;gap:10px;flex-wrap:wrap">
        <button class="btn btn-secondary" @click="modalEditarCupo = true">
          ✏️ Editar cupo
        </button>
        <button class="btn btn-danger" @click="confirmarCancelar = true">
          🚫 Cancelar esta clase
        </button>
      </div>
    </div>

    <div class="alert alert-error" v-if="error">{{ error }}</div>
    <div class="alert alert-success" v-if="mensaje">{{ mensaje }}</div>
    <div class="alert alert-warning" v-if="clase.cancelada">
      Esta clase fue cancelada por el administrador.
    </div>

    <!-- Info general -->
    <div class="grid-3" style="margin-bottom:24px">
      <div class="card stat-card">
        <span class="stat-num">{{ clase.cupos_disponibles }}</span>
        <span class="stat-label">Cupos disponibles</span>
      </div>
      <div class="card stat-card">
        <span class="stat-num">{{ clase.cupo_maximo }}</span>
        <span class="stat-label">Cupo máximo</span>
      </div>
      <div class="card stat-card">
        <span class="stat-num">${{ clase.precio_clase?.toLocaleString() }}</span>
        <span class="stat-label">Precio por clase</span>
      </div>
    </div>

    <!-- QR: solo para cliente con reserva activa -->
    <div class="card" style="margin-bottom:24px" v-if="auth.isCliente && miReserva">
      <h3 style="font-size:20px;margin-bottom:16px">📲 Tu QR de asistencia</h3>
      <div v-if="miReserva.estado === 'activa'" style="display:flex;align-items:center;gap:24px;flex-wrap:wrap">
        <img
          v-if="miReserva.qr_code"
          :src="`data:image/png;base64,${miReserva.qr_code}`"
          style="width:160px;height:160px;border-radius:8px;background:white;padding:8px"
        />
        <div>
          <p style="font-size:14px;color:var(--text-muted);margin-bottom:8px">
            Mostrá este QR al empleado al ingresar a la clase.
          </p>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <span class="badge" :class="miReserva.tipo === 'abonado' ? 'badge-green' : 'badge-blue'">
              {{ miReserva.tipo === 'abonado' ? 'Abonado' : 'Clase suelta' }}
            </span>
            <span class="badge" :class="miReserva.senia_pagada ? 'badge-green' : 'badge-red'">
              {{ miReserva.senia_pagada ? 'Seña pagada' : 'Seña pendiente' }}
            </span>
          </div>
          <button
            class="btn btn-danger btn-sm"
            style="margin-top:12px"
            @click="confirmarCancelarReserva = true"
          >
            ✕ Cancelar mi reserva
          </button>
        </div>
      </div>
      <div v-else>
        <span class="badge badge-red">Reserva {{ miReserva.estado }}</span>
      </div>
    </div>

    <!-- Sin reserva: botón para reservar -->
    <div class="card" style="margin-bottom:24px" v-if="auth.isCliente && !miReserva && !clase.cancelada">
      <h3 style="font-size:20px;margin-bottom:12px">Reservar esta clase</h3>
      <div v-if="reservando">
        <p style="font-size:13px;color:var(--text-muted);margin-bottom:12px">¿Cómo querés inscribirte?</p>
        <div style="display:flex;gap:10px;flex-wrap:wrap">
          <button class="btn btn-primary" @click="reservar('abonado')" :disabled="reservandoLoading">
            📅 Abonado — ${{ clase.precio_clase?.toLocaleString() }}
          </button>
          <button class="btn btn-secondary" @click="reservar('no_abonado')" :disabled="reservandoLoading">
            🎯 Clase suelta — seña ${{ Math.round(clase.precio_clase * 0.5).toLocaleString() }}
          </button>
          <button class="btn btn-outline" @click="reservando = false">Cancelar</button>
        </div>
      </div>
      <button v-else class="btn btn-primary" @click="reservando = true">
        {{ clase.cupos_disponibles === 0 ? '⏳ Anotarme en lista de espera' : '+ Reservar' }}
      </button>
    </div>

    <!-- Lista de inscriptos: empleado y admin -->
    <div class="card" style="margin-bottom:24px" v-if="auth.isEmpleado || auth.isAdmin">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
        <h3 style="font-size:20px">👥 Inscriptos</h3>
        <button class="btn btn-outline btn-sm" @click="fetchInscriptos">↻ Actualizar</button>
      </div>
      <div v-if="loadingInscriptos" style="color:var(--text-muted);font-size:14px">Cargando...</div>
      <div v-else-if="inscriptos.length === 0" style="color:var(--text-muted);font-size:14px">Sin inscriptos aún.</div>
      <table v-else>
        <thead>
          <tr><th>Cliente</th><th>DNI</th><th>Tipo</th><th>Seña</th><th>Pagado</th></tr>
        </thead>
        <tbody>
          <tr v-for="r in inscriptos" :key="r.id">
            <td>
              <router-link :to="`/usuarios/${r.usuario?.id}`" style="color:var(--verde-claro)">
                {{ r.usuario?.nombre }} {{ r.usuario?.apellido }}
              </router-link>
            </td>
            <td style="color:var(--text-muted)">{{ r.usuario?.dni }}</td>
            <td><span class="badge" :class="r.tipo === 'abonado' ? 'badge-green' : 'badge-blue'">{{ r.tipo }}</span></td>
            <td>
              <span :class="r.senia_pagada ? 'text-green' : 'text-danger'">
                {{ r.senia_pagada ? '✓' : '✗' }}
              </span>
            </td>
            <td>${{ r.monto_pagado?.toLocaleString() }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Lista de espera: solo admin -->
    <div class="card" v-if="auth.isAdmin">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
        <h3 style="font-size:20px">⏳ Lista de espera</h3>
        <span v-if="listaEspera.length >= 10" class="badge badge-red">⚠️ Alta demanda</span>
      </div>
      <div v-if="loadingEspera" style="color:var(--text-muted);font-size:14px">Cargando...</div>
      <div v-else-if="listaEspera.length === 0" style="color:var(--text-muted);font-size:14px">Lista vacía.</div>
      <table v-else>
        <thead>
          <tr><th>#</th><th>Cliente</th><th>Preferencia</th><th>Fecha inscripción</th><th>Estado</th></tr>
        </thead>
        <tbody>
          <tr v-for="(l, i) in listaEspera" :key="l.id">
            <td>{{ i + 1 }}</td>
            <td>{{ l.usuario?.nombre }} {{ l.usuario?.apellido }}</td>
            <td><span class="badge" :class="l.tipo_preferencia === 'abonado' ? 'badge-green' : 'badge-blue'">{{ l.tipo_preferencia }}</span></td>
            <td style="font-size:12px;color:var(--text-muted)">{{ new Date(l.fecha_inscripcion).toLocaleDateString() }}</td>
            <td><span class="badge badge-yellow">{{ l.estado }}</span></td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal editar cupo -->
    <div class="modal-overlay" v-if="modalEditarCupo" @click.self="modalEditarCupo = false">
      <div class="modal card">
        <h3>✏️ Editar cupo</h3>
        <p style="font-size:13px;color:var(--text-muted);margin-bottom:16px">
          Cupo actual: <strong>{{ clase.cupo_maximo }}</strong> ·
          Inscriptos: <strong>{{ clase.cupo_maximo - clase.cupos_disponibles }}</strong>
        </p>
        <div class="input-group">
          <label>Nuevo cupo máximo</label>
          <input
            v-model.number="nuevoCupo"
            type="number"
            :min="clase.cupo_maximo - clase.cupos_disponibles"
            max="50"
          />
        </div>
        <div class="alert alert-warning" style="font-size:13px">
          No podés bajar el cupo por debajo de los inscriptos actuales ({{ clase.cupo_maximo - clase.cupos_disponibles }}).
        </div>
        <div style="display:flex;gap:10px;margin-top:12px">
          <button class="btn btn-primary" @click="guardarCupo" :disabled="guardandoCupo">
            {{ guardandoCupo ? 'Guardando...' : 'Guardar' }}
          </button>
          <button class="btn btn-outline" @click="modalEditarCupo = false">Cancelar</button>
        </div>
      </div>
    </div>

    <!-- Modal confirmar cancelar clase -->
    <div class="modal-overlay" v-if="confirmarCancelar" @click.self="confirmarCancelar = false">
      <div class="modal card">
        <h3>🚫 Cancelar clase</h3>
        <p style="color:var(--text-muted);margin:12px 0;font-size:14px">
          Vas a cancelar la clase de <strong>{{ clase.actividad }}</strong> del <strong>{{ formatFecha(clase.fecha) }}</strong>.
          Esto liberará todas las reservas activas. ¿Estás seguro?
        </p>
        <div style="display:flex;gap:10px">
          <button class="btn btn-danger" @click="cancelarClase" :disabled="cancelando">
            {{ cancelando ? 'Cancelando...' : 'Sí, cancelar clase' }}
          </button>
          <button class="btn btn-outline" @click="confirmarCancelar = false">Volver</button>
        </div>
      </div>
    </div>

    <!-- Modal confirmar cancelar reserva -->
    <div class="modal-overlay" v-if="confirmarCancelarReserva" @click.self="confirmarCancelarReserva = false">
      <div class="modal card">
        <h3>⚠️ Cancelar reserva</h3>
        <p style="color:var(--text-muted);margin:12px 0;font-size:14px">
          Recordá las políticas de cancelación:
        </p>
        <ul style="font-size:13px;color:var(--text-muted);margin-bottom:20px;padding-left:20px">
          <li v-if="miReserva?.tipo === 'abonado'">Abonado: crédito a favor si cancelás con 48hs de anticipación</li>
          <li v-else>No abonado: recuperás la seña si cancelás con 24hs de anticipación</li>
          <li>Fuera del plazo: perdés el dinero abonado</li>
        </ul>
        <div style="display:flex;gap:10px">
          <button class="btn btn-danger" @click="cancelarReserva" :disabled="cancelandoReserva">
            {{ cancelandoReserva ? 'Cancelando...' : 'Sí, cancelar reserva' }}
          </button>
          <button class="btn btn-outline" @click="confirmarCancelarReserva = false">Volver</button>
        </div>
      </div>
    </div>
  </div>

  <div v-else-if="loadingClase" class="loading-text">Cargando clase...</div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import api from '../api.js'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const clase = ref(null)
const loadingClase = ref(true)
const inscriptos = ref([])
const loadingInscriptos = ref(false)
const listaEspera = ref([])
const loadingEspera = ref(false)
const miReserva = ref(null)
const error = ref('')
const mensaje = ref('')
const reservando = ref(false)
const reservandoLoading = ref(false)
const confirmarCancelar = ref(false)
const cancelando = ref(false)
const modalEditarCupo = ref(false)
const nuevoCupo = ref(10)
const guardandoCupo = ref(false)
const confirmarCancelarReserva = ref(false)
const cancelandoReserva = ref(false)

function sportEmoji(nombre) {
  const map = { 'Fútbol': '⚽', 'Pádel': '🎾', 'Básquet': '🏀', 'Vóley': '🏐' }
  return map[nombre] || '🏃'
}

function formatFecha(fechaStr) {
  if (!fechaStr) return ''
  const [y, m, d] = fechaStr.split('-')
  return `${d}/${m}/${y}`
}

async function fetchClase() {
  loadingClase.value = true
  try {
    const { data } = await api.get(`/clases/${route.params.id}`)
    clase.value = data
  } catch (e) {
    error.value = 'No se pudo cargar la clase'
  } finally {
    if (data) nuevoCupo.value = data.cupo_maximo
    loadingClase.value = false
  }
}

async function fetchInscriptos() {
  if (!auth.isEmpleado && !auth.isAdmin) return
  loadingInscriptos.value = true
  try {
    const { data } = await api.get(`/clases/${route.params.id}/inscriptos`)
    inscriptos.value = data
  } finally {
    loadingInscriptos.value = false
  }
}

async function fetchListaEspera() {
  if (!auth.isAdmin) return
  loadingEspera.value = true
  try {
    const { data } = await api.get(`/clases/${route.params.id}/lista-espera`)
    listaEspera.value = data
  } finally {
    loadingEspera.value = false
  }
}

async function fetchMiReserva() {
  if (!auth.isCliente) return
  try {
    const { data } = await api.get('/reservas/')
    miReserva.value = data.find(r => r.clase_id === parseInt(route.params.id)) || null
  } catch {}
}

async function reservar(tipo) {
  reservandoLoading.value = true
  error.value = ''
  try {
    const { data } = await api.post('/reservas/', { clase_id: parseInt(route.params.id), tipo })
    if (data.en_espera) {
      mensaje.value = data.mensaje
    } else {
      mensaje.value = 'Reserva creada exitosamente'
      miReserva.value = data.reserva
    }
    reservando.value = false
    fetchClase()
  } catch (e) {
    error.value = e.response?.data?.error || 'Error al reservar'
  } finally {
    reservandoLoading.value = false
  }
}

async function guardarCupo() {
  guardandoCupo.value = true
  error.value = ''
  try {
    await api.put(`/clases/${route.params.id}`, { cupo_maximo: nuevoCupo.value })
    mensaje.value = 'Cupo actualizado correctamente'
    modalEditarCupo.value = false
    await fetchClase()
  } catch (e) {
    error.value = e.response?.data?.error || 'Error al actualizar cupo'
  } finally {
    guardandoCupo.value = false
  }
}

async function cancelarClase() {
  cancelando.value = true
  error.value = ''
  try {
    const { data } = await api.post(`/clases/${route.params.id}/cancelar`)
    mensaje.value = data.mensaje
    confirmarCancelar.value = false
    await fetchClase()
    await fetchInscriptos()
  } catch (e) {
    error.value = e.response?.data?.error || 'Error al cancelar'
  } finally {
    cancelando.value = false
  }
}

async function cancelarReserva() {
  cancelandoReserva.value = true
  error.value = ''
  try {
    const { data } = await api.post(`/reservas/${miReserva.value.id}/cancelar`)
    mensaje.value = data.mensaje || 'Reserva cancelada'
    confirmarCancelarReserva.value = false
    miReserva.value = null
    await fetchClase()
  } catch (e) {
    error.value = e.response?.data?.error || 'Error al cancelar reserva'
  } finally {
    cancelandoReserva.value = false
  }
}

onMounted(async () => {
  await fetchClase()
  await Promise.all([fetchMiReserva(), fetchInscriptos(), fetchListaEspera()])
})
</script>

<style scoped>
.back-link { font-size: 13px; color: var(--text-muted); transition: color 0.2s; }
.back-link:hover { color: var(--verde-claro); }
.dia-badge { display: inline-block; padding: 2px 8px; background: var(--dark-3); border-radius: 4px; font-size: 12px; color: var(--text-muted); }
.fecha-badge { color: var(--verde-claro); background: rgba(46,125,50,0.15); }
.stat-card { text-align: center; }
.stat-num { font-size: 36px; font-family: 'Bebas Neue', sans-serif; color: var(--verde-claro); display: block; }
.stat-label { font-size: 12px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.text-green { color: var(--success); font-weight: 600; }
.text-danger { color: var(--danger); font-weight: 600; }
.loading-text { text-align: center; padding: 60px; color: var(--text-muted); }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 200; }
.modal { max-width: 460px; width: 100%; }
.modal h3 { font-size: 22px; margin-bottom: 8px; }
</style>
