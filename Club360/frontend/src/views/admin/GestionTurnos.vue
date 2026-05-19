<template>
  <div>
    <div class="page-header" style="display:flex;align-items:center;justify-content:space-between">
      <div>
        <h2>GESTIÓN DE TURNOS</h2>
        <p>Cada turno genera clases automáticamente hasta fin de año (sin feriados)</p>
      </div>
      <button class="btn btn-primary" @click="abrirCrear">+ Nuevo Turno</button>
    </div>

    <div class="alert alert-error" v-if="error">{{ error }}</div>
    <div class="alert alert-success" v-if="mensaje">{{ mensaje }}</div>

    <!-- Filtros -->
    <div class="card" style="margin-bottom:20px;padding:16px">
      <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end">
        <div class="input-group" style="margin:0;flex:1;min-width:160px">
          <label>Actividad</label>
          <select v-model="filtroActividad" @change="fetchTurnos">
            <option value="">Todas</option>
            <option v-for="a in actividades" :key="a.id" :value="a.id">{{ a.nombre }}</option>
          </select>
        </div>
        <div class="input-group" style="margin:0">
          <label>Estado</label>
          <select v-model="filtroActivo" @change="fetchTurnos">
            <option value="true">Solo activos</option>
            <option value="false">Todos</option>
          </select>
        </div>
        <button class="btn btn-outline btn-sm" @click="filtroActividad=''; filtroActivo='true'; fetchTurnos()">Limpiar</button>
      </div>
    </div>

    <div v-if="loading" class="loading-text">Cargando...</div>

    <div v-else class="card" style="overflow:auto">
      <table>
        <thead>
          <tr>
            <th>Actividad</th><th>Día</th><th>Hora</th><th>Cupo</th>
            <th>Precio/clase</th><th>Clases generadas</th><th>Estado</th><th>Acciones</th>
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
              <span :class="t.activo ? 'badge badge-green' : 'badge badge-red'">
                {{ t.activo ? 'Activo' : 'Inactivo' }}
              </span>
            </td>
            <td>
              <div style="display:flex;gap:6px;flex-wrap:wrap">
                <button class="btn btn-outline btn-sm" @click="abrirEditar(t)">✏️ Editar </button>
                <!-- <button v-if="t.activo" class="btn btn-danger btn-sm" @click="confirmarDesactivar(t)">
                  🗑 Desactivar
                </button> -->
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="turnos.length === 0" style="text-align:center;padding:32px;color:var(--text-muted)">
        No hay turnos con esos filtros.
      </p>
    </div>

    <!-- Modal crear turno -->
    <div class="modal-overlay" v-if="formModal" @click.self="formModal = false">
      <div class="modal card">
        <h3>Nuevo Turno</h3>
        <p style="font-size:13px;color:var(--text-muted);margin-bottom:20px">
          Se generarán clases automáticamente para cada semana hasta el 31/12, saltando feriados nacionales.
        </p>

        <div class="input-group">
          <label>Actividad</label>
          <select v-model="form.actividad_id" @change="actualizarPrecio">
            <option value="">Seleccioná una actividad</option>
            <option v-for="a in actividades" :key="a.id" :value="a.id">{{ a.nombre }}</option>
          </select>
        </div>

        <div class="input-group">
          <label>Día de la semana</label>
          <select v-model="form.dia_semana">
            <option v-for="d in dias" :key="d.val" :value="d.val">{{ d.label }}</option>
          </select>
        </div>

        <div class="input-group">
          <label>Hora de inicio</label>
          <input v-model="form.hora_inicio" type="time" />
        </div>

        <div class="input-group">
          <label>Cupo máximo por clase</label>
          <input v-model.number="form.cupo_maximo" type="number" min="1" max="50" />
        </div>

        <div class="input-group">
          <label>Precio por clase ($)</label>
          <input v-model.number="form.precio_clase" type="number" min="0" />
          <p v-if="precioDefecto" style="font-size:11px;color:var(--text-muted);margin-top:4px">
            Precio base de {{ actividadSeleccionada?.nombre }}: ${{ precioDefecto?.toLocaleString() }}
          </p>
        </div>

        <!-- Preview del turno -->
        <div v-if="form.actividad_id && form.dia_semana !== ''" class="turno-preview">
          <p style="font-size:12px;color:var(--text-muted);margin-bottom:6px">Se crearán clases para:</p>
          <p style="font-size:14px;font-weight:600">
            {{ sportEmoji(actividadSeleccionada?.nombre) }} {{ actividadSeleccionada?.nombre }} —
            {{ dias.find(d=>d.val==form.dia_semana)?.label }}
            a las {{ form.hora_inicio }} hs
          </p>
          <p style="font-size:13px;color:var(--verde-claro)">
            ~{{ clasesEstimadas }} clases hasta el 31/12/{{ anoActual }}
          </p>
        </div>

        <div style="display:flex;gap:10px;margin-top:8px">
          <button class="btn btn-primary" @click="guardar" :disabled="guardando">
            {{ guardando ? 'Creando...' : 'Crear turno y generar clases' }}
          </button>
          <button class="btn btn-outline" @click="formModal = false">Cancelar</button>
        </div>
      </div>
    </div>

    <!-- Modal editar turno -->
    <div class="modal-overlay" v-if="editModal" @click.self="editModal = false">
      <div class="modal card">
        <h3>Editar Turno</h3>
        <p style="font-size:13px;color:var(--text-muted);margin-bottom:16px">
          {{ sportEmoji(editando?.actividad) }} {{ editando?.actividad }} ·
          {{ editando?.dia_semana_str }} {{ editando?.hora_inicio }} hs
        </p>
        <div class="alert alert-warning" style="font-size:13px">
          Solo se actualizarán las clases futuras <strong>sin inscriptos</strong>.
        </div>
        <div class="input-group" style="margin-top:16px">
          <label>Cupo máximo</label>
          <input v-model.number="editForm.cupo_maximo" type="number" min="1" />
        </div>
        <!-- <div class="input-group">
          <label>Precio por clase ($)</label>
          <input v-model.number="editForm.precio_clase" type="number" min="0" />
        </div> -->
        <div style="display:flex;gap:10px">
          <button class="btn btn-primary" @click="guardarEdicion" :disabled="guardando">
            {{ guardando ? 'Guardando...' : 'Guardar cambios' }}
          </button>
          <button class="btn btn-outline" @click="editModal = false">Cancelar</button>
        </div>
      </div>
    </div>

    <!-- Modal confirmar desactivar -->
    <div class="modal-overlay" v-if="desactivarModal" @click.self="desactivarModal = null">
      <div class="modal card">
        <h3>🗑 Desactivar turno</h3>
        <p style="color:var(--text-muted);font-size:14px;margin:12px 0">
          Vas a desactivar el turno de
          <strong>{{ desactivarModal?.actividad }} · {{ desactivarModal?.dia_semana_str }} {{ desactivarModal?.hora_inicio }} hs</strong>
        </p>
        <div class="alert alert-warning">
          Las clases futuras <strong>sin inscriptos</strong> se cancelarán automáticamente.
          Las clases con inscriptos quedarán activas.
        </div>
        <div style="display:flex;gap:10px;margin-top:16px">
          <button class="btn btn-danger" @click="ejecutarDesactivar" :disabled="desactivando">
            {{ desactivando ? 'Desactivando...' : 'Sí, desactivar' }}
          </button>
          <button class="btn btn-outline" @click="desactivarModal = null">Cancelar</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api.js'

const turnos = ref([])
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
  actividades.value.find(a => a.id == form.value.actividad_id)
)
const precioDefecto = computed(() => actividadSeleccionada.value?.precio_clase)

function actualizarPrecio() {
  if (actividadSeleccionada.value) {
    form.value.precio_clase = actividadSeleccionada.value.precio_clase
  }
}

// Estimar clases hasta fin de año (aprox, sin contar feriados exactos)
const clasesEstimadas = computed(() => {
  const hoy = new Date()
  const finAno = new Date(hoy.getFullYear(), 11, 31)
  const semanas = Math.floor((finAno - hoy) / (7 * 24 * 60 * 60 * 1000))
  return Math.max(0, semanas - 2) // restar aprox feriados
})

function abrirCrear() {
  form.value = { actividad_id: '', dia_semana: 0, hora_inicio: '08:00', cupo_maximo: 10, precio_clase: 0 }
  error.value = ''
  formModal.value = true
}

function abrirEditar(t) {
  editando.value = t
  editForm.value = { cupo_maximo: t.cupo_maximo, precio_clase: t.precio_clase }
  editModal.value = true
}

function confirmarDesactivar(t) {
  desactivarModal.value = t
}

async function guardar() {
  if (!form.value.actividad_id) { error.value = 'Seleccioná una actividad'; return }
  if (!form.value.precio_clase) { error.value = 'Ingresá el precio por clase'; return }
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

async function guardarEdicion() {
  guardando.value = true
  error.value = ''
  try {
    const { data } = await api.put(`/turnos/${editando.value.id}`, editForm.value)
    mensaje.value = `Turno actualizado. ${data.clases_actualizadas} clase(s) futuras actualizadas.`
    editModal.value = false
    await fetchTurnos()
  } catch (e) {
    error.value = e.response?.data?.error || 'Error al editar'
  } finally {
    guardando.value = false
  }
}

async function ejecutarDesactivar() {
  desactivando.value = true
  try {
    const { data } = await api.post(`/turnos/${desactivarModal.value.id}/desactivar`)
    mensaje.value = data.mensaje
    if (data.clases_con_inscriptos > 0) {
      mensaje.value += ` (${data.clases_con_inscriptos} clase(s) con inscriptos quedan activas)`
    }
    desactivarModal.value = null
    await fetchTurnos()
  } catch (e) {
    error.value = e.response?.data?.error || 'Error al desactivar'
  } finally {
    desactivando.value = false
  }
}

async function fetchTurnos() {
  loading.value = true
  try {
    const params = { activos: filtroActivo.value }
    if (filtroActividad.value) params.actividad_id = filtroActividad.value
    const { data } = await api.get('/turnos/', { params })
    turnos.value = data
  } finally {
    loading.value = false
  }
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
</style>
