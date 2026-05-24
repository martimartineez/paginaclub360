<template>
  <div class="tarjeta-form">
    <div class="card-preview">
      <div class="card-chip">▪▪▪</div>
      <div class="card-number">
        {{ previewNumero }}
      </div>
      <div class="card-footer">
        <div>
          <div class="card-label">TITULAR</div>
          <div class="card-value">{{ form.titular || 'NOMBRE APELLIDO' }}</div>
        </div>
        <div>
          <div class="card-label">VENCE</div>
          <div class="card-value">{{ form.vencimiento || 'MM/AA' }}</div>
        </div>
      </div>
    </div>

    <div class="alert alert-error" v-if="errorLocal">{{ errorLocal }}</div>

    <form @submit.prevent="guardar">
      <div class="input-group">
        <label>Número de tarjeta</label>
        <input
          v-model="form.numero"
          @input="formatNumero"
          placeholder="1234 5678 9012 3456"
          maxlength="19"
          inputmode="numeric"
          required
        />
        <p v-if="errorNumero" class="field-error">{{ errorNumero }}</p>
      </div>

      <div class="input-group">
        <label>Nombre del titular (como figura en la tarjeta)</label>
        <input
          v-model="form.titular"
          @input="form.titular = form.titular.toUpperCase()"
          placeholder="JUAN PÉREZ"
          required
        />
        <p v-if="errorTitular" class="field-error">{{ errorTitular }}</p>
      </div>

      <div class="grid-2">
        <div class="input-group">
          <label>Vencimiento</label>
          <input
            v-model="form.vencimiento"
            @input="formatVenc"
            placeholder="MM/AA"
            maxlength="5"
            inputmode="numeric"
            required
          />
          <p v-if="errorVencimiento" class="field-error">{{ errorVencimiento }}</p>
        </div>
        <div class="input-group">
          <label>CVV</label>
          <input
            v-model="form.cvv"
            placeholder="123"
            maxlength="4"
            type="password"
            inputmode="numeric"
            required
          />
          <p v-if="errorCvv" class="field-error">{{ errorCvv }}</p>
        </div>
      </div>

      <p class="secure-note">🔒 Tus datos están protegidos con encriptación. Solo guardamos los últimos 4 dígitos.</p>

      <div style="display:flex;gap:10px;margin-top:8px">
        <button 
          class="btn btn-primary" 
          type="submit" 
          :disabled="loading || !isFormValido"
          style="flex: 1"
        >
          {{ loading ? 'Guardando...' : labelBoton }}
        </button>
        <button 
          class="btn btn-outline" 
          type="button" 
          v-if="showCancelar" 
          @click="$emit('cancelar')"
        >
          Cancelar
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import api from '../api.js'

const props = defineProps({
  labelBoton: { type: String, default: 'Guardar tarjeta' },
  showCancelar: { type: Boolean, default: true }
})
const emit = defineEmits(['guardada', 'cancelar'])

const form = ref({ numero: '', titular: '', vencimiento: '', cvv: '' })
const loading = ref(false)
const errorLocal = ref('')

// --- FORMATO VISUAL ---
const previewNumero = computed(() => {
  const n = form.value.numero.replace(/\s/g, '')
  const padded = n.padEnd(16, '•')
  return padded.match(/.{1,4}/g)?.join(' ') || '•••• •••• •••• ••••'
})

function formatNumero() {
  let v = form.value.numero.replace(/\D/g, '').substring(0, 16)
  form.value.numero = v.match(/.{1,4}/g)?.join(' ') || v
}

function formatVenc() {
  let v = form.value.vencimiento.replace(/\D/g, '').substring(0, 4)
  if (v.length >= 3) v = v.substring(0, 2) + '/' + v.substring(2)
  form.value.vencimiento = v
}

// --- VALIDACIONES EN TIEMPO REAL ---

const errorTitular = computed(() => {
  if (!form.value.titular) return ''
  if (form.value.titular.trim() === '') {
    return 'El titular no puede ser solo espacios vacíos'
  }
  const tieneNumeros = /\d/
  if (tieneNumeros.test(form.value.titular)) {
    return 'El nombre del titular no puede contener números'
  }
  return ''
})

const errorNumero = computed(() => {
  if (!form.value.numero) return ''
  const numLimpio = form.value.numero.replace(/\s/g, '')
  if (numLimpio.length < 13) {
    return 'El número debe tener al menos 13 dígitos'
  }
  return ''
})

const errorVencimiento = computed(() => {
  if (!form.value.vencimiento) return ''
  if (form.value.vencimiento.length !== 5) {
    return 'El formato debe ser MM/AA'
  }

  const [mmStr, aaStr] = form.value.vencimiento.split('/')
  const mes = parseInt(mmStr, 10)
  const anio = parseInt(aaStr, 10)

  if (mes < 1 || mes > 12) return 'Ingrese un mes válido (01 a 12)'

  const hoy = new Date()
  const anioCompleto = 2000 + anio
  const mesActual = hoy.getMonth() + 1
  const anioActual = hoy.getFullYear()

  if (anioCompleto < anioActual || (anioCompleto === anioActual && mes < mesActual)) {
    return 'La tarjeta está vencida'
  }
  return ''
})

const errorCvv = computed(() => {
  if (!form.value.cvv) return ''
  const cvvLimpio = form.value.cvv.replace(/\D/g, '')
  if (cvvLimpio.length < 3) {
    return 'El CVV debe tener al menos 3 números'
  }
  return ''
})

const isFormValido = computed(() => {
  return (
    form.value.numero.trim() !== '' &&
    form.value.titular.trim() !== '' &&
    form.value.vencimiento.trim() !== '' &&
    form.value.cvv.trim() !== '' &&
    !errorNumero.value &&
    !errorTitular.value &&
    !errorVencimiento.value &&
    !errorCvv.value
  )
})

// --- ENVÍO AL BACKEND ---
async function guardar() {
  errorLocal.value = ''
  
  const numero = form.value.numero.replace(/\s/g, '')
  loading.value = true
  
  try {
    const { data } = await api.post('/auth/tarjetas', {
      numero,
      titular: form.value.titular,
      vencimiento: form.value.vencimiento
      // Nota: El CVV no se envía al backend porque tu API no lo guarda, 
      // lo cual es una excelente práctica de seguridad.
    })
    form.value = { numero: '', titular: '', vencimiento: '', cvv: '' }
    emit('guardada', data.tarjeta)
  } catch (e) {
    errorLocal.value = e.response?.data?.error || 'Error al guardar tarjeta'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.tarjeta-form { max-width: 440px; }
.card-preview {
  background: linear-gradient(135deg, #1565C0, #2E7D32);
  border-radius: 14px;
  padding: 24px;
  margin-bottom: 24px;
  color: white;
  font-family: 'Courier New', monospace;
  position: relative;
  min-height: 160px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  box-shadow: 0 8px 24px rgba(0,0,0,0.4);
}
.card-chip { font-size: 20px; letter-spacing: 2px; opacity: 0.8; }
.card-number { font-size: 20px; letter-spacing: 3px; text-align: center; font-weight: 600; }
.card-footer { display: flex; justify-content: space-between; }
.card-label { font-size: 9px; opacity: 0.7; letter-spacing: 1px; margin-bottom: 2px; }
.card-value { font-size: 13px; font-weight: 600; letter-spacing: 1px; }
.secure-note { font-size: 12px; color: var(--text-muted); margin-top: 8px; }
.field-error { font-size: 12px; color: var(--danger); margin-top: 4px; }
</style>