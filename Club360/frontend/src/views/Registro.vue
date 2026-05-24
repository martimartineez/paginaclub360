<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-header">
        <img :src="logo" alt="Club 360 Logo" class="auth-logo" />

        <h2>CLUB 360</h2>

        <p>
          {{
            paso === 1
              ? "Creá tu cuenta (mayores de 18 años)"
              : "Agregá tu tarjeta de crédito"
          }}
        </p>
      </div>

      <div class="reg-steps">
        <div
          class="reg-step"
          :class="{ active: paso >= 1, done: paso > 1 }"
        >
          <span>{{ paso > 1 ? "✓" : "1" }}</span>
          Datos personales
        </div>

        <div
          class="reg-step-line"
          :class="{ active: paso > 1 }"
        ></div>

        <div class="reg-step" :class="{ active: paso >= 2 }">
          <span>2</span>
          Tarjeta de crédito
        </div>
      </div>

      <div v-if="paso === 1">
        <div class="alert alert-error" v-if="error">{{ error }}</div>

        <form @submit.prevent="handleRegister">
          <div class="grid-2">
            <div class="input-group">
              <label>Nombre</label>
              <input v-model="form.nombre" placeholder="Juan" required />
            </div>

            <div class="input-group">
              <label>Apellido</label>
              <input v-model="form.apellido" placeholder="Pérez" required />
            </div>
          </div>
          <p v-if="errorNombre" class="field-error">{{ errorNombre }}</p>

          <div class="input-group">
            <label>DNI</label>
            <input v-model="form.dni" placeholder="12345678" required />
            <p v-if="errorDni" class="field-error">{{ errorDni }}</p>
          </div>

          <div class="input-group">
            <label>Email</label>
            <input
              v-model="form.email"
              type="email"
              placeholder="tu@email.com"
              required
            />
            <p v-if="errorEmail" class="field-error">{{ errorEmail }}</p>
          </div>

          <div class="input-group">
            <label>Contraseña</label>
            <input
              v-model="form.password"
              type="password"
              placeholder="Mínimo 8 caracteres"
              required
              minlength="8"
            />
            <p v-if="errorPassword" class="field-error">{{ errorPassword }}</p>
          </div>

          <div class="input-group">
            <label>Fecha de nacimiento</label>
            <input
              v-model="form.fecha_nacimiento"
              type="date"
              :max="maxFechaNacimiento"
              required
            />
            <p v-if="errorFecha" class="field-error">{{ errorFecha }}</p>
          </div>

          <button
            class="btn btn-primary"
            style="width: 100%"
            :disabled="loading || !isFormValido"
            type="submit"
          >
            {{ loading ? "Registrando..." : "Continuar →" }}
          </button>
        </form>
      </div>

      <div v-if="paso === 2">
        <div class="alert alert-success" style="margin-bottom: 16px">
          ✅ Cuenta creada. Ahora agregá tu tarjeta para poder pagar clases
          online.
        </div>

        <FormTarjeta
          label-boton="Guardar tarjeta y entrar"
          :show-cancelar="true"
          @guardada="onTarjetaGuardada"
          @cancelar="saltarTarjeta"
        />

        <p
          style="
            text-align: center;
            margin-top: 12px;
            font-size: 12px;
            color: var(--text-muted);
          "
        >
          También podés agregarla después desde tu perfil.
        </p>
      </div>

      <p class="auth-footer" v-if="paso === 1">
        ¿Ya tenés cuenta?
        <router-link to="/login">Ingresá</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth.js";
import FormTarjeta from "../components/FormTarjeta.vue";

import logo from "../assets/logo.png";

const auth = useAuthStore();
const router = useRouter();

const paso = ref(1);

const form = ref({
  nombre: "",
  apellido: "",
  dni: "",
  email: "",
  password: "",
  fecha_nacimiento: "",
});

const error = ref("");
const loading = ref(false);

// --- VALIDACIONES EN TIEMPO REAL (COMPUTED) ---

// 1. Error de Nombre/Apellido con números o puro espacio
const errorNombre = computed(() => {
  if (!form.value.nombre && !form.value.apellido) return "";
  
  if (form.value.nombre.length > 0 && form.value.nombre.trim() === "") {
    return "El nombre no puede estar compuesto solo por espacios vacíos";
  }
  
  if (form.value.apellido.length > 0 && form.value.apellido.trim() === "") {
    return "El apellido no puede estar compuesto solo por espacios vacíos";
  }

  const tieneNumeros = /\d/;
  if (tieneNumeros.test(form.value.nombre) || tieneNumeros.test(form.value.apellido)) {
    return "Debes colocar un nombre/apellido sin números";
  }
  return "";
});

// 2. Error de DNI inválido
const errorDni = computed(() => {
  if (!form.value.dni) return "";
  const dniValido = /^\d{7,9}$/;
  if (!dniValido.test(form.value.dni)) {
    return "El DNI debe ser solo números (entre 7 y 9 dígitos, sin puntos)";
  }
  return "";
});

// 3. Error de Email inválido
const errorEmail = computed(() => {
  if (!form.value.email) return "";
  // La RegEx exige texto que no sea un arroba, seguido de un @, seguido de más texto
  const emailRegex = /^[^@\s]+@[^@\s]+$/;
  if (!emailRegex.test(form.value.email)) {
    return "Debes colocar texto antes del @, incluir el @, y texto luego del @";
  }
  return "";
});

// 4. Error de Contraseña corta
const errorPassword = computed(() => {
  if (!form.value.password) return "";
  if (form.value.password.length < 8) {
    return "La contraseña debe tener al menos 8 caracteres";
  }
  return "";
});

// 5. Error de Edad menor a 18
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

// 6. VALIDACIÓN GLOBAL DEL FORMULARIO
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

// Máximo calendario HTML
const maxFechaNacimiento = computed(() => {
  const hoy = new Date();
  hoy.setFullYear(hoy.getFullYear() - 18);
  return hoy.toISOString().split("T")[0];
});

async function handleRegister() {
  loading.value = true;
  error.value = "";

  try {
    await auth.register(form.value);
    paso.value = 2;
  } catch (e) {
    error.value = e.response?.data?.error || "Error al registrarse";
  } finally {
    loading.value = false;
  }
}

function onTarjetaGuardada() {
  router.push("/");
}

function saltarTarjeta() {
  router.push("/");
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(
    ellipse at center,
    #0a1628 0%,
    var(--dark) 70%
  );
  padding: 20px;
}

.auth-card {
  background: var(--dark-2);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 40px;
  width: 100%;
  max-width: 480px;
  box-shadow: var(--shadow);
}

.auth-header {
  text-align: center;
  margin-bottom: 24px;
}

.auth-logo {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
  margin: 0 auto 16px;
  filter: drop-shadow(0 0 10px rgba(0, 0, 0, 0.4));
}

.auth-header h2 {
  font-size: 32px;
}

.auth-header p {
  color: var(--text-muted);
  margin-top: 4px;
  font-size: 14px;
}

.auth-footer {
  text-align: center;
  margin-top: 20px;
  font-size: 14px;
  color: var(--text-muted);
}

.auth-footer a {
  color: var(--verde-claro);
}

/* Indicador de pasos */

.reg-steps {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 24px;
}

.reg-step {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-muted);
}

.reg-step span {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--dark-3);
  border: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
}

.reg-step.active {
  color: var(--text);
}

.reg-step.active span {
  background: var(--verde);
  border-color: var(--verde);
  color: white;
}

.reg-step.done span {
  background: var(--success);
  border-color: var(--success);
  color: white;
}

.reg-step-line {
  width: 32px;
  height: 2px;
  background: var(--border);
  border-radius: 1px;
}

.reg-step-line.active {
  background: var(--verde);
}
.field-error { font-size: 12px; color: var(--danger); margin-top: 4px; }
</style>