<template>
  <div id="app">
    <nav class="nav">
      <div class="nav-logo">Club 360</div>
      
      <div v-if="usuario" class="menu-acciones">
        <span class="user-info">Hola, {{ usuario.nombre }} {{ usuario.apellido }} </span>
        
        <button v-if="usuario.rol === 'Administrador'" class="btn-nav" @click="vista = 'admin'">
          Gestión de Turnos
        </button>

        <button v-if="usuario.rol === 'Administrador'" class="btn-nav" @click="vista = 'registrar_staff'">
          Registrar Staff
        </button>
        
        <button v-if="['Administrador', 'Empleado'].includes(usuario.rol)" class="btn-nav" @click="vista = 'registrar_cliente'">
          Registrar Cliente
        </button>
        
        <button v-if="usuario.rol === 'Cliente'" class="btn-nav" @click="vista = 'cliente'">
          Reservar Clase
        </button>

        <button class="btn-nav" @click="vista = 'seguridad'">
          ⚙️ Seguridad
        </button>

        <button class="btn-toggle" @click="cerrarSesion" style="margin-left: 15px;">Cerrar Sesión</button>
      </div>
    </nav>

    <main>
      <AuthPanel v-if="!usuario" @login-exitoso="setUsuario" />
      
      <div v-else style="padding: 20px;">
        <AdminPanel v-if="vista === 'admin' && usuario.rol === 'Administrador'" @actualizar="refrescar" />
        
        <RegistrarStaff v-else-if="vista === 'registrar_staff' && usuario.rol === 'Administrador'" />
        
        <RegistrarCliente v-else-if="vista === 'registrar_cliente' && ['Administrador', 'Empleado'].includes(usuario.rol)" />
        
        <ReservaWizard v-else-if="vista === 'cliente' && usuario.rol === 'Cliente'" :clases="clases" />

        <CambiarPassword v-else-if="vista === 'seguridad'" :usuarioId="usuario.id" />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import axios from 'axios';
import AuthPanel from './components/AuthPanel.vue';
import AdminPanel from './components/AdminPanel.vue';
import ReservaWizard from './components/ReservaWizard.vue';
import RegistrarCliente from './components/RegistrarCliente.vue';
import RegistrarStaff from './components/RegistrarStaff.vue';
import CambiarPassword from './components/CambiarPassword.vue'; // <-- Importación agregada

const usuario = ref(null);
const vista = ref('');
const clases = ref([]);

const setUsuario = (dataUsuario) => {
  usuario.value = dataUsuario;
  
  if(dataUsuario.rol === 'Cliente') {
    vista.value = 'cliente';
    refrescar();
  } else if (dataUsuario.rol === 'Administrador') {
    vista.value = 'admin';
  } else if (dataUsuario.rol === 'Empleado') {
    vista.value = 'registrar_cliente'; 
  }
};

const cerrarSesion = () => {
  usuario.value = null;
  vista.value = '';
};

const refrescar = async () => {
  try {
    const r = await axios.get('http://127.0.0.1:5000/api/clases');
    clases.value = r.data;
  } catch (error) {
    console.error("Error al cargar clases:", error);
  }
};
</script>

<style>
.nav { background: #2E5A88; color: white; padding: 15px; display: flex; justify-content: space-between; align-items: center; }
.nav-logo { font-weight: bold; font-size: 1.2rem; }
.btn-toggle { background: #d9534f; color: white; border: none; padding: 8px 15px; border-radius: 6px; cursor: pointer; }
.user-info { font-size: 14px; font-weight: 600; margin-right: 15px; }
.btn-nav { background: transparent; border: 1px solid white; color: white; padding: 6px 12px; border-radius: 4px; cursor: pointer; margin-left: 10px; font-weight: 500;}
.btn-nav:hover { background: rgba(255,255,255,0.2); }
.menu-acciones { display: flex; align-items: center; }
</style>