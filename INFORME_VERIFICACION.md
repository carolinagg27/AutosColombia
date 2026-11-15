# Autos Colombia — Informe de verificación de la Iteración 2

**Fecha:** 15 de noviembre de 2026  
**Alcance:** código del proyecto Autos Colombia, gestión de usuarios y celdas, integración de entradas/salidas y respaldo SQLite.

## Estado real de las comprobaciones

| Verificación | Resultado | Alcance y límites |
|---|---|---|
| Pruebas reales de SQLite | **15 aprobadas / 15 ejecutadas** | Restricciones, claves foráneas, índices únicos, transacciones, respaldo y restauración real con copia preventiva. |
| Comprobaciones de código y plantillas | **6 aprobadas / 6 ejecutadas** | Compilación Python, Jinja2 (con filtro personalizado), enlaces `url_for`, CSRF en formularios y sintaxis JavaScript. |
| Interacción de ingreso en Chromium | **6 escenarios aprobados** | JS real ejecutado en Chromium con la API simulada: consulta válida, cambio de placa, mensualidad vencida, vehículo inexistente, error de conexión y respuesta desfasada. |
| Compilación global Python | **Aprobada** | `python -m compileall -q .` |
| Sintaxis JavaScript | **Aprobada** | `node --check app/static/js/entrada.js` |
| Pruebas completas de Flask (rutas, sesión, formulario y CSRF) | **Pendientes de ejecución** | Flask y sus extensiones no están instaladas en este entorno; el acceso a dependencias de PyPI está bloqueado. |
| Descarga real en Windows y navegación Chrome / Edge | **Pendientes de ejecución** | Requieren el equipo Windows y sus navegadores. |

**Importante:** los resultados anteriores no constituyen una certificación de funcionamiento del 100 % del sistema; los 19 casos de aceptación del plan deben ejecutarse sobre la aplicación instalada. Tampoco se ha efectuado un despliegue público o pruebas de carga/concurrencia a gran escala.

## Correcciones implementadas

1. Se rechazan placas con caracteres distintos de letras y números.
2. El pago de una mensualidad se considera válido solo si el recibo registrado corresponde al valor total del contrato.
3. La consulta por placa omite celdas con movimientos activos, incluso ante estados históricos desincronizados.
4. El registro de entrada vuelve a comprobar en el servidor el vehículo, la mensualidad, el tipo y la ocupación; en SQLite se mantienen los índices únicos de movimiento activo.
5. La salida no puede registrarse con una fecha anterior a la entrada; se conserva el usuario de salida como opcional hasta cerrar el movimiento.
6. Se añadieron filtros de nombre, usuario, rol y estado para la administración de usuarios.
7. La pantalla de ingreso ignora resultados de consultas anteriores si el operario cambia la placa mientras se procesa una petición y evita confirmaciones con selecciones inválidas.
8. El respaldo SQLite se comprueba con `integrity_check`, `foreign_key_check` y la presencia de las ocho tablas; se atienden rutas de Windows con espacios.
9. La restauración produce una copia preventiva, verifica la copia antes de sustituir, usa reemplazo atómico y se niega a actuar si existen archivos auxiliares WAL/SHM.
10. Se agregó `tzdata` como dependencia específica de Windows, necesaria para `ZoneInfo("America/Bogota")` en equipos sin base horaria IANA.
11. Se amplió la batería automatizada de aceptación: CP-01 a CP-19, CSRF, filtros y errores de búsqueda.

## Cómo completar la validación de Flask en Windows

1. Descomprimir `Autos_Colombia_Software` en una carpeta local.
2. Ejecutar `instalar_windows.bat` (instala dependencias y prepara usuarios de prueba).
3. Ejecutar **`probar_windows.bat`**. El script instala pytest y corre las pruebas, incluidas las de Flask, utilizando archivos SQLite **temporales**: no altera el contenido de `instance/autos_colombia.db`.
4. Antes de marcar **Aprobados** los casos del punto g), revisar que ninguna prueba falle. Si falla, conservar el mensaje del terminal para corregir el defecto.
5. Ejecutar `iniciar_windows.bat` y abrir `http://127.0.0.1:5000` en Chrome y Edge. Probar manualmente roles, formularios y los filtros de celdas.
6. Desde el panel principal descargar un respaldo en Windows, detener la aplicación y comprobar su restauración en una **copia de prueba** de la base; revisar que los registros coincidan.

Comando alternativo desde PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -v --tb=short
```

**Criterio de aprobación integral:** batería completa sin fallos + navegación manual en Windows correcta + respaldo descargado y restaurado correctamente. No afirmar una cifra del 100 % antes de completar estas comprobaciones.
