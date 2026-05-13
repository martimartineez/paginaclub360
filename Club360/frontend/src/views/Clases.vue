<template>
  <div>
    <!-- Sin sesión -->
    <div v-if="!auth.isAuthenticated" class="no-auth-banner card">
      <div class="no-auth-content">
        <span style="font-size:48px">🔒</span>
        <h3>Iniciá sesión para ver las clases</h3>
        <p>Necesitás una cuenta para reservar clases.</p>
        <div style="display:flex;gap:12px;justify-content:center;margin-top:16px">
          <router-link to="/login" class="btn btn-primary">Ingresar</router-link>
          <router-link to="/registro" class="btn btn-outline">Registrarse gratis</router-link>
        </div>
      </div>
    </div>

    <!-- Flujo de reserva para clientes autenticados -->
    <template v-else-if="auth.isCliente">
      <!-- Barra de progreso -->
      <div class="progress-bar" v-if="paso < 6">
        <div v-for="i in 5" :key="i" class="progress-step" :class="{ active: paso >= i, current: paso === i }">
          <div class="step-dot">{{ paso > i ? '✓' : i }}</div>
          <div class="step-label">{{ stepLabels[i-1] }}</div>
        </div>
        <div class="progress-line" :style="{ width: ((paso-1)/4*100) + '%' }"></div>
      </div>

      <!-- PASO 1: Elegir deporte -->
      <div v-if="paso === 1" class="step-container">
        <div class="step-header">
          <div class="step-num">Paso 1</div>
          <h2>¿Qué deporte querés jugar?</h2>
          <p>Seleccioná una actividad</p>
        </div>
        <div class="deportes-grid">
          <div
            v-for="a in actividades"
            :key="a.id"
            class="deporte-card"
            @click="elegirDeporte(a)"
          >
            <span class="deporte-icon">{{ sportEmoji(a.nombre) }}</span>
            <span class="deporte-nombre">{{ a.nombre }}</span>
            <span class="deporte-precio">${{ a.precio_clase?.toLocaleString() }} / clase</span>
          </div>
        </div>
      </div>

      <!-- PASO 2: Tipo de inscripción -->
      <div v-if="paso === 2" class="step-container">
        <button class="back-btn" @click="paso = 1">← Cambiar deporte</button>
        <div class="step-header">
          <div class="step-num">Paso 2</div>
          <h2>¿Cómo querés inscribirte?</h2>
          <p>{{ seleccion.actividad?.nombre }}</p>
        </div>
        <div class="planes-grid">
          <div class="plan-card" @click="elegirTipo('no_abonado')">
            <div class="plan-nombre">🎯 Clase suelta</div>
            <div class="plan-precio">${{ seleccion.actividad?.precio_clase?.toLocaleString() }}<span>/clase</span></div>
            <div class="plan-desc">Reservá una clase en particular. Pagás una seña del 50% para confirmar.</div>
            <ul class="plan-feats">
              <li>Sin compromiso mensual</li>
              <li>Cancelación hasta 24hs antes</li>
              <li>Recuperás la seña si cancelás a tiempo</li>
            </ul>
            <button class="btn btn-outline" style="width:100%">Elegir</button>
          </div>
          <div class="plan-card plan-featured" @click="elegirTipo('abonado')">
            <div class="plan-badge">MÁS ELEGIDO</div>
            <div class="plan-nombre">📅 Abono mensual</div>
            <div class="plan-precio">${{ precioMensual?.toLocaleString() }}<span>/mes</span></div>
            <div class="plan-desc">Pagás el mes completo y tenés tu lugar asegurado cada semana.</div>
            <ul class="plan-feats">
              <li>20% de descuento si entrás a mitad de mes</li>
              <li>Cancelación hasta 48hs antes con crédito</li>
              <li>Prioridad en lista de espera</li>
            </ul>
            <button class="btn btn-primary" style="width:100%">Elegir</button>
          </div>
        </div>
      </div>

      <!-- PASO 3: Elegir fecha y horario -->
      <div v-if="paso === 3" class="step-container">
        <button class="back-btn" @click="paso = 2">← Cambiar tipo</button>
        <div class="step-header">
          <div class="step-num">Paso 3</div>
          <h2>Elegí el día y horario</h2>
          <p>{{ seleccion.actividad?.nombre }} · {{ seleccion.tipo === 'abonado' ? 'Abono mensual' : 'Clase suelta' }}</p>
        </div>

        <div v-if="loadingClases" class="loading-text">Buscando clases disponibles...</div>
        <div v-else-if="clasesDisponibles.length === 0" class="empty-state">
          <p>😕 No hay clases disponibles para esta actividad.</p>
          <button class="btn btn-outline" style="margin-top:12px" @click="paso = 1">Elegir otro deporte</button>
        </div>

        <div v-else>
          <!-- Agrupar por fecha -->
          <div v-for="(grupo, fecha) in clasesPorFecha" :key="fecha" class="fecha-grupo">
            <div class="fecha-titulo">
              <span class="fecha-dia">{{ grupo.diaNombre }}</span>
              <span class="fecha-fecha">{{ formatFecha(fecha) }}</span>
            </div>
            <div class="horarios-grid">
              <div
                v-for="clase in grupo.clases"
                :key="clase.id"
                class="horario-btn"
                :class="{
                  selected: seleccion.clase?.id === clase.id,
                  'sin-cupo': clase.cupos_disponibles === 0
                }"
                @click="elegirClase(clase)"
              >
                <span class="horario-hora">{{ clase.hora_inicio }}</span>
                <span class="horario-cupo" :class="{ 'cupo-agotado': clase.cupos_disponibles === 0 }">
                  {{ clase.cupos_disponibles > 0 ? `${clase.cupos_disponibles} cupos` : 'Sin cupo' }}
                </span>
              </div>
            </div>
          </div>

          <div v-if="seleccion.clase" class="seleccion-banner">
            <span>✓ Seleccionaste: {{ seleccion.clase.dia_semana }} {{ formatFecha(seleccion.clase.fecha) }} a las {{ seleccion.clase.hora_inicio }} hs</span>
            <button class="btn btn-primary" @click="paso = 4">Continuar →</button>
          </div>
        </div>
      </div>

      <!-- PASO 4: Confirmar selección -->
      <div v-if="paso === 4" class="step-container">
        <button class="back-btn" @click="paso = 3">← Cambiar horario</button>
        <div class="step-header">
          <div class="step-num">Paso 4</div>
          <h2>Confirmá tu reserva</h2>
          <p>Revisá los detalles antes de continuar</p>
        </div>

        <div class="confirm-card card">
          <div class="confirm-row">
            <span class="confirm-label">Deporte</span>
            <span class="confirm-value">{{ sportEmoji(seleccion.actividad?.nombre) }} {{ seleccion.actividad?.nombre }}</span>
          </div>
          <div class="confirm-row">
            <span class="confirm-label">Tipo</span>
            <span class="confirm-value">
              <span class="badge" :class="seleccion.tipo === 'abonado' ? 'badge-green' : 'badge-blue'">
                {{ seleccion.tipo === 'abonado' ? 'Abono mensual' : 'Clase suelta' }}
              </span>
            </span>
          </div>
          <div class="confirm-row">
            <span class="confirm-label">Fecha</span>
            <span class="confirm-value">{{ seleccion.clase?.dia_semana }}, {{ formatFecha(seleccion.clase?.fecha) }}</span>
          </div>
          <div class="confirm-row">
            <span class="confirm-label">Horario</span>
            <span class="confirm-value">{{ seleccion.clase?.hora_inicio }} hs</span>
          </div>
          <div class="confirm-row total-row">
            <span class="confirm-label">
              {{ seleccion.tipo === 'no_abonado' ? 'Seña a pagar (50%)' : 'Total a pagar' }}
            </span>
            <span class="confirm-value total-value">${{ montoAPagar?.toLocaleString() }}</span>
          </div>
        </div>

        <div class="alert alert-warning" v-if="seleccion.tipo === 'no_abonado'" style="max-width:440px">
          💡 Pagás la seña ahora para confirmar el turno. El resto lo abonás al llegar.
        </div>

        <div style="max-width:440px;margin-top:16px">
          <button class="btn btn-primary" style="width:100%" @click="irAPagar">
            Ir a pagar →
          </button>
        </div>
      </div>

      <!-- PASO 5: Pagar con tarjeta -->
      <div v-if="paso === 5" class="step-container">
        <button class="back-btn" @click="paso = 4">← Volver</button>
        <div class="step-header">
          <div class="step-num">Paso 5</div>
          <h2>Pago con tarjeta de crédito</h2>
          <p>Monto a pagar: <strong style="color:var(--verde-claro)">${{ montoAPagar?.toLocaleString() }}</strong></p>
        </div>

        <div class="alert alert-error" v-if="errorPago">{{ errorPago }}</div>

        <!-- Sin tarjeta registrada -->
        <div v-if="tarjetas.length === 0" style="max-width:440px">
          <div class="alert alert-warning">No tenés ninguna tarjeta registrada. Agregá una para continuar.</div>
          <FormTarjeta label-boton="Guardar y pagar" :show-cancelar="false" @guardada="onTarjetaGuardada" />
        </div>

        <!-- Con tarjetas -->
        <div v-else style="max-width:440px">
          <p style="font-size:14px;color:var(--text-muted);margin-bottom:16px">Seleccioná una tarjeta:</p>
          <div
            v-for="t in tarjetas"
            :key="t.id"
            class="tarjeta-opcion"
            :class="{ selected: tarjetaSeleccionada?.id === t.id }"
            @click="tarjetaSeleccionada = t"
          >
            <div class="tarjeta-icon">💳</div>
            <div>
              <p style="font-weight:600">•••• •••• •••• {{ t.ultimos_4 }}</p>
              <p style="font-size:12px;color:var(--text-muted)">{{ t.titular }} · Vence {{ t.vencimiento }}</p>
            </div>
            <div class="tarjeta-check" v-if="tarjetaSeleccionada?.id === t.id">✓</div>
          </div>

          <div v-if="!mostrarNuevaTarjeta">
            <button class="btn btn-outline btn-sm" style="margin-top:10px" @click="mostrarNuevaTarjeta = true">
              + Usar otra tarjeta
            </button>
          </div>
          <div v-else style="margin-top:16px;padding-top:16px;border-top:1px solid var(--border)">
            <FormTarjeta label-boton="Guardar tarjeta" @guardada="onTarjetaGuardada" @cancelar="mostrarNuevaTarjeta = false" />
          </div>

          <button
            class="btn btn-primary"
            style="width:100%;margin-top:20px"
            @click="confirmarPago"
            :disabled="!tarjetaSeleccionada || pagando"
          >
            {{ pagando ? 'Procesando...' : `Pagar $${montoAPagar?.toLocaleString()}` }}
          </button>
        </div>
      </div>

      <!-- PASO 6: Éxito -->
      <div v-if="paso === 6" class="step-container success-container">
        <div class="success-icon">✅</div>
        <h2>¡Reserva confirmada!</h2>
        <p style="color:var(--text-muted)">Te enviamos los detalles por email.</p>

        <div class="confirm-card card" style="max-width:380px;margin:24px auto">
          <div class="confirm-row">
            <span class="confirm-label">Deporte</span>
            <span class="confirm-value">{{ sportEmoji(seleccion.actividad?.nombre) }} {{ seleccion.actividad?.nombre }}</span>
          </div>
          <div class="confirm-row">
            <span class="confirm-label">Tipo</span>
            <span class="confirm-value">{{ seleccion.tipo === 'abonado' ? 'Abono mensual' : 'Clase suelta' }}</span>
          </div>
          <div class="confirm-row">
            <span class="confirm-label">Fecha</span>
            <span class="confirm-value">{{ seleccion.clase?.dia_semana }}, {{ formatFecha(seleccion.clase?.fecha) }}</span>
          </div>
          <div class="confirm-row">
            <span class="confirm-label">Horario</span>
            <span class="confirm-value">{{ seleccion.clase?.hora_inicio }} hs</span>
          </div>
          <div class="confirm-row total-row">
            <span class="confirm-label">Pagado</span>
            <span class="confirm-value total-value">${{ montoAPagar?.toLocaleString() }}</span>
          </div>
        </div>

        <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap">
          <router-link to="/mis-reservas" class="btn btn-primary">Ver mis reservas</router-link>
          <button class="btn btn-outline" @click="reiniciar">Nueva reserva</button>
        </div>
      </div>
    </template>

    <!-- Admin/empleado: listado clásico -->
    <template v-else>
      <div class="page-header">
        <h2>CLASES DISPONIBLES</h2>
      </div>
      <div class="card filters-bar" style="margin-bottom:20px">
        <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end">
          <div class="input-group" style="margin:0;flex:1">
            <select v-model="filtros.actividad_id" @change="fetchClasesAdmin">
              <option value="">Todas las actividades</option>
              <option v-for="a in actividades" :key="a.id" :value="a.id">{{ a.nombre }}</option>
            </select>
          </div>
          <div class="input-group" style="margin:0;flex:1">
            <input v-model="filtros.desde" type="date" @change="fetchClasesAdmin" />
          </div>
          <div class="input-group" style="margin:0;flex:1">
            <input v-model="filtros.hasta" type="date" @change="fetchClasesAdmin" />
          </div>
          <button class="btn btn-outline" @click="filtros={actividad_id:'',desde:'',hasta:''}; fetchClasesAdmin()">Limpiar</button>
        </div>
      </div>
      <div class="clases-grid">
        <div v-for="clase in clasesAdmin" :key="clase.id" class="clase-card card" :class="{'cancelada-card': clase.cancelada}">
          <div class="clase-header">
            <span style="font-size:32px">{{ sportEmoji(clase.actividad) }}</span>
            <div style="flex:1">
              <h3>{{ clase.actividad }}</h3>
              <div style="display:flex;gap:6px;margin-top:4px;flex-wrap:wrap">
                <span class="dia-badge">{{ clase.dia_semana }}</span>
                <span class="dia-badge fecha-badge">{{ formatFecha(clase.fecha) }}</span>
                <span v-if="clase.cancelada" class="badge badge-red">Cancelada</span>
              </div>
            </div>
            <div style="text-align:center">
              <span style="font-size:24px;font-family:'Bebas Neue',sans-serif;color:var(--success);display:block">{{ clase.cupos_disponibles }}</span>
              <span style="font-size:11px;color:var(--text-muted)">cupos</span>
            </div>
          </div>
          <div style="display:flex;gap:8px;font-size:13px;color:var(--text-muted)">
            <span>🕐 {{ clase.hora_inicio }} hs</span>
            <span>👥 Cupo: {{ clase.cupo_maximo }}</span>
            <span>💰 ${{ clase.precio_clase?.toLocaleString() }}</span>
          </div>
          <router-link :to="`/clases/${clase.id}`" class="btn btn-outline btn-sm">🔍 Ver detalle</router-link>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth.js'
import FormTarjeta from '../components/FormTarjeta.vue'
import api from '../api.js'

const auth = useAuthStore()

// --- Estado del flujo de reserva ---
const paso = ref(1)
const actividades = ref([])
const seleccion = ref({ actividad: null, tipo: null, clase: null })
const clasesDisponibles = ref([])
const loadingClases = ref(false)
const tarjetas = ref([])
const tarjetaSeleccionada = ref(null)
const mostrarNuevaTarjeta = ref(false)
const pagando = ref(false)
const errorPago = ref('')
const reservaCreada = ref(null)

// Admin/empleado
const clasesAdmin = ref([])
const filtros = ref({ actividad_id: '', desde: '', hasta: '' })

const stepLabels = ['Deporte', 'Tipo', 'Fecha/Hora', 'Confirmar', 'Pagar']

const precioMensual = computed(() => {
  if (!seleccion.value.actividad) return 0
  return seleccion.value.actividad.precio_clase * 4
})

const montoAPagar = computed(() => {
  if (!seleccion.value.actividad) return 0
  const precio = seleccion.value.actividad.precio_clase
  if (seleccion.value.tipo === 'no_abonado') return Math.round(precio * 0.5)
  return precio
})

const clasesPorFecha = computed(() => {
  const grupos = {}
  const dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
  clasesDisponibles.value.forEach(c => {
    if (!grupos[c.fecha]) {
      const d = new Date(c.fecha + 'T00:00:00')
      grupos[c.fecha] = {
        diaNombre: dias[d.getDay() === 0 ? 6 : d.getDay() - 1],
        clases: []
      }
    }
    grupos[c.fecha].clases.push(c)
  })
  return grupos
})

function sportEmoji(nombre) {
  return { 'Fútbol': '⚽', 'Pádel': '🎾', 'Básquet': '🏀', 'Vóley': '🏐' }[nombre] || '🏃'
}

function formatFecha(fechaStr) {
  if (!fechaStr) return ''
  const [y, m, d] = fechaStr.split('-')
  return `${d}/${m}/${y}`
}

function elegirDeporte(actividad) {
  seleccion.value.actividad = actividad
  seleccion.value.tipo = null
  seleccion.value.clase = null
  paso.value = 2
}

function elegirTipo(tipo) {
  seleccion.value.tipo = tipo
  seleccion.value.clase = null
  paso.value = 3
  fetchClasesActividad()
}

async function fetchClasesActividad() {
  loadingClases.value = true
  clasesDisponibles.value = []
  try {
    const ahora = new Date()
    const pad = n => String(n).padStart(2, '0')
    const hoy = ahora.getFullYear() + '-' + pad(ahora.getMonth()+1) + '-' + pad(ahora.getDate())
    const hastaDate = new Date(ahora)
    hastaDate.setMonth(hastaDate.getMonth() + 1)
    const hasta = hastaDate.getFullYear() + '-' + pad(hastaDate.getMonth()+1) + '-' + pad(hastaDate.getDate())
    console.log('Buscando clases:', { actividad_id: seleccion.value.actividad.id, desde: hoy, hasta })
    const { data } = await api.get('/clases/', {
      params: {
        actividad_id: seleccion.value.actividad.id,
        desde: hoy,
        hasta: hasta,
        solo_activas: true
      }
    })
    console.log('Clases recibidas:', data.length, data)
    clasesDisponibles.value = data
  } catch(e) {
    console.error('Error al buscar clases:', e)
  } finally {
    loadingClases.value = false
  }
}

function elegirClase(clase) {
  if (clase.cupos_disponibles === 0) {
    seleccion.value.clase = clase // igual se puede anotar en espera
  } else {
    seleccion.value.clase = clase
  }
}

function irAPagar() {
  paso.value = 5
  fetchTarjetas()
}

async function fetchTarjetas() {
  try {
    const { data } = await api.get('/auth/tarjetas')
    tarjetas.value = data
    if (data.length > 0) tarjetaSeleccionada.value = data[0]
  } catch {}
}

function onTarjetaGuardada(tarjeta) {
  tarjetas.value.push(tarjeta)
  tarjetaSeleccionada.value = tarjeta
  mostrarNuevaTarjeta.value = false
}

async function confirmarPago() {
  pagando.value = true
  errorPago.value = ''
  try {
    // Crear reserva
    const { data: dataReserva } = await api.post('/reservas/', {
      clase_id: seleccion.value.clase.id,
      tipo: seleccion.value.tipo
    })

    if (dataReserva.en_espera) {
      // Sin cupo, quedó en lista de espera
      reservaCreada.value = null
      paso.value = 6
      return
    }

    // Registrar pago
    const reservaId = dataReserva.reserva.id
    await api.post(`/reservas/${reservaId}/pagar`, {
      metodo: 'tarjeta_credito',
      monto: montoAPagar.value,
      tipo_pago: seleccion.value.tipo === 'no_abonado' ? 'senia' : 'mensualidad'
    })

    reservaCreada.value = dataReserva.reserva
    paso.value = 6
  } catch (e) {
    errorPago.value = e.response?.data?.error || 'Error al procesar el pago'
  } finally {
    pagando.value = false
  }
}

function reiniciar() {
  paso.value = 1
  seleccion.value = { actividad: null, tipo: null, clase: null }
  clasesDisponibles.value = []
  tarjetaSeleccionada.value = null
  mostrarNuevaTarjeta.value = false
  reservaCreada.value = null
  errorPago.value = ''
}

async function fetchClasesAdmin() {
  const params = { solo_activas: false }
  if (filtros.value.actividad_id) params.actividad_id = filtros.value.actividad_id
  if (filtros.value.desde) params.desde = filtros.value.desde
  if (filtros.value.hasta) params.hasta = filtros.value.hasta
  const { data } = await api.get('/clases/', { params })
  clasesAdmin.value = data
}

onMounted(async () => {
  if (auth.isAuthenticated) {
    const { data } = await api.get('/actividades/')
    actividades.value = data
    if (!auth.isCliente) fetchClasesAdmin()
  }
})
</script>

<style scoped>
/* Sin auth */
.no-auth-banner { text-align:center; padding:60px 40px; margin-top:20px; }
.no-auth-content { display:flex; flex-direction:column; align-items:center; gap:12px; }
.no-auth-content h3 { font-size:24px; }
.no-auth-content p { color:var(--text-muted); font-size:15px; }

/* Barra de progreso */
.progress-bar {
  display:flex; align-items:flex-start; justify-content:center;
  position:relative; padding:24px 0 32px; margin-bottom:8px; gap:0;
}
.progress-step { display:flex; flex-direction:column; align-items:center; gap:8px; width:80px; position:relative; z-index:1; }
.step-dot {
  width:36px; height:36px; border-radius:50%;
  background:var(--dark-3); border:2px solid var(--border);
  display:flex; align-items:center; justify-content:center;
  font-size:13px; font-weight:700; color:var(--text-muted);
  transition:all 0.3s;
}
.progress-step.active .step-dot { background:var(--verde); border-color:var(--verde); color:white; }
.progress-step.current .step-dot { box-shadow:0 0 0 4px rgba(46,125,50,0.2); }
.step-label { font-size:11px; color:var(--text-muted); text-align:center; }
.progress-step.active .step-label { color:var(--text); }
.progress-line {
  position:absolute; top:42px; left:calc(50% + 40px);
  height:2px; background:var(--verde); transition:width 0.4s;
  z-index:0;
}

/* Contenedor de pasos */
.step-container { max-width:600px; margin:0 auto; padding-bottom:40px; }
.step-header { text-align:center; margin-bottom:32px; }
.step-num { font-size:12px; color:var(--verde-claro); letter-spacing:2px; text-transform:uppercase; margin-bottom:8px; font-weight:600; }
.step-header h2 { font-size:32px; font-family:'Bebas Neue',sans-serif; }
.step-header p { color:var(--text-muted); margin-top:6px; }
.back-btn { background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:13px; margin-bottom:20px; display:flex; align-items:center; gap:4px; font-family:'DM Sans',sans-serif; }
.back-btn:hover { color:var(--text); }

/* Paso 1: Deportes */
.deportes-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:16px; }
.deporte-card {
  background:var(--dark-2); border:2px solid var(--border); border-radius:14px;
  padding:28px; text-align:center; cursor:pointer; transition:all 0.2s;
  display:flex; flex-direction:column; align-items:center; gap:8px;
}
.deporte-card:hover { border-color:var(--verde); transform:translateY(-3px); box-shadow:0 8px 24px rgba(46,125,50,0.15); }
.deporte-icon { font-size:40px; }
.deporte-nombre { font-size:18px; font-family:'Bebas Neue',sans-serif; letter-spacing:1px; }
.deporte-precio { font-size:13px; color:var(--text-muted); }

/* Paso 2: Planes */
.planes-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:16px; }
.plan-card {
  background:var(--dark-2); border:2px solid var(--border); border-radius:14px;
  padding:24px; cursor:pointer; transition:all 0.2s; display:flex; flex-direction:column; gap:10px;
}
.plan-card:hover { border-color:var(--verde); }
.plan-featured { border-color:var(--verde); background:rgba(46,125,50,0.05); }
.plan-badge { display:inline-block; background:var(--verde); color:white; font-size:10px; font-weight:700; padding:2px 10px; border-radius:4px; letter-spacing:1px; }
.plan-nombre { font-size:18px; font-weight:600; }
.plan-precio { font-size:26px; font-family:'Bebas Neue',sans-serif; color:var(--verde-claro); }
.plan-precio span { font-size:13px; font-weight:400; color:var(--text-muted); font-family:'DM Sans',sans-serif; }
.plan-desc { font-size:13px; color:var(--text-muted); line-height:1.5; }
.plan-feats { list-style:none; display:flex; flex-direction:column; gap:6px; flex:1; }
.plan-feats li { font-size:12px; color:var(--text-muted); display:flex; align-items:center; gap:6px; }
.plan-feats li::before { content:''; width:5px; height:5px; border-radius:50%; background:var(--verde); flex-shrink:0; }

/* Paso 3: Fechas y horarios */
.fecha-grupo { margin-bottom:24px; }
.fecha-titulo { display:flex; align-items:center; gap:12px; margin-bottom:12px; }
.fecha-dia { font-size:18px; font-family:'Bebas Neue',sans-serif; letter-spacing:1px; }
.fecha-fecha { font-size:13px; color:var(--text-muted); background:var(--dark-3); padding:2px 10px; border-radius:6px; }
.horarios-grid { display:flex; flex-wrap:wrap; gap:8px; }
.horario-btn {
  background:var(--dark-2); border:2px solid var(--border); border-radius:10px;
  padding:10px 16px; cursor:pointer; transition:all 0.2s; text-align:center; min-width:90px;
}
.horario-btn:hover:not(.sin-cupo) { border-color:var(--verde); background:rgba(46,125,50,0.1); }
.horario-btn.selected { border-color:var(--verde-claro); background:rgba(46,125,50,0.15); }
.horario-btn.sin-cupo { opacity:0.5; }
.horario-hora { font-size:15px; font-weight:600; display:block; }
.horario-cupo { font-size:11px; color:var(--success); display:block; margin-top:2px; }
.cupo-agotado { color:var(--warning) !important; }
.seleccion-banner {
  display:flex; align-items:center; justify-content:space-between;
  background:rgba(46,125,50,0.1); border:1px solid var(--verde);
  border-radius:10px; padding:14px 18px; margin-top:20px; gap:12px;
  font-size:14px; flex-wrap:wrap;
}

/* Paso 4: Confirmar */
.confirm-card { padding:0; overflow:hidden; }
.confirm-row {
  display:flex; justify-content:space-between; align-items:center;
  padding:14px 20px; border-bottom:1px solid var(--border); font-size:14px;
}
.confirm-row:last-child { border:none; }
.confirm-label { color:var(--text-muted); }
.confirm-value { font-weight:600; }
.total-row { background:rgba(46,125,50,0.05); }
.total-value { font-size:20px; color:var(--verde-claro); font-family:'Bebas Neue',sans-serif; }

/* Paso 5: Pagar */
.tarjeta-opcion {
  display:flex; align-items:center; gap:14px;
  padding:14px 16px; background:var(--dark-3);
  border:2px solid var(--border); border-radius:10px;
  cursor:pointer; transition:all 0.2s; margin-bottom:8px;
}
.tarjeta-opcion:hover { border-color:var(--verde); }
.tarjeta-opcion.selected { border-color:var(--verde-claro); background:rgba(46,125,50,0.08); }
.tarjeta-icon { font-size:24px; }
.tarjeta-check { margin-left:auto; color:var(--verde-claro); font-size:18px; font-weight:700; }

/* Paso 6: Éxito */
.success-container { text-align:center; padding:40px 0; }
.success-icon { font-size:64px; margin-bottom:16px; }
.success-container h2 { font-size:36px; font-family:'Bebas Neue',sans-serif; margin-bottom:8px; }

/* Admin listado */
.clases-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:16px; }
.clase-card { display:flex; flex-direction:column; gap:12px; }
.cancelada-card { opacity:0.6; border-color:var(--danger) !important; }
.clase-header { display:flex; align-items:flex-start; gap:10px; }
.dia-badge { display:inline-block; padding:2px 8px; background:var(--dark-3); border-radius:4px; font-size:12px; color:var(--text-muted); }
.fecha-badge { color:var(--verde-claro); background:rgba(46,125,50,0.15); }
.filters-bar { padding:16px 20px; }
.loading-text { text-align:center; padding:40px; color:var(--text-muted); }
.empty-state { text-align:center; padding:40px; color:var(--text-muted); }
</style>
