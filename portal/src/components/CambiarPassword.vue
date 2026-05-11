<template>
  <div class="panel-container">
    <h2>Seguridad de la Cuenta</h2>
    <p style="color: #666; margin-bottom: 20px;">Actualizá tu contraseña para mantener tu cuenta segura.</p>

    <form @submit.prevent="actualizarPass" class="form-interno">
      <input type="password" v-model="form.password_actual" placeholder="Contraseña actual" required />
      <hr style="border: 0; border-top: 1px solid #eee; margin: 5px 0;" />
      <input type="password" v-model="form.password_nueva" placeholder="Nueva contraseña" required />
      <input type="password" v-model="confirmar" placeholder="Confirmar nueva contraseña" required />
      
      <p v-if="error" style="color: #d9534f; font-size: 13px; font-weight: bold;">{{ error }}</p>

      <button type="submit" class="btn-g" :disabled="cargando">
        {{ cargando ? 'Guardando...' : 'Actualizar Contraseña' }}
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import axios from 'axios';

const props = defineProps(['usuarioId']);
const form = ref({ password_actual: '', password_nueva: '' });
const confirmar = ref('');
const error = ref('');
const cargando = ref(false);

const actualizarPass = async () => {
  error.value = '';
  
  if (form.value.password_nueva !== confirmar.value) {
    error.value = "Las nuevas contraseñas no coinciden.";
    return;
  }

  cargando.value = true;
  try {
    const res = await axios.post('http://127.0.0.1:5000/api/usuario/cambiar-password', {
      usuario_id: props.usuarioId,
      password_actual: form.value.password_actual,
      password_nueva: form.value.password_nueva
    });
    alert(res.data.mensaje);
    form.value = { password_actual: '', password_nueva: '' };
    confirmar.value = '';
  } catch (e) {
    error.value = e.response?.data?.mensaje || "Error al cambiar la contraseña";
  } finally {
    cargando.value = false;
  }
};
</script>

<style scoped>
.panel-container { max-width: 400px; margin: 40px auto; background: #fff; padding: 30px; border-radius: 10px; border: 1px solid #ddd; }
.form-interno { display: flex; flex-direction: column; gap: 15px; }
.form-interno input { padding: 12px; border: 1px solid #ccc; border-radius: 6px; }
.btn-g { background: #2E5A88; color: white; padding: 12px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; }
.btn-g:disabled { opacity: 0.6; }
</style>