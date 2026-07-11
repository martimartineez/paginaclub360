import unittest
from datetime import date, time
from unittest.mock import patch

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

from models import Abono, Actividad, Clase, Pago, Reserva, Suspension, Turno, Usuario, db
from routes.otros import suspensiones_bp
from routes.reservas import reservas_bp


class Dia13(date):
    @classmethod
    def today(cls):
        return cls(2026, 7, 13)


class SuspensionPagoHistorialTestCase(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            SECRET_KEY='test-secret',
            JWT_SECRET_KEY='test-secret',
            JWT_ACCESS_TOKEN_EXPIRES=False,
        )
        db.init_app(self.app)
        JWTManager(self.app)
        self.app.register_blueprint(reservas_bp, url_prefix='/api/reservas')
        self.app.register_blueprint(suspensiones_bp, url_prefix='/api/suspensiones')
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        self.cliente = Usuario(
            nombre='Ciro', apellido='Cliente', dni='2',
            email='cliente@test.com', password_hash='x', rol='cliente'
        )
        self.actividad = Actividad(nombre='Padel', precio_clase=1000)
        db.session.add_all([self.cliente, self.actividad])
        db.session.flush()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def auth_headers(self):
        token = create_access_token(identity=str(self.cliente.id))
        return {'Authorization': f'Bearer {token}'}

    def crear_reservas_pasadas_con_deuda(self):
        reservas = []
        for dia in (3, 4, 5):
            clase = Clase(
                actividad_id=self.actividad.id,
                fecha=date(2020, 7, dia),
                hora_inicio=time(18, 0),
                cupo_maximo=10,
                precio_clase=1000
            )
            db.session.add(clase)
            db.session.flush()
            reserva = Reserva(
                usuario_id=self.cliente.id,
                clase_id=clase.id,
                tipo='no_abonado',
                estado='activa',
                mes=7,
                anio=2020,
                monto_total=1000,
                monto_pagado=500,
                senia_pagada=True
            )
            db.session.add(reserva)
            reservas.append(reserva)
        db.session.commit()
        return reservas

    def crear_abono_suspendido(self):
        turno = Turno(
            actividad_id=self.actividad.id,
            dia_semana=0,
            hora_inicio=time(18, 0),
            cupo_maximo=10,
            precio_clase=1000
        )
        abono = Abono(
            usuario_id=self.cliente.id,
            actividad_id=self.actividad.id,
            mes=7,
            anio=2026,
            monto_total=2000,
            monto_pagado=0
        )
        db.session.add_all([turno, abono])
        db.session.flush()

        clase = Clase(
            actividad_id=self.actividad.id,
            turno_id=turno.id,
            fecha=date(2026, 7, 14),
            hora_inicio=time(18, 0),
            cupo_maximo=10,
            precio_clase=1000
        )
        db.session.add(clase)
        db.session.flush()
        reserva = Reserva(
            usuario_id=self.cliente.id,
            clase_id=clase.id,
            abono_id=abono.id,
            tipo='abonado',
            estado='suspendida',
            mes=7,
            anio=2026,
            monto_total=1000,
            monto_pagado=0,
            senia_pagada=True
        )
        suspension = Suspension(
            usuario_id=self.cliente.id,
            tipo='abonado',
            abono_id=abono.id,
            turno_id=turno.id,
            clase_id=clase.id,
            activa=True,
            cantidad_clases=2,
            monto_original=2000,
            recargo=100,
            monto_deuda=2100,
            motivo='Abono pendiente vencido para este turno.'
        )
        db.session.add_all([reserva, suspension])
        db.session.commit()
        return abono, reserva, suspension

    def test_pagar_suspension_no_marca_reservas_y_aparece_en_historial(self):
        reservas = self.crear_reservas_pasadas_con_deuda()
        suspension = Suspension(
            usuario_id=self.cliente.id,
            tipo='no_abonado',
            activa=True,
            cantidad_clases=3,
            monto_original=1500,
            recargo=75,
            monto_deuda=1575,
            motivo='Inasistencias con pagos pendientes en clases sueltas.'
        )
        db.session.add(suspension)
        db.session.commit()

        pago_response = self.client.post(
            f'/api/suspensiones/{suspension.id}/pagar',
            json={'metodo': 'tarjeta_credito'},
            headers=self.auth_headers()
        )

        self.assertEqual(pago_response.status_code, 200)
        self.assertEqual(Pago.query.count(), 1)
        db.session.refresh(suspension)
        self.assertFalse(suspension.activa)

        for reserva in reservas:
            db.session.refresh(reserva)
            self.assertEqual(float(reserva.monto_pagado), 500)
            self.assertTrue(reserva.senia_pagada)

        resumen_response = self.client.get(
            '/api/reservas/pagos-resumen',
            headers=self.auth_headers()
        )
        suspensiones_response = self.client.get(
            '/api/suspensiones/mis',
            headers=self.auth_headers()
        )

        self.assertEqual(resumen_response.status_code, 200)
        resumen = resumen_response.get_json()
        pagos_suspension = [
            item for item in resumen['pagados']
            if item.get('tipo') == 'suspension' and item.get('suspension_id') == suspension.id
        ]
        self.assertEqual(len(pagos_suspension), 1)
        self.assertEqual(pagos_suspension[0]['tipo_label'], 'Suspension de clase suelta')
        self.assertEqual(pagos_suspension[0]['monto_pagado'], 1575)
        self.assertEqual(pagos_suspension[0]['cantidad_clases'], 3)

        self.assertEqual(suspensiones_response.status_code, 200)
        self.assertEqual(suspensiones_response.get_json(), [])

    def test_pagar_suspension_de_abono_aparece_como_tarjeta_aparte(self):
        abono, reserva, suspension = self.crear_abono_suspendido()

        pago_response = self.client.post(
            f'/api/suspensiones/{suspension.id}/pagar',
            json={'metodo': 'tarjeta_credito'},
            headers=self.auth_headers()
        )

        self.assertEqual(pago_response.status_code, 200)
        db.session.refresh(abono)
        db.session.refresh(reserva)
        self.assertEqual(float(abono.monto_pagado), 0)
        self.assertEqual(float(reserva.monto_pagado), 0)
        self.assertEqual(reserva.estado, 'suspendida')

        with patch('routes.reservas.date', Dia13), patch('suspensiones_logic.date', Dia13):
            resumen_response = self.client.get(
                '/api/reservas/pagos-resumen',
                headers=self.auth_headers()
            )

        self.assertEqual(resumen_response.status_code, 200)
        resumen = resumen_response.get_json()
        abono_impago = [
            item for item in resumen['pagados']
            if item.get('tipo') == 'abonado' and item.get('abono_id') == abono.id
        ]
        self.assertEqual(len(abono_impago), 1)
        self.assertTrue(abono_impago[0]['abono_vencido'])
        self.assertEqual(abono_impago[0]['deuda_label'], 'No pagado - $2,000')

        pagos_suspension = [
            item for item in resumen['pagados']
            if item.get('tipo') == 'suspension' and item.get('suspension_id') == suspension.id
        ]
        self.assertEqual(len(pagos_suspension), 1)
        self.assertEqual(pagos_suspension[0]['tipo_label'], 'Suspension de abono mensual')
        self.assertEqual(pagos_suspension[0]['abono_id'], abono.id)
        self.assertEqual(pagos_suspension[0]['monto_pagado'], 2100)
        self.assertEqual(pagos_suspension[0]['cantidad_clases'], 2)

    def test_pagar_deuda_de_abono_no_reactiva_reserva_suspendida(self):
        abono, reserva, suspension = self.crear_abono_suspendido()

        response = self.client.post(
            f'/api/reservas/abono/{abono.id}/pagar',
            json={'metodo': 'tarjeta_credito', 'monto': 2000},
            headers=self.auth_headers()
        )

        self.assertEqual(response.status_code, 201)
        db.session.refresh(abono)
        db.session.refresh(reserva)
        db.session.refresh(suspension)
        self.assertEqual(float(abono.monto_pagado), 2000)
        self.assertEqual(float(reserva.monto_pagado), 1000)
        self.assertEqual(reserva.estado, 'suspendida')
        self.assertFalse(suspension.activa)


if __name__ == '__main__':
    unittest.main()
