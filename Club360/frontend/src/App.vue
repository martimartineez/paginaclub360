<template>
  <div id="app-wrapper">
    <nav class="navbar" v-if="!isAuthPage">
      <div class="nav-inner">
        <router-link to="/" class="nav-brand">
          <img :src="logo" alt="Club 360 Logo" class="logo-image" />
          <span class="logo-text">CLUB 360</span>
        </router-link>

        <div class="nav-links">
          <template v-if="auth.isAdmin || auth.isEmpleado">
            <router-link to="/clases" class="nav-link">
              Clases disponibles
            </router-link>
          </template>

          <template v-if="auth.isCliente">
            <router-link to="/clases" class="nav-link">
              Reservar clase
            </router-link>
          </template>

          <template v-if="auth.isAuthenticated">
            <router-link to="/mis-reservas" class="nav-link">
              Mis Reservas
            </router-link>

            <template v-if="auth.isAdmin || auth.isEmpleado">
              <router-link to="/admin/usuarios" class="nav-link">
                Usuarios
              </router-link>

              <router-link to="/empleado/asistencia" class="nav-link">
                Asistencia QR
              </router-link>
            </template>

            <template v-if="auth.isAdmin">
              <router-link to="/admin/turnos" class="nav-link">
                Gestión Turnos
              </router-link>

              <!-- <router-link to="/admin/actividades" class="nav-link">Actividades</router-link> -->
            </template>
          </template>
        </div>

        <div class="nav-actions">
          <template v-if="auth.isAuthenticated">
            <router-link to="/perfil" class="nav-user">
              <span class="avatar">{{ auth.user?.nombre?.charAt(0) }}</span>
              <span class="user-name">{{ auth.user?.nombre }}</span>
              <span class="badge" :class="rolBadge">{{ auth.user?.rol }}</span>
            </router-link>

            <button class="btn btn-outline btn-sm" @click="logout">
              Salir
            </button>
          </template>

          <template v-else>
            <router-link to="/login" class="btn btn-outline btn-sm">
              Ingresar
            </router-link>

            <router-link to="/registro" class="btn btn-primary btn-sm">
              Registrarse
            </router-link>
          </template>
        </div>
      </div>
    </nav>

    <main :class="{ 'with-nav': !isAuthPage }">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "./stores/auth.js";

import logo from "./assets/logo.png";

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();

const isAuthPage = computed(() =>
  ["/login", "/registro"].includes(route.path)
);

const rolBadge = computed(() => ({
  "badge-green": auth.user?.rol === "administrador",
  "badge-blue": auth.user?.rol === "empleado",
  "badge-yellow": auth.user?.rol === "cliente",
}));

function logout() {
  auth.logout();
  router.push("/");
}
</script>

<style>
.navbar {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(13, 17, 23, 0.95);
  border-bottom: 1px solid var(--border);
  backdrop-filter: blur(10px);
}

.nav-inner {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 24px;
  height: 64px;
  display: flex;
  align-items: center;
  gap: 32px;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-image {
  width: 100px;
  height: 42px;
  object-fit: contain;
}

.logo-text {
  font-size: 22px;
  background: linear-gradient(
    90deg,
    var(--verde-claro),
    var(--azul-claro)
  );
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.nav-links {
  display: flex;
  gap: 4px;
  flex: 1;
}

.nav-link {
  padding: 6px 14px;
  border-radius: 8px;
  font-size: 14px;
  color: var(--text-muted);
  transition: all 0.2s;
  font-weight: 500;
}

.nav-link:hover,
.nav-link.router-link-active {
  background: var(--dark-3);
  color: var(--text);
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
}

.nav-user {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.nav-user:hover {
  background: var(--dark-3);
}

.avatar {
  width: 30px;
  height: 30px;
  background: linear-gradient(135deg, var(--verde), var(--azul));
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 13px;
}

.user-name {
  font-size: 14px;
  font-weight: 500;
}

main.with-nav {
  max-width: 1280px;
  margin: 0 auto;
  padding: 32px 24px;
}
</style>