<template>
  <div>
    <div class="page-header" style="display:flex;align-items:center;justify-content:space-between">
      <div>
        <h2>GESTIÓN DE USUARIOS</h2>
        <p>Ver y administrar clientes y empleados</p>
      </div>
      <button class="btn btn-primary" v-if="auth.isAdmin" @click="modalRegistrar = true">+ Nuevo Empleado</button>
    </div>

    <div class="card filters-bar" style="margin-bottom:24px">
      <div style="display:flex;gap:12px">
        <div class="input-group" style="margin:0;flex:1">
          <input v-model="busqueda" placeholder="Buscar por nombre, apellido, DNI o email..." @input="fetchUsuarios" />
        </div>
        <div class="input-group" style="margin:0">
          <select v-model="filtroRol" @change="fetchUsuarios">
            <option value="">Todos los roles</option>
            <option value="cliente">Clientes</option>
            <option value="empleado">Empleados</option>
            <option value="administrador">Administradores</option>
          </select>
        </div>
      </div>
    </div>

    <div class="alert alert-error" v-if="error">{{ error }}</div>

    <div class="card" style="overflow:auto">
      <table>
        <thead>
          <tr><th>Nombre</th><th>DNI</th><th>Email</th><th>Rol</th><th>Suspensiones</th><th>Acciones</th></tr>
        </thead>
        <tbody>
          <tr v-for="u in usuarios" :key="u.id">
            <td>{{ u.nombre }} {{ u.apellido }}</td>
            <td>{{ u.dni }}</td>
            <td>{{ u.email }}</td>
            <td><span class="badge" :class="rolBadge(u.rol)">{{ u.rol }}</span></td>
            <td>
              <span v-if="u.suspensiones_activas?.length" class="badge badge-red">{{ u.suspensiones_activas.length }} activa(s)</span>
              <span v-else class="badge badge-green">OK</span>
            </td>
            <td>
              <button class="btn btn-outline btn-sm" @click="verDetalle(u)">Ver detalle</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal detalle usuario -->
    <div class="modal-overlay" v-if="detalleModal" @click.self="detalleModal = null">
      <div class="modal card" style="max-width:560px">
        <div style="display:flex;gap:12px;align-items:center;margin-bottom:20px">
          <div class="avatar-lg">{{ detalleModal.nombre?.charAt(0) }}</div>
          <div>
            <h3>{{ detalleModal.nombre }} {{ detalleModal.apellido }}</h3>
            <p style="color:var(--text-muted);font-size:14px">{{ detalleModal.email }}</p>
            <span class="badge" :class="rolBadge(detalleModal.rol)">{{ detalleModal.rol }}</span>
          </div>
        </div>
        <div class="grid-2" style="margin-bottom:16px">
          <div class="detalle-item"><span class="label">DNI</span><span>{{ detalleModal.dni }}</span></div>
          <div class="detalle-item"><span class="label">Miembro desde</span><span>{{ new Date(detalleModal.fecha_registro).toLocaleDateString() }}</span></div>
        </div>
        <div v-if="detalleModal.suspensiones_activas?.length">
          <h4 style="margin-bottom:12px;color:var(--danger)">⚠️ Suspensiones activas</h4>
          <div v-for="s in detalleModal.suspensiones_activas" :key="s.id" class="suspension-item">
            <span class="badge badge-red">{{ s.tipo }}</span>
            <span style="font-size:13px">{{ s.motivo }}</span>
            <span style="color:var(--warning);font-weight:600">Deuda: ${{ s.monto_deuda?.toLocaleString() }}</span>
          </div>
        </div>
        <button class="btn btn-outline btn-sm" style="margin-top:16px" @click="detalleModal = null">Cerrar</button>
      </div>
    </div>

    <!-- Modal registrar empleado -->
    <div class="modal-overlay" v-if="modalRegistrar" @click.self="modalRegistrar = false">
      <div class="modal card">
        <h3>Registrar Empleado</h3>
        <div class="alert alert-error" v-if="regError">{{ regError }}</div>
        <div class="grid-2">
          <div class="input-group"><label>Nombre</label><input v-model="regForm.nombre" /></div>
          <div class="input-group"><label>Apellido</label><input v-model="regForm.apellido" /></div>
        </div>
        <div class="input-group"><label>DNI</label><input v-model="regForm.dni" /></div>
        <div class="input-group"><label>Email</label><input v-model="regForm.email" type="email" /></div>
        <div class="input-group"><label>Contraseña</label><input v-model="regForm.password" type="password" /></div>
        <div style="display:flex;gap:10px">
          <button class="btn btn-primary" @click="registrarEmpleado" :disabled="regLoading">
            {{ regLoading ? 'Registrando...' : 'Registrar' }}
          </button>
          <button class="btn btn-outline" @click="modalRegistrar = false">Cancelar</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../../stores/auth.js'
import api from '../../api.js'

const auth = useAuthStore()
const usuarios = ref([])
const busqueda = ref('')
const filtroRol = ref('')
const error = ref('')
const detalleModal = ref(null)
const modalRegistrar = ref(false)
const regForm = ref({ nombre:'', apellido:'', dni:'', email:'', password:'', rol:'empleado' })
const regError = ref(''), regLoading = ref(false)

function rolBadge(rol) {
  return { 'administrador':'badge-green', 'empleado':'badge-blue', 'cliente':'badge-yellow' }[rol] || 'badge-yellow'
}

async function fetchUsuarios() {
  const params = {}
  if (busqueda.value) params.q = busqueda.value
  if (filtroRol.value) params.rol = filtroRol.value
  const { data } = await api.get('/usuarios/', { params })
  usuarios.value = data
}

async function verDetalle(u) {
  const { data } = await api.get(`/usuarios/${u.id}`)
  detalleModal.value = data
}

async function registrarEmpleado() {
  regLoading.value = true
  regError.value = ''
  try {
    await api.post('/auth/register', regForm.value)
    modalRegistrar.value = false
    fetchUsuarios()
  } catch (e) {
    regError.value = e.response?.data?.error || 'Error al registrar'
  } finally {
    regLoading.value = false
  }
}

onMounted(fetchUsuarios)
</script>

<style scoped>
.filters-bar { padding: 16px 24px; }
.modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.7); display:flex; align-items:center; justify-content:center; z-index:200; }
.modal { max-width:480px; width:100%; }
.modal h3 { font-size:22px; margin-bottom:20px; }
.avatar-lg {
  width: 56px; height: 56px;
  background: linear-gradient(135deg, var(--verde), var(--azul));
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 22px; font-weight: 700; flex-shrink: 0;
}
.detalle-item { display:flex; flex-direction:column; gap:4px; }
.label { font-size:11px; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.5px; }
.suspension-item { display:flex; align-items:center; gap:10px; padding:10px; background:var(--dark-3); border-radius:6px; margin-bottom:8px; font-size:14px; }
</style>
