# Lista de comprobación manual — Autos Colombia

Realiza las siguientes pruebas con datos de demostración y conserva una captura en cada caso. La ejecución automática desde `probar_windows.bat` no reemplaza estas comprobaciones visuales.

- [ ] Abrir login en Chrome, iniciar sesión como administrador y cerrar la sesión.
- [ ] Crear un usuario, actualizar su nombre y desactivar su cuenta.
- [ ] Comprobar que un operario no puede entrar a Usuarios, Clientes, Vehículos, Pagos o Respaldo.
- [ ] Intentar registrar un usuario con nombre duplicado y verificar el mensaje de rechazo.
- [ ] Registrar un cliente, modificar sus datos y asociarle un vehículo de placa única.
- [ ] Crear una celda de Carro y una de Moto; filtrar el listado por tipo y estado.
- [ ] Cambiar una celda libre a Fuera de servicio y volverla a habilitar.
- [ ] Intentar modificar o deshabilitar una celda ocupada: debe impedirse.
- [ ] En Entrada, consultar `ABC123` y comprobar propietario, tipo y fechas de mensualidad antes de asignar celda.
- [ ] Para un Carro, comprobar que solo aparecen celdas de Carro disponibles y habilitadas.
- [ ] Consultar un vehículo sin mensualidad pagada y vigente: el botón de entrada debe permanecer bloqueado.
- [ ] Confirmar una entrada válida: verificar movimiento activo, usuario de entrada y celda ocupada.
- [ ] Intentar un segundo ingreso sin registrar la salida: debe rechazarse.
- [ ] Registrar la salida: comprobar usuario de salida, movimiento cerrado y celda disponible.
- [ ] Descargar el respaldo en Chrome; verificar nombre y tamaño del archivo `.db`.
- [ ] Detener el servidor; restaurar el respaldo en una **copia de prueba**, no directamente en la única base del proyecto.
- [ ] Abrir la app en Microsoft Edge y repetir login, listado de usuarios, celdas y consulta de placa.
- [ ] Registrar tiempos de respuesta habituales y comprobar el objetivo de 3 segundos.

**Restauración en copia de prueba** (con el servidor detenido):

```powershell
.\.venv\Scripts\python.exe restaurar_respaldo.py "C:\Ruta\al\respaldo.db"
```

El comando anterior sin parámetros adicionales restaura la base del proyecto. Para evitar modificar la única base, realiza la prueba sobre una copia de la carpeta de la aplicación, o usa la función `restaurar(archivo, destino)` desde Python con un destino de pruebas.

**Resultado:** no marcar una casilla hasta realizarla. Guardar evidencia de los fallos y corregir antes de entregar.
