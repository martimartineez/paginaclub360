<template>
  <div class="panel-container">
    <h2>Alta de Personal (Staff)</h2>
    <p style="color: #666; margin-bottom: 20px;">Utilice este formulario para registrar empleados o administradores.</p>
    
    <form @submit.prevent="registrarStaff" class="form-interno">
      <div style="display: flex; gap: 10px;">
        <input type="text" v-model="form.nombre" placeholder="Nombre" required style="width: 50%;" />
        <input type="text" v-model="form.apellido" placeholder="Apellido" required style="width: 50%;" />
      </div>
      
      <input type="text" v-model="form.dni" placeholder="DNI" required />
      <input type="email" v-model="form.email" placeholder="Correo electrónico" required />
      <input type="password" v-model="form.password" placeholder="Asignar contraseña" required />
      
      <div style="display: flex; flex-direction: column; gap: 5px;">
        <label style="font-size: 13px; color: #555; font-weight: bold;">Rol del nuevo integrante</label>
        <select v-model="form.rol" required class="select-rol">
          <option value="Empleado">Empleado (Registro de asistencia y pagos)</option>
          <option value="Administrador">Administrador (Control total)</option>
        </select>
      </div>

      <button type="submit" class="btn-g">Dar de Alta Personal</button>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import axios from 'axios';

const form = ref({ nombre: '', apellido: '', dni: '', email: '', password: '', rol: 'Empleado' });

const registrarStaff = async () => {
  try {
    const res = await axios.post('http://127.0.0.1:5000/api/registro', form.value);
    alert(res.data.mensaje);
    form.value = { nombre: '', apellido: '', dni: '', email: '', password: '', rol: 'Empleado' };
  } catch (e) {
    alert(e.response?.data?.mensaje || "Error en el registro");
  }
};
</script>

<style scoped>
.panel-container { max-width: 500px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 10px; border: 1px solid #ddd; }
.form-interno { display: flex; flex-direction: column; gap: 15px; }
.form-interno input, .select-rol { padding: 12px; border: 1px solid #ccc; border-radius: 6px; font-size: 14px; }
.btn-g { background: #0F6E56; color: white; padding: 12px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; }
</style>