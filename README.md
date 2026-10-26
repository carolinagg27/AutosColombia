# Autos Colombia — Software de parqueadero

Aplicación web académica para gestionar clientes, vehículos, celdas, entradas y salidas, novedades, mensualidades, pagos e historial.

**Tecnologías:** Python 3.11+, Flask, Flask-Login, Flask-WTF, Flask-SQLAlchemy y SQLite. **Base de datos:** 8 tablas del punto 6 del taller.

## 1. Requisitos

- Windows 10/11 (también funciona en macOS y Linux).
- Python 3.11 o superior instalado desde https://www.python.org/downloads/ (en Windows, activar la opción para añadir Python al PATH).
- Conexión a Internet **solo para instalar** las dependencias por primera vez. El CSS incluye estilos locales y Bootstrap por CDN.

## 2. Instalación en Windows (forma recomendada)

1. Descomprime el ZIP en una carpeta, por ejemplo `Documentos\Autos_Colombia_Software`.
2. Abre la carpeta y ejecuta **`instalar_windows.bat`** (doble clic).
3. Se instalarán las dependencias, se creará la base de datos y se generarán usuarios de prueba. **Anota las contraseñas que muestra la ventana**.
4. Ejecuta **`iniciar_windows.bat`**.
5. Entra desde Chrome a **http://127.0.0.1:5000** y escribe el usuario y contraseña impresos durante la instalación.

Si `py` no funciona, instala Python o sustituye `py` por `python` en los comandos.

## 3. Instalación manual (Windows PowerShell)

Desde una terminal abierta en la carpeta del proyecto:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe seed.py
.\.venv\Scripts\python.exe run.py
```

En macOS / Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python seed.py
.venv/bin/python run.py
```

Visita `http://127.0.0.1:5000`. Detén el servidor con `Ctrl + C`.

## 4. Datos para probar

El script `seed.py` crea las cuentas `admin` y `operario`, cada una con una contraseña aleatoria que aparece en la terminal. También crea:

- 8 celdas para carro y 4 para moto.
- Cliente de ejemplo con documento `1000000001`.
- Carro de placa **ABC123**, con mensualidad vigente y pagada.

**Prueba recomendada:** entra con `admin`, registra el ingreso de `ABC123` a la celda `C-01`, registra una novedad y luego la salida. Consulta el historial para comprobar ambos movimientos.

Para entrar por primera vez, es necesario ejecutar `seed.py`. Si ya hay usuarios registrados, el script no crea más cuentas ni muestra otra vez las contraseñas.

## 5. Funcionalidades y roles

| Módulo | Administrador | Operario |
| --- | --- | --- |
| Iniciar sesión, panel y salir | Sí | Sí |
| Consultar celdas | Sí | Sí |
| Registrar entradas/salidas | Sí | Sí |
| Registrar novedades y consultar historial | Sí | Sí |
| Crear/editar clientes y vehículos | Sí | No |
| Crear celdas y cambiar su disponibilidad | Sí | No |
| Registrar mensualidades y pagos | Sí | No |
| Administrar usuarios y descargar respaldo | Sí | No |

**Reglas:** la entrada requiere matrícula del vehículo, celda disponible compatible, mensualidad vigente y pagada, y ausencia de otra entrada activa. La salida libera la celda aunque haya vencido la mensualidad. Cada mensualidad se paga en **una sola transacción completa**. No se calculan tarifas por hora.

## 6. Archivos principales

```
Autos_Colombia_Software/
├── app/
│   ├── __init__.py              # Configuración y página principal
│   ├── models.py                # 8 entidades de base de datos
│   ├── routes/                  # Rutas y vistas de los módulos
│   ├── services/                # Validaciones de entrada/salida y pagos
│   ├── templates/               # HTML de cada pantalla
│   ├── static/css/estilos.css   # Estilos visuales
│   └── utils/validaciones.py    # Validaciones comunes
├── instance/                    # La BD se genera aquí en la instalación
├── tests/test_sistema.py       # Pruebas automáticas
├── sql/modelo_punto6.sql       # Referencia del punto 6, NO ejecutar junto al ORM
├── seed.py                      # Usuarios y datos iniciales
├── run.py                       # Ejecutar aplicación
├── instalar_windows.bat
├── iniciar_windows.bat
├── requirements.txt
└── README.md
```

**Atención:** los modelos de SQLAlchemy crean automáticamente las tablas en el arranque. El archivo `sql/modelo_punto6.sql` se entrega como documentación; no necesitas ejecutarlo.

## 7. Cómo realizar las pruebas

```powershell
.\.venv\Scripts\python.exe -m pip install pytest
.\.venv\Scripts\python.exe -m pytest -q
```

Las pruebas utilizan otra base temporal y no modifican la base de datos del parqueadero.

## 8. Respaldo y limitaciones

Con la cuenta `admin`, abre el panel principal y pulsa **Descargar respaldo**. Se descargará un archivo `.db` con una copia SQLite. Guarda estas copias fuera del equipo principal.

Esta versión es un **prototipo académico para uso local**. No incluye lector de placas, hardware de barreras, facturación electrónica, pagos en línea ni despliegue en Internet. Para una operación comercial real harían falta pruebas adicionales, gestión de cambios del esquema, políticas de datos personales, copias automáticas y servidor web de producción. No habilites el servidor de desarrollo para acceso público.

**Recuperar la base:** detén el servidor, haz una copia de seguridad del archivo actual y reemplaza `instance/autos_colombia.db` por el respaldo descargado, manteniendo el mismo nombre. Las cuentas quedarán como estaban en la fecha del respaldo.
