export const MENSAJE_FONDOS_INSUFICIENTES = 'Fondos insuficientes'
export const EMAIL_PAGO_RECHAZADO = 'jesus@gmail.com'

export function pagoRechazadoPorFondos(user) {
  return String(user?.email || '').trim().toLowerCase() === EMAIL_PAGO_RECHAZADO
}
