<template>
  <div>
    <!-- Sin sesión -->
    <div v-if="!auth.isAuthenticated" class="no-auth-banner card">
      <div class="no-auth-content">
        <span style="font-size:48px">🔒</span>
        <h3>Iniciá sesión para ver las clases</h3>
        <p>Necesitás una cuenta para reservar clases.</p>
        <div style="display:flex;gap:12px;justify-content:center;margin-top:16px">
          <router-link to="/login" class="btn btn-primary">Ingresar</router-link>
          <router-link to="/registro" class="btn btn-outline">Registrarse gratis</router-link>
        </div>
      </div>
    </div>

    <!-- Flujo cliente -->
    <template v-else-if="auth.isCliente">
      <!-- Barra de progreso -->
      <div class="progress-bar" v-if="paso < 6">
        <div v-for="(label, i) in stepLabels" :key="i"
          class="progress-step"
          :class="{ active: paso >= i+1, current: paso === i+1 }">
          <div class="step-dot">{{ paso > i+1 ? '✓' : i+1 }}</div>
          <div class="step-label">{{ label }}</div>
        </div>
      </div>

      <!-- PASO 1: Elegir deporte -->
      <div v-if="paso === 1" class="step-container">
        <div class="step-header">
          <div class="step-num">Paso 1</div>
          <h2>¿Qué deporte querés jugar?</h2>
        </div>
        <div class="deportes-grid">
          <div v-for="a in actividades" :key="a.id" class="deporte-card" @click="elegirDeporte(a)">
            <span class="deporte-icon">{{ sportEmoji(a.nombre) }}</span>
            <span class="deporte-nombre">{{ a.nombre }}</span>
            <!-- <span class="deporte-precio">${{ a.precio_clase?.toLocaleString() }} / clase</span> -->
          </div>
        </div>
      </div>

      <!-- PASO 2: Tipo -->
      <div v-if="paso === 2" class="step-container">
        <button class="back-btn" @click="paso = 1">← Cambiar deporte</button>
        <div class="step-header">
          <div class="step-num">Paso 2</div>
          <h2>¿Cómo querés inscribirte?</h2>
          <p>{{ seleccion.actividad?.nombre }}</p>
        </div>
        <div class="planes-grid">
          <div class="plan-card" @click="elegirTipo('no_abonado')">
            <div class="plan-nombre">🎯 Clase suelta</div>
            <div class="plan-precio">${{ seleccion.actividad?.precio_clase?.toLocaleString() }}<span>/clase</span></div>
            <div class="plan-desc">Elegís una fecha y horario puntual. Podés pagar la seña (50%) o el total.</div>
            <ul class="plan-feats">
              <li>Sin compromiso mensual</li>
              <li>Cancelación hasta 24hs antes</li>
              <li>Recuperás la seña si cancelás a tiempo</li>
            </ul>
            <button class="btn btn-outline" style="width:100%">Elegir</button>
          </div>
          <div class="plan-card plan-featured" @click="elegirTipo('abonado')">
            <div class="plan-badge">MÁS ELEGIDO</div>
            <div class="plan-nombre">📅 Abono mensual</div>
            <div class="plan-precio">${{ (seleccion.actividad?.precio_clase * 4)?.toLocaleString() }}<span>/mes aprox.</span></div>
            <div class="plan-desc">Elegís un día y horario fijo. Te inscribís a todas las clases del mes en ese turno.</div>
            <ul class="plan-feats">
              <li>20% de descuento si te sumás a mitad de mes</li>
              <li>Cancelación hasta 48hs antes con crédito</li>
              <li>Prioridad en lista de espera</li>
            </ul>
            <button class="btn btn-primary" style="width:100%">Elegir</button>
          </div>
        </div>
      </div>

      <!-- PASO 3a: Clase individual → elegir fecha, luego horario -->
      <div v-if="paso === 3 && seleccion.tipo === 'no_abonado'" class="step-container">
        <button class="back-btn" @click="paso = 2; seleccion.clase = null; seleccion.fecha = null">← Cambiar tipo</button>
        <div class="step-header">
          <div class="step-num">Paso 3</div>
          <h2>Elegí la fecha</h2>
          <p>{{ seleccion.actividad?.nombre }} · Clase suelta</p>
        </div>

        <div v-if="loadingClases" class="loading-text">Buscando fechas disponibles...</div>
        <div v-else-if="fechasDisponibles.length === 0" class="empty-state">
          <p>😕 No hay clases disponibles para esta actividad.</p>
          <button class="btn btn-outline" style="margin-top:12px" @click="paso = 1">Elegir otro deporte</button>
        </div>
        <div v-else>
          <!-- Selector de fecha -->
          <div v-if="!seleccion.fecha">
            <div class="fechas-grid">
              <div
                v-for="f in fechasDisponibles" :key="f.fecha"
                class="fecha-btn"
                @click="elegirFecha(f)"
              >
                <span class="fecha-dia-nombre">{{ f.dia_semana }}</span>
                <span class="fecha-numero">{{ formatFechaCorta(f.fecha) }}</span>
                <span class="fecha-horarios-count">{{ f.horarios.length }} horario(s)</span>
              </div>
            </div>
          </div>

          <!-- Selector de horario (una vez elegida la fecha) -->
          <div v-else>
            <div class="fecha-seleccionada-banner">
              <span>📅 {{ seleccion.fecha.dia_semana }}, {{ formatFecha(seleccion.fecha.fecha) }}</span>
              <button class="btn btn-outline btn-sm" @click="seleccion.fecha = null; seleccion.clase = null">Cambiar fecha</button>
            </div>
            <h3 style="font-size:18px;margin-bottom:16px">Elegí el horario</h3>
            <div class="horarios-grid">
              <div
                v-for="h in seleccion.fecha.horarios" :key="h.clase_id"
                class="horario-btn"
                :class="{ selected: seleccion.clase?.id === h.clase_id, 'sin-cupo': h.cupos_disponibles === 0 }"
                @click="elegirHorario(h)"
              >
                <span class="horario-hora">{{ h.hora_inicio }}</span>
                <span class="horario-cupo" :class="{ 'cupo-agotado': h.cupos_disponibles === 0 }">
                  {{ h.cupos_disponibles > 0 ? `${h.cupos_disponibles} cupos` : 'Lista de espera' }}
                </span>
              </div>
            </div>

            <div v-if="seleccion.clase" class="seleccion-banner">
              <span>
                ✓ {{ seleccion.actividad?.nombre }} · {{ seleccion.fecha.dia_semana }} {{ formatFecha(seleccion.fecha.fecha) }} ·
                <template v-if="seleccion.clase?.cupos_disponibles === 0">Lista de espera</template>
                <template v-else>{{ seleccion.clase?.hora_inicio }} hs</template>
              </span>
              <button class="btn btn-primary" @click="paso = 4">
                {{ seleccion.clase?.cupos_disponibles === 0 ? 'Inscribirme en la lista de espera →' : 'Continuar →' }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- PASO 3b: Abono → primero elegir día, luego elegir horario -->
      <div v-if="paso === 3 && seleccion.tipo === 'abonado'" class="step-container">
        <button class="back-btn" @click="paso = 2; seleccion.opcionAbono = null; abonoDiaSeleccionado = null">← Cambiar tipo</button>
        <div class="step-header">
          <div class="step-num">Paso 3</div>
          <h2>Elegí el día</h2>
          <p>{{ seleccion.actividad?.nombre }} · Abono mensual</p>
        </div>

        <div v-if="loadingClases" class="loading-text">Buscando horarios disponibles...</div>
        <div v-else-if="horariosAbono.length === 0" class="empty-state">
          <p>😕 No hay turnos disponibles para abono este mes.</p>
          <button class="btn btn-outline" style="margin-top:12px" @click="paso = 1">Elegir otro deporte</button>
        </div>
        <div v-else>
          <!-- Selector de día -->
          <div v-if="!abonoDiaSeleccionado">
            <div class="fechas-grid">
              <div
                v-for="dia in diasAbono" :key="dia.dia_semana_num"
                class="fecha-btn"
                @click="abonoDiaSeleccionado = dia"
              >
                <span class="fecha-dia-nombre">{{ dia.dia_semana }}</span>
                <span class="fecha-numero" style="font-size:16px;margin:4px 0">{{ dia.horarios.length }} horario(s)</span>
                <span class="fecha-horarios-count">este mes</span>
              </div>
            </div>
          </div>

          <!-- Selector de horario (una vez elegido el día) -->
          <div v-else>
            <div class="fecha-seleccionada-banner">
              <span>📅 {{ abonoDiaSeleccionado.dia_semana }}</span>
              <button class="btn btn-outline btn-sm" @click="abonoDiaSeleccionado = null; seleccion.opcionAbono = null">Cambiar día</button>
            </div>
            <h3 style="font-size:18px;margin-bottom:16px">Elegí el horario</h3>
            <div class="horarios-grid">
              <div
                v-for="op in abonoDiaSeleccionado.horarios" :key="op.hora_inicio"
                class="horario-btn"
                :class="{ selected: seleccion.opcionAbono?.hora_inicio === op.hora_inicio }"
                @click="elegirOpcionAbono(op)"
              >
                <span class="horario-hora">{{ op.hora_inicio }}</span>
                <span class="horario-cupo">{{ op.clases_mes.filter(c => c.cupos_disponibles > 0 && !c.ya_inscripto).length }} clase(s) con cupo</span>
              </div>
            </div>

            <div v-if="seleccion.opcionAbono" class="seleccion-banner">
              <span>✓ {{ seleccion.actividad?.nombre }} · {{ abonoDiaSeleccionado.dia_semana }} {{ seleccion.opcionAbono.hora_inicio }} hs</span>
              <button class="btn btn-primary" @click="cargarDetalleAbono">Ver detalle del abono →</button>
            </div>
          </div>
        </div>
      </div>

      <!-- PASO 4a: Confirmar clase individual (si hay cupo) -->
      <div v-if="paso === 4 && seleccion.tipo === 'no_abonado' && seleccion.clase?.cupos_disponibles > 0" class="step-container">
        <button class="back-btn" @click="paso = 3">← Cambiar horario</button>
        <div class="step-header">
          <div class="step-num">Paso 4</div>
          <h2>Confirmá tu reserva</h2>
        </div>

        <div class="confirm-card card">
          <div class="confirm-row"><span class="confirm-label">Deporte</span><span class="confirm-value">{{ sportEmoji(seleccion.actividad?.nombre) }} {{ seleccion.actividad?.nombre }}</span></div>
          <div class="confirm-row"><span class="confirm-label">Fecha</span><span class="confirm-value">{{ seleccion.fecha?.dia_semana }}, {{ formatFecha(seleccion.fecha?.fecha) }}</span></div>
          <div class="confirm-row"><span class="confirm-label">Horario</span><span class="confirm-value">{{ seleccion.clase?.hora_inicio }} hs</span></div>
          <div class="confirm-row"><span class="confirm-label">Precio total</span><span class="confirm-value">${{ seleccion.actividad?.precio_clase?.toLocaleString() }}</span></div>
        </div>

        <!-- Elegir monto a pagar -->
        <div class="pago-opciones">
          <h3 style="font-size:16px;margin-bottom:14px">¿Cuánto querés pagar?</h3>
          <div class="pago-opcion" :class="{ selected: montoPago === 'senia' }" @click="montoPago = 'senia'">
            <div class="pago-radio">{{ montoPago === 'senia' ? '●' : '○' }}</div>
            <div>
              <p style="font-weight:600">Seña (50%) — ${{ Math.round(seleccion.actividad?.precio_clase * 0.5).toLocaleString() }}</p>
              <p style="font-size:12px;color:var(--text-muted)">El resto lo abonás al llegar a la clase</p>
            </div>
          </div>
          <div class="pago-opcion" :class="{ selected: montoPago === 'total' }" @click="montoPago = 'total'">
            <div class="pago-radio">{{ montoPago === 'total' ? '●' : '○' }}</div>
            <div>
              <p style="font-weight:600">Total — ${{ seleccion.actividad?.precio_clase?.toLocaleString() }}</p>
              <p style="font-size:12px;color:var(--text-muted)">Pagás todo ahora, no debés nada al llegar</p>
            </div>
          </div>
        </div>

          <button class="btn btn-primary" style="width:100%;max-width:440px;margin-top:16px" @click="paso = 5; fetchTarjetas()">
            Ir a pagar ${{ montoPago === 'senia' ? Math.round(seleccion.actividad?.precio_clase * 0.5).toLocaleString() : seleccion.actividad?.precio_clase?.toLocaleString() }} →
          </button>
      </div>

        <!-- PASO 4a-2: Inscribirme en lista de espera (si no hay cupo) -->
        <div v-if="paso === 4 && seleccion.tipo === 'no_abonado' && seleccion.clase?.cupos_disponibles === 0" class="step-container">
          <button class="back-btn" @click="paso = 3">← Cambiar horario</button>
          <div class="step-header">
            <div class="step-num">Paso 4</div>
            <h2>Inscribirme en la lista de espera</h2>
            <p>Te anotás en la lista de espera para esta clase. Te avisaremos si se libera un cupo.</p>
          </div>

          <div class="confirm-card card">
            <div class="confirm-row"><span class="confirm-label">Deporte</span><span class="confirm-value">{{ sportEmoji(seleccion.actividad?.nombre) }} {{ seleccion.actividad?.nombre }}</span></div>
            <div class="confirm-row"><span class="confirm-label">Fecha</span><span class="confirm-value">{{ seleccion.fecha?.dia_semana }}, {{ formatFecha(seleccion.fecha?.fecha) }}</span></div>
            <div class="confirm-row"><span class="confirm-label">Horario</span><span class="confirm-value">Lista de espera</span></div>
          </div>

          <div style="margin-top:16px;max-width:440px">
            <div class="alert alert-info" style="margin-bottom:12px">Si un cupo queda disponible serás notificado por email.</div>
            <button class="btn btn-primary" style="width:100%" @click="inscribirEnListaEspera" :disabled="pagando">
              {{ pagando ? 'Procesando...' : 'Inscribirme en la lista de espera' }}
            </button>
          </div>
        </div>

      <!-- PASO 4b: Detalle del abono -->
      <div v-if="paso === 4 && seleccion.tipo === 'abonado'" class="step-container">
        <button class="back-btn" @click="paso = 3">← Cambiar turno</button>
        <div class="step-header">
          <div class="step-num">Paso 4</div>
          <h2>Detalle de tu abono</h2>
          <p>{{ seleccion.actividad?.nombre }} · {{ detalleAbono?.dia_semana }} {{ detalleAbono?.hora_inicio }} hs</p>
          <p>Si hay una clase sin cupo, serás anotado automaticamente en la lista de espera.</p>
        </div>

        <div v-if="loadingDetalle" class="loading-text">Calculando abono...</div>
        <div v-else-if="detalleAbono">
          <div v-if="detalleAbono.aplicar_descuento" class="alert alert-success" style="max-width:500px">
            🎉 Estás entrando a mitad de mes con más de 1 clase disponible. ¡Tenés un 20% de descuento en cada clase!
          </div>
          <div v-else-if="!detalleAbono.usuario_tiene_beneficio && detalleAbono.total_disponibles > 1" class="alert alert-warning" style="max-width:500px">
            ⚠️ Perdiste el beneficio del 20% de descuento por haber cancelado 3 o más clases de abono. Se cobra el precio completo.
          </div>

          <div class="abono-clases-lista">
            <div v-for="c in detalleAbono.clases" :key="c.clase_id" class="abono-clase-item"
              :class="{
                'clase-incluida': c.incluida_en_abono,
                'clase-excluida': !c.incluida_en_abono && !c.en_espera && !c.ya_inscripto,
                'clase-ya-inscripto': c.ya_inscripto,
                'clase-en-espera': c.en_espera
              }">
              <div style="display:flex;align-items:center;gap:10px">
                <span class="clase-check">{{ c.incluida_en_abono ? '✓' : (c.ya_inscripto ? '→' : (c.en_espera ? '⏳' : '✗')) }}</span>
                <div>
                  <p style="font-weight:600;font-size:14px">{{ c.dia_semana }} {{ formatFecha(c.fecha) }}</p>
                  <p style="font-size:12px;color:var(--text-muted)">{{ c.hora_inicio }} hs</p>
                </div>
              </div>
              <div style="text-align:right">
                <p v-if="c.incluida_en_abono" style="font-weight:600;color:var(--verde-claro)">${{ c.precio_clase?.toLocaleString() }}</p>
                <p v-else-if="c.ya_inscripto" style="font-size:12px;color:var(--azul-claro)">Ya inscripto</p>
                <p v-else-if="c.en_espera" style="font-size:12px;color:var(--warning);font-weight:600">Lista de espera</p>
                <p v-else style="font-size:12px;color:var(--danger)">
                  {{ c.cancelada ? 'Cancelada' : 'Sin cupo ' }}
                </p>
              </div>
            </div>
          </div>
          <div v-if="detalleAbono.ya_inscripto_en?.length" class="alert alert-warning" style="margin-top:10px;font-size:13px">
            ℹ️ Ya estás inscripto en {{ detalleAbono.ya_inscripto_en.length }} clase(s) de este turno. Solo se te cobrarán las clases nuevas.
          </div>

          <div class="confirm-card card" style="margin-top:16px">
            <div class="confirm-row"><span class="confirm-label">Clases incluidas en el abono</span><span class="confirm-value">{{ detalleAbono.total_disponibles }}</span></div>
            <template v-if="detalleAbono.clases.some(c => c.en_espera)">
              <div class="confirm-row">
                <span class="confirm-label" style="color:var(--warning)">⏳ En lista de espera (no cobradas)</span>
                <span class="confirm-value" style="color:var(--warning)">{{ detalleAbono.clases.filter(c => c.en_espera).length }}</span>
              </div>
            </template>
            <template v-else-if="detalleAbono.total_clases_mes > detalleAbono.total_disponibles">
              <div class="confirm-row">
                <span class="confirm-label" style="color:var(--warning)">Clases sin cupo (no incluidas)</span>
                <span class="confirm-value">{{ detalleAbono.total_clases_mes - detalleAbono.total_disponibles }}</span>
              </div>
            </template>
            <div class="confirm-row"><span class="confirm-label">Precio por clase</span>
              <span class="confirm-value">
                ${{ detalleAbono.precio_por_clase?.toLocaleString() }}
                <span v-if="detalleAbono.aplicar_descuento" style="font-size:12px;color:var(--success)"> (20% desc.)</span>
              </span>
            </div>
            <div class="confirm-row total-row">
              <span class="confirm-label">Total del abono</span>
              <span class="confirm-value total-value">${{ detalleAbono.monto_total?.toLocaleString() }}</span>
            </div>
          </div>

          <button class="btn btn-primary" style="width:100%;max-width:500px;margin-top:16px"
            @click="detalleAbono.total_disponibles === 0 ? confirmarPago() : (paso = 5, fetchTarjetas())"
            :disabled="!detalleAbono.clases?.some(c => !c.cancelada && !c.ya_inscripto) || pagando">
            {{ pagando ? 'Procesando...' : detalleAbono.total_disponibles === 0
              ? `Anotarme en lista de espera →`
              : `Ir a pagar $${detalleAbono.monto_total?.toLocaleString()} →` }}
          </button>
        </div>
      </div>

      <!-- PASO 5: Pagar -->
      <div v-if="paso === 5" class="step-container">
        <button class="back-btn" @click="paso = 4">← Volver</button>
        <div class="step-header">
          <div class="step-num">Paso 5</div>
          <!-- Abono en periodo gracia (1-10): no paga ahora -->
          <template v-if="seleccion.tipo === 'abonado' && esPeriodoGracia">
            <h2>Confirmar inscripción</h2>
            <p>Tu abono se registra ahora. Tenés hasta el <strong>día 10</strong> para abonar.</p>
          </template>
          <template v-else>
            <h2>Pago con tarjeta de crédito</h2>
            <p>Monto: <strong style="color:var(--verde-claro)">${{ montoFinal?.toLocaleString() }}</strong></p>
          </template>
        </div>

        <div class="alert alert-error" v-if="errorPago">{{ errorPago }}</div>

        <!-- ABONO PERIODO GRACIA: solo confirmar, sin pagar -->
        <div v-if="seleccion.tipo === 'abonado' && esPeriodoGracia" style="max-width:500px">
          <div class="confirm-card card" style="margin-bottom:20px">
            <div class="confirm-row">
              <span class="confirm-label">Deporte</span>
              <span class="confirm-value">{{ sportEmoji(seleccion.actividad?.nombre) }} {{ seleccion.actividad?.nombre }}</span>
            </div>
            <div class="confirm-row">
              <span class="confirm-label">Turno</span>
              <span class="confirm-value">{{ detalleAbono?.dia_semana }} {{ detalleAbono?.hora_inicio }} hs</span>
            </div>
            <div class="confirm-row">
              <span class="confirm-label">Clases del mes</span>
              <span class="confirm-value">{{ detalleAbono?.total_disponibles }}</span>
            </div>
            <div class="confirm-row total-row">
              <span class="confirm-label">Total a pagar antes del día 10</span>
              <span class="confirm-value total-value">${{ montoFinal?.toLocaleString() }}</span>
            </div>
          </div>
          <div class="alert alert-warning" style="margin-bottom:16px">
            📅 Estás en el período de pago (1 al 10 del mes). Tu inscripción quedará registrada y deberás abonar
            <strong>${{ montoFinal?.toLocaleString() }}</strong> antes del día 10.
            Podés pagar desde <strong>Mis Pagos</strong>.
          </div>
          <button class="btn btn-primary" style="width:100%"
            @click="confirmarPago" :disabled="pagando">
            {{ pagando ? 'Procesando...' : 'Confirmar inscripción' }}
          </button>
        </div>

        <!-- PAGO NORMAL CON TARJETA -->
        <template v-else>
          <div v-if="tarjetas.length === 0" style="max-width:440px">
            <div class="alert alert-warning">No tenés ninguna tarjeta registrada. Agregá una para continuar.</div>
            <FormTarjeta label-boton="Guardar tarjeta" :show-cancelar="false" @guardada="onTarjetaGuardada" />
          </div>
          <div v-else style="max-width:440px">
            <p style="font-size:14px;color:var(--text-muted);margin-bottom:12px">Seleccioná una tarjeta:</p>
            <div v-for="t in tarjetas" :key="t.id" class="tarjeta-opcion"
              :class="{ selected: tarjetaSeleccionada?.id === t.id }"
              @click="tarjetaSeleccionada = t">
              <div class="tarjeta-icon">💳</div>
              <div>
                <p style="font-weight:600">•••• •••• •••• {{ t.ultimos_4 }}</p>
                <p style="font-size:12px;color:var(--text-muted)">{{ t.titular }} · Vence {{ t.vencimiento }}</p>
              </div>
              <div class="tarjeta-check" v-if="tarjetaSeleccionada?.id === t.id">✓</div>
            </div>
            <button v-if="!mostrarNuevaTarjeta" class="btn btn-outline btn-sm" style="margin-top:10px" @click="mostrarNuevaTarjeta = true">+ Usar otra tarjeta</button>
            <div v-else style="margin-top:16px;padding-top:16px;border-top:1px solid var(--border)">
              <FormTarjeta label-boton="Guardar tarjeta" @guardada="onTarjetaGuardada" @cancelar="mostrarNuevaTarjeta = false" />
            </div>
            <button class="btn btn-primary" style="width:100%;margin-top:20px"
              @click="confirmarPago" :disabled="!tarjetaSeleccionada || pagando">
              {{ pagando ? 'Procesando...' : `Pagar $${montoFinal?.toLocaleString()}` }}
            </button>
          </div>
        </template>
      </div>

      <!-- PASO 6: Éxito -->
      <div v-if="paso === 6" class="step-container success-container">
        <div class="success-icon">{{ (resultadoExito?.en_espera || resultadoExito?.total_inscripto === 0) ? '⏳' : '✅' }}</div>
        <h2>¡{{ (resultadoExito?.en_espera || resultadoExito?.total_inscripto === 0) ? 'En lista de espera' : 'Reserva confirmada' }}!</h2>
        <p style="color:var(--text-muted)">
          {{ resultadoExito?.en_espera || resultadoExito?.total_inscripto === 0
            ? 'Te anotamos en lista de espera. Te avisaremos cuando se libere un cupo.'
            : resultadoExito?.pago_diferido
              ? 'Tu inscripción quedó registrada. Tenés hasta el día 10 para abonar desde Mis Pagos.'
              : 'Te enviamos los detalles por email.' }}
        </p>
        <div v-if="!resultadoExito?.en_espera && resultadoExito?.total_inscripto !== 0" class="confirm-card card" style="max-width:380px;margin:24px auto">
          <div class="confirm-row"><span class="confirm-label">Deporte</span><span class="confirm-value">{{ sportEmoji(seleccion.actividad?.nombre) }} {{ seleccion.actividad?.nombre }}</span></div>
          <div class="confirm-row"><span class="confirm-label">Tipo</span><span class="confirm-value">{{ seleccion.tipo === 'abonado' ? 'Abono mensual' : 'Clase suelta' }}</span></div>
          <div v-if="seleccion.tipo === 'abonado'" class="confirm-row"><span class="confirm-label">Clases inscripto</span><span class="confirm-value">{{ resultadoExito?.total_inscripto }}</span></div>
          <div v-if="seleccion.tipo === 'abonado' && resultadoExito?.clases_en_espera?.length > 0" class="confirm-row">
            <span class="confirm-label" style="color:var(--warning)">⏳ En lista de espera</span>
            <span class="confirm-value" style="color:var(--warning)">{{ resultadoExito.clases_en_espera.length }} clase(s)</span>
          </div>
          <div class="confirm-row total-row"><span class="confirm-label">Pagado</span><span class="confirm-value total-value">${{ montoFinal?.toLocaleString() }}</span></div>
        </div>
        <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap">
          <router-link to="/mis-reservas" class="btn btn-primary">Ver mis reservas</router-link>
          <button class="btn btn-outline" @click="reiniciar">Nueva reserva</button>
        </div>
      </div>
    </template>

    <!-- Admin/empleado: listado clásico -->
    <template v-else>
      <div class="page-header"><h2>CLASES DISPONIBLES</h2></div>
      <div class="card" style="margin-bottom:20px;padding:16px">
        <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end">
          <div class="input-group" style="margin:0;flex:1">
            <select v-model="filtros.actividad_id" @change="fetchClasesAdmin">
              <option value="">Todas las actividades</option>
              <option v-for="a in actividades" :key="a.id" :value="a.id">{{ a.nombre }}</option>
            </select>
          </div>
          <div class="input-group" style="margin:0;flex:1">
            <input v-model="filtros.desde" type="date" @change="fetchClasesAdmin" />
          </div>
          <div class="input-group" style="margin:0;flex:1">
            <input v-model="filtros.hasta" type="date" @change="fetchClasesAdmin" />
          </div>
          <button class="btn btn-outline" @click="filtros={actividad_id:'',desde:'',hasta:''}; fetchClasesAdmin()">Limpiar</button>
        </div>
      </div>
      <div class="clases-grid">
        <div v-for="clase in clasesAdmin" :key="clase.id" class="clase-card card" :class="{'cancelada-card': clase.cancelada}">
          <div class="clase-header">
            <span style="font-size:32px">{{ sportEmoji(clase.actividad) }}</span>
            <div style="flex:1">
              <h3>{{ clase.actividad }}</h3>
              <div style="display:flex;gap:6px;margin-top:4px;flex-wrap:wrap">
                <span class="dia-badge">{{ clase.dia_semana }}</span>
                <span class="dia-badge fecha-badge">{{ formatFecha(clase.fecha) }}</span>
                <span v-if="clase.cancelada" class="badge badge-red">Cancelada</span>
              </div>
            </div>
            <div style="text-align:center">
              <span style="font-size:24px;font-family:'Bebas Neue',sans-serif;color:var(--success);display:block">{{ clase.cupos_disponibles }}</span>
              <span style="font-size:11px;color:var(--text-muted)">cupos</span>
            </div>
          </div>
          <div style="display:flex;gap:8px;font-size:13px;color:var(--text-muted)">
            <span>🕐 {{ clase.hora_inicio }} hs</span>
            <span>👥 {{ clase.cupo_maximo }}</span>
            <span>💰 ${{ clase.precio_clase?.toLocaleString() }}</span>
          </div>
          <router-link :to="`/clases/${clase.id}`" class="btn btn-outline btn-sm">🔍 Ver detalle</router-link>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth.js'
import FormTarjeta from '../components/FormTarjeta.vue'
import api from '../api.js'

const auth = useAuthStore()

const paso = ref(1)
const actividades = ref([])
const seleccion = ref({ actividad: null, tipo: null, fecha: null, clase: null, opcionAbono: null })
const fechasDisponibles = ref([])
const horariosAbono = ref([])
const detalleAbono = ref(null)
const loadingClases = ref(false)
const loadingDetalle = ref(false)
const tarjetas = ref([])
const tarjetaSeleccionada = ref(null)
const mostrarNuevaTarjeta = ref(false)
const pagando = ref(false)
const errorPago = ref('')
const resultadoExito = ref(null)
const montoPago = ref('senia') // 'senia' o 'total' para clase individual
const abonoDiaSeleccionado = ref(null)
const clasesAdmin = ref([])
const filtros = ref({ actividad_id: '', desde: '', hasta: '' })

const stepLabels = ['Deporte', 'Tipo', 'Fecha/Hora', 'Confirmar', 'Pagar']

const montoFinal = computed(() => {
  if (seleccion.value.tipo === 'abonado') {
    return detalleAbono.value?.monto_total || 0
  }
  const precio = seleccion.value.actividad?.precio_clase || 0
  return montoPago.value === 'senia' ? Math.round(precio * 0.5) : precio
})

// Si hoy es entre 1 y 10 del mes, el abono se inscribe sin pagar (pago diferido hasta el 10)
const esPeriodoGracia = computed(() => {
  const dia = new Date().getDate()
  return dia >= 1 && dia <= 10
})


// Agrupa horariosAbono por día para mostrar primero días, luego horarios
const diasAbono = computed(() => {
  const map = {}
  for (const op of horariosAbono.value) {
    const key = op.dia_semana_num
    if (!map[key]) {
      map[key] = { dia_semana: op.dia_semana, dia_semana_num: op.dia_semana_num, horarios: [] }
    }
    map[key].horarios.push(op)
  }
  return Object.values(map).sort((a, b) => a.dia_semana_num - b.dia_semana_num)
})

function sportEmoji(n) {
  return { 'Fútbol': '⚽', 'Pádel': '🎾', 'Básquet': '🏀', 'Vóley': '🏐' }[n] || '🏃'
}

function formatFecha(f) {
  if (!f) return ''
  const [y, m, d] = f.split('-')
  return `${d}/${m}/${y}`
}

function formatFechaCorta(f) {
  if (!f) return ''
  const [y, m, d] = f.split('-')
  return `${d}/${m}`
}

function elegirDeporte(a) {
  seleccion.value = { actividad: a, tipo: null, fecha: null, clase: null, opcionAbono: null }
  paso.value = 2
}

function elegirTipo(tipo) {
  seleccion.value.tipo = tipo
  seleccion.value.fecha = null
  seleccion.value.clase = null
  seleccion.value.opcionAbono = null
  detalleAbono.value = null
  abonoDiaSeleccionado.value = null
  paso.value = 3
  if (tipo === 'no_abonado') fetchFechasDisponibles()
  else fetchHorariosAbono()
}

async function fetchFechasDisponibles() {
  loadingClases.value = true
  fechasDisponibles.value = []
  try {
    const ahora = new Date()
    const pad = n => String(n).padStart(2, '0')
    const hoy = `${ahora.getFullYear()}-${pad(ahora.getMonth()+1)}-${pad(ahora.getDate())}`
    const hasta = new Date(ahora)
    hasta.setMonth(hasta.getMonth() + 1)
    const hastaStr = `${hasta.getFullYear()}-${pad(hasta.getMonth()+1)}-${pad(hasta.getDate())}`
    const { data } = await api.get('/clases/fechas-disponibles', {
      params: { actividad_id: seleccion.value.actividad.id, desde: hoy, hasta: hastaStr }
    })
    fechasDisponibles.value = data
  } catch(e) { console.error(e) }
  finally { loadingClases.value = false }
}

async function fetchHorariosAbono() {
  loadingClases.value = true
  horariosAbono.value = []
  try {
    const { data } = await api.get('/clases/horarios-disponibles', {
      params: { actividad_id: seleccion.value.actividad.id, usuario_id: auth.user?.id }
    })
    horariosAbono.value = data
  } catch(e) { console.error(e) }
  finally { loadingClases.value = false }
}

function elegirFecha(f) {
  seleccion.value.fecha = f
  seleccion.value.clase = null
}

function elegirHorario(h) {
  seleccion.value.clase = { id: h.clase_id, hora_inicio: h.hora_inicio, cupos_disponibles: h.cupos_disponibles }
}

function elegirOpcionAbono(op) {
  seleccion.value.opcionAbono = op
}

async function cargarDetalleAbono() {
  loadingDetalle.value = true
  paso.value = 4
  try {
    const op = seleccion.value.opcionAbono
    const authStore = auth
    const { data } = await api.get('/clases/detalle-abono', {
      params: {
        actividad_id: seleccion.value.actividad.id,
        dia_semana_num: op.dia_semana_num,
        hora_inicio: op.hora_inicio,
        usuario_id: authStore.user?.id
      }
    })
    detalleAbono.value = data
  } catch(e) { console.error(e) }
  finally { loadingDetalle.value = false }
}

async function fetchTarjetas() {
  try {
    const { data } = await api.get('/auth/tarjetas')
    tarjetas.value = data
    if (data.length > 0) tarjetaSeleccionada.value = data[0]
  } catch {}
}

function onTarjetaGuardada(t) {
  tarjetas.value.push(t)
  tarjetaSeleccionada.value = t
  mostrarNuevaTarjeta.value = false
}

async function confirmarPago() {
  pagando.value = true
  errorPago.value = ''
  try {
    if (seleccion.value.tipo === 'abonado') {
      const clasesIds = detalleAbono.value.clases
        .filter(c => c.incluida_en_abono)
        .map(c => c.clase_id)

      // También enviamos las sin cupo para que el backend las ponga en lista de espera
      const clasesSinCupoIds = detalleAbono.value.clases
        .filter(c => !c.incluida_en_abono && !c.ya_inscripto && !c.cancelada)
        .map(c => c.clase_id)

      const pagoAhora = !esPeriodoGracia.value  // si NO es periodo gracia, paga ahora

      const { data } = await api.post('/reservas/abono', {
        clases_ids: [...clasesIds, ...clasesSinCupoIds],
        monto_total: detalleAbono.value.monto_total,
        metodo_pago: pagoAhora ? 'tarjeta_credito' : null,
        aplicar_descuento: detalleAbono.value.aplicar_descuento,
        pago_diferido: esPeriodoGracia.value
      })
      resultadoExito.value = { ...data, pago_diferido: esPeriodoGracia.value }
    } else {
      // Clase individual: siempre paga ahora
      const { data } = await api.post('/reservas/', {
        clase_id: seleccion.value.clase.id,
        tipo: 'no_abonado',
        monto_pagar: montoPago.value,
        metodo_pago: 'tarjeta_credito'
      })
      if (data.en_espera) {
        resultadoExito.value = { en_espera: true }
      } else {
        resultadoExito.value = data
      }
    }
    paso.value = 6
  } catch(e) {
    errorPago.value = e.response?.data?.error || 'Error al procesar el pago'
  } finally {
    pagando.value = false
  }
}

async function inscribirEnListaEspera() {
  pagando.value = true
  errorPago.value = ''
  try {
    const { data } = await api.post('/reservas/', {
      clase_id: seleccion.value.clase.id,
      tipo: 'no_abonado'
    })
    if (data.en_espera) {
      resultadoExito.value = { en_espera: true, mensaje: data.mensaje }
    } else {
      resultadoExito.value = data
    }
    paso.value = 6
  } catch (e) {
    errorPago.value = e.response?.data?.error || 'Error al inscribirse en la lista de espera'
  } finally {
    pagando.value = false
  }
}

function reiniciar() {
  paso.value = 1
  seleccion.value = { actividad: null, tipo: null, fecha: null, clase: null, opcionAbono: null }
  fechasDisponibles.value = []
  horariosAbono.value = []
  detalleAbono.value = null
  abonoDiaSeleccionado.value = null
  tarjetaSeleccionada.value = null
  mostrarNuevaTarjeta.value = false
  resultadoExito.value = null
  errorPago.value = ''
  montoPago.value = 'senia'
}

async function fetchClasesAdmin() {
  const params = { solo_activas: false }
  if (filtros.value.actividad_id) params.actividad_id = filtros.value.actividad_id
  if (filtros.value.desde) params.desde = filtros.value.desde
  if (filtros.value.hasta) params.hasta = filtros.value.hasta
  const { data } = await api.get('/clases/', { params })
  clasesAdmin.value = data
}

onMounted(async () => {
  if (auth.isAuthenticated) {
    const { data } = await api.get('/actividades/')
    actividades.value = data
    if (!auth.isCliente) fetchClasesAdmin()
  }
})
</script>

<style scoped>
.no-auth-banner { text-align:center;padding:60px 40px;margin-top:20px; }
.no-auth-content { display:flex;flex-direction:column;align-items:center;gap:12px; }
.no-auth-content h3 { font-size:24px; }
.no-auth-content p { color:var(--text-muted);font-size:15px; }

/* Progress bar */
.progress-bar { display:flex;align-items:flex-start;justify-content:center;position:relative;padding:24px 0 32px;gap:0; }
.progress-step { display:flex;flex-direction:column;align-items:center;gap:8px;width:90px;position:relative;z-index:1; }
.progress-step:not(:last-child)::after { content:'';position:absolute;top:17px;left:calc(50% + 18px);width:calc(100% - 36px);height:2px;background:var(--border); }
.progress-step.active:not(:last-child)::after { background:var(--verde); }
.step-dot { width:36px;height:36px;border-radius:50%;background:var(--dark-3);border:2px solid var(--border);display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;color:var(--text-muted);transition:all 0.3s; }
.progress-step.active .step-dot { background:var(--verde);border-color:var(--verde);color:white; }
.step-label { font-size:11px;color:var(--text-muted);text-align:center; }
.progress-step.active .step-label { color:var(--text); }

/* Step container */
.step-container { max-width:640px;margin:0 auto;padding-bottom:40px; }
.step-header { text-align:center;margin-bottom:28px; }
.step-num { font-size:12px;color:var(--verde-claro);letter-spacing:2px;text-transform:uppercase;margin-bottom:8px;font-weight:600; }
.step-header h2 { font-size:32px;font-family:'Bebas Neue',sans-serif; }
.step-header p { color:var(--text-muted);margin-top:6px; }
.back-btn { background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:13px;margin-bottom:16px;display:flex;align-items:center;gap:4px;font-family:'DM Sans',sans-serif; }
.back-btn:hover { color:var(--text); }

/* Paso 1 */
.deportes-grid { display:grid;grid-template-columns:repeat(2,1fr);gap:16px; }
.deporte-card { background:var(--dark-2);border:2px solid var(--border);border-radius:14px;padding:28px;text-align:center;cursor:pointer;transition:all 0.2s;display:flex;flex-direction:column;align-items:center;gap:8px; }
.deporte-card:hover { border-color:var(--verde);transform:translateY(-3px);box-shadow:0 8px 24px rgba(46,125,50,0.15); }
.deporte-icon { font-size:40px; }
.deporte-nombre { font-size:18px;font-family:'Bebas Neue',sans-serif;letter-spacing:1px; }
.deporte-precio { font-size:13px;color:var(--text-muted); }

/* Paso 2 */
.planes-grid { display:grid;grid-template-columns:repeat(2,1fr);gap:16px; }
.plan-card { background:var(--dark-2);border:2px solid var(--border);border-radius:14px;padding:24px;cursor:pointer;transition:all 0.2s;display:flex;flex-direction:column;gap:10px; }
.plan-card:hover { border-color:var(--verde); }
.plan-featured { border-color:var(--verde);background:rgba(46,125,50,0.05); }
.plan-badge { display:inline-block;background:var(--verde);color:white;font-size:10px;font-weight:700;padding:2px 10px;border-radius:4px;letter-spacing:1px; }
.plan-nombre { font-size:18px;font-weight:600; }
.plan-precio { font-size:26px;font-family:'Bebas Neue',sans-serif;color:var(--verde-claro); }
.plan-precio span { font-size:13px;font-weight:400;color:var(--text-muted);font-family:'DM Sans',sans-serif; }
.plan-desc { font-size:13px;color:var(--text-muted);line-height:1.5; }
.plan-feats { list-style:none;display:flex;flex-direction:column;gap:6px;flex:1; }
.plan-feats li { font-size:12px;color:var(--text-muted);display:flex;align-items:center;gap:6px; }
.plan-feats li::before { content:'';width:5px;height:5px;border-radius:50%;background:var(--verde);flex-shrink:0; }

/* Paso 3 individual - fechas */
.fechas-grid { display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:10px; }
.fecha-btn { background:var(--dark-2);border:2px solid var(--border);border-radius:10px;padding:14px 10px;text-align:center;cursor:pointer;transition:all 0.2s;display:flex;flex-direction:column;gap:4px; }
.fecha-btn:hover { border-color:var(--verde);transform:translateY(-2px); }
.fecha-dia-nombre { font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px; }
.fecha-numero { font-size:22px;font-family:'Bebas Neue',sans-serif;color:var(--verde-claro); }
.fecha-horarios-count { font-size:11px;color:var(--text-muted); }
.fecha-seleccionada-banner { display:flex;align-items:center;justify-content:space-between;background:rgba(46,125,50,0.1);border:1px solid var(--verde);border-radius:10px;padding:12px 16px;margin-bottom:20px;font-size:14px;font-weight:500; }

/* Horarios */
.horarios-grid { display:flex;flex-wrap:wrap;gap:10px;margin-bottom:16px; }
.horario-btn { background:var(--dark-2);border:2px solid var(--border);border-radius:10px;padding:12px 18px;cursor:pointer;transition:all 0.2s;text-align:center;min-width:100px; }
.horario-btn:hover:not(.sin-cupo) { border-color:var(--verde);background:rgba(46,125,50,0.1); }
.horario-btn.selected { border-color:var(--verde-claro);background:rgba(46,125,50,0.15); }
.horario-btn.sin-cupo { opacity:0.6; }
.horario-hora { font-size:16px;font-weight:600;display:block; }
.horario-cupo { font-size:11px;color:var(--success);display:block;margin-top:3px; }
.cupo-agotado { color:var(--warning) !important; }
.seleccion-banner { display:flex;align-items:center;justify-content:space-between;background:rgba(46,125,50,0.1);border:1px solid var(--verde);border-radius:10px;padding:14px 18px;margin-top:16px;gap:12px;font-size:14px;flex-wrap:wrap; }

/* Paso 3 abono */
.horarios-abono-lista { display:flex;flex-direction:column;gap:10px;margin-bottom:16px; }
.horario-abono-btn { background:var(--dark-2);border:2px solid var(--border);border-radius:12px;padding:16px 20px;cursor:pointer;transition:all 0.2s; }
.horario-abono-btn:hover { border-color:var(--verde); }
.horario-abono-btn.selected { border-color:var(--verde-claro);background:rgba(46,125,50,0.08); }

/* Paso 4 abono - detalle */
.abono-clases-lista { display:flex;flex-direction:column;gap:8px; }
.abono-clase-item { display:flex;align-items:center;justify-content:space-between;padding:12px 16px;border-radius:8px;border:1px solid var(--border); }
.clase-incluida { background:rgba(63,185,80,0.06);border-color:rgba(63,185,80,0.2); }
.clase-excluida { background:rgba(218,54,51,0.05);border-color:rgba(218,54,51,0.15);opacity:0.7; }
.clase-ya-inscripto { background:rgba(21,101,192,0.08);border-color:rgba(21,101,192,0.25);opacity:0.8; }
.clase-en-espera { background:rgba(234,179,8,0.07);border-color:rgba(234,179,8,0.4); }
.clase-check { font-size:18px;width:24px;text-align:center; }
.clase-incluida .clase-check { color:var(--success); }
.clase-excluida .clase-check { color:var(--danger); }
.clase-en-espera .clase-check { color:var(--warning); }

/* Paso 4 individual - pago opciones */
.pago-opciones { max-width:440px;margin-top:20px; }
.pago-opcion { display:flex;align-items:flex-start;gap:12px;padding:14px 16px;background:var(--dark-2);border:2px solid var(--border);border-radius:10px;cursor:pointer;margin-bottom:10px;transition:all 0.2s; }
.pago-opcion:hover { border-color:var(--verde); }
.pago-opcion.selected { border-color:var(--verde-claro);background:rgba(46,125,50,0.08); }
.pago-radio { font-size:18px;color:var(--verde-claro);flex-shrink:0;margin-top:2px; }

/* Confirmar */
.confirm-card { padding:0;overflow:hidden; }
.confirm-row { display:flex;justify-content:space-between;align-items:center;padding:14px 20px;border-bottom:1px solid var(--border);font-size:14px; }
.confirm-row:last-child { border:none; }
.confirm-label { color:var(--text-muted); }
.confirm-value { font-weight:600; }
.total-row { background:rgba(46,125,50,0.05); }
.total-value { font-size:20px;color:var(--verde-claro);font-family:'Bebas Neue',sans-serif; }

/* Pagar */
.tarjeta-opcion { display:flex;align-items:center;gap:14px;padding:14px 16px;background:var(--dark-3);border:2px solid var(--border);border-radius:10px;cursor:pointer;transition:all 0.2s;margin-bottom:8px; }
.tarjeta-opcion:hover { border-color:var(--verde); }
.tarjeta-opcion.selected { border-color:var(--verde-claro);background:rgba(46,125,50,0.08); }
.tarjeta-icon { font-size:24px; }
.tarjeta-check { margin-left:auto;color:var(--verde-claro);font-size:18px;font-weight:700; }

/* Éxito */
.success-container { text-align:center;padding:40px 0; }
.success-icon { font-size:64px;margin-bottom:16px; }
.success-container h2 { font-size:36px;font-family:'Bebas Neue',sans-serif;margin-bottom:8px; }

/* Admin */
.clases-grid { display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px; }
.clase-card { display:flex;flex-direction:column;gap:12px; }
.cancelada-card { opacity:0.6;border-color:var(--danger) !important; }
.clase-header { display:flex;align-items:flex-start;gap:10px; }
.dia-badge { display:inline-block;padding:2px 8px;background:var(--dark-3);border-radius:4px;font-size:12px;color:var(--text-muted); }
.fecha-badge { color:var(--verde-claro);background:rgba(46,125,50,0.15); }
.loading-text { text-align:center;padding:40px;color:var(--text-muted); }
.empty-state { text-align:center;padding:40px;color:var(--text-muted); }
</style>
