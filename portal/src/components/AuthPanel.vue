<template>
  <div class="auth-container">
    <div class="auth-box">
      <h2 style="color: #2E5A88; margin-bottom: 20px;">
        {{ modoRegistro ? 'Registrarse en Club 360' : 'Iniciar Sesión' }}
      </h2>

      <form v-if="!modoRegistro" @submit.prevent="login" class="form">
        <input type="email" v-model="formLogin.email" placeholder="Correo electrónico" required />
        <input type="password" v-model="formLogin.password" placeholder="Contraseña" required />
        <button type="submit" class="btn-g">Ingresar</button>
      </form>

      <form v-else @submit.prevent="registro" class="form">
        <div style="display: flex; gap: 10px;">
          <input type="text" v-model="formReg.nombre" placeholder="Nombre" required style="width: 50%;" />
          <input type="text" v-model="formReg.apellido" placeholder="Apellido" required style="width: 50%;" />
        </div>
        
        <input type="text" v-model="formReg.dni" placeholder="DNI" required />
        <input type="email" v-model="formReg.email" placeholder="Correo electrónico" required />
        <input type="password" v-model="formReg.password" placeholder="Crear contraseña" required />
        
        <div style="display: flex; flex-direction: column; gap: 5px;">
          <label style="font-size: 13px; color: #555; font-weight: bold;">Fecha de Nacimiento (Solo mayores de 18)</label>
          <input type="date" v-model="formReg.fechaNacimiento" required />
        </div>

        <button type="submit" class="btn-g">Crear Cuenta</button>
      </form>

      <p style="text-align: center; margin-top: 15px; font-size: 14px;">
        {{ modoRegistro ? '¿Ya tenés cuenta?' : '¿No tenés cuenta?' }}
        <a href="#" @click.prevent="modoRegistro = !modoRegistro" style="color: #0F6E56; font-weight: bold;">
          {{ modoRegistro ? 'Iniciá Sesión' : 'Registrate' }}
        </a>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import axios from 'axios';

const emit = defineEmits(['login-exitoso']);
const modoRegistro = ref(false);

const formLogin = ref({ email: '', password: '' });
// Agregamos apellido y fechaNacimiento al objeto
const formReg = ref({ nombre: '', apellido: '', dni: '', email: '', password: '', fechaNacimiento: '' });

// Función para calcular la edad exacta según la fecha ingresada
const calcularEdad = (fecha) => {
  const hoy = new Date();
  const cumpleanos = new Date(fecha);
  let edad = hoy.getFullYear() - cumpleanos.getFullYear();
  const mes = hoy.getMonth() - cumpleanos.getMonth();
  
  if (mes < 0 || (mes === 0 && hoy.getDate() < cumpleanos.getDate())) {
    edad--;
  }
  return edad;
};

const login = async () => {
  try {
    const res = await axios.post('http://127.0.0.1:5000/api/login', formLogin.value);
    emit('login-exitoso', res.data); // Le pasamos los datos del usuario a App.vue
  } catch (e) {
    alert(e.response?.data?.mensaje || "Error al iniciar sesión");
  }
};

const registro = async () => {
  // 1. Validamos la edad antes de tocar la base de datos
  if (calcularEdad(formReg.value.fechaNacimiento) < 18) {
    alert("Acceso denegado: Debes ser mayor de 18 años para registrarte en Club 360.");
    return; // Corta la ejecución de la función
  }

  // 2. Si pasa la validación, envía los datos al backend (Flask ignorará la fecha porque no la definiste en el modelo, pero guardará el resto perfecto)
  try {
    const res = await axios.post('http://127.0.0.1:5000/api/registro', formReg.value);
    alert(res.data.mensaje);
    modoRegistro.value = false; // Lo mandamos a loguearse
    
    // Limpiamos el formulario para que quede prolijo
    formReg.value = { nombre: '', apellido: '', dni: '', email: '', password: '', fechaNacimiento: '' };
  } catch (e) {
    alert(e.response?.data?.mensaje || "Error en el registro");
  }
};
</script>

<style scoped>
.auth-container { display: flex; justify-content: center; align-items: center; min-height: 80vh; background-color: #f4f4f4; }
.auth-box { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); width: 100%; max-width: 400px; }
.form { display: flex; flex-direction: column; gap: 15px; }
.form input { padding: 12px; border: 1px solid #ccc; border-radius: 6px; font-size: 15px; box-sizing: border-box; }
.btn-g { background: #0F6E56; color: white; padding: 12px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; }
.btn-g:hover { background: #085041; }
</style>