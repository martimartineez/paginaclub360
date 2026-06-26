<template>
  <div v-if="usuario">
    <div class="page-header">
      <router-link to="/admin/usuarios" class="back-link">← Volver a usuarios</router-link>
      <div style="display:flex;align-items:center;gap:16px;margin-top:12px">
        <div class="avatar-xl">{{ usuario.nombre?.charAt(0) }}</div>
        <div>
          <h2>{{ usuario.nombre }} {{ usuario.apellido }}</h2>
          <p style="color:var(--text-muted);font-size:14px">{{ usuario.email }}</p>
          <div style="display:flex;gap:8px;margin-top:6px">
            <span class="badge" :class="rolBadge(usuario.rol)">{{ usuario.rol }}</span>
            <span v-if="usuario.suspensiones_activas?.length" class="badge badge-red">
              {{ usuario.suspensiones_activas.length }} suspensión(es) activa(s)
            </span>
          </div>
        </div>
      </div>
    </div>

    <div class="alert alert-success" v-if="msg">{{ msg }}</div>
    <div class="alert alert-error" v-if="err">{{ err }}</div>

    <!-- Datos básicos -->
    <div class="card" style="margin-bottom:24px">
      <h3 style="font-size:18px;margin-bottom:16px">Información básica</h3>
      <div class="grid-2">
        <div class="detalle-item"><span class="label">Nombre completo</span><span>{{ usuario.nombre }} {{ usuario.apellido }}</span></div>
        <div class="detalle-item"><span class="label">DNI</span><span>{{ usuario.dni }}</span></div>
        <div class="detalle-item"><span class="label">Email</span><span>{{ usuario.email }}</span></div>
        <div class="detalle-item"><span class="label">Miembro desde</span><span>{{ new Date(usuario.fecha_registro).toLocaleDateString() }}</span></div>
      </div>
    </div>

    <!-- Acciones según rol del usuario visto -->
    <div class="card acciones-card" style="margin-bottom:24px">
      <h3 style="font-size:18px;margin-bottom:16px">Acciones</h3>
      <div class="acciones-grid">
        <template v-if="usuario.rol === 'cliente'">
          <button class="accion-btn" @click="abrirReservas">
            <span class="accion-icon">📋</span>
            <span>Ver reservas</span>
          </button>
          <button class="accion-btn" @click="inscribir">
            <span class="accion-icon">➕</span>
            <span>Inscribir a clase</span>
          </button>
          <button class="accion-btn" @click="tab = 'suspensiones'; fetchSuspensiones()" v-if="usuario.suspensiones_activas?.length">
            <span class="accion-icon">🔓</span>
            <span>Ver suspensiones</span>
          </button>
          <button class="accion-btn" v-if="auth.isAdmin" @click="crearSuspensionClaseSueltaPrueba" :disabled="creandoSuspensionPrueba">
            <span class="accion-icon">!</span>
            <span>{{ creandoSuspensionPrueba ? 'Creando...' : 'Probar suspension clase suelta' }}</span>
          </button>
        </template>
        <button
          class="accion-btn"
          v-if="auth.isAdmin && usuario.rol === 'empleado'"
          @click="modalPromoverAdmin = true"
          :disabled="promoviendoAdmin"
        >
          <span class="accion-icon">A</span>
          <span>Convertir en administrador</span>
        </button>
        <button
          class="accion-btn"
          v-if="auth.isAdmin && usuario.rol === 'administrador' && !esUsuarioActual"
          @click="modalDegradarAdmin = true"
          :disabled="degradandoAdmin"
        >
          <span class="accion-icon">E</span>
          <span>Convertir en empleado</span>
        </button>
        <button
          class="accion-btn accion-peligro"
          v-if="puedeEliminarUsuario"
          @click="modalEliminar = true"
        >
          <span class="accion-icon">🗑️</span>
          <span>Eliminar usuario</span>
        </button>
      </div>
    </div>

    <!-- Tab: Reservas del usuario -->
    <div class="card" style="margin-bottom:24px" v-if="tab === 'reservas'">
      <h3 style="font-size:18px;margin-bottom:16px">📋 Reservas de {{ usuario.nombre }}</h3>
      <div v-if="loadingReservas" style="color:var(--text-muted);font-size:14px">Cargando...</div>
      <div v-else-if="reservas.length === 0" style="color:var(--text-muted);font-size:14px">Sin reservas.</div>
      <template v-else>
        <table>
          <thead>
            <tr><th>Clase</th><th>Fecha</th><th>Tipo</th><th>Estado</th><th>Total</th><th>Acciones</th></tr>
          </thead>
          <tbody>
            <tr v-for="r in reservas" :key="r.id">
              <td>{{ r.clase?.actividad }}</td>
              <td style="font-size:13px">{{ formatFecha(r.clase?.fecha) }} {{ r.clase?.hora_inicio }}</td>
              <td><span class="badge" :class="r.tipo === 'abonado' ? 'badge-green' : 'badge-blue'">{{ r.tipo }}</span></td>
              <td><span class="badge" :class="estadoBadge(estadoReserva(r))">{{ estadoReserva(r) }}</span></td>
              <td>
                <span :class="reservaTotalPagado(r) ? 'text-green' : 'text-danger'">
                  {{ reservaTotalPagado(r) ? 'Pagado' : 'No pagado' }}
                </span>
              </td>
              <td>
                <div style="display:flex;gap:6px;flex-wrap:wrap">
                  <button
                    v-if="puedePagarReserva(r)"
                    class="btn btn-primary btn-sm"
                    @click="abrirPagoReserva(r)"
                  >
                    Pagar total
                  </button>
                  <button
                    v-if="puedeCancelarReserva(r)"
                    class="btn btn-danger btn-sm"
                    @click="confirmarCancelarReserva(r)"
                  >
                    ✕ Cancelar reserva
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>

        <div v-if="reservasPagination.totalPages > 1" class="reservas-pagination">
          <button
            class="pagination-arrow"
            :disabled="!reservasPagination.hasPrev || loadingReservas"
            aria-label="Página anterior"
            title="Página anterior"
            @click="cambiarPaginaReservas(-1)"
          >
            ←
          </button>
          <button
            class="pagination-arrow"
            :disabled="!reservasPagination.hasNext || loadingReservas"
            aria-label="Página siguiente"
            title="Página siguiente"
            @click="cambiarPaginaReservas(1)"
          >
            →
          </button>
        </div>
      </template>
    </div>
  <!-- Modal de SUSPENSIÓN-->
  <div class="modal-overlay" v-if="suspensionAConfirmar" 
       style="position:fixed;inset:0;background:rgba(0,0,0,0.45);display:flex;align-items:center;justify-content:center;z-index:1000"
       @click.self="suspensionAConfirmar = null">
    <div style="background:var(--dark-2);border-radius:12px;border:0.5px solid var(--border);padding:1.5rem;width:100%;max-width:400px;margin:0 1rem">
      <h3 style="font-size:16px;font-weight:500;margin:0 0 1rem">Confirmar levantamiento</h3>

      <div style="display:flex;flex-direction:column;gap:8px;font-size:14px;margin-bottom:1.5rem">
        <div style="display:flex;justify-content:space-between">
          <span style="color:var(--text-secondary)">Tipo</span>
          <span style="font-weight:500">{{ suspensionAConfirmar.tipo }}</span>
        </div>

        <div v-if="suspensionAConfirmar.tipo === 'abonado'" style="display:flex;justify-content:space-between">
          <span style="color:var(--text-secondary)">Actividad</span>
          <span style="font-weight:500">{{ suspensionAConfirmar.actividad || '—' }}</span>
        </div>

        <div style="display:flex;justify-content:space-between">
          <span style="color:var(--text-secondary)">Monto original</span>
          <span>${{ suspensionAConfirmar.monto_original?.toLocaleString() }}</span>
        </div>

        <div style="display:flex;justify-content:space-between;border-top:0.5px solid var(--border);padding-top:8px;margin-top:4px">
          <span style="color:var(--text-secondary)">Monto a pagar</span>
          <span style="font-weight:500;color:var(--text-warning)">${{ suspensionAConfirmar.monto_deuda?.toLocaleString() }}</span>
        </div>
      </div>
      <div class="alert alert-warning" style="margin-top:12px">
          ⚠️ Al confirmar, el sistema registrará el cobro en efectivo automáticamente.
      </div>
      <div style="display:flex;gap:8px;justify-content:flex-end">
        <button class="btn btn-secondary btn-sm" @click="suspensionAConfirmar = null">
          Cancelar
        </button>
        <button class="btn btn-primary btn-sm" @click="confirmarLevantamiento" :disabled="levantando === suspensionAConfirmar.id">
          {{ levantando === suspensionAConfirmar.id ? 'Procesando...' : 'Confirmar pago' }}
        </button>
      </div>
    </div>
  </div>
    <!-- Tab: Inscribir a clase -->
    <div class="card" style="margin-bottom:24px" v-if="tab === 'inscribir'">
      <h3 style="font-size:18px;margin-bottom:16px">➕ Inscribir a {{ usuario.nombre }} en una clase</h3>
      <div class="grid-2" style="margin-bottom:16px">
        <div class="input-group" style="margin:0">
          <label>Actividad</label>
          <select v-model="inscribirForm.actividad_id" @change="onActividadChange">
            <option value="">Seleccioná una actividad</option>
            <option v-for="a in actividades" :key="a.id" :value="a.id">{{ a.nombre }}</option>
          </select>
        </div>
        <div class="input-group" style="margin:0">
          <label>Tipo de inscripción</label>
          <select v-model="inscribirForm.tipo" @change="onTipoChange">
            <option value="abonado">Abonado (mensual)</option>
            <option value="no_abonado">Clase suelta</option>
          </select>
        </div>
      </div>

      <!-- ABONADO: selector día → horario (igual que el flujo del cliente) -->
      <template v-if="inscribirForm.tipo === 'abonado' && inscribirForm.actividad_id">
        <div v-if="loadingHorariosAbono" style="color:var(--text-muted);font-size:13px;padding:12px 0">Buscando turnos...</div>
        <div v-else-if="diasAbonoEmpl.length === 0" style="color:var(--text-muted);font-size:13px;padding:12px 0">No hay turnos disponibles este mes.</div>
        <template v-else>
          <!-- Paso 1: elegir día -->
          <div v-if="!abonoDiaEmpl">
            <p style="font-size:13px;color:var(--text-muted);margin-bottom:10px">Seleccioná el día:</p>
            <div style="display:flex;flex-wrap:wrap;gap:10px">
              <div
                v-for="dia in diasAbonoEmpl" :key="dia.dia_semana_num"
                class="dia-btn-empl"
                @click="abonoDiaEmpl = dia; inscribirForm.abono_opcion = null"
              >
                <span style="font-size:15px;font-weight:600">{{ dia.dia_semana }}</span>
                <span style="font-size:11px;color:var(--text-muted)">{{ dia.horarios.length }} horario(s)</span>
              </div>
            </div>
          </div>

          <!-- Paso 2: elegir horario -->
          <div v-else>
            <div class="fecha-sel-banner-empl">
              <span>📅 {{ abonoDiaEmpl.dia_semana }}</span>
              <button class="btn btn-outline btn-sm" @click="abonoDiaEmpl = null; inscribirForm.abono_opcion = null">Cambiar día</button>
            </div>
            <p style="font-size:13px;color:var(--text-muted);margin-bottom:10px">Seleccioná el horario:</p>
            <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px">
              <div
                v-for="op in abonoDiaEmpl.horarios" :key="op.hora_inicio"
                class="horario-btn-empl"
                :class="{ selected: inscribirForm.abono_opcion?.hora_inicio === op.hora_inicio }"
                @click="elegirHorarioAbonoEmpl(op)"
              >
                <span style="font-weight:600;font-size:15px">{{ op.hora_inicio }}</span>
                <span
                  style="font-size:11px"
                  :class="op.clases_mes.some(c => c.cupos_disponibles > 0) ? 'text-green' : 'text-warning'"
                >
                  {{ op.clases_mes.some(c => c.cupos_disponibles > 0)
                    ? `${op.clases_mes.filter(c => c.cupos_disponibles > 0).length} con cupo`
                    : 'Lista de espera' }}
                </span>
              </div>
            </div>

            <!-- Detalle del abono -->
            <div v-if="loadingDetalleAbonoEmpl" style="color:var(--text-muted);font-size:13px">Calculando abono...</div>
            <div v-else-if="detalleAbonoEmpl" style="margin-top:8px">
              <div v-if="detalleAbonoEmpl.total_disponibles === 0" class="alert alert-warning" style="font-size:13px;margin-bottom:10px">
                ⏳ Ninguna clase de este turno tiene cupo. Al confirmar, se anotará al cliente en la lista de espera de todas esas clases y no se registrará ningún cobro.
              </div>
              <div v-else-if="clasesParaListaEspera.length > 0" class="alert alert-warning" style="font-size:13px;margin-bottom:10px">
                ⏳ Las {{ clasesParaListaEspera.length }} clase(s) sin cupo se agregarán a la lista de espera y no se cobrarán.
              </div>
              <p style="font-size:13px;font-weight:600;margin-bottom:8px">Clases del abono:</p>
              <div class="abono-detalle-lista">
                <div v-for="c in detalleAbonoEmpl.clases" :key="c.clase_id"
                  class="abono-detalle-item"
                  :class="{ incluida: c.incluida_en_abono, excluida: !c.incluida_en_abono && !c.ya_inscripto, 'ya-inscripto-item': c.ya_inscripto }">
                  <div style="display:flex;align-items:center;gap:8px">
                    <span>{{ c.incluida_en_abono ? '✓' : (c.ya_inscripto ? '→' : '✗') }}</span>
                    <div>
                      <p style="font-size:13px;font-weight:600">{{ c.dia_semana }} {{ formatFecha(c.fecha) }}</p>
                      <p style="font-size:11px;color:var(--text-muted)">{{ c.hora_inicio }} hs</p>
                    </div>
                  </div>
                  <span v-if="c.incluida_en_abono" style="font-size:13px;color:var(--verde-claro);font-weight:600">${{ c.precio_clase?.toLocaleString() }}</span>
                  <span v-else-if="c.ya_inscripto" style="font-size:11px;color:var(--azul-claro)">Ya inscripto</span>
                  <span v-else-if="c.cancelada" style="font-size:11px;color:var(--danger)">Cancelada</span>
                  <span v-else-if="c.suspendida" style="font-size:11px;color:var(--danger)">Suspendida</span>
                  <span v-else style="font-size:11px;color:var(--warning);font-weight:600">
                    {{ c.en_espera ? 'Ya está en lista de espera' : 'Se anotará en lista de espera' }}
                  </span>
                </div>
              </div>
              <div v-if="detalleAbonoEmpl.ya_inscripto_en?.length" class="alert alert-warning" style="font-size:13px;margin-top:8px">
                ℹ️ El cliente ya está inscripto en {{ detalleAbonoEmpl.ya_inscripto_en.length }} clase(s) de este turno. Solo se lo inscribirá en las clases nuevas.
              </div>
              <div v-if="detalleAbonoEmpl.aplicar_descuento" class="alert alert-success" style="margin-top:10px;font-size:13px">
                🎉 Mitad de mes con más de 1 clase disponible. 20% de descuento por clase.
              </div>
              <div v-else-if="!detalleAbonoEmpl.usuario_tiene_beneficio && detalleAbonoEmpl.total_disponibles > 1" class="alert alert-warning" style="margin-top:10px;font-size:13px">
                ⚠️ El cliente perdió el beneficio del 20% por haber cancelado 3 o más clases de abono. Se cobra precio completo.
              </div>
              <div class="abono-total-empl">
                <span>Total abono ({{ detalleAbonoEmpl.total_disponibles }} clases)</span>
                <span style="font-size:20px;font-weight:700;color:var(--verde-claro)">${{ detalleAbonoEmpl.monto_total?.toLocaleString() }}</span>
              </div>
            </div>
          </div>
        </template>
      </template>

      <!-- NO ABONADO: selector día → horario → clases de ese día/hora -->
      <template v-if="inscribirForm.tipo === 'no_abonado' && inscribirForm.actividad_id">
        <div v-if="loadingFechasEmpl" style="color:var(--text-muted);font-size:13px;padding:12px 0">Buscando fechas...</div>
        <div v-else-if="diasSueltaEmpl.length === 0 && !sueltaDiaEmpl" style="color:var(--text-muted);font-size:13px;padding:12px 0">No hay clases disponibles.</div>
        <template v-else>

          <!-- Paso 1: elegir día -->
          <div v-if="!sueltaDiaEmpl">
            <p style="font-size:13px;color:var(--text-muted);margin-bottom:10px">Seleccioná el día:</p>
            <div style="display:flex;flex-wrap:wrap;gap:10px">
              <div
                v-for="dia in diasSueltaEmpl" :key="dia.fecha"
                class="dia-btn-empl"
                @click="sueltaDiaEmpl = dia; inscribirForm.clase_id = null"
              >
                <span style="font-size:15px;font-weight:600">{{ dia.dia_semana }}</span>
                <span style="font-size:13px;color:var(--verde-claro)">{{ formatFechaCorta(dia.fecha) }}</span>
                <span style="font-size:11px;color:var(--text-muted)">{{ dia.horarios.length }} horario(s)</span>
              </div>
            </div>
          </div>

          <!-- Paso 2: elegir horario -->
          <div v-else-if="!sueltaHorarioEmpl">
            <div class="fecha-sel-banner-empl">
              <span>📅 {{ sueltaDiaEmpl.dia_semana }} {{ formatFechaCorta(sueltaDiaEmpl.fecha) }}</span>
              <button class="btn btn-outline btn-sm" @click="sueltaDiaEmpl = null; sueltaHorarioEmpl = null; inscribirForm.clase_id = null">Cambiar día</button>
            </div>
            <p style="font-size:13px;color:var(--text-muted);margin-bottom:10px">Seleccioná el horario:</p>
            <div style="display:flex;flex-wrap:wrap;gap:8px">
              <div
                v-for="h in sueltaDiaEmpl.horarios" :key="h.clase_id"
                class="horario-btn-empl"
                :class="{ selected: sueltaHorarioEmpl?.clase_id === h.clase_id }"
                @click="sueltaHorarioEmpl = h; inscribirForm.clase_id = h.clase_id"
              >
                <span style="font-weight:600;font-size:15px">{{ h.hora_inicio }}</span>
                <span style="font-size:11px;" :class="h.cupos_disponibles > 0 ? 'text-green' : 'text-warning'">
                  {{ h.cupos_disponibles > 0 ? `${h.cupos_disponibles} cupos` : 'Lista espera' }}
                </span>
              </div>
            </div>
          </div>

          <!-- Paso 3: confirmar clase elegida -->
          <div v-else>
            <div class="fecha-sel-banner-empl">
              <span>📅 {{ sueltaDiaEmpl.dia_semana }} {{ formatFecha(sueltaDiaEmpl.fecha) }} · {{ sueltaHorarioEmpl.hora_inicio }} hs</span>
              <button class="btn btn-outline btn-sm" @click="sueltaHorarioEmpl = null; inscribirForm.clase_id = null">Cambiar horario</button>
            </div>

            <!-- Monto a pagar -->
            <template v-if="!sueltaEnListaEspera">
              <p style="font-size:13px;color:var(--text-muted);margin-bottom:8px">¿El cliente paga la seña o el total?</p>
              <div style="display:flex;gap:8px;flex-wrap:wrap">
                <button class="btn btn-sm" :class="inscribirForm.monto_pagar === 'senia' ? 'btn-primary' : 'btn-outline'"
                  @click="inscribirForm.monto_pagar = 'senia'">
                  Seña (50%) — ${{ Math.round((sueltaHorarioEmpl?.precio_clase||0)*0.5).toLocaleString() }}
                </button>
                <button class="btn btn-sm" :class="inscribirForm.monto_pagar === 'total' ? 'btn-primary' : 'btn-outline'"
                  @click="inscribirForm.monto_pagar = 'total'">
                  Total — ${{ (sueltaHorarioEmpl?.precio_clase||0).toLocaleString() }}
                </button>
              </div>
            </template>
            <div v-else class="alert alert-warning" style="margin-top:8px">
              Sin cupo disponible: el cliente se anotará en lista de espera y no se cobrará seña.
            </div>
          </div>

        </template>
      </template>

      <div style="display:flex;gap:10px;margin-top:16px">
        <button
          class="btn btn-secondary"
          @click="abrirConfirmacionInscripcion"
          :disabled="inscribirForm.tipo === 'no_abonado' ? !inscribirForm.clase_id || !sueltaHorarioEmpl : !inscribirForm.abono_opcion"
        >
          Ver detalle y confirmar →
        </button>
        <button class="btn btn-outline" @click="tab = null">Cancelar</button>
      </div>
    </div>

    <!-- Tab: Suspensiones activas -->
    <div class="card" style="margin-bottom:24px" v-if="tab === 'suspensiones'">
      <h3 style="font-size:18px;margin-bottom:16px">🔓 Suspensiones activas de {{ usuario.nombre }}</h3>
      <div v-if="suspensiones.length === 0" style="color:var(--text-muted);font-size:14px">Sin suspensiones activas.</div>
      <div v-for="s in suspensiones" :key="s.id" class="suspension-item">
        <div>
          <span class="badge badge-red">{{ s.tipo }}</span>
          <p style="font-size:13px;color:var(--text-muted);margin-top:4px">{{ s.motivo || 'Sin motivo especificado' }}</p>
          <p style="color:var(--warning);font-weight:600;margin-top:4px">Deuda: ${{ s.monto_deuda?.toLocaleString() }}</p>
        </div>
        <div style="display:flex;gap:8px;align-items:center">
          <button class="btn btn-primary btn-sm" @click="abrirModal(s)" :disabled="levantando === s.id">
            {{ levantando === s.id ? 'Procesando...' : 'Levantar' }}
          </button>
        </div>
      </div>
    </div>
    <!-- Modal confirmación inscripción en efectivo -->
    <div class="modal-overlay" v-if="modalConfirmInscripcion" @click.self="modalConfirmInscripcion = false">
      <div class="modal card">
        <h3>
          {{ inscripcionSoloListaEspera
            ? '⏳ Confirmar lista de espera'
            : '💵 Confirmar inscripción en efectivo' }}
        </h3>
        <p v-if="!inscripcionSoloListaEspera" style="color:var(--text-muted);font-size:14px;margin-bottom:16px">
          El cliente <strong>{{ usuario?.nombre }} {{ usuario?.apellido }}</strong> pagará en efectivo en la sede.
        </p>
        <p v-else style="color:var(--text-muted);font-size:14px;margin-bottom:16px">
          El cliente <strong>{{ usuario?.nombre }} {{ usuario?.apellido }}</strong> será anotado en la lista de espera. No se registrará ningún cobro.
        </p>

        <!-- Detalle para clase suelta -->
        <template v-if="inscribirForm.tipo === 'no_abonado'">
          <div class="confirm-row-modal">
            <span class="confirm-label">Fecha</span>
            <span>{{ sueltaDiaEmpl?.dia_semana }}, {{ formatFecha(sueltaDiaEmpl?.fecha) }}</span>
          </div>
          <div class="confirm-row-modal">
            <span class="confirm-label">Horario</span>
            <span>{{ sueltaHorarioEmpl?.hora_inicio }} hs</span>
          </div>
          <div class="confirm-row-modal">
            <span class="confirm-label">Tipo</span>
            <span><span class="badge badge-blue">Clase suelta</span></span>
          </div>
          <div class="confirm-row-modal">
            <span class="confirm-label">Monto a cobrar</span>
            <span v-if="sueltaEnListaEspera" style="font-weight:700;color:var(--warning);font-size:18px">
              $0 (lista de espera)
            </span>
            <span v-else style="font-weight:700;color:var(--verde-claro);font-size:18px">
              ${{ inscribirForm.monto_pagar === 'senia'
                ? Math.round((sueltaHorarioEmpl?.precio_clase||0)*0.5).toLocaleString()
                : (sueltaHorarioEmpl?.precio_clase||0).toLocaleString() }}
              {{ inscribirForm.monto_pagar === 'senia' ? '(seña 50%)' : '(total)' }}
            </span>
          </div>
        </template>

        <!-- Detalle para abono -->
        <template v-if="inscribirForm.tipo === 'abonado' && detalleAbonoEmpl">
          <div class="confirm-row-modal">
            <span class="confirm-label">Deporte</span>
            <span>{{ detalleAbonoEmpl.actividad }}</span>
          </div>
          <div class="confirm-row-modal">
            <span class="confirm-label">Turno</span>
            <span>{{ detalleAbonoEmpl.dia_semana }} {{ detalleAbonoEmpl.hora_inicio }} hs</span>
          </div>
          <div class="confirm-row-modal">
            <span class="confirm-label">Tipo</span>
            <span><span class="badge badge-green">Abono mensual</span></span>
          </div>
          <div class="confirm-row-modal">
            <span class="confirm-label">Clases incluidas</span>
            <span>{{ detalleAbonoEmpl.total_disponibles }} de {{ detalleAbonoEmpl.total_clases_mes }} este mes</span>
          </div>
          <div v-if="clasesParaListaEspera.length > 0" class="confirm-row-modal">
            <span class="confirm-label" style="color:var(--warning)">Lista de espera</span>
            <span style="color:var(--warning);font-weight:600">{{ clasesParaListaEspera.length }} clase(s)</span>
          </div>
          <div v-if="detalleAbonoEmpl.aplicar_descuento" class="confirm-row-modal">
            <span class="confirm-label">Descuento</span>
            <span style="color:var(--success)">50% por ingreso a mitad de mes</span>
          </div>
          <div class="confirm-row-modal">
            <span class="confirm-label">Monto total a cobrar</span>
            <span style="font-weight:700;color:var(--verde-claro);font-size:18px">${{ detalleAbonoEmpl.monto_total?.toLocaleString() }}</span>
          </div>
        </template>
        <div v-if="!inscripcionSoloListaEspera" class="alert alert-warning" style="margin-top:12px">
          ⚠️ Al confirmar, el sistema registrará el cobro en efectivo automáticamente.
        </div>
        <div v-else class="alert alert-warning" style="margin-top:12px">
          ⏳ Al confirmar, el cliente quedará en la lista de espera de las clases sin cupo. No se registrará ningún cobro.
        </div>
        <div style="display:flex;gap:10px;margin-top:16px">
          <button class="btn btn-primary" @click="inscribirCliente" :disabled="inscribiendo">
            {{ inscribiendo
              ? 'Procesando...'
              : (inscripcionSoloListaEspera
                ? '⏳ Anotar en lista de espera'
                : '✓ Confirmar inscripción en efectivo') }}
          </button>
          <button class="btn btn-outline" @click="modalConfirmInscripcion = false">Cancelar</button>
        </div>
      </div>
    </div>

    <!-- Modal eliminar usuario -->
    <div class="modal-overlay" v-if="modalEliminar" @click.self="modalEliminar = false">
      <div class="modal card">
        <h3>🗑️ Eliminar usuario</h3>
        <p style="color:var(--text-muted);font-size:14px;margin:12px 0">
          ¿Estás seguro que querés desactivar a
          <strong>{{ usuario?.nombre }} {{ usuario?.apellido }}</strong>?
        </p>
        <div class="alert alert-warning">
          El usuario quedará inactivo y no podrá ingresar al sistema.
          Si se re-registra con los mismos datos, se reactivará automáticamente.
        </div>
        <div style="display:flex;gap:10px;margin-top:16px">
          <button class="btn btn-danger" @click="ejecutarEliminar" :disabled="eliminando">
            {{ eliminando ? 'Eliminando...' : 'Sí, eliminar' }}
          </button>
          <button class="btn btn-outline" @click="modalEliminar = false">Cancelar</button>
        </div>
      </div>
    </div>

    <!-- Modal convertir empleado en administrador -->
    <div class="modal-overlay" v-if="modalPromoverAdmin" @click.self="modalPromoverAdmin = false">
      <div class="modal card">
        <h3>Convertir en administrador</h3>
        <p style="color:var(--text-muted);font-size:14px;margin:12px 0">
          Vas a darle permisos de administrador a
          <strong>{{ usuario?.nombre }} {{ usuario?.apellido }}</strong>.
        </p>
        <div class="alert alert-warning">
          El usuario podrá gestionar empleados, clases, turnos y configuraciones del sistema.
        </div>
        <div style="display:flex;gap:10px;margin-top:16px">
          <button class="btn btn-primary" @click="ejecutarPromoverAdmin" :disabled="promoviendoAdmin">
            {{ promoviendoAdmin ? 'Convirtiendo...' : 'Sí, convertir' }}
          </button>
          <button class="btn btn-outline" @click="modalPromoverAdmin = false">Cancelar</button>
        </div>
      </div>
    </div>

    <!-- Modal convertir administrador en empleado -->
    <div class="modal-overlay" v-if="modalDegradarAdmin" @click.self="modalDegradarAdmin = false">
      <div class="modal card">
        <h3>Convertir en empleado</h3>
        <p style="color:var(--text-muted);font-size:14px;margin:12px 0">
          Vas a quitarle permisos de administrador a
          <strong>{{ usuario?.nombre }} {{ usuario?.apellido }}</strong>.
        </p>
        <div class="alert alert-warning">
          Debe quedar al menos un administrador activo en el sistema.
        </div>
        <div style="display:flex;gap:10px;margin-top:16px">
          <button class="btn btn-primary" @click="ejecutarDegradarAdmin" :disabled="degradandoAdmin">
            {{ degradandoAdmin ? 'Convirtiendo...' : 'Sí, convertir' }}
          </button>
          <button class="btn btn-outline" @click="modalDegradarAdmin = false">Cancelar</button>
        </div>
      </div>
    </div>

    <!-- Modal confirmar cancelación de reserva -->
    <div class="modal-overlay" v-if="modalCancelarReserva" @click.self="modalCancelarReserva = null">
      <div class="modal card">
        <h3>⚠️ Cancelar reserva</h3>
        <p style="color:var(--text-muted);font-size:14px;margin:12px 0">
          Vas a cancelar la reserva de <strong>{{ usuario?.nombre }}</strong> para:
        </p>
        <div class="confirm-row-modal">
          <span class="confirm-label">Clase</span>
          <span>{{ modalCancelarReserva?.clase?.actividad }}</span>
        </div>
        <div class="confirm-row-modal">
          <span class="confirm-label">Fecha</span>
          <span>{{ formatFecha(modalCancelarReserva?.clase?.fecha) }} {{ modalCancelarReserva?.clase?.hora_inicio }} hs</span>
        </div>
        <div class="confirm-row-modal">
          <span class="confirm-label">Tipo</span>
          <span><span class="badge" :class="modalCancelarReserva?.tipo === 'abonado' ? 'badge-green' : 'badge-blue'">{{ modalCancelarReserva?.tipo }}</span></span>
        </div>
        <div class="alert alert-warning" style="margin-top:12px" v-if="modalCancelarReserva?.tipo === 'abonado'">
          Si el cliente lleva 2 cancelaciones, esta será la tercera y perderá el beneficio del 20% al abonar a mitad de mes.
        </div>
        <div style="display:flex;gap:10px;margin-top:16px">
          <button class="btn btn-danger" @click="ejecutarCancelarReserva" :disabled="cancelandoReserva">
            {{ cancelandoReserva ? 'Cancelando...' : 'Sí, cancelar reserva' }}
          </button>
          <button class="btn btn-outline" @click="modalCancelarReserva = null">Volver</button>
        </div>
      </div>
    </div>

    <!-- Modal pago total -->
    <div class="modal-overlay" v-if="pagoReservaModal" @click.self="pagoReservaModal = null">
      <div class="modal card">
        <h3>Registrar pago total</h3>
        <p style="color:var(--text-muted);font-size:14px;margin-bottom:16px">
          {{ pagoReservaModal.clase?.actividad }} — {{ formatFecha(pagoReservaModal.clase?.fecha) }}
        </p>
        <div class="alert alert-warning">
          Saldo pendiente: <strong>${{ saldoPendienteReserva(pagoReservaModal).toLocaleString() }}</strong>
        </div>
        <div class="input-group" style="margin-top:16px">
          <label>Metodo de pago</label>
          <select v-model="metodoPagoReserva">
            <option value="efectivo">Efectivo</option>
            <option value="tarjeta_credito">Tarjeta de credito</option>
          </select>
        </div>
        <div style="display:flex;gap:10px;margin-top:8px">
          <button class="btn btn-primary" @click="pagarReserva" :disabled="pagandoReserva">
            {{ pagandoReserva ? 'Procesando...' : 'Confirmar pago' }}
          </button>
          <button class="btn btn-outline" @click="pagoReservaModal = null">Cancelar</button>
        </div>
      </div>
    </div>
  </div>

  <div v-else-if="loading" class="loading-text">Cargando usuario...</div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth.js'
import api from '../../api.js'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const usuario = ref(null)
const loading = ref(true)
const tab = ref(null)
const msg = ref(''), err = ref('')

const reservas = ref([])
const loadingReservas = ref(false)
const reservasPage = ref(1)
const reservasLimit = 8
const reservasPagination = ref({
  totalPages: 1,
  hasPrev: false,
  hasNext: false
})
const suspensionAConfirmar = ref(null)
const actividades = ref([])
const clasesDisponibles = ref([])
const inscribirForm = ref({ actividad_id: '', clase_id: null, tipo: 'abonado', monto_pagar: 'senia', abono_opcion: null })
const inscribiendo = ref(false)
const modalConfirmInscripcion = ref(false)
const abonoDiaEmpl = ref(null)
const horariosAbonoEmpl = ref([])
const loadingHorariosAbono = ref(false)
const detalleAbonoEmpl = ref(null)
const loadingDetalleAbonoEmpl = ref(false)
const clasesParaListaEspera = computed(() =>
  detalleAbonoEmpl.value?.clases?.filter(
    c => !c.incluida_en_abono && !c.ya_inscripto && !c.cancelada && !c.suspendida
  ) || []
)
// clase suelta empleado
const sueltaDiaEmpl = ref(null)
const sueltaHorarioEmpl = ref(null)
const loadingFechasEmpl = ref(false)
const fechasSueltaEmpl = ref([])
const sueltaEnListaEspera = computed(() =>
  inscribirForm.value.tipo === 'no_abonado'
  && sueltaHorarioEmpl.value
  && Number(sueltaHorarioEmpl.value.cupos_disponibles || 0) <= 0
)
const inscripcionSoloListaEspera = computed(() =>
  sueltaEnListaEspera.value
  || (inscribirForm.value.tipo === 'abonado' && detalleAbonoEmpl.value?.total_disponibles === 0)
)

// Días disponibles para clase suelta (empleado)
const diasSueltaEmpl = computed(() => {
  return fechasSueltaEmpl.value
})

// Agrupa horarios de abono por día
const diasAbonoEmpl = computed(() => {
  const map = {}
  for (const op of horariosAbonoEmpl.value) {
    const key = op.dia_semana_num
    if (!map[key]) {
      map[key] = { dia_semana: op.dia_semana, dia_semana_num: op.dia_semana_num, horarios: [] }
    }
    map[key].horarios.push(op)
  }
  return Object.values(map).sort((a, b) => a.dia_semana_num - b.dia_semana_num)
})

const suspensiones = ref([])
const metodoLevantamiento = ref('efectivo')
const levantando = ref(null)
const creandoSuspensionPrueba = ref(false)
const modalPromoverAdmin = ref(false)
const promoviendoAdmin = ref(false)
const modalDegradarAdmin = ref(false)
const degradandoAdmin = ref(false)
const modalEliminar = ref(false)
const eliminando = ref(false)
const modalCancelarReserva = ref(null)
const cancelandoReserva = ref(false)

const pagoReservaModal = ref(null)
const metodoPagoReserva = ref('efectivo')
const pagandoReserva = ref(false)

const esUsuarioActual = computed(() => Number(usuario.value?.id) === Number(auth.user?.id))
const puedeEliminarUsuario = computed(() => {
  if (!usuario.value || esUsuarioActual.value) return false
  return auth.isAdmin || usuario.value.rol === 'cliente'
})

function rolBadge(rol) {
  return { 'administrador': 'badge-green', 'empleado': 'badge-blue', 'cliente': 'badge-yellow' }[rol] || 'badge-yellow'
}
function estadoBadge(estado) {
  return { 'activa': 'badge-green', 'asistida': 'badge-green', 'cancelada': 'badge-red', 'suspendida': 'badge-yellow', 'falto': 'badge-red' }[estado] || 'badge-yellow'
}
function estadoReserva(reserva) {
  if (reserva.asistida) return 'asistida'
  return reserva.falto ? 'falto' : reserva.estado
}
function saldoPendienteReserva(reserva) {
  if (reserva?.saldo_pendiente != null) return Number(reserva.saldo_pendiente || 0)
  const total = Number(reserva?.monto_total || 0)
  const pagado = Number(reserva?.monto_pagado || 0)
  return Math.max(0, Math.round((total - pagado) * 100) / 100)
}
function reservaTotalPagado(reserva) {
  if (typeof reserva?.total_pagado === 'boolean') return reserva.total_pagado
  return saldoPendienteReserva(reserva) <= 0
}
function reservaEsFutura(reserva) {
  if (!reserva?.clase?.fecha || !reserva?.clase?.hora_inicio) return false
  const hora = String(reserva.clase.hora_inicio)
  const horaNormalizada = hora.length === 5 ? `${hora}:00` : hora
  return new Date(`${reserva.clase.fecha}T${horaNormalizada}`) > new Date()
}
function puedePagarReserva(reserva) {
  if (typeof reserva?.puede_pagar_total === 'boolean') return reserva.puede_pagar_total
  return reserva.estado === 'activa' && reservaEsFutura(reserva) && saldoPendienteReserva(reserva) > 0
}
function puedeCancelarReserva(reserva) {
  return reserva?.estado === 'activa' && !reserva.falto && !reserva.asistida && reservaEsFutura(reserva)
}
function sportEmoji(nombre) {
  const map = { 'Fútbol': '⚽', 'Pádel': '🎾', 'Básquet': '🏀', 'Vóley': '🏐' }
  return map[nombre] || '🏃'
}
function formatFecha(fechaStr) {
  if (!fechaStr) return ''
  const [y, m, d] = fechaStr.split('-')
  return `${d}/${m}/${y}`
}

function formatFechaCorta(f) {
  if (!f) return ''
  const [y, m, d] = f.split('-')
  return `${d}/${m}`
}

async function fetchUsuario() {
  loading.value = true
  try {
    const { data } = await api.get(`/usuarios/${route.params.id}`)
    usuario.value = data
  } catch (e) {
    err.value = 'No se pudo cargar el usuario'
  } finally {
    loading.value = false
  }
}

async function abrirReservas() {
  tab.value = 'reservas'
  reservasPage.value = 1
  await fetchReservas()
}

async function inscribir() {
  tab.value = 'inscribir'
  resetInscribirState()
}
async function fetchReservas() {
  loadingReservas.value = true
  try {
    const { data } = await api.get(`/usuarios/${route.params.id}/reservas`, {
      params: {
        page: reservasPage.value,
        limit: reservasLimit
      }
    })
    reservas.value = data.data
    reservasPage.value = data.pagination.page
    reservasPagination.value = {
      totalPages: data.pagination.total_pages,
      hasPrev: data.pagination.has_prev,
      hasNext: data.pagination.has_next
    }
  } finally {
    loadingReservas.value = false
  }
}

async function cambiarPaginaReservas(direccion) {
  const nuevaPagina = reservasPage.value + direccion
  if (nuevaPagina < 1 || nuevaPagina > reservasPagination.value.totalPages) return
  reservasPage.value = nuevaPagina
  await fetchReservas()
}

async function fetchSuspensiones() {
  try {
    const { data } = await api.get('/suspensiones/', { params: { activas: true, usuario_id: parseInt(route.params.id) } })
    suspensiones.value = data
  } catch {}
}

function resetInscribirState() {
  inscribirForm.value.clase_id = null
  inscribirForm.value.abono_opcion = null
  abonoDiaEmpl.value = null
  detalleAbonoEmpl.value = null
  clasesDisponibles.value = []
  horariosAbonoEmpl.value = []
  sueltaDiaEmpl.value = null
  sueltaHorarioEmpl.value = null
  fechasSueltaEmpl.value = []
}

function onActividadChange() {
  resetInscribirState()
  if (!inscribirForm.value.actividad_id) return
  if (inscribirForm.value.tipo === 'no_abonado') fetchFechasSueltaEmpl()
  else fetchHorariosAbonoEmpl()
}

function onTipoChange() {
  resetInscribirState()
  if (!inscribirForm.value.actividad_id) return
  if (inscribirForm.value.tipo === 'no_abonado') fetchFechasSueltaEmpl()
  else fetchHorariosAbonoEmpl()
}

async function fetchFechasSueltaEmpl() {
  if (!inscribirForm.value.actividad_id) return
  loadingFechasEmpl.value = true
  fechasSueltaEmpl.value = []
  try {
    const ahora = new Date()
    const pad = n => String(n).padStart(2, '0')
    const hoy = `${ahora.getFullYear()}-${pad(ahora.getMonth()+1)}-${pad(ahora.getDate())}`
    const hasta = new Date(ahora)
    hasta.setMonth(hasta.getMonth() + 1)
    const hastaStr = `${hasta.getFullYear()}-${pad(hasta.getMonth()+1)}-${pad(hasta.getDate())}`
    const { data } = await api.get('/clases/fechas-disponibles', {
      params: { actividad_id: inscribirForm.value.actividad_id, desde: hoy, hasta: hastaStr , usuario_id: route.params.id}
    })

    fechasSueltaEmpl.value = data
    .map(fecha => ({
      ...fecha,
      horarios: fecha.horarios.filter(horario => {
        const [hh, mm] = horario.hora_inicio.split(':').map(Number)
        const fechaHorario = new Date(fecha.fecha + 'T' + horario.hora_inicio + ':00')
        return fechaHorario > ahora
      })
    })).filter(fecha => fecha.horarios.length > 0)
    
  } finally {
    loadingFechasEmpl.value = false
  }
}

async function fetchHorariosAbonoEmpl() {
  if (!inscribirForm.value.actividad_id) return
  loadingHorariosAbono.value = true
  horariosAbonoEmpl.value = []
  try {
    const { data } = await api.get('/clases/horarios-disponibles', {
      params: { actividad_id: inscribirForm.value.actividad_id , usuario_id: route.params.id}
    })
    const ahora = new Date()
    horariosAbonoEmpl.value = data
      .map(horario => ({
        ...horario,
        clases_mes: horario.clases_mes.filter(c => {
          const fechaHora = new Date(c.fecha + 'T' + horario.hora_inicio + ':00')
          return fechaHora > ahora
        })
      }))
      .filter(horario => !horario.clases_mes.every(c => c.ya_inscripto))
      .filter(horario => horario.clases_mes.length > 0)

  } finally {
    loadingHorariosAbono.value = false
  }
}

async function elegirHorarioAbonoEmpl(op) {
  inscribirForm.value.abono_opcion = op
  loadingDetalleAbonoEmpl.value = true
  detalleAbonoEmpl.value = null
  try {
    const { data } = await api.get('/clases/detalle-abono', {
      params: {
        actividad_id: inscribirForm.value.actividad_id,
        dia_semana_num: abonoDiaEmpl.value.dia_semana_num,
        hora_inicio: op.hora_inicio,
        usuario_id: parseInt(route.params.id)  // para verificar beneficio y clases ya inscriptas
      }
    })
    detalleAbonoEmpl.value = data
  } finally {
    loadingDetalleAbonoEmpl.value = false
  }
}

function abrirConfirmacionInscripcion() {
  modalConfirmInscripcion.value = true
}

async function inscribirCliente() {
  inscribiendo.value = true
  err.value = ''
  try {
    if (inscribirForm.value.tipo === 'abonado' && detalleAbonoEmpl.value) {
      // Abono: reservar las disponibles y anotar las clases llenas en lista de espera.
      const clasesIds = detalleAbonoEmpl.value.clases
        .filter(c => c.incluida_en_abono)
        .map(c => c.clase_id)
      const clasesSinCupoIds = clasesParaListaEspera.value.map(c => c.clase_id)
      const { data } = await api.post('/reservas/abono', {
        clases_ids: [...clasesIds, ...clasesSinCupoIds],
        monto_total: detalleAbonoEmpl.value.monto_total,
        metodo_pago: 'efectivo',
        usuario_id: parseInt(route.params.id)
      })
      const totalEspera = data.clases_en_espera?.length || 0
      if (data.total_inscripto === 0 && totalEspera > 0) {
        msg.value = `${usuario.value.nombre} fue anotado en la lista de espera de ${totalEspera} clase(s). No se registró ningún cobro.`
      } else if (totalEspera > 0) {
        msg.value = `${usuario.value.nombre} fue inscripto en ${data.total_inscripto} clase(s) y anotado en lista de espera de ${totalEspera}. Total cobrado: $${detalleAbonoEmpl.value.monto_total?.toLocaleString()}`
      } else {
        msg.value = `${usuario.value.nombre} inscripto en ${data.total_inscripto} clase(s). Total cobrado: $${detalleAbonoEmpl.value.monto_total?.toLocaleString()}`
      }
    } else {
      // Clase suelta
      const { data } = await api.post(`/usuarios/${route.params.id}/inscribir`, {
        clase_id: inscribirForm.value.clase_id,
        tipo: inscribirForm.value.tipo,
        monto_pagar: inscribirForm.value.monto_pagar
      })
      if (data.en_espera) {
        msg.value = `${usuario.value.nombre} fue añadido a la lista de espera. No se registró ningún cobro.`
      } else {
        msg.value = `${usuario.value.nombre} inscripto correctamente. Cobrado en efectivo.`
      }
    }
    modalConfirmInscripcion.value = false
    tab.value = 'reservas'
    await fetchReservas()
  } catch (e) {
    err.value = e.response?.data?.error || 'Error al inscribir'
  } finally {
    inscribiendo.value = false
  }
}

async function ejecutarEliminar() {
  eliminando.value = true
  err.value = ''
  try {
    await api.post(`/usuarios/${route.params.id}/borrar`)
    msg.value = 'Usuario eliminado correctamente'
    modalEliminar.value = false
    // Redirigir a la lista después de eliminar
    setTimeout(() => router.push('/admin/usuarios'), 1500)
  } catch (e) {
    err.value = e.response?.data?.error || 'Error al eliminar'
  } finally {
    eliminando.value = false
  }
}

async function ejecutarPromoverAdmin() {
  promoviendoAdmin.value = true
  err.value = ''
  msg.value = ''
  try {
    const { data } = await api.post(`/usuarios/${route.params.id}/promover-admin`)
    usuario.value = data.usuario
    msg.value = data.mensaje || 'Empleado convertido en administrador'
    modalPromoverAdmin.value = false
  } catch (e) {
    err.value = e.response?.data?.error || 'Error al convertir en administrador'
  } finally {
    promoviendoAdmin.value = false
  }
}

async function ejecutarDegradarAdmin() {
  degradandoAdmin.value = true
  err.value = ''
  msg.value = ''
  try {
    const { data } = await api.post(`/usuarios/${route.params.id}/degradar-empleado`)
    usuario.value = data.usuario
    msg.value = data.mensaje || 'Administrador convertido en empleado'
    modalDegradarAdmin.value = false
  } catch (e) {
    err.value = e.response?.data?.error || 'Error al convertir en empleado'
  } finally {
    degradandoAdmin.value = false
  }
}

function confirmarCancelarReserva(r) {
  if (!puedeCancelarReserva(r)) return
  modalCancelarReserva.value = r
}

function mensajeCancelacionReserva(data) {
  const partes = ['Reserva cancelada']
  if (data.info) partes.push(data.info)
  if (data.credito_generado > 0) partes.push(`Credito generado: $${data.credito_generado.toLocaleString()}`)
  if (data.descuento_aplicado > 0) partes.push(`Descuento aplicado: $${data.descuento_aplicado.toLocaleString()}`)
  if (data.devolucion_senia > 0) partes.push(`Senia a devolver: $${data.devolucion_senia.toLocaleString()}`)
  if (data.advertencia) partes.push(data.advertencia)
  return partes.join(' - ')
}

async function ejecutarCancelarReserva() {
  if (!puedeCancelarReserva(modalCancelarReserva.value)) {
    modalCancelarReserva.value = null
    return
  }
  cancelandoReserva.value = true
  err.value = ''
  try {
    const uid = parseInt(route.params.id)
    const { data } = await api.post(`/reservas/cliente/${uid}/cancelar/${modalCancelarReserva.value.id}`)
    msg.value = mensajeCancelacionReserva(data)
    modalCancelarReserva.value = null
    await fetchReservas()
  } catch (e) {
    err.value = e.response?.data?.error || 'Error al cancelar reserva'
  } finally {
    cancelandoReserva.value = false
  }
}

async function levantarSuspension(s) {
  levantando.value = s.id
  err.value = ''
  try {
    await api.post(`/suspensiones/solicitar-retiro/${s.id}`, { metodo: metodoLevantamiento.value })
    msg.value = 'Suspensión levantada'
    await fetchUsuario()
    await fetchSuspensiones()
  } catch (e) {
    err.value = e.response?.data?.error || 'Error al levantar suspensión'
  } finally {
    levantando.value = null
  }
}

async function abrirModal(s) {
  suspensionAConfirmar.value = s
}

async function confirmarLevantamiento() {
  const s = suspensionAConfirmar.value
  suspensionAConfirmar.value = null
  await levantarSuspension(s)
}

async function crearSuspensionClaseSueltaPrueba() {
  if (usuario.value?.suspensiones_activas?.some(s => s.tipo === 'no_abonado')) {
    msg.value = 'El usuario ya tiene una suspension activa por clase suelta'
    tab.value = 'suspensiones'
    await fetchSuspensiones()
    return
  }

  creandoSuspensionPrueba.value = true
  err.value = ''
  msg.value = ''
  try {
    await api.post('/suspensiones/', {
      usuario_id: parseInt(route.params.id),
      tipo: 'no_abonado',
      motivo: 'Suspension de prueba por 3 inasistencias con pagos pendientes en clases sueltas.',
      cantidad_clases: 3,
      monto_original: 3000
    })
    msg.value = 'Suspension de prueba creada correctamente'
    tab.value = 'suspensiones'
    await fetchUsuario()
    await fetchSuspensiones()
  } catch (e) {
    err.value = e.response?.data?.error || 'Error al crear la suspension de prueba'
  } finally {
    creandoSuspensionPrueba.value = false
  }
}

function abrirPagoReserva(r) {
  pagoReservaModal.value = r
  metodoPagoReserva.value = 'efectivo'
}

async function pagarReserva() {
  pagandoReserva.value = true
  err.value = ''
  msg.value = ''
  try {
    const { data } = await api.post(`/usuarios/${route.params.id}/pagar-reserva/${pagoReservaModal.value.id}`, {
      metodo: metodoPagoReserva.value
    })
    msg.value = data.mensaje || 'Reserva pagada correctamente'
    pagoReservaModal.value = null
    await fetchReservas()
  } catch (e) {
    err.value = e.response?.data?.error || 'Error al registrar el pago'
  } finally {
    pagandoReserva.value = false
  }
}

onMounted(async () => {
  const { data } = await api.get('/actividades/')
  actividades.value = data
  await fetchUsuario()
})
</script>

<style scoped>
.back-link { font-size: 13px; color: var(--text-muted); transition: color 0.2s; }
.back-link:hover { color: var(--verde-claro); }
.avatar-xl {
  width: 64px; height: 64px;
  background: linear-gradient(135deg, var(--verde), var(--azul));
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 26px; font-weight: 700; flex-shrink: 0;
}
.detalle-item { display: flex; flex-direction: column; gap: 4px; margin-bottom: 16px; }
.label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.acciones-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
.accion-btn {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 20px 12px;
  background: var(--dark-3); border: 1px solid var(--border);
  border-radius: 10px; cursor: pointer; color: var(--text);
  font-family: 'DM Sans', sans-serif; font-size: 14px; font-weight: 500;
  transition: all 0.2s;
}
.accion-btn:hover { border-color: var(--verde); color: var(--verde-claro); transform: translateY(-2px); }
.accion-btn:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
.accion-peligro { border-color: rgba(218,54,51,0.3) !important; }
.accion-peligro:hover { border-color: var(--danger) !important; color: var(--danger) !important; }
.accion-icon { font-size: 28px; }
.clases-lista { display: flex; flex-direction: column; gap: 8px; }
.clase-opcion {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px;
  background: var(--dark-3); border: 1px solid var(--border);
  border-radius: 8px; cursor: pointer; transition: all 0.2s;
}
.clase-opcion:hover { border-color: var(--verde); }
.clase-opcion.selected { border-color: var(--verde-claro); background: rgba(46,125,50,0.1); }
.clase-opcion.sin-cupo { opacity: 0.7; }
.suspension-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px; background: var(--dark-3); border-radius: 8px; margin-bottom: 10px;
  border: 1px solid rgba(218,54,51,0.2);
}
.text-green { color: var(--success); font-weight: 600; }
.text-danger { color: var(--danger); font-weight: 600; }
.loading-text { text-align: center; padding: 60px; color: var(--text-muted); }
.confirm-row-modal { display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid var(--border);font-size:14px; }
.confirm-label { color:var(--text-muted); }
.dia-btn-empl { background:var(--dark-3);border:2px solid var(--border);border-radius:10px;padding:12px 18px;cursor:pointer;transition:all 0.2s;display:flex;flex-direction:column;align-items:center;gap:4px;min-width:100px;text-align:center; }
.dia-btn-empl:hover { border-color:var(--verde);transform:translateY(-2px); }
.horario-btn-empl { background:var(--dark-3);border:2px solid var(--border);border-radius:8px;padding:10px 16px;cursor:pointer;transition:all 0.2s;display:flex;flex-direction:column;align-items:center;gap:3px;min-width:90px; }
.horario-btn-empl:hover { border-color:var(--verde); }
.horario-btn-empl.selected { border-color:var(--verde-claro);background:rgba(46,125,50,0.1); }
.fecha-sel-banner-empl { display:flex;align-items:center;justify-content:space-between;background:rgba(46,125,50,0.08);border:1px solid var(--verde);border-radius:8px;padding:10px 14px;margin-bottom:14px;font-size:13px;font-weight:500; }
.abono-detalle-lista { display:flex;flex-direction:column;gap:6px;margin-bottom:10px; }
.abono-detalle-item { display:flex;align-items:center;justify-content:space-between;padding:8px 12px;border-radius:6px;border:1px solid var(--border);font-size:13px; }
.abono-detalle-item.incluida { background:rgba(63,185,80,0.05);border-color:rgba(63,185,80,0.2); }
.abono-detalle-item.excluida { background:rgba(218,54,51,0.04);border-color:rgba(218,54,51,0.15);opacity:0.75; }
.abono-detalle-item.ya-inscripto-item { background:rgba(21,101,192,0.06);border-color:rgba(21,101,192,0.2);opacity:0.8; }
.abono-total-empl { display:flex;justify-content:space-between;align-items:center;padding:12px 14px;background:rgba(46,125,50,0.08);border-radius:8px;border:1px solid var(--verde);margin-top:8px;font-size:14px;font-weight:600; }
.text-green { color:var(--success); }
.text-warning { color:var(--warning); }
.reservas-pagination { display:flex;justify-content:center;gap:10px;margin-top:18px; }
.pagination-arrow {
  width:42px;height:38px;display:flex;align-items:center;justify-content:center;
  border:1px solid var(--border);border-radius:8px;background:var(--dark-3);
  color:var(--text);font-size:20px;cursor:pointer;transition:all 0.2s;
}
.pagination-arrow:hover:not(:disabled) { border-color:var(--verde);color:var(--verde-claro); }
.pagination-arrow:disabled { opacity:0.35;cursor:not-allowed; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 200; }
.modal { max-width: 440px; width: 100%; }
.modal h3 { font-size: 22px; margin-bottom: 8px; }
</style>
