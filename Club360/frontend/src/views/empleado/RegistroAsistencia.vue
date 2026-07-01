<template>
  <div>
    <div class="page-header">
      <h2>REGISTRO DE ASISTENCIA</h2>
      <p>Escaneá el QR de la clase para validar al cliente y marcarlo presente</p>
    </div>

    <div class="alert alert-error asistencia-error" v-if="error">
      <p>{{ error }}</p>
      <router-link
        v-if="errorDetalleUsuarioId"
        :to="`/usuarios/${errorDetalleUsuarioId}`"
        class="btn btn-outline btn-sm"
      >
        Ver detalle
      </router-link>
    </div>
    <div class="alert alert-success" v-if="mensaje">{{ mensaje }}</div>

    <div class="grid-2">
      <div class="card">
        <h3 class="scanner-title">Escanear código QR</h3>

        <div v-if="scannerActivo" class="camera-box">
          <video ref="videoRef" autoplay muted playsinline></video>
          <div class="camera-frame"></div>
        </div>

        <div class="scanner-actions">
          <button
            v-if="!scannerActivo"
            class="btn btn-primary"
            @click="iniciarScanner"
            :disabled="loading"
          >
            📷 Abrir cámara
          </button>
          <button v-else class="btn btn-danger" @click="detenerScanner">
            Detener cámara
          </button>
        </div>

        <p class="scanner-help">
          Apuntá la cámara al QR que el cliente muestra en “Mis clases”.
          La validación de pago y suspensiones se realiza en el servidor.
        </p>

      </div>

      <div class="card resultado" v-if="resultado">
        <h3 class="resultado-title">✅ Asistencia registrada</h3>
        <div class="cliente-info">
          <div class="avatar-lg">{{ resultado.nombre?.charAt(0) }}</div>
          <div>
            <p class="cliente-nombre">{{ resultado.nombre }}</p>
            <p class="clase-info">
              {{ resultado.reserva?.clase?.actividad }} —
              {{ resultado.reserva?.clase?.dia_semana }}
              {{ resultado.reserva?.clase?.hora_inicio }} hs
            </p>
            <span
              class="badge"
              :class="resultado.reserva?.tipo === 'abonado' ? 'badge-green' : 'badge-blue'"
            >
              {{ resultado.reserva?.tipo === 'abonado' ? 'Abono' : 'Clase suelta' }}
            </span>
          </div>
        </div>
        <div class="alert alert-success">
          El cliente fue marcado como presente.
        </div>
      </div>

      <div class="card resultado-placeholder" v-else>
        <div>
          <p class="placeholder-icon">📲</p>
          <p>El resultado del escaneo aparecerá aquí</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, ref } from 'vue'
import jsQR from 'jsqr'
import api from '../../api.js'

const resultado = ref(null)
const loading = ref(false)
const error = ref('')
const errorDetalleUsuarioId = ref(null)
const mensaje = ref('')
const scannerActivo = ref(false)
const videoRef = ref(null)

let stream = null
let detector = null
let scanTimer = null
let detectando = false
const canvasLectura = document.createElement('canvas')
const canvasContexto = canvasLectura.getContext('2d', { willReadFrequently: true })

function limpiarMensajes() {
  error.value = ''
  errorDetalleUsuarioId.value = null
  mensaje.value = ''
  resultado.value = null
}

async function iniciarScanner() {
  limpiarMensajes()
  if (!navigator.mediaDevices?.getUserMedia) {
    error.value = 'La cámara no está disponible en este dispositivo.'
    return
  }

  try {
    detector = null
    if ('BarcodeDetector' in window) {
      const formatos = await window.BarcodeDetector.getSupportedFormats()
      if (formatos.includes('qr_code')) {
        detector = new window.BarcodeDetector({ formats: ['qr_code'] })
      }
    }

    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: 'environment' } },
      audio: false
    })
    scannerActivo.value = true
    await new Promise(resolve => setTimeout(resolve, 0))
    videoRef.value.srcObject = stream
    await videoRef.value.play()
    programarDeteccion()
  } catch (e) {
    detenerScanner()
    error.value = e?.name === 'NotAllowedError'
      ? 'No se concedió permiso para usar la cámara.'
      : 'No se pudo iniciar la cámara. Verificá que no esté siendo usada por otra aplicación.'
  }
}

function programarDeteccion() {
  if (!scannerActivo.value) return
  scanTimer = window.setTimeout(detectarQr, 250)
}

async function leerContenidoQr() {
  if (detector) {
    const codigos = await detector.detect(videoRef.value)
    return codigos.find(codigo => codigo.rawValue)?.rawValue || ''
  }

  const video = videoRef.value
  if (!video.videoWidth || !video.videoHeight || !canvasContexto) return ''

  canvasLectura.width = video.videoWidth
  canvasLectura.height = video.videoHeight
  canvasContexto.drawImage(video, 0, 0, canvasLectura.width, canvasLectura.height)
  const imagen = canvasContexto.getImageData(
    0,
    0,
    canvasLectura.width,
    canvasLectura.height
  )
  return jsQR(imagen.data, imagen.width, imagen.height, {
    inversionAttempts: 'attemptBoth'
  })?.data || ''
}

async function detectarQr() {
  if (!scannerActivo.value || !videoRef.value || detectando) {
    programarDeteccion()
    return
  }

  detectando = true
  try {
    const contenido = await leerContenidoQr()
    if (contenido) {
      detenerScanner()
      await registrar(contenido)
      return
    }
  } catch {
    // Algunos navegadores fallan mientras el video todavía está calentando.
  } finally {
    detectando = false
  }
  programarDeteccion()
}

function detenerScanner() {
  scannerActivo.value = false
  if (scanTimer) window.clearTimeout(scanTimer)
  scanTimer = null
  if (stream) stream.getTracks().forEach(track => track.stop())
  stream = null
  if (videoRef.value) videoRef.value.srcObject = null
}

async function registrar(qrData) {
  if (!qrData || loading.value) return
  detenerScanner()
  limpiarMensajes()
  loading.value = true
  try {
    const { data } = await api.post('/asistencia/registrar', {
      qr_data: qrData
    })
    resultado.value = data
    mensaje.value = data.mensaje || 'Asistencia registrada correctamente.'
  } catch (e) {
    const respuesta = e.response?.data || {}
    error.value = respuesta.error || 'No se pudo registrar la asistencia.'
    errorDetalleUsuarioId.value = respuesta.usuario_id || null
  } finally {
    loading.value = false
  }
}

onBeforeUnmount(detenerScanner)
</script>

<style scoped>
.scanner-title, .resultado-title { margin-bottom: 18px; font-size: 20px; }
.asistencia-error { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.asistencia-error p { margin: 0; }
.scanner-actions { display: flex; gap: 10px; margin-bottom: 14px; }
.scanner-help { font-size: 13px; color: var(--text-muted); line-height: 1.5; }
.camera-box {
  position: relative;
  overflow: hidden;
  aspect-ratio: 4 / 3;
  margin-bottom: 14px;
  border-radius: 10px;
  background: #000;
}
.camera-box video { width: 100%; height: 100%; object-fit: cover; }
.camera-frame {
  position: absolute;
  inset: 18%;
  border: 3px solid var(--verde-claro);
  border-radius: 12px;
  box-shadow: 0 0 0 999px rgba(0, 0, 0, 0.25);
}
.cliente-info { display: flex; align-items: center; gap: 14px; margin-bottom: 16px; }
.avatar-lg {
  width: 52px;
  height: 52px;
  background: linear-gradient(135deg, var(--verde), var(--azul));
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 700;
  flex-shrink: 0;
}
.cliente-nombre { font-size: 18px; font-weight: 600; margin-bottom: 4px; }
.clase-info { font-size: 13px; color: var(--text-muted); margin-bottom: 6px; }
.resultado-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 240px;
  text-align: center;
  color: var(--text-muted);
}
.placeholder-icon { font-size: 48px; margin-bottom: 8px; }
</style>
