<template>
  <div class="admin-container">
    <h2>Panel de Administración - Gestión de Turnos</h2>
    <div class="admin-form">
      <select v-on:change="formClase.actividad = $event.target.value">
        <option value="" disabled selected>Seleccione Deporte</option>
        <option value="Fútbol">Fútbol</option>
        <option value="Básquet">Básquet</option>
        <option value="Pádel">Pádel</option>
        <option value="Vóley">Vóley</option>
      </select>
      
      <select v-on:change="formClase.dia = $event.target.value">
        <option value="" disabled selected>Día</option>
        <option v-for="d in ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']" :key="d">{{ d }}</option>
      </select>

      <select v-on:change="formClase.hora = $event.target.value">
        <option value="" disabled selected>Horario (8:00 a 22:00)</option>
        <option v-for="h in horarios" :key="h">{{ h }}</option>
      </select>

      <input type="number" v-model="formClase.cupo_maximo" placeholder="Cupo Máximo" />
      <input type="number" v-model="formClase.precio" placeholder="Precio Base ($)" />
      
      <button class="btn-g" @click="crear">Guardar Clase</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import axios from 'axios';

const emit = defineEmits(['actualizar']);
const formClase = ref({ actividad: '', dia: '', hora: '', cupo_maximo: null, precio: null });
const horarios = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00", "20:00", "21:00", "22:00"];

const crear = async () => {
  try {
    await axios.post('http://127.0.0.1:5000/api/clases', formClase.value);
    alert("Clase creada correctamente.");
    emit('actualizar'); // Avisa al padre que refresque la lista de la DB
  } catch (e) { alert("Error al crear clase."); }
};
</script>

<style scoped>
.admin-form { display: flex; flex-direction: column; gap: 10px; max-width: 400px; padding: 20px; background: #f9f9f9; border-radius: 8px; margin: 0 auto; }
.admin-form select, .admin-form input { padding: 10px; border-radius: 4px; border: 1px solid #ccc; }
.btn-g { background: #0F6E56; color: white; padding: 10px; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; }
</style>