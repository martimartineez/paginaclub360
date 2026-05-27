<template>
  <div>
    <div class="page-header">
      <h2>MIS PAGOS</h2>
      <p>Gestioná tus pagos pendientes y revisá tu historial</p>
    </div>

    <div v-if="loading" class="loading-text">Cargando pagos...</div>

    <template v-else>
      <div class="seccion">
        <div class="seccion-header">
          <h3>⏳ Pagos pendientes</h3>
          <span class="badge badge-red" v-if="pendientes.length">{{ pendientes.length }}</span>
          <span class="badge badge-green" v-else>Al día</span>
        </div>

        <div v-if="pendientes.length === 0" class="empty-card card">
          <span style="font-size:40px">✅</span>
          <p>No tenés pagos pendientes.</p>
        </div>

        <div v-else class="pagos-lista">
          <div v-for="item in pendientes" :key="item.tipo === 'abonado' ? 'abono-' + item.abono_id : 'reserva-' + item.reserva_id" class="pago-card card">
            <div class="pago-header">
              <span class="sport-emoji">{{ sportEmoji(item.actividad) }}</span>
              <div class="pago-info">
                <div class="pago-titulo">
                  <h4>{{ item.actividad }}</h4>
                  <span class="badge" :class="item.tipo === 'abonado' ? 'badge-green' : 'badge-blue'">
                    {{ item.tipo === 'abonado' ? 'Abono Mensual' : 'Clase suelta' }}
                  </span>
                </div>
                <p class="pago-fecha">
                  {{ item.dia_semana }} <span v-if="item.fecha_clase">· {{ formatFecha(item.fecha_clase) }}</span> · {{ item.hora_inicio }} hs
                </p>
              </div>
              <div class="pago-monto-col">
                <span class="monto-deuda">${{ item.deuda?.toLocaleString() }}</span>
                <span class="monto-label">pendiente</span>
              </div>
            </div>

            <div class="pago-progreso">
              <div class="progreso-barra">
                <div
                  class="progreso-fill"
                  :style="{ width: progresoWidth(item) + '%' }"
                ></div>
              </div>
              <span class="progreso-txt">
                ${{ item.monto_pagado?.toLocaleString() }} de ${{ item.monto_total?.toLocaleString() }} pagado
              </span>
            </div>

            <div v-if="item.vence_dia_10" class="alert alert-warning" style="font-size:13px;padding:8px 12px">
              📅 Tenés hasta el <strong>día 10</strong> de este mes para pagar este abono.
            </div>

            <!-- <div class="pago-detalle-label">{{ item.deuda_label }}</div> -->

            <div class="pago-acciones">
              <template v-if="item.tipo === 'abonado'">
                <button
                  class="btn btn-primary btn-sm"
                  @click="abrirPagoAbono(item)"
                >
                  💳 Pagar 
                </button>
              </template>

              <template v-else>
                <button
                  v-if="!item.senia_pagada"
                  class="btn btn-secondary btn-sm"
                  @click="abrirPagoIndividual(item, 'senia')"
                >
                  💳 Pagar 
                </button>
                <!-- <button
                  v-if="!item.senia_pagada"
                  class="btn btn-primary btn-sm"
                  @click="abrirPagoIndividual(item, 'total')"
                >
                  💳 Pagar total ${{ item.monto_total?.toLocaleString() }}
                </button> -->
                <!-- <button
                  v-if="item.senia_pagada && item.deuda > 0"
                  class="btn btn-primary btn-sm"
                  @click="abrirPagoIndividual(item, 'restante')"
                >
                  💳 Pagar restante ${{ item.deuda?.toLocaleString() }}
                </button> -->
              </template>
            </div>
          </div>
        </div>
      </div>

      <div class="seccion" style="margin-top:32px">
        <div class="seccion-header">
          <h3>✅ Pagado</h3>
          <span class="badge badge-blue">{{ pagados.length }}</span>
        </div>

        <div v-if="pagados.length === 0" class="empty-card card">
          <p style="color:var(--text-muted)">No hay pagos registrados aún.</p>
        </div>

        <div v-else class="pagos-lista">
          <div v-for="item in pagados" :key="item.tipo === 'abonado' ? 'abono-' + item.abono_id : 'reserva-' + item.reserva_id" class="pago-card card pago-pagado">
            <div class="pago-header">
              <span class="sport-emoji">{{ sportEmoji(item.actividad) }}</span>
              <div class="pago-info">
                <div class="pago-titulo">
                  <h4>{{ item.actividad }}</h4>
                  <span class="badge" :class="item.tipo === 'abonado' ? 'badge-green' : 'badge-blue'">
                    {{ item.tipo === 'abonado' ? 'Abono Mensual' : 'Clase suelta' }}
                  </span>
                  <span v-if="item.estado === 'cancelada'" class="badge badge-red">Cancelada</span>
                </div>
                <p class="pago-fecha">
                  {{ item.dia_semana }} <span v-if="item.fecha_clase">· {{ formatFecha(item.fecha_clase) }}</span> · {{ item.hora_inicio }} hs
                </p>
              </div>
              <div class="pago-monto-col">
                <span class="monto-pagado-ok">${{ item.monto_pagado?.toLocaleString() }}</span>
                <span class="monto-label">pagado</span>
              </div>
            </div>

            <div class="pago-progreso">
              <div class="progreso-barra">
                <div class="progreso-fill progreso-completo" style="width:100%"></div>
              </div>
              <span class="progreso-txt">
                ${{ item.monto_pagado?.toLocaleString() }} de ${{ item.monto_total?.toLocaleString() }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <div class="modal-overlay" v-if="pagoModal" @click.self="pagoModal = null">
      <div class="modal card">
        <h3>💳 Pagar con tarjeta de crédito</h3>
        <p style="color:var(--text-muted);font-size:14px;margin-bottom:16px">
          {{ pagoModal.actividad }} ·
          {{ pagoModal.tipo === 'abonado' ? 'Abono Mensual' : 'Clase suelta' }}
          <span v-if="pagoModal.fecha_clase"> · {{ formatFecha(pagoModal.fecha_clase) }}</span>
        </p>

        <div class="alert alert-warning" style="margin-bottom:16px">
          Monto a pagar: <strong>${{ montoModalPago?.toLocaleString() }}</strong>
        </div>

        <div class="alert alert-error" v-if="errPago">{{ errPago }}</div>

        <div v-if="tarjetas.length === 0">
          <p style="font-size:13px;color:var(--text-muted);margin-bottom:12px">
            No tenés tarjetas registradas. Agregá una:
          </p>
          <FormTarjeta label-boton="Guardar tarjeta" :show-cancelar="true"
            @guardada="onTarjetaGuardada" @cancelar="pagoModal = null" />
        </div>

        <div v-else>
          <p style="font-size:13px;color:var(--text-muted);margin-bottom:10px">Seleccioná una tarjeta:</p>
          <div
            v-for="t in tarjetas" :key="t.id"
            class="tarjeta-opcion"
            :class="{ selected: tarjetaSeleccionada?.id === t.id }"
            @click="tarjetaSeleccionada = t"
          >
            <span style="font-size:22px">💳</span>
            <div>
              <p style="font-weight:600;font-size:14px">•••• •••• •••• {{ t.ultimos_4 }}</p>
              <p style="font-size:12px;color:var(--text-muted)">{{ t.titular }} · Vence {{ t.vencimiento }}</p>
            </div>
            <span v-if="tarjetaSeleccionada?.id === t.id" style="margin-left:auto;color:var(--verde-claro);font-weight:700">✓</span>
          </div>

          <div v-if="!mostrarNuevaTarjeta">
            <button class="btn btn-outline btn-sm" style="margin-top:10px" @click="mostrarNuevaTarjeta = true">
              + Usar otra tarjeta
            </button>
          </div>
          <div v-else style="margin-top:14px;padding-top:14px;border-top:1px solid var(--border)">
            <FormTarjeta label-boton="Guardar tarjeta"
              @guardada="onTarjetaGuardada" @cancelar="mostrarNuevaTarjeta = false" />
          </div>

          <div style="display:flex;gap:10px;margin-top:20px">
            <button
              class="btn btn-primary"
              @click="ejecutarPago"
              :disabled="!tarjetaSeleccionada || procesando"
              style="flex:1"
            >
              {{ procesando ? 'Procesando...' : `Pagar $${montoModalPago?.toLocaleString()}` }}
            </button>
            <button class="btn btn-outline" @click="pagoModal = null">Cancelar</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../api.js'
import FormTarjeta from '../components/FormTarjeta.vue'

const loading = ref(true)
const pendientes = ref([])
const pagados = ref([])
const tarjetas = ref([])
const tarjetaSeleccionada = ref(null)
const mostrarNuevaTarjeta = ref(false)
const pagoModal = ref(null)
const tipoModalPago = ref(null)
const procesando = ref(false)
const errPago = ref('')

const montoModalPago = computed(() => {
  if (!pagoModal.value) return 0
  const item = pagoModal.value
  if (tipoModalPago.value === 'senia') return Math.round(item.monto_total * 0.5)
  if (tipoModalPago.value === 'total') return item.monto_total
  if (tipoModalPago.value === 'restante') return item.deuda
  if (tipoModalPago.value === 'abono') return item.deuda
  return item.deuda
})

function sportEmoji(nombre) {
  return { 'Fútbol': '⚽', 'Pádel': '🎾', 'Básquet': '🏀', 'Vóley': '🏐' }[nombre] || '🏃'
}

function formatFecha(fechaStr) {
  if (!fechaStr) return ''
  const [y, m, d] = fechaStr.split('-')
  return `${d}/${m}/${y}`
}

function progresoWidth(item) {
  if (!item.monto_total) return 0
  return Math.min(100, (item.monto_pagado / item.monto_total) * 100)
}

async function fetchPagos() {
  loading.value = true
  try {
    const { data } = await api.get('/reservas/pagos-resumen')
    pendientes.value = data.pendientes
    pagados.value = data.pagados
  } catch (e) {
    console.error('Error al cargar pagos', e)
  } finally {
    loading.value = false
  }
}

async function fetchTarjetas() {
  try {
    const { data } = await api.get('/auth/tarjetas')
    tarjetas.value = data
    if (data.length > 0) tarjetaSeleccionada.value = data[0]
  } catch {}
}

function abrirPagoAbono(item) {
  pagoModal.value = item
  tipoModalPago.value = 'abono'
  errPago.value = ''
  mostrarNuevaTarjeta.value = false
}

function abrirPagoIndividual(item, tipo) {
  pagoModal.value = item
  tipoModalPago.value = tipo
  errPago.value = ''
  mostrarNuevaTarjeta.value = false
}

function onTarjetaGuardada(t) {
  tarjetas.value.push(t)
  tarjetaSeleccionada.value = t
  mostrarNuevaTarjeta.value = false
}

async function ejecutarPago() {
  if (!tarjetaSeleccionada.value) return
  procesando.value = true
  errPago.value = ''
  try {
    const monto = montoModalPago.value
    
    if (pagoModal.value.tipo === 'abonado') {
      // Pega al nuevo endpoint para pagar la suscripción global
      await api.post(`/reservas/abono/${pagoModal.value.abono_id}/pagar`, {
        metodo: 'tarjeta_credito',
        monto
      })
    } else {
      // Mantiene el flujo clásico para las clases individuales sueltas
      let tipoPago = 'mensualidad'
      if (tipoModalPago.value === 'senia') tipoPago = 'senia'
      
      await api.post(`/reservas/${pagoModal.value.reserva_id}/pagar`, {
        metodo: 'tarjeta_credito',
        monto,
        tipo_pago: tipoPago
      })
    }

    pagoModal.value = null
    tarjetaSeleccionada.value = tarjetas.value[0] || null
    await fetchPagos()
  } catch (e) {
    errPago.value = e.response?.data?.error || 'Error al procesar el pago'
  } finally {
    procesando.value = false
  }
}

onMounted(async () => {
  await Promise.all([fetchPagos(), fetchTarjetas()])
})
</script>

<style scoped>
.seccion-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}
.seccion-header h3 {
  font-size: 22px;
  font-family: 'Bebas Neue', sans-serif;
  letter-spacing: 1px;
}

.empty-card {
  text-align: center;
  padding: 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: var(--text-muted);
}

.pagos-lista { display: flex; flex-direction: column; gap: 14px; }

.pago-card { transition: border-color 0.2s; }
.pago-pagado { opacity: 0.75; }

.pago-header {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  margin-bottom: 14px;
}

.sport-emoji { font-size: 32px; flex-shrink: 0; }

.pago-info { flex: 1; }
.pago-titulo {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 4px;
}
.pago-titulo h4 {
  font-size: 18px;
  font-family: 'Bebas Neue', sans-serif;
  letter-spacing: 0.5px;
}
.pago-fecha { font-size: 13px; color: var(--text-muted); text-transform: capitalize; }

.pago-monto-col {
  flex-shrink: 0;
  text-align: right;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}
.monto-deuda {
  font-size: 22px;
  font-family: 'Bebas Neue', sans-serif;
  color: var(--danger);
}
.monto-pagado-ok {
  font-size: 22px;
  font-family: 'Bebas Neue', sans-serif;
  color: var(--success);
}
.monto-label { font-size: 11px; color: var(--text-muted); }

.pago-progreso { margin-bottom: 10px; }
.progreso-barra {
  height: 4px;
  background: var(--dark-3);
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 4px;
}
.progreso-fill {
  height: 100%;
  background: var(--verde);
  border-radius: 2px;
  transition: width 0.4s;
}
.progreso-completo { background: var(--success); }
.progreso-txt { font-size: 11px; color: var(--text-muted); }

.pago-detalle-label {
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 12px;
  padding: 8px 12px;
  background: var(--dark-3);
  border-radius: 6px;
}

.pago-acciones { display: flex; gap: 8px; flex-wrap: wrap; }

.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.7);
  display: flex; align-items: center; justify-content: center;
  z-index: 200;
}
.modal { max-width: 460px; width: 100%; }
.modal h3 { font-size: 22px; margin-bottom: 8px; }

.tarjeta-opcion {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 14px;
  background: var(--dark-3);
  border: 2px solid var(--border);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 8px;
}
.tarjeta-opcion:hover { border-color: var(--verde); }
.tarjeta-opcion.selected { border-color: var(--verde-claro); background: rgba(46,125,50,0.08); }

.loading-text { text-align: center; padding: 60px; color: var(--text-muted); }
</style>