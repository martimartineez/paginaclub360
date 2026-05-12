# Club 360 — Sistema de Gestión Deportiva

Proyecto de Ingeniería de Software 2 — RedKey Software  
Stack: Python + Flask + SQLAlchemy + PostgreSQL | Vue 3 + Vite

---

## Requisitos previos

- Python 3.10+ (probado en 3.14)
- Node.js 18+
- PostgreSQL 14+

---

## 1. Configurar PostgreSQL

Abrí psql o pgAdmin y ejecutá:

```sql
CREATE DATABASE club360;
CREATE USER postgres WITH PASSWORD 'postgres';
GRANT ALL PRIVILEGES ON DATABASE club360 TO postgres;
```

Si ya tenés un usuario/contraseña distinto, ajustá el `.env` del backend.

---

## 2. Backend (Flask)

### 2.1 Crear entorno virtual

```bash
cd club360/backend
python -m venv venv

# Windows:
venv\Scripts\activate
```

Sabés que está activo cuando ves `(venv)` al inicio del prompt.

### 2.2 Instalar dependencias

```bash
pip install Flask Flask-SQLAlchemy Flask-Migrate Flask-JWT-Extended Flask-CORS python-dotenv bcrypt qrcode APScheduler
pip install Pillow --upgrade
pip install "psycopg[binary]"
```

> ⚠️ **No uses** `pip install -r requirements.txt` directamente si tenés Python 3.13/3.14 en Windows, porque `psycopg2-binary` falla. Los comandos de arriba instalan todo correctamente.

### 2.3 Configurar variables de entorno

Copiá `.env.example` y renombralo a `.env`:

```bash
# Windows:
copy .env.example .env
```

El `.env` debe quedar así (ajustá usuario/contraseña si es diferente):

```
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/club360
JWT_SECRET_KEY=una-clave-secreta-larga
```

> ⚠️ El prefijo es `postgresql+psycopg://` (no `postgresql://`) porque usamos el driver psycopg3.

### 2.4 Crear tablas y cargar datos iniciales

```bash
python app.py
```

Esto crea todas las tablas automáticamente y carga datos de prueba:
- Admin: `admin@club360.com` / `admin123`
- Empleado: `empleado@club360.com` / `emp123`
- Cliente: `cliente@club360.com` / `cliente123`
- 4 actividades (Fútbol, Pádel, Básquet, Vóley) con precios
- 6 clases de ejemplo distribuidas en la semana

El servidor queda corriendo en **http://localhost:5000**

> Para correrlo luego sin recrear datos: `python app.py` (el seed solo carga si la base está vacía)

---

## 3. Frontend (Vue 3 + Vite)

En **otra terminal** (sin cerrar la del backend):

```bash
cd club360/frontend
npm install
npm run dev
```

El frontend queda disponible en **http://localhost:5173**

---

## 4. Estructura del proyecto

```
club360/
├── backend/
│   ├── app.py                  ← Entrada principal Flask
│   ├── requirements.txt
│   ├── .env.example
│   ├── models/
│   │   └── __init__.py         ← Modelos SQLAlchemy
│   └── routes/
│       ├── auth.py             ← Login, registro, perfil
│       ├── clases.py           ← CRUD clases, inscriptos, espera
│       ├── reservas.py         ← Reservar, pagar, cancelar, QR
│       └── otros.py            ← Usuarios, actividades, asistencia, suspensiones
│
└── frontend/
    ├── index.html
    ├── vite.config.js
    ├── package.json
    └── src/
        ├── main.js
        ├── App.vue             ← Layout principal + navbar
        ├── style.css           ← Estilos globales (tema Club 360)
        ├── api.js              ← Axios configurado con JWT
        ├── router/index.js     ← Rutas con guards por rol
        ├── stores/auth.js      ← Pinia store autenticación
        └── views/
            ├── Inicio.vue      ← Landing page pública
            ├── Login.vue
            ├── Registro.vue
            ├── Clases.vue      ← Ver clases, reservar, lista de espera
            ├── MisReservas.vue ← Ver QR, pagar, cancelar
            ├── Perfil.vue
            ├── admin/
            │   ├── GestionClases.vue       ← Crear/editar clases, ver inscriptos y espera
            │   ├── GestionUsuarios.vue     ← Buscar usuarios, ver suspensiones
            │   └── GestionActividades.vue  ← CRUD actividades y precios
            └── empleado/
                ├── RegistroAsistencia.vue  ← Escanear QR y registrar asistencia
                └── Suspensiones.vue        ← Ver y levantar suspensiones
```

---

## 5. Funcionalidades implementadas

### Visitantes (sin login)
- Ver página de inicio con info del club
- Ver clases disponibles y filtrar por actividad/día
- Ver cupos disponibles en tiempo real

### Clientes
- Registro (nombre, apellido, DNI, email)
- Login / logout
- Reservar clase como **abonado (mensual)** o **no abonado (clase suelta)**
- Si no hay cupo → se agrega automáticamente a la **lista de espera**
- Ver mis reservas con estado, montos y QR
- **Ver código QR** de asistencia por reserva
- **Pagar online** con tarjeta de crédito
- **Cancelar reserva** con política de crédito a favor o recupero de seña
- Editar perfil y cambiar contraseña

### Empleados
- Todo lo de un cliente
- **Registrar asistencia por QR** (ingresar código, ver alertas del cliente)
- Ver y levantar suspensiones (activas e historial)

### Administradores
- Todo lo de empleados
- **Crear/editar clases** (actividad, día, hora, cupo)
- **Ver inscriptos y lista de espera** por clase (con alerta si hay 10+ en espera)
- **Gestión de actividades** (nombre, descripción, precio por clase)
- **Buscar y filtrar usuarios** por nombre/DNI/email/rol
- **Ver detalle de usuario** con suspensiones activas
- Registrar empleados nuevos
- Crear suspensiones manuales

---

## 6. Endpoints API principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | /api/auth/login | Login |
| POST | /api/auth/register | Registro de usuario |
| GET | /api/auth/me | Usuario actual |
| GET | /api/actividades/ | Listar actividades |
| GET | /api/clases/ | Listar clases (con filtros) |
| POST | /api/clases/ | Crear clase (admin) |
| GET | /api/clases/{id}/inscriptos | Ver inscriptos (empleado/admin) |
| GET | /api/clases/{id}/lista-espera | Ver lista de espera |
| GET | /api/reservas/ | Mis reservas |
| POST | /api/reservas/ | Crear reserva |
| POST | /api/reservas/{id}/cancelar | Cancelar reserva |
| POST | /api/reservas/{id}/pagar | Registrar pago |
| GET | /api/reservas/{id}/qr | Ver QR |
| GET | /api/usuarios/ | Listar usuarios (empleado/admin) |
| POST | /api/asistencia/registrar | Registrar asistencia por QR |
| GET | /api/suspensiones/ | Ver suspensiones |
| POST | /api/suspensiones/solicitar-retiro/{id} | Levantar suspensión |

---

## 7. Notas de implementación

- Los pagos online son solo con **tarjeta de crédito** (simulado)
- Los pagos en efectivo los registra el **empleado** en sede
- El **QR** se genera como imagen base64 al crear la reserva
- Las **listas de espera** tienen lógica de prioridad (abonados primero si el que cancela era abonado)
- El sistema alerta al admin cuando hay **10+ personas en lista de espera**
- Los créditos a favor aplican solo al mes siguiente y al mismo turno
- Las suspensiones incluyen un **recargo del 5%** sobre la deuda
- Solo mayores de 18 años pueden registrarse (validación en frontend)

---

## 8. Problemas conocidos en Windows con Python 3.13/3.14

| Error | Causa | Solución |
|-------|-------|----------|
| `Failed building wheel for psycopg2-binary` | No hay wheel para Python 3.14 | Usar `psycopg[binary]` en su lugar |
| `Failed building wheel for Pillow` | Versión fija incompatible | Instalar con `pip install Pillow --upgrade` |
| `ModuleNotFoundError: No module named 'flask'` | pip abortó por error previo | Reinstalar con los comandos del paso 2.2 |
