export const MENSAJE_TARJETA_VENCIDA = 'La tarjeta esta vencida. Elegi otra tarjeta o agrega una nueva.'

export function tarjetaVencida(vencimiento, hoy = new Date()) {
  if (!vencimiento || typeof vencimiento !== 'string') return true
  if (vencimiento.length !== 5 || vencimiento[2] !== '/') return true

  const [mmStr, aaStr] = vencimiento.split('/')
  const mes = Number.parseInt(mmStr, 10)
  const anio = Number.parseInt(aaStr, 10)
  if (!Number.isInteger(mes) || !Number.isInteger(anio)) return true
  if (mes < 1 || mes > 12) return true

  const anioCompleto = 2000 + anio
  const mesActual = hoy.getMonth() + 1
  const anioActual = hoy.getFullYear()
  return anioCompleto < anioActual || (anioCompleto === anioActual && mes < mesActual)
}
