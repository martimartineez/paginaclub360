<template>
  <div>
    <div class="page-header">
      <h2>CLASES DISPONIBLES</h2>
      <p>Explorá las actividades y reservá tu lugar</p>
    </div>

    <!-- Visitante sin sesión -->
    <div v-if="!auth.isAuthenticated" class="no-auth-banner card">
      <div class="no-auth-content">
        <span style="font-size:48px">🔒</span>
        <h3>Iniciá sesión para ver las clases</h3>
        <p>Necesitás una cuenta para ver las clases disponibles y hacer reservas.</p>
        <div style="display:flex;gap:12px;justify-content:center;margin-top:16px">
          <router-link to="/login" class="btn btn-primary">Ingresar</router-link>
          <router-link to="/registro" class="btn btn-outline">Registrarse gratis</router-link>
        </div>
      </div>
    </div>

    <!-- Contenido solo para autenticados -->
    <template v-else>
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
            <input v-model="filtros.desde" type="date" @change="fetchClases" placeholder="Desde" />
          </div>
          <div class="input-group" style="margin:0;flex:1">
            <input v-model="filtros.hasta" type="date" @change="fetchClases" placeholder="Hasta" />
          </div>
          <button class="btn btn-outline" @click="resetFiltros">Limpiar</button>
        </div>
      </div>

      <div class="alert alert-error" v-if="error">{{ error }}</div>
      <div class="alert alert-success" v-if="mensaje">{{ mensaje }}</div>

      <div v-if="loading" class="loading-text">Cargando clases...</div>

      <div class="clases-grid" v-else>
        <div v-for="clase in clases" :key="clase.id" class="clase-card card" :class="{ 'cancelada-card': clase.cancelada }">
          <div class="clase-header">
            <span class="sport-emoji">{{ sportEmoji(clase.actividad) }}</span>
            <div style="flex:1">
              <h3>{{ clase.actividad }}</h3>
              <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:4px">
                <span class="dia-badge">{{ clase.dia_semana }}</span>
                <span class="dia-badge fecha-badge">{{ formatFecha(clase.fecha) }}</span>
                <span v-if="clase.cancelada" class="badge badge-red">Cancelada</span>
              </div>
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

          <div class="clase-actions">
            <router-link :to="`/clases/${clase.id}`" class="btn btn-outline btn-sm">
              🔍 Ver detalle
            </router-link>

            <template v-if="auth.isCliente && !clase.cancelada">
              <div class="tipo-selector" v-if="reservando === clase.id">
                <p style="font-size:13px;color:var(--text-muted);margin-bottom:10px">¿Cómo querés inscribirte?</p>
                <div class="tipo-btns">
                  <button class="btn btn-primary btn-sm" @click="reservar(clase, 'abonado')" :disabled="reservandoLoading === clase.id">
                    📅 Abonado — ${{ clase.precio_clase?.toLocaleString() }}
                  </button>
                  <button class="btn btn-secondary btn-sm" @click="reservar(clase, 'no_abonado')" :disabled="reservandoLoading === clase.id">
                    🎯 Clase suelta — seña ${{ Math.round(clase.precio_clase * 0.5).toLocaleString() }}
                  </button>
                  <button class="btn btn-outline btn-sm" @click="reservando = null">Cancelar</button>
                </div>
              </div>
              <button v-else class="btn btn-primary btn-sm" @click="reservando = clase.id">
                {{ clase.cupos_disponibles === 0 ? '⏳ Lista de espera' : '+ Reservar' }}
              </button>
            </template>
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
    </template>
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
const filtros = ref({ actividad_id: '', desde: '', hasta: '' })

function sportEmoji(nombre) {
  const map = { 'Fútbol': '⚽', 'Pádel': '🎾', 'Básquet': '🏀', 'Vóley': '🏐' }
  return map[nombre] || '🏃'
}
function formatFecha(fechaStr) {
  if (!fechaStr) return ''
  const [y, m, d] = fechaStr.split('-')
  return `${d}/${m}/${y}`
}
function barraWidth(clase) {
  return ((clase.cupo_maximo - clase.cupos_disponibles) / clase.cupo_maximo) * 100
}
function barraColor(clase) {
  const pct = barraWidth(clase)
  if (pct >= 90) return '#da3633'
  if (pct >= 60) return '#d29922'
  return '#3fb950'
}

async function fetchClases() {
  loading.value = true
  error.value = ''
  try {
    const params = { solo_activas: true }
    if (filtros.value.actividad_id) params.actividad_id = filtros.value.actividad_id
    if (filtros.value.desde) params.desde = filtros.value.desde
    if (filtros.value.hasta) params.hasta = filtros.value.hasta
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
  filtros.value = { actividad_id: '', desde: '', hasta: '' }
  fetchClases()
}

onMounted(async () => {
  if (auth.isAuthenticated) {
    const { data } = await api.get('/actividades/')
    actividades.value = data
    fetchClases()
  }
})
</script>

<style scoped>
.no-auth-banner { text-align: center; padding: 60px 40px; margin-top: 20px; }
.no-auth-content { display: flex; flex-direction: column; align-items: center; gap: 12px; }
.no-auth-content h3 { font-size: 24px; }
.no-auth-content p { color: var(--text-muted); font-size: 15px; }
.filters-bar .filter-row { display: flex; gap: 12px; align-items: flex-end; }
.clases-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }
.clase-card { display: flex; flex-direction: column; gap: 14px; }
.cancelada-card { opacity: 0.6; border-color: var(--danger) !important; }
.clase-header { display: flex; align-items: flex-start; gap: 12px; }
.sport-emoji { font-size: 36px; flex-shrink: 0; }
.clase-header h3 { font-size: 20px; font-family: 'Bebas Neue', sans-serif; letter-spacing: 1px; }
.dia-badge { display: inline-block; padding: 2px 8px; background: var(--dark-3); border-radius: 4px; font-size: 12px; color: var(--text-muted); }
.fecha-badge { color: var(--verde-claro); background: rgba(46,125,50,0.15); }
.cupo-info { flex-shrink: 0; text-align: center; }
.cupo-num { font-size: 28px; font-family: 'Bebas Neue', sans-serif; color: var(--success); display: block; }
.cupo-label { font-size: 11px; color: var(--text-muted); }
.sin-cupo .cupo-num { color: var(--danger); }
.clase-info { display: flex; flex-direction: column; gap: 5px; }
.info-item { font-size: 14px; color: var(--text-muted); }
.clase-barra { height: 4px; background: var(--dark-3); border-radius: 2px; overflow: hidden; }
.barra-fill { height: 100%; border-radius: 2px; transition: width 0.5s; }
.clase-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.tipo-btns { display: flex; flex-direction: column; gap: 8px; width: 100%; }
.empty-state { text-align: center; padding: 60px; color: var(--text-muted); }
.loading-text { text-align: center; padding: 40px; color: var(--text-muted); }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 200; }
.modal { max-width: 420px; width: 100%; text-align: center; }
.modal h3 { font-size: 24px; margin-bottom: 12px; }
.modal p { color: var(--text-muted); font-size: 14px; margin-bottom: 8px; }
.monto-info { color: var(--text) !important; font-size: 16px !important; }
</style>
