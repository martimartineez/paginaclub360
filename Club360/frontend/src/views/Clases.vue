<template>
  <div>
    <div class="page-header">
      <h2>CLASES DISPONIBLES</h2>
      <p>Explorá las actividades y reservá tu lugar</p>
    </div>

    <!-- Filtros -->
    <div class="card filters-bar" style="margin-bottom:24px">
      <div class="filter-row">
        <div class="input-group" style="margin:0;flex:1">
          <select v-model="filtros.actividad_id" @change="fetchClases">
            <option value="">Todas las actividades</option>
            <option v-for="a in actividades" :key="a.id" :value="a.id">{{ a.nombre }}</option>
          </select>
        </div>
        <div class="input-group" style="margin:0;flex:1">
          <select v-model="filtros.dia" @change="fetchClases">
            <option value="">Todos los días</option>
            <option v-for="d in dias" :key="d.val" :value="d.val">{{ d.label }}</option>
          </select>
        </div>
        <button class="btn btn-outline" @click="resetFiltros">Limpiar</button>
      </div>
    </div>

    <div class="alert alert-error" v-if="error">{{ error }}</div>
    <div class="alert alert-success" v-if="mensaje">{{ mensaje }}</div>

    <div v-if="loading" class="loading-text">Cargando clases...</div>

    <div class="clases-grid" v-else>
      <div v-for="clase in clases" :key="clase.id" class="clase-card card">
        <div class="clase-header">
          <span class="sport-emoji">{{ sportEmoji(clase.actividad) }}</span>
          <div>
            <h3>{{ clase.actividad }}</h3>
            <span class="dia-badge">{{ clase.dia_semana }}</span>
          </div>
          <div class="cupo-info" :class="{ 'sin-cupo': clase.cupos_disponibles === 0 }">
            <span class="cupo-num">{{ clase.cupos_disponibles }}</span>
            <span class="cupo-label">cupos</span>
          </div>
        </div>

        <div class="clase-info">
          <div class="info-item">🕐 {{ clase.hora_inicio }} hs — 1 hora</div>
          <div class="info-item">👥 Cupo máximo: {{ clase.cupo_maximo }}</div>
          <div class="info-item">💰 ${{ clase.precio_clase?.toLocaleString() }} / clase</div>
        </div>

        <div class="clase-barra">
          <div class="barra-fill" :style="{ width: barraWidth(clase) + '%', background: barraColor(clase) }"></div>
        </div>

        <div class="clase-actions" v-if="auth.isAuthenticated && auth.isCliente">
          <div class="tipo-selector" v-if="reservando === clase.id">
            <p style="font-size:13px;color:var(--text-muted);margin-bottom:10px">¿Cómo querés inscribirte?</p>
            <div class="tipo-btns">
              <button class="btn btn-primary btn-sm" @click="reservar(clase, 'abonado')">
                📅 Mensual — ${{ calcularMensual(clase).toLocaleString() }}
              </button>
              <button class="btn btn-secondary btn-sm" @click="reservar(clase, 'no_abonado')">
                🎯 Clase suelta — seña ${{ Math.round(clase.precio_clase * 0.5).toLocaleString() }}
              </button>
              <button class="btn btn-outline btn-sm" @click="reservando = null">Cancelar</button>
            </div>
          </div>
          <button v-else class="btn btn-primary" @click="reservando = clase.id" :disabled="reservandoLoading === clase.id">
            {{ clase.cupos_disponibles === 0 ? '⏳ Anotarme en lista de espera' : '+ Reservar' }}
          </button>
        </div>
        <div v-else-if="!auth.isAuthenticated">
          <router-link to="/login" class="btn btn-outline btn-sm">Iniciá sesión para reservar</router-link>
        </div>
      </div>
    </div>

    <div v-if="!loading && clases.length === 0" class="empty-state">
      <p>No hay clases disponibles con esos filtros.</p>
    </div>

    <!-- Modal resultado reserva -->
    <div class="modal-overlay" v-if="resultadoReserva" @click.self="resultadoReserva = null">
      <div class="modal card">
        <h3 v-if="resultadoReserva.en_espera">⏳ En lista de espera</h3>
        <h3 v-else>✅ Reserva creada</h3>
        <p v-if="resultadoReserva.en_espera">{{ resultadoReserva.mensaje }}</p>
        <template v-else>
          <p>Tu reserva fue creada exitosamente.</p>
          <p class="monto-info">Monto a pagar: <strong>${{ resultadoReserva.monto_a_pagar?.toLocaleString() }}</strong></p>
          <router-link to="/mis-reservas" class="btn btn-primary" style="margin-top:16px">Ver mis reservas</router-link>
        </template>
        <button class="btn btn-outline btn-sm" style="margin-top:10px" @click="resultadoReserva = null">Cerrar</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth.js'
import api from '../api.js'

const auth = useAuthStore()
const clases = ref([])
const actividades = ref([])
const loading = ref(false)
const error = ref('')
const mensaje = ref('')
const reservando = ref(null)
const reservandoLoading = ref(null)
const resultadoReserva = ref(null)
const filtros = ref({ actividad_id: '', dia: '' })

const dias = [
  { val: 'lunes', label: 'Lunes' }, { val: 'martes', label: 'Martes' },
  { val: 'miercoles', label: 'Miércoles' }, { val: 'jueves', label: 'Jueves' },
  { val: 'viernes', label: 'Viernes' }, { val: 'sabado', label: 'Sábado' }
]

function sportEmoji(nombre) {
  const map = { 'Fútbol': '⚽', 'Pádel': '🎾', 'Básquet': '🏀', 'Vóley': '🏐' }
  return map[nombre] || '🏃'
}

function barraWidth(clase) {
  const ocupados = clase.cupo_maximo - clase.cupos_disponibles
  return (ocupados / clase.cupo_maximo) * 100
}
function barraColor(clase) {
  const pct = barraWidth(clase)
  if (pct >= 90) return '#da3633'
  if (pct >= 60) return '#d29922'
  return '#3fb950'
}

function calcularMensual(clase) {
  // Aproximado para mostrar en UI
  return clase.precio_clase * 4
}

async function fetchClases() {
  loading.value = true
  try {
    const params = {}
    if (filtros.value.actividad_id) params.actividad_id = filtros.value.actividad_id
    if (filtros.value.dia) params.dia = filtros.value.dia
    const { data } = await api.get('/clases/', { params })
    clases.value = data
  } catch (e) {
    error.value = 'Error al cargar clases'
  } finally {
    loading.value = false
  }
}

async function reservar(clase, tipo) {
  reservandoLoading.value = clase.id
  error.value = ''
  mensaje.value = ''
  try {
    const { data } = await api.post('/reservas/', { clase_id: clase.id, tipo })
    resultadoReserva.value = data
    reservando.value = null
    fetchClases()
  } catch (e) {
    error.value = e.response?.data?.error || 'Error al reservar'
  } finally {
    reservandoLoading.value = null
  }
}

function resetFiltros() {
  filtros.value = { actividad_id: '', dia: '' }
  fetchClases()
}

onMounted(async () => {
  const { data } = await api.get('/actividades/')
  actividades.value = data
  fetchClases()
})
</script>

<style scoped>
.filters-bar .filter-row { display: flex; gap: 12px; align-items: flex-end; }
.clases-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }
.clase-card { display: flex; flex-direction: column; gap: 16px; }
.clase-header { display: flex; align-items: center; gap: 12px; }
.sport-emoji { font-size: 36px; }
.clase-header h3 { font-size: 20px; font-family: 'Bebas Neue', sans-serif; letter-spacing: 1px; }
.dia-badge {
  display: inline-block;
  padding: 2px 8px;
  background: var(--dark-3);
  border-radius: 4px;
  font-size: 12px;
  color: var(--text-muted);
  text-transform: capitalize;
}
.cupo-info { margin-left: auto; text-align: center; }
.cupo-num { font-size: 28px; font-family: 'Bebas Neue', sans-serif; color: var(--success); display: block; }
.cupo-label { font-size: 11px; color: var(--text-muted); }
.sin-cupo .cupo-num { color: var(--danger); }
.clase-info { display: flex; flex-direction: column; gap: 6px; }
.info-item { font-size: 14px; color: var(--text-muted); }
.clase-barra { height: 4px; background: var(--dark-3); border-radius: 2px; overflow: hidden; }
.barra-fill { height: 100%; border-radius: 2px; transition: width 0.5s; }
.tipo-btns { display: flex; flex-direction: column; gap: 8px; }
.empty-state { text-align: center; padding: 60px; color: var(--text-muted); }
.loading-text { text-align: center; padding: 40px; color: var(--text-muted); }
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.7);
  display: flex; align-items: center; justify-content: center;
  z-index: 200;
}
.modal { max-width: 420px; width: 100%; text-align: center; }
.modal h3 { font-size: 24px; margin-bottom: 12px; }
.modal p { color: var(--text-muted); font-size: 14px; margin-bottom: 8px; }
.monto-info { color: var(--text) !important; font-size: 16px !important; }
</style>
