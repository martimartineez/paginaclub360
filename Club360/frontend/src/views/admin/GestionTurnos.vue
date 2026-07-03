<template>
  <div>
    <div class="page-header" style="display:flex;align-items:center;justify-content:space-between">
      <div>
        <h2>GESTIÓN DE TURNOS</h2>
        <p>Cada turno genera clases automáticamente hasta fin de año (sin incluir feriados) </p>
      </div>
      <button class="btn btn-primary" @click="abrirCrear">+ Nuevo Turno</button>
    </div>

    <div class="alert alert-error" v-if="error">{{ error }}</div>
    <div class="alert alert-success" v-if="mensaje">{{ mensaje }}</div>

    <div class="card" style="margin-bottom:20px;padding:16px">
      <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end">
        <div class="input-group" style="margin:0;flex:1;min-width:160px">
          <label>Actividad</label>
          <select v-model="filtroActividad" @change="fetchTurnos">
            <option value="">Todas</option>
            <option v-for="a in actividades" :key="a.id" :value="a.id">{{ a.nombre }}</option>
          </select>
        </div>
        <!-- <div class="input-group" style="margin:0">
          <label>Estado</label>
          <select v-model="filtroActivo" @change="fetchTurnos">
            <option value="true">Solo activos</option>
            <option value="false">Todos</option>
          </select>
        </div> -->
        <button class="btn btn-outline btn-sm" @click="filtroActividad=''; filtroActivo='true'; fetchTurnos()">Limpiar</button>
      </div>
    </div>

    <div v-if="loading" class="loading-text">Cargando...</div>

    <div v-else class="card" style="overflow:auto">
      <table>
        <thead>
          <tr>
            <th>Actividad</th><th>Día</th><th>Hora</th><th>Cupo</th>
            <th>Precio/clase</th><th>Clases generadas</th><th>Acciones</th>
            <!-- <th>Estado</th> -->
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in turnos" :key="t.id" :class="{ 'row-inactivo': !t.activo }">
            <td>{{ sportEmoji(t.actividad) }} {{ t.actividad }}</td>
            <td>{{ t.dia_semana_str }}</td>
            <td>{{ t.hora_inicio }} hs</td>
            <td>{{ t.cupo_maximo }}</td>
            <td>${{ t.precio_clase?.toLocaleString() }}</td>
            <td>
              <span class="badge badge-blue">{{ t.total_clases }} clases</span>
            </td>
            <td>
              <button
                v-if="t.activo"
                class="btn btn-danger btn-sm"
                @click="confirmarCancelarTurno(t)"
              >
                Cancelar turno
              </button>
              <span v-else class="badge badge-red">Cancelado</span>
            </td>
            <!-- <td>
              <span :class="t.activo ? 'badge badge-green' : 'badge badge-red'">
                {{ t.activo ? 'Activo' : 'Inactivo' }}
              </span>
            </td> -->
          </tr>
        </tbody>
      </table>
      <p v-if="turnos.length === 0" style="text-align:center;padding:32px;color:var(--text-muted)">
        No hay turnos disponibles.
      </p>
    </div>

    <div class="card historial-card">
      <div class="historial-header">
        <div>
          <h3>Historial de cancelaciones</h3>
          <p>Turnos cancelados. Al reactivar se generan clases nuevas desde cero.</p>
        </div>
      </div>

      <div v-if="historialCancelados.length === 0" class="empty-historial">
        No hay turnos cancelados.
      </div>

      <div v-else style="overflow:auto">
        <table>
          <thead>
            <tr>
              <th>Actividad</th><th>Dia</th><th>Hora</th><th>Cancelado</th><th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="t in historialCancelados" :key="`hist-${t.id}`">
              <td>{{ sportEmoji(t.actividad) }} {{ t.actividad }}</td>
              <td>{{ t.dia_semana_str }}</td>
              <td>{{ t.hora_inicio }} hs</td>
              <td>{{ formatFechaHora(t.cancelado_fecha) }}</td>
              <td>
                <button
                  class="btn btn-primary btn-sm"
                  @click="reactivarTurno(t)"
                  :disabled="reactivandoId === t.id"
                >
                  {{ reactivandoId === t.id ? 'Reactivando...' : 'Reactivar' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="modal-overlay" v-if="formModal" @click.self="formModal = false">
      <div class="modal card">
        <h3>Nuevo Turno</h3>
        <p style="font-size:13px;color:var(--text-muted);margin-bottom:20px">
          Se generarán clases automáticamente para cada semana hasta el 31/12, saltando feriados nacionales.
        </p>

        <div class="alert alert-error" v-if="error" style="margin-bottom: 16px;">
          {{ error }}
        </div>

        <form @submit.prevent="guardar">
          <div class="input-group">
            <label>Actividad</label>
            <select v-model="form.actividad_id" @change="actualizarPrecio" required>
              <option value="">Seleccioná una actividad</option>
              <option v-for="a in actividades" :key="a.id" :value="a.id">{{ a.nombre }}</option>
            </select>
            <p v-if="errorActividad" class="field-error">{{ errorActividad }}</p>
          </div>

          <div class="input-group">
            <label>Precio por clase ($)</label>
            <input v-model.number="form.precio_clase" type="number" min="0" required />
            <p v-if="precioDefecto" style="font-size:11px;color:var(--text-muted);margin-top:4px">
              Precio base de {{ actividadSeleccionada?.nombre }}: ${{ precioDefecto?.toLocaleString() }}
            </p>
            <p v-if="errorPrecio" class="field-error">{{ errorPrecio }}</p>
          </div>

          <div class="input-group">
            <label>Día de la semana</label>
            <select v-model="form.dia_semana" required>
              <option v-for="d in dias" :key="d.val" :value="d.val">{{ d.label }}</option>
            </select>
          </div>

          <div class="input-group">
            <label>Hora de inicio (08:00 a 22:00)</label>
            <input v-model="form.hora_inicio" type="time" min="08:00" max="22:00" required />
            <p v-if="errorHora" class="field-error">{{ errorHora }}</p>
          </div>
          

          <div class="input-group">
            <label>Cupo máximo por clase</label>
            <input v-model.number="form.cupo_maximo" type="number" min="0" max="50" required />
            <p v-if="errorCupo" class="field-error">{{ errorCupo }}</p>
          </div>

          <div v-if="form.actividad_id && form.dia_semana !== ''" class="turno-preview">
            <p style="font-size:12px;color:var(--text-muted);margin-bottom:6px">Se crearán clases para:</p>
            <p style="font-size:14px;font-weight:600">
              {{ sportEmoji(actividadSeleccionada?.nombre) }} {{ actividadSeleccionada?.nombre }} —
              {{ dias.find(d=>d.val===form.dia_semana)?.label }}
              a las {{ form.hora_inicio }} hs
            </p>
            <!-- <p style="font-size:13px;color:var(--verde-claro)">
              ~{{ clasesEstimadas }} clases hasta el 31/12/{{ anoActual }}
            </p> -->
          </div>

          <div style="display:flex;gap:10px;margin-top:8px">
            <button class="btn btn-primary" type="submit" :disabled="guardando || !isFormValido ">
              {{ guardando ? 'Creando...' : 'Crear turno y generar clases' }}
            </button>
            <button class="btn btn-outline" type="button" @click="formModal = false">Cancelar</button>
          </div>
        </form>
      </div>
    </div>

    <div class="modal-overlay" v-if="editModal" @click.self="editModal = false">
      <div class="modal card">
        </div>
    </div>

    <div class="modal-overlay" v-if="desactivarModal" @click.self="desactivarModal = null">
      <div class="modal card">
        <h3>Cancelar turno</h3>
        <p style="color:var(--text-muted);margin:12px 0;font-size:14px">
          Vas a cancelar el turno de <strong>{{ desactivarModal.actividad }}</strong>
          los <strong>{{ desactivarModal.dia_semana_str }}</strong> a las
          <strong>{{ desactivarModal.hora_inicio }} hs</strong>.
        </p>
        <p style="color:var(--text-muted);margin:12px 0;font-size:14px">
          Se cancelaran todas sus clases futuras y se procesaran devoluciones de seña,
          descuentos en abonos pendientes o creditos segun corresponda.
        </p>
        <div style="display:flex;gap:10px">
          <button class="btn btn-danger" @click="cancelarTurno" :disabled="desactivando">
            {{ desactivando ? 'Cancelando...' : 'Si, cancelar turno' }}
          </button>
          <button class="btn btn-outline" @click="desactivarModal = null">Volver</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import api from '../../api.js'

const turnos = ref([])
const historialCancelados = ref([])
const actividades = ref([])
const loading = ref(false)
const error = ref(''), mensaje = ref('')
const formModal = ref(false)
const editModal = ref(false)
const editando = ref(null)
const editForm = ref({ cupo_maximo: 10, precio_clase: 0 })
const guardando = ref(false)
const desactivarModal = ref(null)
const desactivando = ref(false)
const reactivandoId = ref(null)
const filtroActividad = ref('')
const filtroActivo = ref('true')

const form = ref({
  actividad_id: '',
  dia_semana: 0,
  hora_inicio: '08:00',
  cupo_maximo: 10,
  precio_clase: 0
})

const dias = [
  { val: 0, label: 'Lunes' }, { val: 1, label: 'Martes' },
  { val: 2, label: 'Miércoles' }, { val: 3, label: 'Jueves' },
  { val: 4, label: 'Viernes' }, { val: 5, label: 'Sábado' }
]

const anoActual = new Date().getFullYear()

function sportEmoji(n) {
  return { 'Fútbol': '⚽', 'Pádel': '🎾', 'Básquet': '🏀', 'Vóley': '🏐' }[n] || '🏃'
}

const actividadSeleccionada = computed(() =>
  actividades.value.find(a => a.id === form.value.actividad_id)
)
const precioDefecto = computed(() => actividadSeleccionada.value?.precio_clase)

function actualizarPrecio() {
  if (actividadSeleccionada.value) {
    form.value.precio_clase = actividadSeleccionada.value.precio_clase
  }
}

const clasesEstimadas = computed(() => {
  const hoy = new Date()
  const finAno = new Date(hoy.getFullYear(), 11, 31)
  const semanas = Math.floor((finAno - hoy) / (7 * 24 * 60 * 60 * 1000))
  return Math.max(0, semanas - 2)
})

// --- VALIDACIONES EN TIEMPO REAL (COMPUTED) ---

const errorActividad = computed(() => {
  if (form.value.actividad_id === '') return 'Debés seleccionar una actividad'
  return ''
})

const errorPrecio = computed(() => {
  if (form.value.precio_clase === '' || form.value.precio_clase === null) return 'El precio es requerido'
  if (form.value.precio_clase < 0) return 'El precio no puede ser menor a $0'
  return ''
})

const errorHora = computed(() => {
  if (!form.value.hora_inicio) return 'El horario es requerido'
  
  // Extraer las horas y minutos para convertirlos a un número comparable (ej: 08:30 -> 8.5)
  const [h, m] = form.value.hora_inicio.split(':').map(Number)
  const timeNum = h + (m / 60)
  
  // Limitar estrictamente entre las 08:00 y las 22:00
  if (timeNum < 8 || timeNum > 22) {
    return 'El horario de la clase debe estar entre las 08:00 y las 22:00 hs'
  }
  return ''
})

const errorCupo = computed(() => {
  if (form.value.cupo_maximo === '' || form.value.cupo_maximo === null) return 'El cupo es requerido'
  if (form.value.cupo_maximo < 0) return 'El cupo no puede ser un número negativo'
  return ''
})

// Validación global para el botón
const isFormValido = computed(() => {
  return (
    form.value.actividad_id !== '' &&
    form.value.precio_clase >= 0 &&
    form.value.hora_inicio !== '' &&
    form.value.cupo_maximo >= 0 &&
    !errorActividad.value &&
    !errorPrecio.value &&
    !errorHora.value &&
    !errorCupo.value
  )
})

// watch(form, () => {
//   error.value = ''
// }, { deep: true })


// --- FUNCIONES ---

function abrirCrear() {
  form.value = { actividad_id: '', dia_semana: 0, hora_inicio: '08:00', cupo_maximo: 10, precio_clase: 0 }
  error.value = ''
  formModal.value = true
}

// ... Las funciones abrirEditar, confirmarDesactivar y guardarEdicion se mantienen igual ...

async function guardar() {
  // Como el botón ya está bloqueado, si entra acá es porque el form está válido
  guardando.value = true
  error.value = ''
  try {
    const { data } = await api.post('/turnos/', form.value)
    if (data.reactivado) {
      mensaje.value = `♻️ ${data.mensaje}`
    } else {
      mensaje.value = `✅ ${data.mensaje}`
    }
    formModal.value = false
    await fetchTurnos()
  } catch (e) {
    error.value = e.response?.data?.error || 'Error al crear turno'
  } finally {
    guardando.value = false
  }
}

// ... Las demás funciones se mantienen igual ...

function confirmarCancelarTurno(turno) {
  error.value = ''
  mensaje.value = ''
  desactivarModal.value = turno
}

async function cancelarTurno() {
  if (!desactivarModal.value) return

  desactivando.value = true
  error.value = ''
  mensaje.value = ''
  try {
    const { data } = await api.post(`/turnos/${desactivarModal.value.id}/cancelar`)
    mensaje.value = data.mensaje || 'Turno cancelado correctamente'
    desactivarModal.value = null
    await fetchTurnos()
  } catch (e) {
    error.value = e.response?.data?.error || 'Error al cancelar turno'
  } finally {
    desactivando.value = false
  }
}

async function reactivarTurno(turno) {
  reactivandoId.value = turno.id
  error.value = ''
  mensaje.value = ''
  try {
    const { data } = await api.post(`/turnos/${turno.id}/reactivar`)
    mensaje.value = data.mensaje || 'Turno reactivado correctamente'
    await fetchTurnos()
  } catch (e) {
    error.value = e.response?.data?.error || 'Error al reactivar turno'
  } finally {
    reactivandoId.value = null
  }
}

async function fetchTurnos() {
  loading.value = true
  try {
    const params = { activos: filtroActivo.value }
    if (filtroActividad.value) params.actividad_id = filtroActividad.value
    const activosParams = { ...params, activos: 'true' }
    const historialParams = { ...params, activos: 'false' }
    const [activosRes, historialRes] = await Promise.all([
      api.get('/turnos/', { params: activosParams }),
      api.get('/turnos/', { params: historialParams })
    ])
    turnos.value = activosRes.data
    historialCancelados.value = historialRes.data.filter(t => !t.activo)
  } finally {
    loading.value = false
  }
}

function formatFechaHora(valor) {
  if (!valor) return '-'
  return new Date(valor).toLocaleString()
}

onMounted(async () => {
  const { data } = await api.get('/actividades/')
  actividades.value = data
  fetchTurnos()
})
</script>

<style scoped>
.loading-text { text-align:center;padding:40px;color:var(--text-muted); }
.row-inactivo td { opacity:0.5; }
.historial-card { margin-top:24px; }
.historial-header { display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:16px; }
.historial-header h3 { font-size:20px;margin-bottom:4px; }
.historial-header p { color:var(--text-muted);font-size:13px; }
.empty-historial { padding:18px;text-align:center;color:var(--text-muted);background:var(--dark-3);border-radius:8px; }
.modal-overlay { position:fixed;inset:0;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;z-index:200; }
.modal { max-width:520px;width:100%; }
.modal h3 { font-size:22px;margin-bottom:16px; }
.turno-preview {
  background:rgba(46,125,50,0.08);
  border:1px solid var(--verde);
  border-radius:8px;
  padding:12px 16px;
  margin-bottom:16px;
}
.field-error { font-size: 12px; color: var(--danger); margin-top: 4px; }
</style>
