const tabla = document.querySelector("#ordenes");
const detalle = document.querySelector("#detalle");
const mensajeLista = document.querySelector("#mensaje-lista");
const mensajeDetalle = document.querySelector("#mensaje-detalle");
const tituloDetalle = document.querySelector("#titulo-detalle");
const filtroEstado = document.querySelector("#filtro-estado");
const actualizar = document.querySelector("#actualizar");

const anterior = document.querySelector("#pagina-anterior");
const siguiente = document.querySelector("#pagina-siguiente");
const indicadorPagina = document.querySelector("#pagina-actual");

const formularioBusqueda = document.querySelector("#buscar-orden");
const numeroOrden = document.querySelector("#numero-orden");
const botonBuscar = document.querySelector("#boton-buscar");

const TAMANO_PAGINA = 20;

let paginaActual = 0;
let hayPaginaSiguiente = false;
let solicitudLista = 0;

let solicitudDetalle = 0;
let ordenSeleccionada = null;

const estados = {
  recibido: "Recibido",
  diagnostico: "Diagnóstico",
  en_reparacion: "En reparación",
  listo: "Listo",
  entregado: "Entregado",
};

const moneda = new Intl.NumberFormat("es-PE", {
  style: "currency",
  currency: "PEN",
});

function elemento(etiqueta, texto) {
  const nodo = document.createElement(etiqueta);
  if (texto !== undefined) nodo.textContent = texto;
  return nodo;
}

function mostrarMensaje(nodo, texto, error = false) {
  nodo.textContent = texto;
  nodo.classList.toggle("error", error);
}

function fecha(valor) {
  if (!valor) return "Pendiente";
  return new Date(valor).toLocaleString("es-PE");
}

function costo(valor) {
  return valor == null ? "Pendiente" : moneda.format(valor);
}

function dias(valor) {
  return valor == null ? "Pendiente" : `${valor} días`;
}

async function consultar(ruta) {
  let respuesta;

  try {
    respuesta = await fetch(ruta);
  } catch {
    throw new Error(
      "No se pudo conectar. Comprueba que el servidor siga encendido."
    );
  }

  if (!respuesta.ok) {
    const datos = await respuesta.json().catch(() => ({}));
    throw new Error(
      typeof datos.detail === "string"
        ? datos.detail
        : `La consulta falló (HTTP ${respuesta.status}).`
    );
  }

  return respuesta.json();
}

function agregarSeccion(titulo, campos) {
  detalle.append(elemento("h3", titulo));
  const lista = elemento("dl");

  for (const [nombre, valor] of campos) {
    lista.append(
      elemento("dt", nombre),
      elemento("dd", valor ?? "Sin registrar")
    );
  }

  detalle.append(lista);
}

function marcarSeleccion() {
  for (const fila of tabla.rows) {
    const seleccionada = Number(fila.dataset.id) === ordenSeleccionada;
    fila.classList.toggle("seleccionada", seleccionada);
    fila.querySelector("button").setAttribute(
      "aria-pressed", String(seleccionada)
    );
  }
}

async function verDetalle(id) {
  // Evita mostrar una respuesta antigua si se elige otra orden rápidamente.
  const turno = ++solicitudDetalle;
  ordenSeleccionada = id;
  marcarSeleccion();
  detalle.replaceChildren();
  tituloDetalle.textContent = `Orden #${id}`;
  mostrarMensaje(mensajeDetalle, "Cargando detalle…");

  try {
    const datos = await consultar(`/ordenes/${id}/detalle`);
    if (turno !== solicitudDetalle) return;

    const { orden, cliente, equipo, tecnico, observaciones, historial } = datos;

    agregarSeccion("Servicio", [
      ["Estado", estados[orden.estado] ?? orden.estado],
      ["Prioridad", orden.prioridad],
      ["Descripción del cliente", orden.descripcion_falla],
      ["Categoría confirmada",
        orden.categoria_falla?.replaceAll("_", " ") ?? "Pendiente"],
      ["Ingreso", fecha(orden.fecha_ingreso)],
      ["Entrega", fecha(orden.fecha_entrega)],
    ]);

    agregarSugerenciasIA(orden.id, turno);
    agregarFormularioDiagnostico(orden, turno);
    
    agregarSeccion("Cliente y equipo", [
      ["Cliente", cliente.nombre],
      ["Teléfono", cliente.telefono],
      ["Correo", cliente.email],
      ["Equipo", `${equipo.tipo} · ${equipo.marca} ${equipo.modelo}`],
      ["Serie", equipo.serie],
      ["Técnico asignado", tecnico?.nombre ?? "Sin asignar"],
    ]);

    agregarSeccion("Estimaciones y resultados", [
      ["Tiempo estimado", dias(orden.tiempo_estimado_dias)],
      ["Tiempo real", dias(orden.tiempo_real_dias)],
      ["Costo estimado", costo(orden.costo_estimado)],
      ["Costo real", costo(orden.costo_real)],
    ]);

    agregarFormularioEstimacion(orden, turno);
    agregarFormularioCostoReal(orden, turno);
    agregarComparacion(orden, turno);
    agregarHistorialEstimaciones(orden, turno);

    detalle.append(elemento("h3", "Observaciones técnicas"));
    agregarFormularioObservacion(orden, turno);

    if (observaciones.length === 0) {
      detalle.append(elemento("p", "Todavía no hay observaciones."));
    } else {
      const lista = elemento("ul");
      for (const observacion of observaciones) {
        lista.append(elemento(
          "li",
          `${fecha(observacion.fecha)} · Técnico #${observacion.tecnico_id}\n` +
          observacion.texto
        ));
      }
      detalle.append(lista);
    }

    agregarCambioEstado(orden, turno);

    detalle.append(elemento("h3", "Historial de estados"));

    if (historial.length === 0) {
      detalle.append(elemento("p", "Todavía no hay cambios registrados."));
    } else {
      const lista = elemento("ol");
      for (const cambio of historial) {
        lista.append(elemento(
          "li",
          `${estados[cambio.estado] ?? cambio.estado} · ${fecha(cambio.fecha)}`
        ));
      }
      detalle.append(lista);
    }

    mostrarMensaje(mensajeDetalle, "Detalle cargado.");
    tituloDetalle.focus();
  } catch (error) {
    if (turno !== solicitudDetalle) return;
    mostrarMensaje(
      mensajeDetalle,
      `${error.message} Pulsa “Ver detalle” para reintentar.`,
      true
    );
  }
}

async function cargarOrdenes(nuevaPagina = 0) {
  const turno = ++solicitudLista;

  actualizar.disabled = true;
  anterior.disabled = true;
  siguiente.disabled = true;
  mostrarMensaje(mensajeLista, "Cargando órdenes…");

  try {
    const desplazamiento = nuevaPagina * TAMANO_PAGINA;

    // Pedimos una orden adicional para saber si existe otra página.
    const estadoElegido = filtroEstado.value;
    const nombreFiltro = filtroEstado.selectedOptions[0].textContent;

    const parametros = new URLSearchParams({
      limite: String(TAMANO_PAGINA + 1),
      desplazamiento: String(desplazamiento),
    });

    if (estadoElegido) {
      parametros.set("estado", estadoElegido);
    }

    const resultados = await consultar(`/ordenes?${parametros}`);

    if (turno !== solicitudLista) return;

    const ordenes = resultados.slice(0, TAMANO_PAGINA);

    paginaActual = nuevaPagina;
    hayPaginaSiguiente = resultados.length > TAMANO_PAGINA;

    tabla.replaceChildren();

    for (const orden of ordenes) {
      const fila = elemento("tr");
      fila.dataset.id = orden.id;

      const estado = elemento(
        "span",
        estados[orden.estado] ?? orden.estado
      );
      estado.className = "estado";

      const celdaEstado = elemento("td");
      celdaEstado.append(estado);

      const boton = elemento("button", "Ver detalle");
      boton.type = "button";
      boton.setAttribute(
        "aria-label",
        `Ver detalle de la orden ${orden.id}`
      );
      boton.addEventListener("click", () => verDetalle(orden.id));

      const accion = elemento("td");
      accion.append(boton);

      fila.append(
        elemento("td", `#${orden.id}`),
        elemento("td", orden.descripcion_falla),
        celdaEstado,
        accion
      );

      tabla.append(fila);
    }

    indicadorPagina.textContent = `Página ${paginaActual + 1}`;
    marcarSeleccion();

      mostrarMensaje(
      mensajeLista,
      ordenes.length
        ? `${nombreFiltro}: ${ordenes.length} órdenes en esta página.`
        : `No hay órdenes en esta página para “${nombreFiltro}”.`
    );
  } catch (error) {
    if (turno !== solicitudLista) return;

    mostrarMensaje(
      mensajeLista,
      `${error.message} Puedes volver a intentar la consulta.`,
      true
    );
  } finally {
    if (turno === solicitudLista) {
      actualizar.disabled = false;
      anterior.disabled = paginaActual === 0;
      siguiente.disabled = !hayPaginaSiguiente;
    }
  }
}

actualizar.addEventListener("click", () => {
  cargarOrdenes(paginaActual);
});

anterior.addEventListener("click", () => {
  if (paginaActual > 0) {
    cargarOrdenes(paginaActual - 1);
  }
});

siguiente.addEventListener("click", () => {
  if (hayPaginaSiguiente) {
    cargarOrdenes(paginaActual + 1);
  }
});

numeroOrden.addEventListener("input", () => {
  numeroOrden.setCustomValidity("");
});

formularioBusqueda.addEventListener("submit", async (evento) => {
  evento.preventDefault();

  if (botonBuscar.disabled) return;

  const id = Number(numeroOrden.value);

  if (!Number.isSafeInteger(id) || id <= 0) {
    numeroOrden.setCustomValidity(
      "Ingresa un número entero positivo."
    );
    numeroOrden.reportValidity();
    return;
  }

  botonBuscar.disabled = true;
  botonBuscar.textContent = "Buscando…";

  try {
    await verDetalle(id);
  } finally {
    botonBuscar.disabled = false;
    botonBuscar.textContent = "Abrir orden";
  }
});

cargarOrdenes();

const formularioOrden = document.querySelector("#formulario-orden");
const camposOrden = document.querySelector("#campos-orden");
const equipoInput = document.querySelector("#equipo-id");
const prioridadInput = document.querySelector("#prioridad-orden");
const descripcionInput = document.querySelector("#descripcion-orden");
const guardarOrden = document.querySelector("#guardar-orden");
const mensajeCreacion = document.querySelector("#mensaje-creacion");

let guardandoOrden = false;

descripcionInput.addEventListener("input", () => {
  descripcionInput.setCustomValidity("");
});

formularioOrden.addEventListener("submit", async (evento) => {
  evento.preventDefault();

  if (guardandoOrden) return;

  const descripcion = descripcionInput.value.trim();
  const equipoId = Number(equipoInput.value);

    if (
    !clienteSeleccionado ||
    clienteSeleccionado.dni !== dniCliente.value.trim() ||
    !equiposDelCliente.has(equipoId)
  ) {
    mostrarMensaje(
      mensajeCreacion,
      "Busca un cliente y selecciona uno de sus equipos.",
      true
    );
    return;
  }

  if (!descripcion) {
    descripcionInput.setCustomValidity(
      "Escribe una descripción; los espacios solos no cuentan."
    );
    descripcionInput.reportValidity();
    return;
  }

  if (!Number.isSafeInteger(equipoId) || equipoId <= 0) {
    mostrarMensaje(
      mensajeCreacion,
      "El número de equipo debe ser un entero positivo.",
      true
    );
    return;
  }

  const datos = {
    equipo_id: equipoId,
    descripcion_falla: descripcion,
    prioridad: prioridadInput.value,
  };

  guardandoOrden = true;
  camposOrden.disabled = true;
  guardarOrden.textContent = "Guardando…";
  mostrarMensaje(mensajeCreacion, "Guardando la orden…");

  try {
    let respuesta;

    try {
      respuesta = await fetch("/ordenes", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(datos),
      });
    } catch {
      throw new Error(
        "Se perdió la conexión y no podemos confirmar el guardado. " +
        "Consulta “Actualizar lista” antes de volver a enviar."
      );
    }

    if (!respuesta.ok) {
      const error = await respuesta.json().catch(() => ({}));

      if (respuesta.status >= 500) {
        throw new Error(
          "El servidor tuvo un problema. Revisa la lista antes de " +
          "volver a enviar para comprobar si se creó la orden."
        );
      }

      throw new Error(
        typeof error.detail === "string"
          ? error.detail
          : `Revisa los datos enviados (HTTP ${respuesta.status}).`
      );
    }

    let orden;

    try {
      orden = await respuesta.json();

      if (!Number.isSafeInteger(orden.id)) {
        throw new Error("Respuesta incompleta");
      }
    } catch {
      throw new Error(
        "El servidor aceptó la solicitud, pero no pudimos leer la orden. " +
        "Consulta “Actualizar lista” antes de volver a enviar."
      );
    }

    formularioOrden.reset();

    mostrarMensaje(
      mensajeCreacion,
      `Orden #${orden.id} creada correctamente.`
    );

    await cargarOrdenes();
    await verDetalle(orden.id);
  } catch (error) {
    mostrarMensaje(mensajeCreacion, error.message, true);
  } finally {
    guardandoOrden = false;
    camposOrden.disabled = false;
    guardarOrden.textContent = "Crear orden";
  }
});

function agregarSugerenciasIA(ordenId, turnoDetalle) {
  const seccion = elemento("section");
  seccion.className = "sugerencias-ia";

  const titulo = elemento("h3", "Sugerencias de IA");

  const explicacion = elemento(
    "p",
    "Basadas en la descripción del cliente. " +
    "Las puntuaciones son orientativas; el técnico confirma el diagnóstico."
  );

  const boton = elemento("button", "Consultar sugerencias de IA");
  boton.type = "button";

  const mensaje = elemento("p");
  mensaje.setAttribute("role", "status");

  const lista = elemento("ol");
  lista.className = "lista-sugerencias";

  seccion.append(titulo, explicacion, boton, mensaje, lista);
  detalle.append(seccion);

  const nombres = {
    bateria: "Batería",
    pantalla: "Pantalla",
    placa_madre: "Placa madre",
    fuente_poder: "Fuente de poder",
    disco_duro: "Disco duro",
    software: "Software",
    sobrecalentamiento: "Sobrecalentamiento",
    teclado_touchpad: "Teclado o touchpad",
    atasco_papel: "Atasco de papel",
    cabezal_tinta: "Cabezal de tinta",
    fusor_laser: "Fusor láser",
  };

  boton.addEventListener("click", async () => {
    if (boton.disabled) return;

    boton.disabled = true;
    boton.textContent = "Consultando…";
    lista.replaceChildren();
    mostrarMensaje(mensaje, "Analizando la descripción del cliente…");

    try {
      const datos = await consultar(
        `/ordenes/${ordenId}/sugerencias?cantidad=3`
      );

      // Ignoramos el resultado si el usuario ya abrió otra ficha.
      if (turnoDetalle !== solicitudDetalle) return;

      for (const sugerencia of datos.sugerencias) {
        const fila = elemento("li");

        const nombre = elemento(
          "strong",
          nombres[sugerencia.categoria] ?? sugerencia.categoria
        );

        const puntuacion = elemento(
          "span",
          `Puntuación: ${sugerencia.puntuacion.toFixed(4)}`
        );

        fila.append(nombre, puntuacion);
        lista.append(fila);
      }

      mostrarMensaje(
        mensaje,
        datos.sugerencias.length
          ? "Sugerencias ordenadas de mayor a menor puntuación."
          : "No se recibieron sugerencias."
      );
    } catch (error) {
      if (turnoDetalle !== solicitudDetalle) return;

      mostrarMensaje(
        mensaje,
        `${error.message} Puedes volver a consultar.`,
        true
      );
    } finally {
      boton.disabled = false;
      boton.textContent = "Consultar sugerencias de IA";
    }
  });
}

async function agregarFormularioDiagnostico(orden, turnoDetalle) {
  if (!["recibido", "diagnostico"].includes(orden.estado)) return;

  const formulario = elemento("form");
  formulario.className = "formulario-diagnostico";

  const titulo = elemento("h3", "Confirmar diagnóstico");
  const campos = elemento("fieldset");
  campos.disabled = true;

  const leyenda = elemento("legend", "Técnico y categoría");
  leyenda.className = "solo-lectores";
  campos.append(leyenda);

  function agregarSelector(id, tituloCampo) {
    const contenedor = elemento("div");
    contenedor.className = "campo";

    const etiqueta = elemento("label", tituloCampo);
    etiqueta.htmlFor = id;

    const selector = elemento("select");
    selector.id = id;
    selector.required = true;

    const inicial = elemento("option", "Selecciona una opción");
    inicial.value = "";
    selector.append(inicial);

    contenedor.append(etiqueta, selector);
    campos.append(contenedor);

    return selector;
  }

  const tecnicoSelect = agregarSelector(
    `tecnico-diagnostico-${orden.id}`,
    "Técnico responsable"
  );

  const categoriaSelect = agregarSelector(
    `categoria-diagnostico-${orden.id}`,
    "Categoría confirmada por el técnico"
  );

  const categorias = {
    bateria: "Batería",
    pantalla: "Pantalla",
    placa_madre: "Placa madre",
    fuente_poder: "Fuente de poder",
    disco_duro: "Disco duro",
    software: "Software",
    sobrecalentamiento: "Sobrecalentamiento",
    teclado_touchpad: "Teclado o touchpad",
    atasco_papel: "Atasco de papel",
    cabezal_tinta: "Cabezal de tinta",
    fusor_laser: "Fusor láser",
  };

  for (const [valor, nombre] of Object.entries(categorias)) {
    const opcion = elemento("option", nombre);
    opcion.value = valor;
    categoriaSelect.append(opcion);
  }

  categoriaSelect.value = orden.categoria_falla ?? "";

  const boton = elemento("button", "Guardar diagnóstico");
  boton.type = "submit";
  campos.append(boton);

  const mensaje = elemento("p");
  mensaje.setAttribute("role", "status");

  formulario.append(titulo, campos, mensaje);
  detalle.append(formulario);

  let guardando = false;

  formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();

    if (
      guardando ||
      campos.disabled ||
      turnoDetalle !== solicitudDetalle
    ) return;

    if (!formulario.reportValidity()) return;

    const datos = {
      tecnico_id: Number(tecnicoSelect.value),
      categoria_falla: categoriaSelect.value,
    };

    guardando = true;
    campos.disabled = true;
    boton.textContent = "Guardando…";
    mostrarMensaje(mensaje, "Guardando diagnóstico…");

    try {
      let respuesta;

      try {
        respuesta = await fetch(`/ordenes/${orden.id}/diagnostico`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(datos),
        });
      } catch {
        throw new Error(
          "No se pudo confirmar el guardado. " +
          "Vuelve a abrir la ficha para comprobar el diagnóstico."
        );
      }

      if (!respuesta.ok) {
        const error = await respuesta.json().catch(() => ({}));

        throw new Error(
          typeof error.detail === "string"
            ? error.detail
            : `No se pudo confirmar el cambio (HTTP ${respuesta.status}). ` +
              "Vuelve a abrir la ficha para revisar su estado."
        );
      }

      // Evitamos que un guardado anterior cambie la ficha seleccionada.
      if (turnoDetalle !== solicitudDetalle) return;

      mostrarMensaje(mensaje, "Diagnóstico guardado.");
      await cargarOrdenes();

      if (turnoDetalle === solicitudDetalle) {
        await verDetalle(orden.id);
      }
    } catch (error) {
      if (turnoDetalle === solicitudDetalle) {
        mostrarMensaje(mensaje, error.message, true);
      }
    } finally {
      guardando = false;
      campos.disabled = false;
      boton.textContent = "Guardar diagnóstico";
    }
  });

  mostrarMensaje(mensaje, "Cargando técnicos…");

  try {
    const tecnicos = await consultar("/tecnicos?limite=100");
    if (turnoDetalle !== solicitudDetalle) return;

    if (tecnicos.length === 0) {
      mostrarMensaje(mensaje, "No hay técnicos registrados.", true);
      return;
    }

    for (const tecnico of tecnicos) {
      const opcion = elemento(
        "option",
        `${tecnico.nombre} — ${tecnico.especialidad}`
      );
      opcion.value = tecnico.id;
      tecnicoSelect.append(opcion);
    }

    tecnicoSelect.value = orden.tecnico_id == null
      ? ""
      : String(orden.tecnico_id);

    campos.disabled = false;
    mostrarMensaje(mensaje, "");
  } catch (error) {
    if (turnoDetalle !== solicitudDetalle) return;

    mostrarMensaje(
      mensaje,
      `${error.message} Vuelve a abrir la ficha para cargar los técnicos.`,
      true
    );
  }
}

function agregarFormularioObservacion(orden, turnoDetalle) {
  const estadosPermitidos = ["diagnostico", "en_reparacion", "listo"];

  if (
    !estadosPermitidos.includes(orden.estado) ||
    orden.tecnico_id == null
  ) return;

  const formulario = elemento("form");
  formulario.className = "formulario-observacion";

  const campo = elemento("div");
  campo.className = "campo";

  const etiqueta = elemento("label", "Nueva observación técnica");
  const texto = elemento("textarea");

  texto.id = `observacion-${orden.id}`;
  etiqueta.htmlFor = texto.id;

  texto.rows = 4;
  texto.required = true;
  texto.maxLength = 3000;
  texto.placeholder = "Describe las pruebas realizadas y los hallazgos.";

  campo.append(etiqueta, texto);

  const boton = elemento("button", "Guardar observación");
  boton.type = "submit";

  const mensaje = elemento("p");
  mensaje.setAttribute("role", "status");

  formulario.append(campo, boton, mensaje);
  detalle.append(formulario);

  let guardando = false;

  texto.addEventListener("input", () => {
    texto.setCustomValidity("");
  });

  formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();

    if (guardando || turnoDetalle !== solicitudDetalle) return;

    const contenido = texto.value.trim();

    if (!contenido) {
      texto.setCustomValidity(
        "Escribe una observación; los espacios solos no cuentan."
      );
      texto.reportValidity();
      return;
    }

    if (!formulario.reportValidity()) return;

    guardando = true;
    texto.disabled = true;
    boton.disabled = true;
    boton.textContent = "Guardando…";

    mostrarMensaje(mensaje, "Guardando observación…");

    try {
      let respuesta;

      try {
        respuesta = await fetch(`/ordenes/${orden.id}/observaciones`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            texto: contenido,
          }),
        });
      } catch {
        throw new Error(
          "No se pudo confirmar el guardado. " +
          "Vuelve a abrir la ficha y revisa las observaciones antes de reenviar."
        );
      }

      if (!respuesta.ok) {
        const error = await respuesta.json().catch(() => ({}));

        if (respuesta.status >= 500) {
          throw new Error(
            "El servidor tuvo un problema. Vuelve a abrir la ficha " +
            "y revisa las observaciones antes de reenviar."
          );
        }

        throw new Error(
          typeof error.detail === "string"
            ? error.detail
            : `Revisa la observación (HTTP ${respuesta.status}).`
        );
      }

      // La respuesta exitosa confirma el guardado.
      texto.value = "";

      // Si ya se abrió otra orden, no cambiamos esa ficha.
      if (turnoDetalle !== solicitudDetalle) return;

      mostrarMensaje(mensaje, "Observación guardada.");
      await verDetalle(orden.id);
    } catch (error) {
      if (turnoDetalle === solicitudDetalle) {
        mostrarMensaje(mensaje, error.message, true);
      }
    } finally {
      guardando = false;
      texto.disabled = false;
      boton.disabled = false;
      boton.textContent = "Guardar observación";
    }
  });
}

function agregarFormularioEstimacion(orden, turnoDetalle) {
  if (
    orden.estado !== "diagnostico" ||
    orden.tecnico_id == null ||
    !orden.categoria_falla
  ) return;

  const formulario = elemento("form");
  formulario.className = "formulario-estimacion";

  const campo = elemento("div");
  campo.className = "campo";

  const etiqueta = elemento("label", "Tipos de repuesto previstos");

  const entrada = elemento("input");
  entrada.id = `repuestos-estimacion-${orden.id}`;
  entrada.type = "number";
  entrada.min = "0";
  entrada.step = "1";
  entrada.required = true;

  etiqueta.htmlFor = entrada.id;

  const ayuda = elemento(
    "small",
    "Por ejemplo: solo teclado = 1; teclado y batería = 2; " +
    "sin repuestos = 0."
  );

  ayuda.id = `ayuda-estimacion-${orden.id}`;
  entrada.setAttribute("aria-describedby", ayuda.id);

  campo.append(etiqueta, entrada, ayuda);

  const explicacion = elemento(
    "p",
    "Se calculará con el diagnóstico guardado. " +
    "El tiempo corresponde a la duración total prevista desde el ingreso."
  );

  const boton = elemento("button", "Calcular estimación");
  boton.type = "submit";

  const mensaje = elemento("p");
  mensaje.setAttribute("role", "status");

  formulario.append(campo, explicacion, boton, mensaje);
  detalle.append(formulario);

  let calculando = false;

  formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();

    if (calculando || turnoDetalle !== solicitudDetalle) return;
    if (!formulario.reportValidity()) return;

    const cantidad = Number(entrada.value);

    if (!Number.isSafeInteger(cantidad) || cantidad < 0) {
      mostrarMensaje(
        mensaje,
        "Ingresa un número entero igual o mayor que cero.",
        true
      );
      return;
    }

    calculando = true;
    entrada.disabled = true;
    boton.disabled = true;
    boton.textContent = "Calculando…";
    mostrarMensaje(mensaje, "Calculando tiempo y costo estimados…");

    try {
      let respuesta;

      try {
        respuesta = await fetch(`/ordenes/${orden.id}/estimacion`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            num_repuestos: cantidad,
          }),
        });
      } catch {
        throw new Error(
          "No se pudo confirmar el cálculo. " +
          "Vuelve a abrir la ficha para comprobar las estimaciones."
        );
      }

      if (!respuesta.ok) {
        const error = await respuesta.json().catch(() => ({}));

        throw new Error(
          typeof error.detail === "string"
            ? error.detail
            : `No se pudo confirmar la estimación (HTTP ${respuesta.status}). ` +
              "Vuelve a abrir la ficha para revisar los valores."
        );
      }

      if (turnoDetalle !== solicitudDetalle) return;

      mostrarMensaje(mensaje, "Estimación calculada y guardada.");
      await verDetalle(orden.id);
    } catch (error) {
      if (turnoDetalle === solicitudDetalle) {
        mostrarMensaje(mensaje, error.message, true);
      }
    } finally {
      calculando = false;
      entrada.disabled = false;
      boton.disabled = false;
      boton.textContent = "Calcular estimación";
    }
  });
}

function agregarCambioEstado(orden, turnoDetalle) {
  const seccion = elemento("section");
  seccion.className = "cambio-estado";
  seccion.append(elemento("h3", "Avance del servicio"));
  detalle.append(seccion);

  if (orden.estado === "recibido") {
    seccion.append(elemento(
      "p",
      "Asigna un técnico y confirma el diagnóstico para continuar."
    ));
    return;
  }

  if (orden.estado === "entregado") {
    seccion.append(elemento(
      "p",
      `Servicio entregado el ${fecha(orden.fecha_entrega)}.`
    ));
    return;
  }

  const pasos = {
    diagnostico: {
      siguiente: "en_reparacion",
      boton: "Iniciar reparación",
      descripcion: "Registra que el técnico comienza la reparación.",
    },
    en_reparacion: {
      siguiente: "listo",
      boton: "Marcar como listo",
      descripcion: "Registra que el equipo está listo para entregar.",
    },
    listo: {
      siguiente: "entregado",
      boton: "Registrar entrega",
      descripcion:
        "Registra la entrega al cliente con la fecha y hora actuales. " +
        "También calcula el tiempo total desde el ingreso.",
    },
  };

  const paso = pasos[orden.estado];
  if (!paso) return;

  const descripcion = elemento("p", paso.descripcion);
  const boton = elemento("button", paso.boton);
  boton.type = "button";

  const mensaje = elemento("p");
  mensaje.setAttribute("role", "status");

  seccion.append(descripcion, boton, mensaje);

  let guardando = false;

  boton.addEventListener("click", async () => {
    if (guardando || turnoDetalle !== solicitudDetalle) return;

    guardando = true;
    boton.disabled = true;
    boton.textContent = "Guardando…";
    mostrarMensaje(mensaje, "Actualizando el estado…");

    try {
      let respuesta;

      try {
        respuesta = await fetch(`/ordenes/${orden.id}/estado`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            estado: paso.siguiente,
          }),
        });
      } catch {
        throw new Error(
          "No se pudo confirmar el cambio. " +
          "Vuelve a abrir la ficha para comprobar el estado."
        );
      }

      if (!respuesta.ok) {
        const error = await respuesta.json().catch(() => ({}));

        throw new Error(
          typeof error.detail === "string"
            ? error.detail
            : `No se pudo confirmar el cambio (HTTP ${respuesta.status}). ` +
              "Vuelve a abrir la ficha para revisar su estado."
        );
      }

      if (turnoDetalle !== solicitudDetalle) return;

      mostrarMensaje(mensaje, "Estado actualizado.");
      await cargarOrdenes();

      if (turnoDetalle === solicitudDetalle) {
        await verDetalle(orden.id);
      }
    } catch (error) {
      if (turnoDetalle === solicitudDetalle) {
        mostrarMensaje(mensaje, error.message, true);
      }
    } finally {
      guardando = false;
      boton.disabled = false;
      boton.textContent = paso.boton;
    }
  });
}

function agregarFormularioCostoReal(orden, turnoDetalle) {
  if (!["listo", "entregado"].includes(orden.estado)) return;

  const formulario = elemento("form");
  formulario.className = "formulario-costo";

  const campo = elemento("div");
  campo.className = "campo";

  const etiqueta = elemento("label", "Importe final cobrado (S/)");
  const entrada = elemento("input");

  entrada.id = `costo-real-${orden.id}`;
  entrada.type = "number";
  entrada.min = "0";
  entrada.step = "0.01";
  entrada.required = true;
  entrada.value = orden.costo_real ?? "";

  etiqueta.htmlFor = entrada.id;
  campo.append(etiqueta, entrada);

  const boton = elemento("button", "Guardar costo real");
  boton.type = "submit";

  const mensaje = elemento("p");
  mensaje.setAttribute("role", "status");

  formulario.append(campo, boton, mensaje);
  detalle.append(formulario);

  let guardando = false;

  formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();

    if (guardando || turnoDetalle !== solicitudDetalle) return;
    if (!formulario.reportValidity()) return;

    const importe = Number(entrada.value);

    if (!Number.isFinite(importe) || importe < 0) {
      mostrarMensaje(
        mensaje,
        "Ingresa un importe válido igual o mayor que cero.",
        true
      );
      return;
    }

    guardando = true;
    entrada.disabled = true;
    boton.disabled = true;
    boton.textContent = "Guardando…";
    mostrarMensaje(mensaje, "Guardando costo real…");

    try {
      let respuesta;

      try {
        respuesta = await fetch(`/ordenes/${orden.id}/costo-real`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            costo_real: importe,
          }),
        });
      } catch {
        throw new Error(
          "No se pudo confirmar el guardado. " +
          "Vuelve a abrir la ficha para comprobar el importe."
        );
      }

      if (!respuesta.ok) {
        const error = await respuesta.json().catch(() => ({}));

        throw new Error(
          typeof error.detail === "string"
            ? error.detail
            : `No se pudo confirmar el cambio (HTTP ${respuesta.status}). ` +
              "Vuelve a abrir la ficha para revisar el importe."
        );
      }

      if (turnoDetalle !== solicitudDetalle) return;

      mostrarMensaje(mensaje, "Costo real guardado.");
      await verDetalle(orden.id);
    } catch (error) {
      if (turnoDetalle === solicitudDetalle) {
        mostrarMensaje(mensaje, error.message, true);
      }
    } finally {
      guardando = false;
      entrada.disabled = false;
      boton.disabled = false;
      boton.textContent = "Guardar costo real";
    }
  });
}

async function agregarComparacion(orden, turnoDetalle) {
  if (!["listo", "entregado"].includes(orden.estado)) return;

  const seccion = elemento("section");
  seccion.className = "comparacion-servicio";

  const titulo = elemento("h3", "Diferencia frente a lo estimado");
  const mensaje = elemento("p", "Cargando comparación…");
  mensaje.setAttribute("role", "status");

  seccion.append(titulo, mensaje);
  detalle.append(seccion);

  try {
    const datos = await consultar(`/ordenes/${orden.id}/comparacion`);

    if (turnoDetalle !== solicitudDetalle) return;

    const lista = elemento("dl");

    lista.append(
      elemento("dt", "Diferencia de costo"),
      elemento(
        "dd",
        datos.costo_soles.diferencia == null
          ? "Pendiente: falta el costo estimado o real."
          : costo(datos.costo_soles.diferencia)
      ),
      elemento("dt", "Diferencia de tiempo"),
      elemento(
        "dd",
        datos.tiempo_dias.diferencia == null
          ? "Pendiente: falta el tiempo estimado o real."
          : dias(datos.tiempo_dias.diferencia)
      )
    );

    seccion.append(
      lista,
      elemento(
        "p",
        "Diferencia = valor real menos estimado. " +
        "Un valor positivo indica que se superó la estimación; " +
        "uno negativo indica que el valor real fue menor."
      )
    );

    mostrarMensaje(mensaje, "");
  } catch (error) {
    if (turnoDetalle !== solicitudDetalle) return;

    mostrarMensaje(
      mensaje,
      `${error.message} Vuelve a abrir la ficha para consultar la comparación.`,
      true
    );
  }
}

const dniCliente = document.querySelector("#dni-cliente");
const buscarCliente = document.querySelector("#buscar-cliente");
const resultadoCliente = document.querySelector("#resultado-cliente");

let solicitudCliente = 0;
let clienteSeleccionado = null;
let equiposDelCliente = new Set();

function vaciarEquipos(texto) {
  const opcion = elemento("option", texto);
  opcion.value = "";
  equipoInput.replaceChildren(opcion);
}

function limpiarSeleccionCliente() {
  solicitudCliente++;
  clienteSeleccionado = null;
  equiposDelCliente = new Set();

  vaciarEquipos("Primero busca un cliente");
  mostrarMensaje(resultadoCliente, "");

  buscarCliente.disabled = false;
  buscarCliente.textContent = "Buscar cliente";
}

dniCliente.addEventListener("input", limpiarSeleccionCliente);
formularioOrden.addEventListener("reset", limpiarSeleccionCliente);

buscarCliente.addEventListener("click", async () => {
  if (guardandoOrden || buscarCliente.disabled) return;
  if (!dniCliente.reportValidity()) return;

  const dni = dniCliente.value.trim();
  const turno = ++solicitudCliente;

  clienteSeleccionado = null;
  equiposDelCliente = new Set();
  vaciarEquipos("Buscando equipos…");

  buscarCliente.disabled = true;
  buscarCliente.textContent = "Buscando…";
  mostrarMensaje(resultadoCliente, "Buscando cliente y equipos…");

  try {
    const clientes = await consultar(
      `/clientes?dni=${encodeURIComponent(dni)}`
    );

    if (turno !== solicitudCliente) return;

    const cliente = clientes.find((item) => item.dni === dni);

    if (!cliente) {
      vaciarEquipos("No hay cliente seleccionado");
      mostrarMensaje(
        resultadoCliente,
        "No existe un cliente registrado con ese DNI.",
        true
      );
      return;
    }

    const equipos = [];
    let desplazamiento = 0;

    // Recuperamos todos sus equipos, incluso si superan una página.
    while (true) {
      const pagina = await consultar(
        `/equipos?cliente_id=${cliente.id}` +
        `&limite=100&desplazamiento=${desplazamiento}`
      );

      if (turno !== solicitudCliente) return;

      equipos.push(...pagina);

      if (pagina.length < 100) break;
      desplazamiento += 100;
    }

    if (equipos.length === 0) {
      vaciarEquipos("El cliente no tiene equipos registrados");
      mostrarMensaje(
        resultadoCliente,
        `${cliente.nombre}: primero debes registrar un equipo.`
      );
      return;
    }

    vaciarEquipos("Selecciona un equipo");

    for (const equipo of equipos) {
      const opcion = elemento(
        "option",
        `${equipo.tipo} — ${equipo.marca} ${equipo.modelo}` +
        ` — Serie: ${equipo.serie ?? "sin registrar"}` +
        ` — Equipo #${equipo.id}`
      );

      opcion.value = equipo.id;
      equipoInput.append(opcion);
    }

    clienteSeleccionado = cliente;
    equiposDelCliente = new Set(equipos.map((equipo) => equipo.id));

    mostrarMensaje(
      resultadoCliente,
      `Cliente: ${cliente.nombre}. ` +
      `${equipos.length} equipo(s) disponibles.`
    );
  } catch (error) {
    if (turno !== solicitudCliente) return;

    vaciarEquipos("Vuelve a buscar el cliente");
    mostrarMensaje(
      resultadoCliente,
      `${error.message} Puedes volver a buscar.`,
      true
    );
  } finally {
    if (turno === solicitudCliente) {
      buscarCliente.disabled = false;
      buscarCliente.textContent = "Buscar cliente";
    }
  }
});

function configurarRegistro(
  formularioId,
  ruta,
  prepararDatos,
  mensajeExito
) {
  const formulario = document.getElementById(formularioId);
  const campos = formulario.querySelector("fieldset");
  const boton = formulario.querySelector('button[type="submit"]');
  const mensaje = formulario.querySelector('[role="status"]');
  const textoBoton = boton.textContent;

  let guardando = false;

  formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();

    if (guardando || !formulario.reportValidity()) return;

    // Leemos los campos antes de deshabilitarlos.
    const valores = Object.fromEntries(new FormData(formulario));

    for (const nombre of Object.keys(valores)) {
      valores[nombre] = valores[nombre].trim();
    }

    guardando = true;
    campos.disabled = true;
    boton.textContent = "Guardando…";
    mostrarMensaje(mensaje, "Comprobando y guardando los datos…");

    try {
      const datos = await prepararDatos(valores);

      let respuesta;

      try {
        respuesta = await fetch(ruta, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(datos),
        });
      } catch {
        throw new Error(
          "No se pudo confirmar el guardado. Busca el cliente y sus " +
          "equipos en “Nueva orden” antes de volver a enviar."
        );
      }

      if (!respuesta.ok) {
        const error = await respuesta.json().catch(() => ({}));

        if (respuesta.status >= 500) {
          throw new Error(
            "El servidor tuvo un problema. Comprueba si el registro " +
            "aparece antes de volver a enviarlo."
          );
        }

        throw new Error(
          typeof error.detail === "string"
            ? error.detail
            : "Revisa los campos obligatorios y el formato de los datos."
        );
      }

      let registro;

      try {
        registro = await respuesta.json();

        if (!Number.isSafeInteger(registro.id)) {
          throw new Error("Respuesta incompleta");
        }
      } catch {
        throw new Error(
          "El servidor aceptó la solicitud, pero no pudimos leer " +
          "el resultado. Busca el registro antes de volver a enviarlo."
        );
      }

      formulario.reset();
      mostrarMensaje(mensaje, mensajeExito(registro, valores));
    } catch (error) {
      mostrarMensaje(mensaje, error.message, true);
    } finally {
      guardando = false;
      campos.disabled = false;
      boton.textContent = textoBoton;
    }
  });
}

configurarRegistro(
  "alta-cliente",
  "/clientes",

  async (valores) => {
    if (!valores.nombre || !valores.telefono) {
      throw new Error(
        "El nombre y el teléfono no pueden contener solo espacios."
      );
    }

    return {
      nombre: valores.nombre,
      dni: valores.dni,
      telefono: valores.telefono,
      email: valores.email || null,
    };
  },

  (cliente) =>
    `Cliente #${cliente.id}: ${cliente.nombre}, registrado correctamente. ` +
    `Ahora puedes registrar su equipo usando el DNI ${cliente.dni}.`
);

configurarRegistro(
  "alta-equipo",
  "/equipos",

  async (valores) => {
    if (!valores.marca || !valores.modelo) {
      throw new Error(
        "La marca y el modelo no pueden contener solo espacios."
      );
    }

    const clientes = await consultar(
      `/clientes?dni=${encodeURIComponent(valores.dni)}`
    );

    const cliente = clientes.find(
      (item) => item.dni === valores.dni
    );

    if (!cliente) {
      throw new Error(
        "No existe un cliente con ese DNI. Registra primero al propietario."
      );
    }

    return {
      cliente_id: cliente.id,
      tipo: valores.tipo,
      marca: valores.marca,
      modelo: valores.modelo,
      serie: valores.serie || null,
    };
  },

  (equipo, valores) =>
    `Equipo #${equipo.id}: ${equipo.marca} ${equipo.modelo}, ` +
    `registrado correctamente. En “Nueva orden”, busca el DNI ` +
    `${valores.dni} para seleccionarlo.`
);

filtroEstado.addEventListener("change", () => {
  paginaActual = 0;
  hayPaginaSiguiente = false;

  indicadorPagina.textContent = "Página 1";
  tabla.replaceChildren();

  cargarOrdenes(0);
});

function agregarHistorialEstimaciones(orden, turnoDetalle) {
  const seccion = elemento("section");
  seccion.className = "historial-estimaciones";

  const titulo = elemento("h3", "Historial de estimaciones");

  const explicacion = elemento(
    "p",
    "Cada registro conserva los datos utilizados en ese cálculo. " +
    "La estimación vigente se muestra en “Estimaciones y resultados”."
  );

  const mensaje = elemento("p");
  mensaje.setAttribute("role", "status");

  const lista = elemento("ol");
  lista.className = "lista-estimaciones";

  const boton = elemento("button", "Cargar más");
  boton.type = "button";
  boton.hidden = true;

  seccion.append(titulo, explicacion, mensaje, lista, boton);
  detalle.append(seccion);

  let desplazamiento = 0;
  let cargando = false;

  function crearRegistro(registro) {
    const item = elemento("li");
    const entrada = registro.datos_entrada;

    item.append(
      elemento("strong", `Cálculo del ${fecha(registro.fecha)}`),
      elemento(
        "p",
        `${dias(registro.tiempo_estimado_dias)} · ` +
        costo(registro.costo_estimado)
      )
    );

    const resumen = elemento("dl");

    for (const [nombre, valor] of [
      ["Categoría utilizada", entrada.categoria_falla?.replaceAll("_", " ")],
      ["Técnico", entrada.tecnico],
      ["Tipos de repuesto previstos", entrada.num_repuestos],
    ]) {
      resumen.append(
        elemento("dt", nombre),
        elemento("dd", valor ?? "Sin registrar")
      );
    }

    item.append(resumen);

    const ampliacion = elemento("details");
    ampliacion.append(elemento("summary", "Ver datos completos del cálculo"));

    const datos = elemento("dl");

    for (const [nombre, valor] of [
      ["Identificador del cálculo", registro.id],
      ["Tipo de equipo", entrada.tipo_equipo],
      ["Marca", entrada.marca],
      ["Experiencia del técnico (años)", entrada.anios_experiencia],
      ["Prioridad", entrada.prioridad],
      ["Huella del modelo de tiempo", registro.modelo_tiempo_sha256],
      ["Huella del modelo de costo", registro.modelo_costo_sha256],
    ]) {
      datos.append(
        elemento("dt", nombre),
        elemento("dd", valor ?? "Sin registrar")
      );
    }

    ampliacion.append(datos);
    item.append(ampliacion);

    return item;
  }

  async function cargar() {
    if (cargando || turnoDetalle !== solicitudDetalle) return;

    cargando = true;
    boton.disabled = true;
    mostrarMensaje(mensaje, "Cargando historial…");

    try {
      const registros = await consultar(
        `/ordenes/${orden.id}/estimaciones` +
        `?limite=21&desplazamiento=${desplazamiento}`
      );

      if (turnoDetalle !== solicitudDetalle) return;

      const pagina = registros.slice(0, 20);

      for (const registro of pagina) {
        lista.append(crearRegistro(registro));
      }

      desplazamiento += pagina.length;
      boton.hidden = registros.length <= 20;
      boton.textContent = "Cargar más";

      let texto = `${desplazamiento} cálculo(s) mostrados, del más antiguo al más reciente.`;

      if (desplazamiento === 0) {
        texto = orden.tiempo_estimado_dias != null ||
                orden.costo_estimado != null
          ? "Esta orden tiene una estimación sin registro histórico."
          : "Todavía no hay estimaciones registradas.";
      }

      mostrarMensaje(mensaje, texto);
    } catch (error) {
      if (turnoDetalle !== solicitudDetalle) return;

      mostrarMensaje(mensaje, error.message, true);
      boton.hidden = false;
      boton.textContent = "Reintentar carga";
    } finally {
      cargando = false;
      boton.disabled = false;
    }
  }

  boton.addEventListener("click", cargar);
  cargar();
}