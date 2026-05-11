<template>
  <div class="wizard-container">
    <div v-if="paso === 1" class="step">
      <div class="stitle">¿Qué deporte querés jugar?</div>
      <div class="sgrid">
        <div v-for="d in deportes" :key="d" class="scard" @click="seleccionarDeporte(d)">{{ d }}</div>
      </div>
    </div>

    <div v-else-if="paso === 2" class="step">
      <div class="stitle">¿Cómo querés abonar?</div>
      <div class="pgrid">
        <div class="pcard" @click="seleccionarPlan('suelta', 'Clase suelta')">Clase suelta (50% seña)</div>
        <div class="pcard feat" @click="seleccionarPlan('mensual', 'Abono mensual')">Abono mensual</div>
      </div>
    </div>

    <div v-else-if="paso === 3" class="step">
      <div class="stitle">Elegí fecha y hora</div>
      <div class="wgrid">
        <div v-for="dia in diasDisponibles" :key="dia" :class="['wday', res.day === dia ? 'sel' : '']" @click="res.day = dia">{{ dia }}</div>
      </div>
      <div v-if="res.day" class="hgrid" style="margin-top:20px;">
        <button v-for="h in horasDisponibles" :key="h" :class="['hbtn', res.hour === h ? 'sel' : '']" @click="res.hour = h">{{ h }}</button>
      </div>
      <button v-if="res.hour" class="btn-g" @click="confirmar" style="margin-top:20px;">Confirmar Reserva</button>
    </div>

    <div v-else-if="paso === 4" class="step">
      <div class="result">
        <h2>{{ estado === 'espera' ? '⏳ En Lista de Espera' : '✔️ Reserva Confirmada' }}</h2>
        <p>{{ mensaje }}</p>
        <button class="btn-g" @click="$emit('reset')">Nueva Reserva</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import axios from 'axios';

const props = defineProps(['clases']);
const emit = defineEmits(['reset']);
const paso = ref(1);
const res = ref({ sport: '', planType: '', plan: '', day: '', hour: '' });
const estado = ref('');
const mensaje = ref('');

const deportes = computed(() => [...new Set(props.clases.map(c => c.actividad))]);
const diasDisponibles = computed(() => [...new Set(props.clases.filter(c => c.actividad === res.value.sport).map(c => c.dia))]);
const horasDisponibles = computed(() => [...new Set(props.clases.filter(c => c.actividad === res.value.sport && c.dia === res.value.day).map(c => c.hora))]);

const seleccionarDeporte = (d) => { res.value.sport = d; paso.value = 2; };
const seleccionarPlan = (tipo, nombre) => { res.value.planType = tipo; res.value.plan = nombre; paso.value = 3; };

const confirmar = async () => {
  try {
    const r = await axios.post('http://127.0.0.1:5000/api/reservar', res.value);
    estado.value = r.data.estado;
    mensaje.value = r.data.mensaje;
    paso.value = 4;
  } catch (e) { alert("Error en reserva."); }
};
</script>

<style scoped>
/* Aquí podés reutilizar los estilos de tu prototipo original */
.scard, .pcard, .wday, .hbtn { cursor: pointer; padding: 15px; border: 1px solid #ddd; border-radius: 8px; text-align: center; }
.sel { background: #0F6E56; color: white; }
.feat { border: 2px solid #0F6E56; }
.sgrid, .pgrid, .wgrid, .hgrid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
</style>