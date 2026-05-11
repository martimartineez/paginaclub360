<template>
  <div class="panel-container">
    <h2>Registrar Nuevo Cliente</h2>
    <p style="color: #666; margin-bottom: 20px;">Completá los datos del cliente que se presentó en la sede.</p>
    
    <form @submit.prevent="registrarDesdeStaff" class="form-interno">
      <div style="display: flex; gap: 10px;">
        <input type="text" v-model="formReg.nombre" placeholder="Nombre" required style="width: 50%;" />
        <input type="text" v-model="formReg.apellido" placeholder="Apellido" required style="width: 50%;" />
      </div>
      
      <input type="text" v-model="formReg.dni" placeholder="DNI" required />
      <input type="email" v-model="formReg.email" placeholder="Correo electrónico" required />
      
      <div style="display: flex; flex-direction: column; gap: 5px;">
        <label style="font-size: 13px; color: #555; font-weight: bold;">Contraseña temporal (Debe informarla al cliente)</label>
        <input type="text" v-model="formReg.password" required />
      </div>
      
      <div style="display: flex; flex-direction: column; gap: 5px;">
        <label style="font-size: 13px; color: #555; font-weight: bold;">Fecha de Nacimiento (Mayor de 18)</label>
        <input type="date" v-model="formReg.fechaNacimiento" required />
      </div>

      <button type="submit" class="btn-g">Registrar Cliente en el Sistema</button>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import axios from 'axios';

// Le ponemos una clave temporal fácil para que el empleado se la dicte al cliente
const formReg = ref({ nombre: '', apellido: '', dni: '', email: '', password: 'club360cambiame', fechaNacimiento: '' });

const calcularEdad = (fecha) => {
  const hoy = new Date();
  const cumpleanos = new Date(fecha);
  let edad = hoy.getFullYear() - cumpleanos.getFullYear();
  const mes = hoy.getMonth() - cumpleanos.getMonth();
  if (mes < 0 || (mes === 0 && hoy.getDate() < cumpleanos.getDate())) { edad--; }
  return edad;
};

const registrarDesdeStaff = async () => {
  if (calcularEdad(formReg.value.fechaNacimiento) < 18) {
    alert("Acceso denegado: El cliente debe ser mayor de 18 años.");
    return;
  }

  try {
    const res = await axios.post('http://127.0.0.1:5000/api/registro', formReg.value);
    alert("¡Cliente registrado con éxito! Ya puede iniciar sesión desde su celular.");
    
    // Limpiamos el formulario para registrar al siguiente
    formReg.value = { nombre: '', apellido: '', dni: '', email: '', password: 'club360cambiame', fechaNacimiento: '' };
  } catch (e) {
    alert(e.response?.data?.mensaje || "Error en el registro");
  }
};
</script>

<style scoped>
.panel-container { max-width: 500px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 10px; border: 1px solid #ddd; }
.form-interno { display: flex; flex-direction: column; gap: 15px; }
.form-interno input { padding: 12px; border: 1px solid #ccc; border-radius: 6px; font-size: 14px; box-sizing: border-box;}
.btn-g { background: #0F6E56; color: white; padding: 12px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; }
.btn-g:hover { background: #085041; }
</style>