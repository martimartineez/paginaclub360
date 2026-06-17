<template>
  <div>
    <div class="alert alert-error" v-if="errorGlobal">{{ errorGlobal }}</div>

    <div class="grid-2">
      <div class="input-group">
        <label>Nombre</label>
        <input v-model="form.nombre" placeholder="Juan" />
      </div>

      <div class="input-group">
        <label>Apellido</label>
        <input v-model="form.apellido" placeholder="Pérez" />
      </div>
    </div>
    <p v-if="errorNombre" class="field-error">{{ errorNombre }}</p>

    <div class="input-group">
      <label>DNI</label>
      <input v-model="form.dni" placeholder="12345678" />
      <p v-if="errorDni" class="field-error">{{ errorDni }}</p>
    </div>

    <div class="input-group">
      <label>Email</label>
      <input
        v-model="form.email"
        type="email"
        placeholder="tu@email.com"
      />
      <p v-if="errorEmail" class="field-error">{{ errorEmail }}</p>
    </div>

    <div class="input-group">
      <label>Contraseña</label>
      <input
        v-model="form.password"
        type="password"
        placeholder="Mínimo 8 caracteres"
      />
      <p v-if="errorPassword" class="field-error">{{ errorPassword }}</p>
    </div>

    <div class="input-group">
      <label>Fecha de nacimiento</label>
      <input
        v-model="form.fecha_nacimiento"
        type="date"
        :max="maxFechaNacimiento"
      />
      <p v-if="errorFecha" class="field-error">{{ errorFecha }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";

const form = ref({
  nombre: "",
  apellido: "",
  dni: "",
  email: "",
  password: "",
  fecha_nacimiento: "",
});

const errorGlobal = ref("");

// --- VALIDACIONES EN TIEMPO REAL ---

// 1. Nombre / Apellido con números o puro espacio
const errorNombre = computed(() => {
  if (!form.value.nombre && !form.value.apellido) return "";

  if (form.value.nombre.length > 0 && form.value.nombre.trim() === "") {
    return "El nombre no puede estar compuesto solo por espacios vacíos";
  }

  if (form.value.apellido.length > 0 && form.value.apellido.trim() === "") {
    return "El apellido no puede estar compuesto solo por espacios vacíos";
  }

  const tieneNumeros = /\d/;
  if (
    tieneNumeros.test(form.value.nombre) ||
    tieneNumeros.test(form.value.apellido)
  ) {
    return "Debes colocar un nombre/apellido sin números";
  }
  return "";
});

// 2. DNI inválido
const errorDni = computed(() => {
  if (!form.value.dni) return "";
  const dniValido = /^\d{7,9}$/;
  if (!dniValido.test(form.value.dni)) {
    return "El DNI debe ser solo números (entre 7 y 9 dígitos, sin puntos)";
  }
  return "";
});

// 3. Email inválido
const errorEmail = computed(() => {
  if (!form.value.email) return "";
  const emailRegex = /^[^@\s]+@[^@\s]+$/;
  if (!emailRegex.test(form.value.email)) {
    return "Debes colocar texto antes del @, incluir el @, y texto luego del @";
  }
  return "";
});

// 4. Contraseña corta
const errorPassword = computed(() => {
  if (!form.value.password) return "";
  if (form.value.password.length < 8) {
    return "La contraseña debe tener al menos 8 caracteres";
  }
  return "";
});

// 5. Edad menor a 18
const errorFecha = computed(() => {
  if (!form.value.fecha_nacimiento) return "";
  const fnac = new Date(form.value.fecha_nacimiento);
  const hoy = new Date();
  let edad = hoy.getFullYear() - fnac.getFullYear();
  const mes = hoy.getMonth() - fnac.getMonth();

  if (mes < 0 || (mes === 0 && hoy.getDate() < fnac.getDate())) {
    edad--;
  }

  if (edad < 18) {
    return "Debes ser mayor de 18 años para registrarte";
  }
  return "";
});

// 6. Validación global
const isFormValido = computed(() => {
  return (
    form.value.nombre.trim() !== "" &&
    form.value.apellido.trim() !== "" &&
    form.value.dni.trim() !== "" &&
    form.value.email.trim() !== "" &&
    form.value.password.trim() !== "" &&
    form.value.fecha_nacimiento !== "" &&
    !errorNombre.value &&
    !errorDni.value &&
    !errorEmail.value &&
    !errorPassword.value &&
    !errorFecha.value
  );
});

// Máximo calendario: 18 años atrás
const maxFechaNacimiento = computed(() => {
  const hoy = new Date();
  hoy.setFullYear(hoy.getFullYear() - 18);
  return hoy.toISOString().split("T")[0];
});

// Exponer lo necesario para el botón externo
defineExpose({
  form,
  isFormValido,
  errorGlobal,
});
</script>

<style scoped>
.field-error {
  font-size: 12px;
  color: var(--danger);
  margin-top: 4px;
}
</style>