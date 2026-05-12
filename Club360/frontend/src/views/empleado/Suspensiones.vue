<template>
  <div>
    <div class="page-header">
      <h2>SUSPENSIONES</h2>
      <p>Gestión de clientes suspendidos y retiros de suspensión</p>
    </div>

    <div class="alert alert-success" v-if="msg">{{ msg }}</div>
    <div class="alert alert-error" v-if="err">{{ err }}</div>

    <div class="tabs" style="margin-bottom:24px">
      <button class="tab-btn" :class="{ active: tab === 'activas' }" @click="tab = 'activas'; fetchSuspensiones()">
        Activas
      </button>
      <button class="tab-btn" :class="{ active: tab === 'historico' }" @click="tab = 'historico'; fetchSuspensiones(false)">
        Historial
      </button>
    </div>

    <div v-if="loading" class="loading-text">Cargando...</div>

    <div v-else-if="suspensiones.length === 0" class="empty-state">
      <p style="font-size:40px">✅</p>
      <p>{{ tab === 'activas' ? 'No hay suspensiones activas' : 'Sin historial' }}</p>
    </div>

    <div v-else class="card" style="overflow:auto">
      <table>
        <thead>
          <tr>
            <th>Cliente</th><th>Tipo</th><th>Motivo</th><th>Deuda</th><th>Fecha</th><th v-if="tab==='activas'">Acciones</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in suspensiones" :key="s.id">
            <td>ID #{{ s.usuario_id }}</td>
            <td><span class="badge" :class="s.tipo === 'abonado' ? 'badge-green' : 'badge-blue'">{{ s.tipo }}</span></td>
            <td style="font-size:13px;color:var(--text-muted);max-width:260px">{{ s.motivo || '—' }}</td>
            <td>
              <span style="color:var(--warning);font-weight:600">${{ s.monto_deuda?.toLocaleString() }}</span>
            </td>
            <td style="font-size:12px;color:var(--text-muted)">
              {{ new Date(s.fecha_creacion).toLocaleDateString() }}
            </td>
            <td v-if="tab==='activas'">
              <button class="btn btn-primary btn-sm" @click="abrirRetiro(s)">
                Levantar suspensión
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal levantar suspensión -->
    <div class="modal-overlay" v-if="retiroModal" @click.self="retiroModal = null">
      <div class="modal card">
        <h3>Levantar Suspensión</h3>
        <p style="color:var(--text-muted);font-size:14px;margin-bottom:16px">
          Cliente ID #{{ retiroModal.usuario_id }} — Tipo: {{ retiroModal.tipo }}
        </p>
        <div class="alert alert-warning">
          Deuda a regularizar: <strong>${{ retiroModal.monto_deuda?.toLocaleString() }}</strong>
          (incluye recargo del 5%)
        </div>
        <div class="input-group" style="margin-top:16px">
          <label>Método de pago</label>
          <select v-model="retiroMetodo">
            <option value="efectivo">Efectivo (en sede)</option>
            <option value="tarjeta_credito">Tarjeta de crédito</option>
          </select>
        </div>
        <div style="display:flex;gap:10px;margin-top:8px">
          <button class="btn btn-primary" @click="ejecutarRetiro" :disabled="retiroLoading">
            {{ retiroLoading ? 'Procesando...' : 'Confirmar levantamiento' }}
          </button>
          <button class="btn btn-outline" @click="retiroModal = null">Cancelar</button>
        </div>
      </div>
    </div>

    <!-- Panel: Crear suspensión manual (admin) -->
    <div class="card" style="margin-top:32px" v-if="auth.isAdmin">
      <h3 style="font-size:20px;margin-bottom:16px">Crear suspensión manual</h3>
      <p style="font-size:13px;color:var(--text-muted);margin-bottom:16px">
        El sistema crea suspensiones automáticamente, pero también podés crearlas manualmente.
      </p>
      <div class="grid-2">
        <div class="input-group">
          <label>ID de Usuario</label>
          <input v-model.number="nuevaSusp.usuario_id" type="number" placeholder="ID del cliente" />
        </div>
        <div class="input-group">
          <label>Tipo</label>
          <select v-model="nuevaSusp.tipo">
            <option value="abonado">Abonado</option>
            <option value="no_abonado">No abonado</option>
          </select>
        </div>
      </div>
      <div class="input-group">
        <label>Motivo</label>
        <input v-model="nuevaSusp.motivo" placeholder="Motivo de la suspensión" />
      </div>
      <div class="input-group">
        <label>Monto de deuda ($)</label>
        <input v-model.number="nuevaSusp.monto_deuda" type="number" />
      </div>
      <button class="btn btn-danger" @click="crearSuspension" :disabled="creandoLoading">
        {{ creandoLoading ? 'Creando...' : 'Crear suspensión' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../../stores/auth.js'
import api from '../../api.js'

const auth = useAuthStore()
const suspensiones = ref([])
const loading = ref(false)
const tab = ref('activas')
const msg = ref(''), err = ref('')
const retiroModal = ref(null)
const retiroMetodo = ref('efectivo')
const retiroLoading = ref(false)
const nuevaSusp = ref({ usuario_id: '', tipo: 'abonado', motivo: '', monto_deuda: 0 })
const creandoLoading = ref(false)

async function fetchSuspensiones(activas = true) {
  loading.value = true
  try {
    const { data } = await api.get('/suspensiones/', { params: { activas } })
    suspensiones.value = data
  } catch (e) {
    err.value = 'Error al cargar suspensiones'
  } finally {
    loading.value = false
  }
}

function abrirRetiro(s) {
  retiroModal.value = s
  retiroMetodo.value = 'efectivo'
}

async function ejecutarRetiro() {
  retiroLoading.value = true
  err.value = ''
  try {
    await api.post(`/suspensiones/solicitar-retiro/${retiroModal.value.id}`, { metodo: retiroMetodo.value })
    msg.value = 'Suspensión levantada correctamente'
    retiroModal.value = null
    fetchSuspensiones()
  } catch (e) {
    err.value = e.response?.data?.error || 'Error al levantar suspensión'
  } finally {
    retiroLoading.value = false
  }
}

async function crearSuspension() {
  creandoLoading.value = true
  err.value = ''
  try {
    await api.post('/suspensiones/', nuevaSusp.value)
    msg.value = 'Suspensión creada'
    nuevaSusp.value = { usuario_id: '', tipo: 'abonado', motivo: '', monto_deuda: 0 }
    fetchSuspensiones()
  } catch (e) {
    err.value = e.response?.data?.error || 'Error al crear suspensión'
  } finally {
    creandoLoading.value = false
  }
}

onMounted(() => fetchSuspensiones())
</script>

<style scoped>
.tabs { display:flex; gap:4px; border-bottom:1px solid var(--border); padding-bottom:0; }
.tab-btn {
  padding: 8px 20px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-muted);
  cursor: pointer;
  font-family: 'DM Sans', sans-serif;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: -1px;
  transition: all 0.2s;
}
.tab-btn.active { color: var(--verde-claro); border-bottom-color: var(--verde-claro); }
.loading-text, .empty-state { text-align:center; padding:60px; color:var(--text-muted); }
.modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.7); display:flex; align-items:center; justify-content:center; z-index:200; }
.modal { max-width:460px; width:100%; }
.modal h3 { font-size:22px; margin-bottom:16px; }
</style>
