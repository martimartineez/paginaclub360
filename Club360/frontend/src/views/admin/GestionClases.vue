<template>
  <div>
    <div class="page-header" style="display:flex;align-items:center;justify-content:space-between">
      <div>
        <h2>GESTIÓN DE CLASES</h2>
        <p>Crear, editar y ver inscriptos de cada clase</p>
      </div>
      <button class="btn btn-primary" @click="abrirCrear">+ Nueva Clase</button>
    </div>

    <div class="alert alert-error" v-if="error">{{ error }}</div>
    <div class="alert alert-success" v-if="mensaje">{{ mensaje }}</div>

    <div v-if="loading" class="loading-text">Cargando...</div>

    <div v-else class="card" style="overflow:auto">
      <table>
        <thead>
          <tr>
            <th>Actividad</th><th>Día</th><th>Hora</th><th>Cupo Máx.</th><th>Disponibles</th><th>Estado</th><th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in clases" :key="c.id">
            <td>{{ sportEmoji(c.actividad) }} {{ c.actividad }}</td>
            <td style="text-transform:capitalize">{{ c.dia_semana }}</td>
            <td>{{ c.hora_inicio }} hs</td>
            <td>{{ c.cupo_maximo }}</td>
            <td>
              <span :class="c.cupos_disponibles === 0 ? 'badge badge-red' : 'badge badge-green'">
                {{ c.cupos_disponibles }}
              </span>
            </td>
            <td>
              <span :class="c.activa ? 'badge badge-green' : 'badge badge-red'">
                {{ c.activa ? 'Activa' : 'Inactiva' }}
              </span>
            </td>
            <td>
              <div style="display:flex;gap:6px">
                <button class="btn btn-outline btn-sm" @click="verInscriptos(c)">👥 Inscriptos</button>
                <button class="btn btn-outline btn-sm" @click="verListaEspera(c)">⏳ Espera</button>
                <button class="btn btn-secondary btn-sm" @click="abrirEditar(c)">✏️</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal crear/editar -->
    <div class="modal-overlay" v-if="formModal" @click.self="formModal = null">
      <div class="modal card">
        <h3>{{ editando ? 'Editar Clase' : 'Nueva Clase' }}</h3>
        <div class="input-group">
          <label>Actividad</label>
          <select v-model="form.actividad_id" :disabled="editando">
            <option v-for="a in actividades" :key="a.id" :value="a.id">{{ a.nombre }}</option>
          </select>
        </div>
        <div class="input-group" v-if="!editando">
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
          <label>Cupo máximo</label>
          <input v-model.number="form.cupo_maximo" type="number" min="1" />
        </div>
        <div style="display:flex;gap:10px">
          <button class="btn btn-primary" @click="guardar" :disabled="guardando">
            {{ guardando ? 'Guardando...' : 'Guardar' }}
          </button>
          <button class="btn btn-outline" @click="formModal = null">Cancelar</button>
        </div>
      </div>
    </div>

    <!-- Modal inscriptos -->
    <div class="modal-overlay" v-if="inscriptosModal" @click.self="inscriptosModal = null">
      <div class="modal card" style="max-width:600px">
        <h3>👥 Inscriptos — {{ inscriptosModal.actividad }} {{ inscriptosModal.dia_semana }}</h3>
        <div v-if="loadingInscriptos" style="padding:20px;text-align:center;color:var(--text-muted)">Cargando...</div>
        <div v-else-if="inscriptos.length === 0" style="padding:20px;text-align:center;color:var(--text-muted)">Sin inscriptos</div>
        <table v-else style="margin-top:16px">
          <thead><tr><th>Cliente</th><th>Tipo</th><th>Pagado</th></tr></thead>
          <tbody>
            <tr v-for="r in inscriptos" :key="r.id">
              <td>{{ r.usuario?.nombre }} {{ r.usuario?.apellido }}</td>
              <td><span class="badge" :class="r.tipo === 'abonado' ? 'badge-green' : 'badge-blue'">{{ r.tipo }}</span></td>
              <td>${{ r.monto_pagado?.toLocaleString() }}</td>
            </tr>
          </tbody>
        </table>
        <button class="btn btn-outline btn-sm" style="margin-top:16px" @click="inscriptosModal = null">Cerrar</button>
      </div>
    </div>

    <!-- Modal lista espera -->
    <div class="modal-overlay" v-if="esperaModal" @click.self="esperaModal = null">
      <div class="modal card" style="max-width:600px">
        <h3>⏳ Lista de Espera — {{ esperaModal.actividad }} {{ esperaModal.dia_semana }}</h3>
        <div v-if="loadingEspera" style="padding:20px;text-align:center;color:var(--text-muted)">Cargando...</div>
        <div v-else-if="listaEspera.length === 0" style="padding:20px;text-align:center;color:var(--text-muted)">Lista vacía</div>
        <div v-else>
          <div v-if="listaEspera.length >= 10" class="alert alert-warning">⚠️ Alta demanda: {{ listaEspera.length }} personas en espera</div>
          <table style="margin-top:16px">
            <thead><tr><th>#</th><th>Cliente</th><th>Preferencia</th><th>Fecha</th></tr></thead>
            <tbody>
              <tr v-for="(l, i) in listaEspera" :key="l.id">
                <td>{{ i + 1 }}</td>
                <td>{{ l.usuario?.nombre }} {{ l.usuario?.apellido }}</td>
                <td><span class="badge" :class="l.tipo_preferencia === 'abonado' ? 'badge-green' : 'badge-blue'">{{ l.tipo_preferencia }}</span></td>
                <td style="font-size:12px;color:var(--text-muted)">{{ new Date(l.fecha_inscripcion).toLocaleDateString() }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <button class="btn btn-outline btn-sm" style="margin-top:16px" @click="esperaModal = null">Cerrar</button>
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
const editando = ref(null)
const guardando = ref(false)
const form = ref({ actividad_id: '', dia_semana: 'lunes', hora_inicio: '08:00', cupo_maximo: 10 })
const inscriptosModal = ref(null), inscriptos = ref([]), loadingInscriptos = ref(false)
const esperaModal = ref(null), listaEspera = ref([]), loadingEspera = ref(false)

const dias = [
  { val: 'lunes', label: 'Lunes' }, { val: 'martes', label: 'Martes' },
  { val: 'miercoles', label: 'Miércoles' }, { val: 'jueves', label: 'Jueves' },
  { val: 'viernes', label: 'Viernes' }, { val: 'sabado', label: 'Sábado' }
]

function sportEmoji(nombre) {
  const map = { 'Fútbol': '⚽', 'Pádel': '🎾', 'Básquet': '🏀', 'Vóley': '🏐' }
  return map[nombre] || '🏃'
}

function abrirCrear() {
  editando.value = null
  form.value = { actividad_id: actividades.value[0]?.id, dia_semana: 'lunes', hora_inicio: '08:00', cupo_maximo: 10 }
  formModal.value = true
}

function abrirEditar(c) {
  editando.value = c
  form.value = { actividad_id: c.actividad_id, hora_inicio: c.hora_inicio, cupo_maximo: c.cupo_maximo }
  formModal.value = true
}

async function guardar() {
  guardando.value = true
  try {
    if (editando.value) {
      await api.put(`/clases/${editando.value.id}`, form.value)
      mensaje.value = 'Clase actualizada'
    } else {
      await api.post('/clases/', form.value)
      mensaje.value = 'Clase creada'
    }
    formModal.value = false
    await fetchClases()
  } catch (e) {
    error.value = e.response?.data?.error || 'Error'
  } finally {
    guardando.value = false
  }
}

async function verInscriptos(c) {
  inscriptosModal.value = c
  loadingInscriptos.value = true
  const { data } = await api.get(`/clases/${c.id}/inscriptos`)
  inscriptos.value = data
  loadingInscriptos.value = false
}

async function verListaEspera(c) {
  esperaModal.value = c
  loadingEspera.value = true
  const { data } = await api.get(`/clases/${c.id}/lista-espera`)
  listaEspera.value = data
  loadingEspera.value = false
}

async function fetchClases() {
  loading.value = true
  const { data } = await api.get('/clases/')
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
.loading-text { text-align:center; padding:40px; color:var(--text-muted); }
.modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.7); display:flex; align-items:center; justify-content:center; z-index:200; }
.modal { max-width:480px; width:100%; }
.modal h3 { font-size:22px; margin-bottom:20px; }
</style>
