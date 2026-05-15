<template>
  <div>
    <div class="page-header" style="display:flex;align-items:center;justify-content:space-between">
      <div>
        <h2>GESTIÓN DE USUARIOS</h2>
        <p>Ver y administrar clientes y empleados</p>
      </div>
      <div style="display:flex;gap:10px">
        <!-- Tanto admin como empleado pueden cargar clientes -->
        <button class="btn btn-primary" @click="abrirRegistro('cliente')">+ Nuevo Cliente</button>
        <!-- Solo admin puede cargar empleados -->
        <button class="btn btn-secondary" v-if="auth.isAdmin" @click="abrirRegistro('empleado')">+ Nuevo Empleado</button>
      </div>
    </div>

    <div class="card filters-bar" style="margin-bottom:24px">
      <div style="display:flex;gap:12px;flex-wrap:wrap">
        <div class="input-group" style="margin:0;flex:1;min-width:200px">
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

    <div class="alert alert-success" v-if="regMsg">{{ regMsg }}</div>
    <div class="alert alert-error" v-if="error">{{ error }}</div>

    <div class="card" style="overflow:auto">
      <table>
        <thead>
          <tr><th>Nombre</th><th>DNI</th><th>Email</th><th>Rol</th><th>Suspensiones</th><th>Acciones</th></tr>
        </thead>
        <tbody>
          <tr v-for="u in usuarios" :key="u.id">
            <td>{{ u.nombre }} {{ u.apellido }}</td>
            <td style="color:var(--text-muted)">{{ u.dni }}</td>
            <td style="color:var(--text-muted);font-size:13px">{{ u.email }}</td>
            <td><span class="badge" :class="rolBadge(u.rol)">{{ u.rol }}</span></td>
            <td>
              <span v-if="u.suspensiones_activas?.length" class="badge badge-red">
                {{ u.suspensiones_activas.length }} activa(s)
              </span>
              <span v-else class="badge badge-green">OK</span>
            </td>
            <td>
              <!-- Todos van a detalle — el borrado está dentro del detalle -->
              <router-link :to="`/usuarios/${u.id}`" class="btn btn-primary btn-sm">
                👤 Ver detalle
              </router-link>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="usuarios.length === 0" style="text-align:center;padding:32px;color:var(--text-muted)">
        No se encontraron usuarios.
      </p>
    </div>

    <!-- Modal info simple (empleados/admins) -->
    <div class="modal-overlay" v-if="detalleSimple" @click.self="detalleSimple = null">
      <div class="modal card">
        <div style="display:flex;gap:12px;align-items:center;margin-bottom:20px">
          <div class="avatar-lg">{{ detalleSimple.nombre?.charAt(0) }}</div>
          <div>
            <h3>{{ detalleSimple.nombre }} {{ detalleSimple.apellido }}</h3>
            <p style="color:var(--text-muted);font-size:14px">{{ detalleSimple.email }}</p>
            <span class="badge" :class="rolBadge(detalleSimple.rol)">{{ detalleSimple.rol }}</span>
          </div>
        </div>
        <div class="grid-2">
          <div class="detalle-item"><span class="label">DNI</span><span>{{ detalleSimple.dni }}</span></div>
          <div class="detalle-item"><span class="label">Miembro desde</span><span>{{ new Date(detalleSimple.fecha_registro).toLocaleDateString() }}</span></div>
        </div>
        <button class="btn btn-outline btn-sm" style="margin-top:16px" @click="detalleSimple = null">Cerrar</button>
      </div>
    </div>

    <!-- Modal registrar usuario (cliente o empleado) -->
    <div class="modal-overlay" v-if="modalRegistrar" @click.self="cerrarModal">
      <div class="modal card">
        <h3>
          {{ rolRegistrando === 'cliente' ? '👤 Registrar Cliente' : '🧑‍💼 Registrar Empleado' }}
        </h3>
        <div class="alert alert-error" v-if="regError">{{ regError }}</div>
        <div class="grid-2">
          <div class="input-group"><label>Nombre</label><input v-model="regForm.nombre" /></div>
          <div class="input-group"><label>Apellido</label><input v-model="regForm.apellido" /></div>
        </div>
        <div class="input-group"><label>DNI</label><input v-model="regForm.dni" placeholder="Sin puntos ni guiones" /></div>
        <div class="input-group"><label>Email</label><input v-model="regForm.email" type="email" /></div>
        <div class="input-group">
          <label>Contraseña inicial</label>
          <input v-model="regForm.password" type="password" placeholder="Mínimo 6 caracteres" />
        </div>
        <p style="font-size:12px;color:var(--text-muted);margin-bottom:16px">
          El usuario podrá cambiar su contraseña desde su perfil.
        </p>
        <div style="display:flex;gap:10px">
          <button class="btn btn-primary" @click="registrarUsuario" :disabled="regLoading">
            {{ regLoading ? 'Registrando...' : `Registrar ${rolRegistrando}` }}
          </button>
          <button class="btn btn-outline" @click="cerrarModal">Cancelar</button>
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
const regMsg = ref('')
const detalleSimple = ref(null)
const modalRegistrar = ref(false)
const rolRegistrando = ref('cliente')
const regForm = ref({ nombre: '', apellido: '', dni: '', email: '', password: '' })
const regError = ref('')
const regLoading = ref(false)
const modalBorrar = ref(null)
const borrando = ref(false)

function rolBadge(rol) {
  return { 'administrador': 'badge-green', 'empleado': 'badge-blue', 'cliente': 'badge-yellow' }[rol] || 'badge-yellow'
}

function verDetalleSimple(u) { detalleSimple.value = u }

function abrirRegistro(rol) {
  rolRegistrando.value = rol
  regForm.value = { nombre: '', apellido: '', dni: '', email: '', password: '' }
  regError.value = ''
  modalRegistrar.value = true
}

function cerrarModal() {
  modalRegistrar.value = false
  regError.value = ''
}

async function fetchUsuarios() {
  const params = {}
  if (busqueda.value) params.q = busqueda.value
  if (filtroRol.value) params.rol = filtroRol.value
  const { data } = await api.get('/usuarios/', { params })
  usuarios.value = data
}

async function registrarUsuario() {
  if (!regForm.value.nombre || !regForm.value.dni || !regForm.value.email || !regForm.value.password) {
    regError.value = 'Completá todos los campos'
    return
  }
  regLoading.value = true
  regError.value = ''
  try {
    const res = await api.post('/auth/register', { ...regForm.value, rol: rolRegistrando.value })
    regMsg.value = `${rolRegistrando.value === 'cliente' ? 'Cliente' : 'Empleado'} ${res.data.reactivado ? 'reactivado' : 'registrado'} correctamente`
    cerrarModal()
    fetchUsuarios()
    setTimeout(() => regMsg.value = '', 3000)
  } catch (e) {
    regError.value = e.response?.data?.error || 'Error al registrar'
  } finally {
    regLoading.value = false
  }
}

function confirmarBorrar(u) {
  modalBorrar.value = u
}

async function ejecutarBorrado() {
  borrando.value = true
  try {
    await api.post(`/usuarios/${modalBorrar.value.id}/borrar`)
    regMsg.value = `${modalBorrar.value.nombre} desactivado correctamente`
    modalBorrar.value = null
    fetchUsuarios()
    setTimeout(() => regMsg.value = '', 3000)
  } catch (e) {
    error.value = e.response?.data?.error || 'Error al desactivar'
  } finally {
    borrando.value = false
  }
}

onMounted(fetchUsuarios)
</script>

<style scoped>
.filters-bar { padding: 16px 24px; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 200; }
.modal { max-width: 480px; width: 100%; }
.modal h3 { font-size: 22px; margin-bottom: 20px; }
.avatar-lg {
  width: 52px; height: 52px;
  background: linear-gradient(135deg, var(--verde), var(--azul));
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; font-weight: 700; flex-shrink: 0;
}
.detalle-item { display: flex; flex-direction: column; gap: 4px; margin-bottom: 12px; }
.label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
</style>
