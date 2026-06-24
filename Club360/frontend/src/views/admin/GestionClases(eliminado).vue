<template>
  <div>
    <div class="page-header" style="display:flex;align-items:center;justify-content:space-between">
      <div>
        <h2>GESTIÓN DE CLASES</h2>
        <p>Crear y administrar clases por fecha</p>
      </div>
      <button class="btn btn-primary" @click="abrirCrear">+ Nueva Clase</button>
    </div>

    <div class="alert alert-error" v-if="error">{{ error }}</div>
    <div class="alert alert-success" v-if="mensaje">{{ mensaje }}</div>

    <!-- Filtros -->
    <div class="card" style="margin-bottom:20px;padding:16px">
      <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end">
        <div class="input-group" style="margin:0;flex:1;min-width:160px">
          <label>Actividad</label>
          <select v-model="filtroActividad" @change="fetchClases">
            <option value="">Todas</option>
            <option v-for="a in actividades" :key="a.id" :value="a.id">{{ a.nombre }}</option>
          </select>
        </div>
        <div class="input-group" style="margin:0">
          <label>Mostrar canceladas</label>
          <select v-model="mostrarCanceladas" @change="fetchClases">
            <option :value="false">Solo activas</option>
            <option :value="true">Todas</option>
          </select>
        </div>
        <button class="btn btn-outline btn-sm" @click="filtroActividad=''; mostrarCanceladas=false; fetchClases()">Limpiar</button>
      </div>
    </div>

    <div v-if="loading" class="loading-text">Cargando...</div>

    <div v-else class="card" style="overflow:auto">
      <table>
        <thead>
          <tr>
            <th>Actividad</th><th>Fecha</th><th>Día</th><th>Hora</th>
            <th>Cupo Máx.</th><th>Disponibles</th><th>Estado</th><th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in clases" :key="c.id" :class="{ 'row-cancelada': c.cancelada }">
            <td>{{ sportEmoji(c.actividad) }} {{ c.actividad }}</td>
            <td>{{ formatFecha(c.fecha) }}</td>
            <td>{{ c.dia_semana }}</td>
            <td>{{ c.hora_inicio }} hs</td>
            <td>{{ c.cupo_maximo }}</td>
            <td>
              <span :class="c.cupos_disponibles === 0 ? 'badge badge-red' : 'badge badge-green'">
                {{ c.cupos_disponibles }}
              </span>
            </td>
            <td>
              <span v-if="c.cancelada" class="badge badge-red">Cancelada</span>
              <span v-else class="badge badge-green">Activa</span>
            </td>
            <td>
              <router-link :to="`/clases/${c.id}`" class="btn btn-outline btn-sm">🔍 Detalle</router-link>
              <button
                v-if="!c.cancelada"
                class="btn btn-danger btn-sm"
                style="margin-left:8px"
                @click="cancelarClase(c)"
                :disabled="cancelandoId === c.id"
              >
                {{ cancelandoId === c.id ? 'Cancelando...' : 'Cancelar clase' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="clases.length === 0" style="text-align:center;padding:32px;color:var(--text-muted)">
        No hay clases con esos filtros.
      </p>
    </div>

    <!-- Modal crear -->
    <div class="modal-overlay" v-if="formModal" @click.self="formModal = false">
      <div class="modal card">
        <h3>Nueva Clase</h3>
        <div class="input-group">
          <label>Actividad</label>
          <select v-model="form.actividad_id">
            <option value="">Seleccioná una actividad</option>
            <option v-for="a in actividades" :key="a.id" :value="a.id">{{ a.nombre }} — ${{ a.precio_clase?.toLocaleString() }}/clase</option>
          </select>
        </div>
        <div class="input-group">
          <label>Fecha exacta de la clase</label>
          <input v-model="form.fecha" type="date" :min="hoy" />
        </div>
        <div class="input-group">
          <label>Hora de inicio</label>
          <input v-model="form.hora_inicio" type="time" />
        </div>
        <div class="input-group">
          <label>Cupo máximo</label>
          <input v-model.number="form.cupo_maximo" type="number" min="1" max="50" />
        </div>
        <p style="font-size:12px;color:var(--text-muted);margin-bottom:16px">
          ⚠️ Cada clase es una instancia única (fecha + hora + actividad). Para clases recurrentes, creá una por semana.
        </p>
        <div style="display:flex;gap:10px">
          <button class="btn btn-primary" @click="guardar" :disabled="guardando">
            {{ guardando ? 'Guardando...' : 'Crear clase' }}
          </button>
          <button class="btn btn-outline" @click="formModal = false">Cancelar</button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../../api.js'

const clases = ref([])
const actividades = ref([])
const loading = ref(false)
const error = ref(''), mensaje = ref('')
const formModal = ref(false)

const guardando = ref(false)
const cancelandoId = ref(null)
const filtroActividad = ref('')
const mostrarCanceladas = ref(false)
const form = ref({ actividad_id: '', fecha: '', hora_inicio: '08:00', cupo_maximo: 10 })
const hoy = new Date().toISOString().split('T')[0]

function sportEmoji(n) {
  return { 'Fútbol': '⚽', 'Pádel': '🎾', 'Básquet': '🏀', 'Vóley': '🏐' }[n] || '🏃'
}
function formatFecha(fechaStr) {
  if (!fechaStr) return ''
  const [y, m, d] = fechaStr.split('-')
  return `${d}/${m}/${y}`
}

function abrirCrear() {
  form.value = { actividad_id: '', fecha: hoy, hora_inicio: '08:00', cupo_maximo: 10 }
  formModal.value = true
}

async function guardar() {
  if (!form.value.actividad_id || !form.value.fecha) {
    error.value = 'Completá todos los campos requeridos'
    return
  }
  guardando.value = true
  error.value = ''
  try {
    const { data } = await api.post('/clases/', form.value)
    if (data.reactivada) {
      mensaje.value = '♻️ ' + data.mensaje
    } else {
      mensaje.value = 'Clase creada correctamente'
    }
    formModal.value = false
    await fetchClases()
  } catch (e) {
    error.value = e.response?.data?.error || 'Error al crear clase'
  } finally {
    guardando.value = false
  }
}

async function cancelarClase(clase) {
  const confirmado = window.confirm(
    `Vas a cancelar la clase de ${clase.actividad} del ${formatFecha(clase.fecha)}. ` +
    'Se procesaran devoluciones de senia, descuentos en abonos pendientes o creditos segun corresponda. Continuar?'
  )
  if (!confirmado) return

  cancelandoId.value = clase.id
  error.value = ''
  mensaje.value = ''
  try {
    const { data } = await api.post(`/clases/${clase.id}/cancelar`)
    mensaje.value = data.mensaje || 'Clase cancelada correctamente'
    await fetchClases()
  } catch (e) {
    error.value = e.response?.data?.error || 'Error al cancelar clase'
  } finally {
    cancelandoId.value = null
  }
}

async function fetchClases() {
  loading.value = true
  const params = { solo_activas: !mostrarCanceladas.value }
  if (filtroActividad.value) params.actividad_id = filtroActividad.value
  const { data } = await api.get('/clases/', { params })
  clases.value = data
  loading.value = false
}

onMounted(async () => {
  const { data } = await api.get('/actividades/')
  actividades.value = data
  fetchClases()
})
</script>

<style scoped>
.loading-text { text-align: center; padding: 40px; color: var(--text-muted); }
.row-cancelada td { opacity: 0.5; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 200; }
.modal { max-width: 480px; width: 100%; }
.modal h3 { font-size: 22px; margin-bottom: 20px; }
</style>
