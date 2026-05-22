<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-header">
        <img :src="logo" alt="Club 360 Logo" class="auth-logo" />

        <h2>CLUB 360</h2>
        <p>Iniciá sesión en tu cuenta</p>
      </div>

      <div class="alert alert-error" v-if="error">{{ error }}</div>

      <form @submit.prevent="handleLogin">
        <div class="input-group">
          <label>Email</label>
          <input
            v-model="form.email"
            type="email"
            placeholder="tu@email.com"
            required
          />
        </div>

        <div class="input-group">
          <label>Contraseña</label>
          <input
            v-model="form.password"
            type="password"
            placeholder="••••••••"
            required
          />
        </div>

        <button
          class="btn btn-primary"
          style="width: 100%"
          :disabled="loading"
        >
          {{ loading ? "Ingresando..." : "Ingresar" }}
        </button>
      </form>

      <p class="auth-footer">
        ¿No tenés cuenta?
        <router-link to="/registro">Registrate</router-link>
      </p>

      <!-- <div class="demo-creds">
        <p>Credenciales de prueba:</p>

        <div class="cred-list">
          <div
            @click="fillDemo('admin@club360.com','admin123')"
            class="cred-item"
          >
            <span class="badge badge-green">Admin</span>
            admin@club360.com / admin123
          </div>

          <div
            @click="fillDemo('empleado@club360.com','emp123')"
            class="cred-item"
          >
            <span class="badge badge-blue">Empleado</span>
            empleado@club360.com / emp123
          </div>

          <div
            @click="fillDemo('cliente@club360.com','cliente123')"
            class="cred-item"
          >
            <span class="badge badge-yellow">Cliente</span>
            cliente@club360.com / cliente123
          </div>
        </div>
      </div> -->
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth.js";

import logo from "../assets/logo.png";

const auth = useAuthStore();
const router = useRouter();
const form = ref({ email: "", password: "" });
const error = ref("");
const loading = ref(false);

async function handleLogin() {
  loading.value = true;
  error.value = "";

  try {
    await auth.login(form.value.email, form.value.password);
    router.push("/");
  } catch (e) {
    error.value = e.response?.data?.error || "Error al iniciar sesión";
  } finally {
    loading.value = false;
  }
}

function fillDemo(email, pass) {
  form.value.email = email;
  form.value.password = pass;
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
}

.auth-card {
  background: var(--dark-2);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 40px;
  width: 100%;
  max-width: 420px;
  box-shadow: var(--shadow);
}

.auth-header {
  text-align: center;
  margin-bottom: 32px;
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

.demo-creds {
  margin-top: 24px;
  border-top: 1px solid var(--border);
  padding-top: 20px;
}

.demo-creds p {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 10px;
}

.cred-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.cred-item {
  font-size: 12px;
  color: var(--text-muted);
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid var(--border);
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 8px;
}

.cred-item:hover {
  border-color: var(--verde);
  color: var(--text);
}
</style>