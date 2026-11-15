// La consulta previa es informativa: el servidor vuelve a validar todos los datos al guardar.
document.addEventListener('DOMContentLoaded', () => {
  const placa = document.querySelector('#placa');
  const botonBuscar = document.querySelector('#buscar-vehiculo');
  const panel = document.querySelector('#resultado-consulta');
  const selectCelda = document.querySelector('#celda_id');
  const botonConfirmar = document.querySelector('#confirmar-entrada');
  const placaConfirmacion = document.querySelector('#placa-confirmacion');
  const formulario = document.querySelector('#form-entrada');
  let versionConsulta = 0;
  const normalizarPlaca = valor => valor.trim().toUpperCase().replace(/\s+/g, '');

  function limpiar() {
    selectCelda.replaceChildren(new Option('Primero consulta una placa', ''));
    selectCelda.disabled = true;
    botonConfirmar.disabled = true;
    placaConfirmacion.value = '';
  }

  placa.addEventListener('input', () => {
    // Las respuestas de una placa anterior no deben habilitar una asignación.
    versionConsulta += 1;
    limpiar();
    botonBuscar.disabled = false;
    panel.textContent = 'Pulsa «Buscar vehículo» para validar la placa.';
  });
  formulario.addEventListener('submit', event => {
    if (placaConfirmacion.value !== normalizarPlaca(placa.value) ||
        !selectCelda.value || selectCelda.disabled) {
      event.preventDefault();
      limpiar();
      panel.textContent = 'Consulta nuevamente la placa y selecciona una celda válida.';
    }
  });
  placa.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') { event.preventDefault(); botonBuscar.click(); }
  });

  botonBuscar.addEventListener('click', async () => {
    limpiar();
    const valor = normalizarPlaca(placa.value);
    const versionActual = ++versionConsulta;
    if (!valor) { panel.textContent = 'Debes escribir una placa.'; return; }
    panel.textContent = 'Consultando información…';
    botonBuscar.disabled = true;
    try {
      const respuesta = await fetch(`${formulario.dataset.consultaUrl}?placa=${encodeURIComponent(valor)}`, {
        headers: {'Accept': 'application/json'}, credentials: 'same-origin'
      });
      const datos = await respuesta.json();
      if (versionActual !== versionConsulta || normalizarPlaca(placa.value) !== valor) return;
      if (!respuesta.ok || !datos.encontrado) {
        panel.textContent = datos.motivo || 'No fue posible consultar el vehículo.';
        return;
      }
      const vigencia = datos.mensualidad.fin ? `${datos.mensualidad.inicio} – ${datos.mensualidad.fin}` : 'Sin mensualidad';
      const detalle = document.createElement('div');
      const filas = [
        ['Placa', datos.placa], ['Cliente', datos.cliente], ['Tipo', datos.tipo],
        ['Período', vigencia], ['Pago', datos.mensualidad.pagada ? 'Pagado' : 'Pendiente'],
        ['Vigencia', datos.mensualidad.vigente ? 'Vigente' : 'Vencida o no registrada']
      ];
      for (const [etiqueta, valor] of filas) {
        const fila = document.createElement('p');
        const titulo = document.createElement('strong'); titulo.textContent = etiqueta + ': ';
        fila.append(titulo, document.createTextNode(String(valor))); detalle.appendChild(fila);
      }
      const aviso = document.createElement('p'); aviso.className = datos.autorizado ? 'texto-aceptado' : 'texto-error';
      aviso.textContent = datos.autorizado ? 'Ingreso autorizado: selecciona una celda.' : datos.motivo;
      detalle.append(aviso); panel.replaceChildren(detalle);
      if (datos.autorizado) {
        selectCelda.replaceChildren(new Option('Selecciona una celda', ''));
        for (const celda of datos.celdas) selectCelda.add(new Option(`${celda.numero} — ${celda.tipo}`, String(celda.id)));
        selectCelda.disabled = false;
        botonConfirmar.disabled = false;
        placaConfirmacion.value = datos.placa;
      }
    } catch (err) {
      if (versionActual === versionConsulta) {
        panel.textContent = 'No fue posible consultar el vehículo. Comprueba la conexión e inténtalo de nuevo.';
      }
    } finally {
      if (versionActual === versionConsulta) botonBuscar.disabled = false;
    }
  });
});
