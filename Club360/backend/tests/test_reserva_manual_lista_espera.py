import unittest
from datetime import date, time

from flask import Flask

from models import Actividad, Clase, ListaEspera, Pago, Reserva, Usuario, db
from routes.reservas import crear_reserva_unica


class ReservaManualListaEsperaTestCase(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            SECRET_KEY='test-secret'
        )
        db.init_app(self.app)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        self.empleado = Usuario(
            nombre='Eva', apellido='Empleado', dni='1',
            email='empleado@test.com', password_hash='x', rol='empleado'
        )
        self.cliente = Usuario(
            nombre='Ciro', apellido='Cliente', dni='2',
            email='cliente@test.com', password_hash='x', rol='cliente'
        )
        self.otro_cliente = Usuario(
            nombre='Ona', apellido='Cliente', dni='3',
            email='otro@test.com', password_hash='x', rol='cliente'
        )
        self.actividad = Actividad(nombre='Padel', precio_clase=1000)
        db.session.add_all([self.empleado, self.cliente, self.otro_cliente, self.actividad])
        db.session.flush()

        self.clase = Clase(
            actividad_id=self.actividad.id,
            fecha=date(2026, 7, 10),
            hora_inicio=time(18, 0),
            cupo_maximo=1,
            precio_clase=1000
        )
        db.session.add(self.clase)
        db.session.flush()

        reserva_existente = Reserva(
            usuario_id=self.otro_cliente.id,
            clase_id=self.clase.id,
            tipo='no_abonado',
            estado='activa',
            mes=7,
            anio=2026,
            monto_total=1000,
            monto_pagado=500,
            senia_pagada=True
        )
        db.session.add(reserva_existente)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_manual_clase_suelta_en_lista_espera_no_registra_pago(self):
        resultado, _, _ = crear_reserva_unica(
            self.cliente.id,
            self.clase.id,
            'no_abonado',
            self.empleado.id,
            metodo_pago='efectivo',
            monto_pagar='senia'
        )

        self.assertEqual(resultado, 'espera')
        self.assertEqual(
            Reserva.query.filter_by(usuario_id=self.cliente.id, clase_id=self.clase.id).count(),
            0
        )
        self.assertEqual(Pago.query.count(), 0)

        espera = ListaEspera.query.filter_by(
            usuario_id=self.cliente.id,
            clase_id=self.clase.id,
            estado='esperando'
        ).first()
        self.assertIsNotNone(espera)
        self.assertEqual(espera.tipo_preferencia, 'no_abonado')


if __name__ == '__main__':
    unittest.main()
