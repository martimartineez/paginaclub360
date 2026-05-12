<template>
  <div>
    <div class="page-header" style="display:flex;align-items:center;justify-content:space-between">
      <div>
        <h2>ACTIVIDADES</h2>
        <p>Gestión de actividades y precios</p>
      </div>
      <button class="btn btn-primary" @click="abrirCrear">+ Nueva Actividad</button>
    </div>

    <div class="alert alert-success" v-if="msg">{{ msg }}</div>
    <div class="alert alert-error" v-if="err">{{ err }}</div>

    <div class="grid-2">
      <div v-for="a in actividades" :key="a.id" class="card actividad-card">
        <div class="actividad-header">
          <span class="sport-emoji">{{ sportEmoji(a.nombre) }}</span>
          <div>
            <h3>{{ a.nombre }}</h3>
            <span :class="a.activa ? 'badge badge-green' : 'badge badge-red'">{{ a.activa ? 'Activa' : 'Inactiva' }}</span>
          </div>
          <div class="precio">
            <span class="precio-num">${{ a.precio_clase?.toLocaleString() }}</span>
            <span style="font-size:12px;color:var(--text-muted)">/clase</span>
          </div>
        </div>
        <p style="font-size:14px;color:var(--text-muted);margin:10px 0">{{ a.descripcion }}</p>
        <button class="btn btn-outline btn-sm" @click="abrirEditar(a)">✏️ Editar</button>
      </div>
    </div>

    <div class="modal-overlay" v-if="formModal" @click.self="formModal = false">
      <div class="modal card">
        <h3>{{ editando ? 'Editar Actividad' : 'Nueva Actividad' }}</h3>
        <div class="input-group"><label>Nombre</label><input v-model="form.nombre" /></div>
        <div class="input-group"><label>Descripción</label><input v-model="form.descripcion" /></div>
        <div class="input-group"><label>Precio por clase ($)</label><input v-model.number="form.precio_clase" type="number" /></div>
        <div v-if="editando" class="input-group">
          <label>Estado</label>
          <select v-model="form.activa">
            <option :value="true">Activa</option>
            <option :value="false">Inactiva</option>
          </select>
        </div>
        <div style="display:flex;gap:10px">
          <button class="btn btn-primary" @click="guardar" :disabled="guardando">Guardar</button>
          <button class="btn btn-outline" @click="formModal = false">Cancelar</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../../api.js'

const actividades = ref([])
const formModal = ref(false)
const editando = ref(null)
const form = ref({ nombre:'', descripcion:'', precio_clase:0, activa:true })
const guardando = ref(false), msg = ref(''), err = ref('')

function sportEmoji(n) {
  const m = { 'Fútbol':'⚽','Pádel':'🎾','Básquet':'🏀','Vóley':'🏐' }
  return m[n] || '🏃'
}

function abrirCrear() { editando.value = null; form.value = { nombre:'', descripcion:'', precio_clase:0, activa:true }; formModal.value = true }
function abrirEditar(a) { editando.value = a; form.value = { ...a }; formModal.value = true }

async function guardar() {
  guardando.value = true
  err.value = ''
  try {
    if (editando.value) {
      await api.put(`/actividades/${editando.value.id}`, form.value)
      msg.value = 'Actividad actualizada'
    } else {
      await api.post('/actividades/', form.value)
      msg.value = 'Actividad creada'
    }
    formModal.value = false
    const { data } = await api.get('/actividades/')
    actividades.value = data
  } catch (e) { err.value = e.response?.data?.error || 'Error' }
  finally { guardando.value = false }
}

onMounted(async () => {
  const { data } = await api.get('/actividades/')
  actividades.value = data
})
</script>

<style scoped>
.actividad-card { }
.actividad-header { display:flex; align-items:center; gap:12px; }
.sport-emoji { font-size:36px; }
.actividad-header h3 { font-size:20px; font-family:'Bebas Neue',sans-serif; }
.precio { margin-left:auto; text-align:right; }
.precio-num { font-size:26px; font-family:'Bebas Neue',sans-serif; color:var(--verde-claro); display:block; }
.modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.7); display:flex; align-items:center; justify-content:center; z-index:200; }
.modal { max-width:440px; width:100%; }
.modal h3 { font-size:22px; margin-bottom:20px; }
</style>
