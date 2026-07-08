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
      <div v-if="auth.isAdmin && !clase.cancelada" style="display:flex;gap:10px;flex-wrap:wrap">
        <button class="btn btn-secondary" @click="abrirEditarCupo">
          ✏️ Editar cupo
        </button>
        <button class="btn btn-danger" @click="confirmarCancelar = true">
          Cancelar clase
        </button>
        </div>
    </div>

    <div class="alert alert-error" v-if="error">{{ error }}</div>
    <div class="alert alert-success" v-if="mensaje">{{ mensaje }}</div>
    <div class="alert alert-warning" v-if="clase.cancelada">
      Esta clase fue cancelada por el administrador.
    </div>

    <div class="card cupo-reservado-card" style="margin-bottom:24px" v-if="cupoReservadoParaMi && !miReserva">
      <h3 style="font-size:20px;margin-bottom:8px">🎉 ¡Tenés un cupo reservado!</h3>
      <p style="font-size:14px;color:var(--text-muted);margin-bottom:16px">
        Sos el primero de la lista de espera para esta clase. Confirmá ahora para asegurar tu lugar antes de que se le ofrezca a la siguiente persona.
      </p>

      <!-- Paso 1: elegir cuanto pagar -->
      <div v-if="!confirmandoPagoCupo">
        <p style="font-size:13px;color:var(--text-muted);margin-bottom:12px">¿Cuánto querés pagar?</p>
        <div class="pago-opciones" style="margin-bottom:16px">
          <div class="pago-opcion" :class="{ selected: montoPagoCupo === 'senia' }" @click="montoPagoCupo = 'senia'">
            <div class="pago-radio">{{ montoPagoCupo === 'senia' ? '●' : '○' }}</div>
            <div>
              <p style="font-weight:600">Seña (50%) — ${{ Math.round((clase.precio_clase || 0) * 0.5).toLocaleString() }}</p>
              <p style="font-size:12px;color:var(--text-muted)">El resto lo abonás al llegar a la clase</p>
            </div>
          </div>
          <div class="pago-opcion" :class="{ selected: montoPagoCupo === 'total' }" @click="montoPagoCupo = 'total'">
            <div class="pago-radio">{{ montoPagoCupo === 'total' ? '●' : '○' }}</div>
            <div>
              <p style="font-weight:600">Total — ${{ clase.precio_clase?.toLocaleString() }}</p>
              <p style="font-size:12px;color:var(--text-muted)">Pagás todo ahora, no debés nada al llegar</p>
            </div>
          </div>
          <div
            v-if="creditoDisponibleCupo > 0"
            class="pago-opcion"
            :class="{ selected: montoPagoCupo === 'credito' }"
            @click="montoPagoCupo = 'credito'"
          >
            <div class="pago-radio">{{ montoPagoCupo === 'credito' ? '●' : '○' }}</div>
            <div>
              <p style="font-weight:600">Pagar con crédito</p>
              <p style="font-size:12px;color:var(--text-muted)">
                Tenés {{ creditoDisponibleCupo }} crédito(s) para esta actividad. Se consume 1 crédito completo.
              </p>
            </div>
          </div>
        </div>
        <div style="display:flex;gap:10px;flex-wrap:wrap">
          <button class="btn btn-primary" @click="irAPagarCupo" :disabled="reservandoLoading">
            Continuar →
          </button>
          <button class="btn btn-outline" @click="rechazarCupoLista" :disabled="reservandoLoading">
            Rechazar cupo
          </button>
        </div>
      </div>

      <!-- Paso 2: tarjeta y confirmacion -->
      <div v-else>
        <button class="back-btn" @click="confirmandoPagoCupo = false" style="margin-bottom:12px">← Cambiar monto</button>

        <div v-if="creditoCupoCubreTotal" style="max-width:440px">
          <div class="alert alert-success" style="margin-bottom:16px">
            El crédito cubre el monto seleccionado. Confirmá la reserva sin cargar tarjeta.
          </div>
          <button class="btn btn-primary" style="width:100%" @click="aceptarCupoLista" :disabled="reservandoLoading">
            {{ reservandoLoading ? 'Procesando...' : 'Confirmar reserva' }}
          </button>
        </div>
        <div v-else-if="loadingTarjetasCupo" class="loading-text">Cargando tarjetas...</div>
        <div v-else-if="tarjetasCupo.length === 0" style="max-width:440px">
          <div class="alert alert-warning">No tenés ninguna tarjeta registrada. Agregá una para continuar.</div>
          <FormTarjeta label-boton="Guardar tarjeta" :show-cancelar="false" @guardada="onTarjetaGuardadaCupo" />
        </div>
        <div v-else style="max-width:440px">
          <p style="font-size:14px;color:var(--text-muted);margin-bottom:12px">Seleccioná una tarjeta:</p>
          <div v-for="t in tarjetasCupo" :key="t.id" class="tarjeta-opcion"
            :class="{ selected: tarjetaSeleccionadaCupo?.id === t.id }"
            @click="tarjetaSeleccionadaCupo = t">
            <div class="tarjeta-icon">💳</div>
            <div>
              <p style="font-weight:600">•••• •••• •••• {{ t.ultimos_4 }}</p>
              <p style="font-size:12px;color:var(--text-muted)">{{ t.titular }} · Vence {{ t.vencimiento }}</p>
            </div>
            <div class="tarjeta-check" v-if="tarjetaSeleccionadaCupo?.id === t.id">✓</div>
          </div>
          <button v-if="!mostrarNuevaTarjetaCupo" class="btn btn-outline btn-sm" style="margin-top:10px" @click="mostrarNuevaTarjetaCupo = true">+ Usar otra tarjeta</button>
          <div v-else style="margin-top:16px;padding-top:16px;border-top:1px solid var(--border)">
            <FormTarjeta label-boton="Guardar tarjeta" @guardada="onTarjetaGuardadaCupo" @cancelar="mostrarNuevaTarjetaCupo = false" />
          </div>
          <button class="btn btn-primary" style="width:100%;margin-top:20px"
            @click="aceptarCupoLista" :disabled="!tarjetaSeleccionadaCupo || reservandoLoading">
            {{ reservandoLoading ? 'Procesando...' : `Pagar $${montoCupoAPagar?.toLocaleString()}` }}
          </button>
        </div>
      </div>
    </div>
    <div class="alert alert-warning" v-else-if="cupoTokenInvalido">
      {{ cupoTokenInvalidoMensaje }}
    </div>

    <div class="grid-3" style="margin-bottom:24px" v-if="auth.isEmpleado || auth.isAdmin">
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

    <div class="card" style="margin-bottom:24px" v-if="auth.isCliente && miReserva">
      <h3 style="font-size:20px;margin-bottom:16px">📲 Tu QR de asistencia</h3>
      <div v-if="miReserva.estado === 'activa' || miReserva.asistida" style="display:flex;align-items:center;gap:24px;flex-wrap:wrap">
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
            v-if="puedeCancelarMiReserva"
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

    <div class="card" style="margin-bottom:24px" v-if="auth.isCliente && !miReserva && !clase.cancelada && !cupoReservadoParaMi">
      <h3 style="font-size:20px;margin-bottom:12px">Reservar esta clase</h3>

      <!-- Sin cupo: panel de lista de espera -->
      <div v-if="clase.cupos_disponibles === 0 && reservando">
        <div class="alert alert-warning" style="margin-bottom:12px">
          ⏳ Este turno no tiene cupos disponibles. Al confirmar, quedás anotado en la lista de espera y te avisaremos si se libera un lugar. <strong>No se realizará ningún cobro.</strong>
        </div>
        <p style="font-size:13px;color:var(--text-muted);margin-bottom:12px">¿Con qué preferencia querés anotarte?</p>
        <div style="display:flex;gap:10px;flex-wrap:wrap">
          <button class="btn btn-primary" @click="reservar('abonado')" :disabled="reservandoLoading">
            {{ reservandoLoading ? 'Procesando...' : '📅 Como abonado' }}
          </button>
          <button class="btn btn-secondary" @click="reservar('no_abonado')" :disabled="reservandoLoading">
            {{ reservandoLoading ? 'Procesando...' : '🎯 Clase suelta' }}
          </button>
          <button class="btn btn-outline" @click="reservando = false">Cancelar</button>
        </div>
      </div>

      <!-- Con cupo: selector de tipo con precio -->
      <div v-else-if="reservando">
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
    </div>

    <div class="card" style="margin-bottom:24px" v-if="auth.isEmpleado || auth.isAdmin">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
        <h3 style="font-size:20px">👥 Inscriptos</h3>
        </div>
      <div v-if="loadingInscriptos" style="color:var(--text-muted);font-size:14px">Cargando...</div>
      <div v-else-if="inscriptos.length === 0" style="color:var(--text-muted);font-size:14px">Sin inscriptos aún.</div>
      <table v-else>
        <thead>
          <tr><th>Cliente</th><th>DNI</th><th>Tipo</th><th>Asistencia</th><th>Seña</th><th>Pagado</th></tr>
        </thead>
        <tbody>
          <tr v-for="r in inscriptos" :key="r.id">
            <td>
              {{ r.usuario?.nombre }} {{ r.usuario?.apellido }}
              </td>
            <td style="color:var(--text-muted)">{{ r.usuario?.dni }}</td>
            <td><span class="badge" :class="r.tipo === 'abonado' ? 'badge-green' : 'badge-blue'">{{ r.tipo }}</span></td>
            <td><span class="badge" :class="asistenciaBadge(r)">{{ asistenciaLabel(r) }}</span></td>
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

    <div class="card" v-if="auth.isAdmin">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
        <h3 style="font-size:20px">⏳ Lista de espera</h3>
        <span v-if="listaEspera.length >= 10" class="badge badge-red">⚠️ Alta demanda</span>
      </div>
      <p style="font-size:12px;color:var(--text-muted);margin-bottom:16px">
        Si cancela un abonado, se avisa primero a la lista de abonados (y si está vacía, a la de no abonados).
        Si cancela un no abonado, se avisa a la lista general (todos combinados por orden de inscripción).
      </p>
      <div v-if="loadingEspera" style="color:var(--text-muted);font-size:14px">Cargando...</div>
      <div v-else-if="listaEspera.length === 0" style="color:var(--text-muted);font-size:14px">Lista vacía.</div>
      <div v-else style="display:flex;flex-direction:column;gap:24px">
        <div>
          <h4 style="font-size:14px;color:var(--text-muted);margin-bottom:8px">
            Lista de abonados ({{ listaEsperaAbonados.length }})
          </h4>
          <div v-if="listaEsperaAbonados.length === 0" style="font-size:13px;color:var(--text-muted)">Vacía.</div>
          <table v-else>
            <thead>
              <tr><th>#</th><th>Cliente</th><th>Fecha inscripción</th><th>Estado</th></tr>
            </thead>
            <tbody>
              <tr v-for="(l, i) in listaEsperaAbonados" :key="l.id">
                <td>{{ i + 1 }}</td>
                <td>{{ l.usuario?.nombre }} {{ l.usuario?.apellido }}</td>
                <td style="font-size:12px;color:var(--text-muted)">{{ new Date(l.fecha_inscripcion).toLocaleDateString() }}</td>
                <td><span class="badge badge-yellow">{{ l.estado }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>

        <div>
          <h4 style="font-size:14px;color:var(--text-muted);margin-bottom:8px">
            Lista de no abonados ({{ listaEsperaNoAbonados.length }})
          </h4>
          <div v-if="listaEsperaNoAbonados.length === 0" style="font-size:13px;color:var(--text-muted)">Vacía.</div>
          <table v-else>
            <thead>
              <tr><th>#</th><th>Cliente</th><th>Fecha inscripción</th><th>Estado</th></tr>
            </thead>
            <tbody>
              <tr v-for="(l, i) in listaEsperaNoAbonados" :key="l.id">
                <td>{{ i + 1 }}</td>
                <td>{{ l.usuario?.nombre }} {{ l.usuario?.apellido }}</td>
                <td style="font-size:12px;color:var(--text-muted)">{{ new Date(l.fecha_inscripcion).toLocaleDateString() }}</td>
                <td><span class="badge badge-yellow">{{ l.estado }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>

        <div>
          <h4 style="font-size:14px;color:var(--text-muted);margin-bottom:8px">
            Lista general — abonados y no abonados combinados ({{ listaEspera.length }})
          </h4>
          <table>
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
      </div>
    </div>

    <div class="modal-overlay" v-if="modalEditarCupo" @click.self="modalEditarCupo = false">
      <div class="modal card">
        <h3>✏️ Editar cupo</h3>
        <p style="font-size:13px;color:var(--text-muted);margin-bottom:16px">
          Cupo actual: <strong>{{ clase.cupo_maximo }}</strong> ·
          Inscriptos: <strong>{{ clase.cupo_maximo - clase.cupos_disponibles }}</strong>
        </p>
        
        <form @submit.prevent="guardarCupo">
          <div class="input-group">
            <label>Nuevo cupo máximo</label>
            <input
              v-model.number="nuevoCupo"
              type="number"
              :min="clase.cupo_maximo - clase.cupos_disponibles" :max="50"
            />
            <p v-if="errorCupo" class="field-error">{{ errorCupo }}</p>
          </div>
          
          <!-- <div class="alert alert-warning" style="font-size:13px">
            No podés bajar el cupo por debajo de los inscriptos actuales ({{ clase.cupo_maximo - clase.cupos_disponibles }}).
          </div> -->
          
          <div style="display:flex;gap:10px;margin-top:12px">
            <button type="submit" class="btn btn-primary" :disabled="guardandoCupo || !isCupoValido || nuevoCupo > 50">
              {{ guardandoCupo ? 'Guardando...' : 'Guardar' }}
            </button>
            <button type="button" class="btn btn-outline" @click="modalEditarCupo = false">Cancelar</button>
          </div>
        </form>
      </div>
    </div>

    <div class="modal-overlay" v-if="confirmarCancelar" @click.self="confirmarCancelar = false">
      <div class="modal card">
        <h3>🚫 Cancelar clase</h3>
        <p style="color:var(--text-muted);margin:12px 0;font-size:14px">
          Vas a cancelar la clase de <strong>{{ clase.actividad }}</strong> del <strong>{{ formatFecha(clase.fecha) }}</strong>.
          Se procesaran devoluciones de senia, descuentos en abonos pendientes o creditos segun corresponda.
          Esta accion no elimina la clase. Estas seguro?
        </p>
        <div style="display:flex;gap:10px">
          <button class="btn btn-danger" @click="cancelarClase" :disabled="cancelando">
            {{ cancelando ? 'Cancelando...' : 'Sí, cancelar clase' }}
          </button>
          <button class="btn btn-outline" @click="confirmarCancelar = false">Volver</button>
        </div>
      </div>
    </div>

    <div class="modal-overlay" v-if="confirmarCancelarReserva && puedeCancelarMiReserva" @click.self="confirmarCancelarReserva = false">
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
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import api from '../api.js'
import FormTarjeta from '../components/FormTarjeta.vue'
import { MENSAJE_TARJETA_VENCIDA, tarjetaVencida } from '../utils/tarjetas.js'
import { MENSAJE_FONDOS_INSUFICIENTES, pagoRechazadoPorFondos } from '../utils/pagos.js'

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
const cupoReservadoParaMi = ref(false)
const cupoTokenInvalido = ref(false)
const cupoTokenInvalidoMensaje = ref('')
const listaEsperaIdToken = ref(null)
const tipoPreferenciaLista = ref(null)
const confirmandoPagoCupo = ref(false)
const montoPagoCupo = ref('senia')
const tarjetasCupo = ref([])
const loadingTarjetasCupo = ref(false)
const tarjetaSeleccionadaCupo = ref(null)
const mostrarNuevaTarjetaCupo = ref(false)
const creditosCupo = ref([])

// --- VALIDACIONES COMPUTED PARA EL CUPO ---

const errorCupo = computed(() => {
  if (!clase.value) return ''
  if (nuevoCupo.value === '' || nuevoCupo.value === null ) return 'El cupo es requerido'
  if (nuevoCupo.value > 50) return 'El cupo no puede ser mayor a 50'

  const inscriptosActuales = clase.value.cupo_maximo - clase.value.cupos_disponibles

  if (nuevoCupo.value < 0) {
    return 'El cupo no puede ser menor a 0'
  }
  if (nuevoCupo.value < inscriptosActuales) {
    return `No podés bajar el cupo por debajo de los inscriptos actuales (${inscriptosActuales})`
  }
  return ''
})

const isCupoValido = computed(() => {
  return errorCupo.value === ''
})

const creditoDisponibleCupo = computed(() => {
  if (!clase.value) return 0
  if (tipoPreferenciaLista.value !== 'no_abonado') return 0
  return creditosCupo.value.filter(c => c.actividad_id === clase.value.actividad_id && c.estado === 'disponible').length
})

const montoCupoAPagar = computed(() => {
  if (!clase.value) return 0
  if (montoPagoCupo.value === 'credito') return 0
  const precio = clase.value.precio_clase || 0
  return montoPagoCupo.value === 'total' ? precio : Math.round(precio * 0.5)
})

const creditoCupoCubreTotal = computed(() => {
  return montoPagoCupo.value === 'credito' && creditoDisponibleCupo.value > 0
})

const listaEsperaAbonados = computed(() => listaEspera.value.filter(l => l.tipo_preferencia === 'abonado'))
const listaEsperaNoAbonados = computed(() => listaEspera.value.filter(l => l.tipo_preferencia === 'no_abonado'))
const puedeCancelarMiReserva = computed(() => {
  const reserva = miReserva.value
  return reserva?.estado === 'activa' && !reserva.asistida && !reserva.falto && reservaEsFutura(reserva)
})

// --- FUNCIONES ---

function sportEmoji(nombre) {
  const map = { 'Fútbol': '⚽', 'Pádel': '🎾', 'Básquet': '🏀', 'Vóley': '🏐' }
  return map[nombre] || '🏃'
}

function formatFecha(fechaStr) {
  if (!fechaStr) return ''
  const [y, m, d] = fechaStr.split('-')
  return `${d}/${m}/${y}`
}

function mensajeCancelacion(data) {
  const partes = [data.mensaje || 'Reserva cancelada']
  if (data.info) partes.push(data.info)
  if (data.credito_generado > 0) partes.push(`Credito generado: $${data.credito_generado.toLocaleString()}`)
  if (data.creditos_devueltos > 0) partes.push(`Credito devuelto: $${data.creditos_devueltos.toLocaleString()}`)
  if (data.descuento_aplicado > 0) partes.push(`Descuento aplicado: $${data.descuento_aplicado.toLocaleString()}`)
  if (data.devolucion_senia > 0) partes.push(`Senia a devolver: $${data.devolucion_senia.toLocaleString()}`)
  if (data.advertencia) partes.push(data.advertencia)
  return partes.join(' - ')
}

function reservaEsFutura(reserva) {
  const fecha = reserva?.clase?.fecha || clase.value?.fecha
  const horaInicio = reserva?.clase?.hora_inicio || clase.value?.hora_inicio
  if (!fecha || !horaInicio) return false
  const hora = String(horaInicio)
  const horaNormalizada = hora.length === 5 ? `${hora}:00` : hora
  return new Date(`${fecha}T${horaNormalizada}`) > new Date()
}

function asistenciaLabel(reserva) {
  if (reserva?.asistida) return 'Asistió'
  if (reserva?.falto) return 'Faltó'
  return 'Pendiente'
}

function asistenciaBadge(reserva) {
  if (reserva?.asistida) return 'badge-green'
  if (reserva?.falto) return 'badge-red'
  return 'badge-yellow'
}

function abrirEditarCupo() {
  nuevoCupo.value = clase.value.cupo_maximo
  modalEditarCupo.value = true
}

async function fetchClase() {
  loadingClase.value = true
  try {
    const { data } = await api.get(`/clases/${route.params.id}`)
    clase.value = data
    nuevoCupo.value = data.cupo_maximo // Seteado de forma segura dentro del try
  } catch (e) {
    error.value = 'No se pudo cargar la clase'
  } finally {
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
      mensaje.value = data.credito_usado > 0
        ? `Reserva creada exitosamente. Se aplico credito por $${data.credito_usado.toLocaleString()}.`
        : 'Reserva creada exitosamente. Podés pagar la seña desde "Mis pagos".'
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
  if (!isCupoValido.value) return
  guardandoCupo.value = true
  error.value = ''
  try {
    await api.put(`/clases/${route.params.id}`, { cupo_maximo: nuevoCupo.value })
    mensaje.value = 'Cupo actualizado correctamente'
    modalEditarCupo.value = false
    await fetchClase()
  } catch (e) {
    error.value = e.response?.data?.error
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
  if (!puedeCancelarMiReserva.value) {
    confirmarCancelarReserva.value = false
    return
  }
  cancelandoReserva.value = true
  error.value = ''
  try {
    const { data } = await api.post(`/reservas/${miReserva.value.id}/cancelar`)
    mensaje.value = mensajeCancelacion(data)
    confirmarCancelarReserva.value = false
    miReserva.value = null
    await fetchClase()
  } catch (e) {
    error.value = e.response?.data?.error || 'Error al cancelar reserva'
  } finally {
    cancelandoReserva.value = false
  }
}

async function verificarTokenLista() {
  const listaEsperaId = route.query.lista_espera_id
  const token = route.query.lista_token
  if (!listaEsperaId || !token || !auth.isCliente) return

  listaEsperaIdToken.value = listaEsperaId
  try {
    const { data } = await api.get(`/reservas/lista-espera/${listaEsperaId}/verificar`, {
      params: { token }
    })
    if (data.valido) {
      cupoReservadoParaMi.value = true
      cupoTokenInvalido.value = false
      tipoPreferenciaLista.value = data.tipo_preferencia
      montoPagoCupo.value = 'senia'
      confirmandoPagoCupo.value = false
      await fetchCreditosCupo()
    } else {
      cupoReservadoParaMi.value = false
      cupoTokenInvalido.value = true
      cupoTokenInvalidoMensaje.value = mensajeTokenInvalido(data.motivo)
    }
  } catch {
    cupoReservadoParaMi.value = false
    cupoTokenInvalido.value = true
    cupoTokenInvalidoMensaje.value = 'No pudimos verificar tu invitación. Probá entrar de nuevo desde el link del email.'
  }
}

function mensajeTokenInvalido(motivo) {
  const mensajes = {
    otro_usuario: 'Este link es para otra cuenta. Iniciá sesión con la cuenta a la que le llegó el aviso.',
    ya_reservado: 'Ya confirmaste este cupo anteriormente.',
    ya_rechazado: 'Ya rechazaste este cupo. Se le ofreció a la siguiente persona en la lista.',
    no_pendiente: 'Esta invitación ya no está disponible.',
    expirado: 'El link de invitación venció.',
    invalido: 'No pudimos verificar este link de invitación.'
  }
  return mensajes[motivo] || mensajes.invalido
}

async function fetchTarjetasCupo() {
  loadingTarjetasCupo.value = true
  try {
    const { data } = await api.get('/auth/tarjetas')
    tarjetasCupo.value = data
    if (data.length > 0) tarjetaSeleccionadaCupo.value = data[0]
  } catch {
    tarjetasCupo.value = []
  } finally {
    loadingTarjetasCupo.value = false
  }
}

async function fetchCreditosCupo() {
  try {
    const { data } = await api.get('/creditos/mis')
    creditosCupo.value = data
  } catch {
    creditosCupo.value = []
  }
}

function onTarjetaGuardadaCupo(t) {
  tarjetasCupo.value.push(t)
  tarjetaSeleccionadaCupo.value = t
  mostrarNuevaTarjetaCupo.value = false
}

async function irAPagarCupo() {
  confirmandoPagoCupo.value = true
  if (montoPagoCupo.value !== 'credito') {
    await fetchTarjetasCupo()
  }
}

async function aceptarCupoLista() {
  error.value = ''
  if (montoCupoAPagar.value > 0 && pagoRechazadoPorFondos(auth.user)) {
    error.value = MENSAJE_FONDOS_INSUFICIENTES
    return
  }
  if (montoCupoAPagar.value > 0 && tarjetaSeleccionadaCupo.value && tarjetaVencida(tarjetaSeleccionadaCupo.value.vencimiento)) {
    error.value = MENSAJE_TARJETA_VENCIDA
    return
  }

  reservandoLoading.value = true
  try {
    const tipo = tipoPreferenciaLista.value || 'no_abonado'
    const usarCredito = montoPagoCupo.value === 'credito'
    const montoPagar = usarCredito ? 'total' : montoPagoCupo.value
    // El metodo_pago solo se manda si realmente hay un cobro: con tarjeta
    // cuando corresponde, o ninguno si el credito cubre todo. Asi evitamos
    // registrar pagos fantasma cuando no hubo una confirmacion real.
    const metodoPago = montoCupoAPagar.value > 0 ? 'tarjeta_credito' : null

    const { data } = await api.post('/reservas/', {
      clase_id: parseInt(route.params.id),
      tipo,
      monto_pagar: montoPagar,
      metodo_pago: metodoPago,
      usar_credito: usarCredito
    })
    if (data.en_espera) {
      mensaje.value = data.mensaje
    } else {
      mensaje.value = montoPagoCupo.value === 'senia'
        ? 'Reserva confirmada y seña pagada. El resto lo abonás al llegar a la clase.'
        : 'Reserva confirmada y pago realizado con éxito.'
      miReserva.value = data.reserva
      cupoReservadoParaMi.value = false
    }
    await fetchClase()
  } catch (e) {
    error.value = e.response?.data?.error || 'Error al confirmar la reserva'
  } finally {
    reservandoLoading.value = false
  }
}

async function rechazarCupoLista() {
  if (!listaEsperaIdToken.value) return
  reservandoLoading.value = true
  error.value = ''
  try {
    const { data } = await api.post(`/reservas/lista-espera/${listaEsperaIdToken.value}/rechazar-app`)
    cupoReservadoParaMi.value = false
    mensaje.value = data.mensaje || 'Rechazaste el cupo. Se lo ofrecimos a la siguiente persona en la lista de espera.'
  } catch (e) {
    error.value = e.response?.data?.error || 'No se pudo rechazar el cupo. Probá desde el link del email.'
  } finally {
    reservandoLoading.value = false
  }
}

onMounted(async () => {
  await fetchClase()
  await Promise.all([fetchMiReserva(), fetchInscriptos(), fetchListaEspera()])
  await verificarTokenLista()
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
.field-error { font-size: 12px; color: var(--danger); margin-top: 4px; }
.cupo-reservado-card { border-color: var(--verde-claro); background: rgba(46,125,50,0.08); }
.back-btn { background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:13px;margin-bottom:16px;display:flex;align-items:center;gap:4px;font-family:'DM Sans',sans-serif; }
.back-btn:hover { color:var(--text); }
.pago-opciones { max-width:440px; }
.pago-opcion { display:flex;align-items:flex-start;gap:12px;padding:14px 16px;background:var(--dark-2);border:2px solid var(--border);border-radius:10px;cursor:pointer;margin-bottom:10px;transition:all 0.2s; }
.pago-opcion:hover { border-color:var(--verde); }
.pago-opcion.selected { border-color:var(--verde-claro);background:rgba(46,125,50,0.08); }
.pago-radio { font-size:18px;color:var(--verde-claro);flex-shrink:0;margin-top:2px; }
.tarjeta-opcion { display:flex;align-items:center;gap:14px;padding:14px 16px;background:var(--dark-3);border:2px solid var(--border);border-radius:10px;cursor:pointer;transition:all 0.2s;margin-bottom:8px; }
.tarjeta-opcion:hover { border-color:var(--verde); }
.tarjeta-opcion.selected { border-color:var(--verde-claro);background:rgba(46,125,50,0.08); }
.tarjeta-icon { font-size:24px; }
.tarjeta-check { margin-left:auto;color:var(--verde-claro);font-size:18px;font-weight:700; }
</style>
