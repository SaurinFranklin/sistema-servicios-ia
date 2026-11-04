# Sistema de servicios técnicos con IA

Prototipo desarrollado individualmente para gestionar servicios técnicos
de laptops, computadoras e impresoras.

Permite registrar clientes y equipos, gestionar órdenes, consultar
sugerencias de fallas y estimar tiempo y costo.

La IA apoya el diagnóstico. El técnico confirma la categoría y registra
sus hallazgos.

## Estado del proyecto

Revisión: 3 de noviembre de 2026.

- Flujo principal implementado en la interfaz web.
- Pruebas manuales realizadas desde la interfaz y Swagger.
- 18 pruebas automatizadas de la API aprobadas localmente.
- Automatización en GitHub Actions incluida en esta actualización;
  primera ejecución remota pendiente de verificar.

El sistema utiliza datos de prueba y modelos entrenados con datos
sintéticos. Sus resultados no equivalen a una validación en un taller real.

## Tecnologías

- Python 3.14.4.
- FastAPI, Pydantic y SQLAlchemy.
- SQLite.
- HTML, CSS y JavaScript.
- BETO, PyTorch, Transformers y scikit-learn.
- XGBoost para estimar tiempo y costo.
- unittest y TestClient para las pruebas.
- GitHub Actions para integración continua.

## Funciones implementadas

- Registro de clientes y validación de DNI duplicado.
- Registro de equipos asociados a sus propietarios.
- Búsqueda de clientes por DNI.
- Selección de equipos al crear una orden.
- Creación y consulta de órdenes.
- Paginación, búsqueda por identificador y filtro por estado.
- Ficha con cliente, equipo, técnico, observaciones e historial.
- Consulta de sugerencias de categorías de falla.
- Asignación de técnico y confirmación del diagnóstico.
- Registro de observaciones técnicas.
- Estimación de tiempo y costo.
- Avance de estados hasta la entrega.
- Cálculo del tiempo real transcurrido.
- Registro del importe final cobrado.
- Comparación entre valores estimados y reales.
- Historial de estimaciones con fecha, datos de entrada y huellas SHA-256
  de los modelos utilizados.

## Organización

```text
.github/workflows/
  pruebas.yml              Ejecución automática de pruebas

backend/
  main.py                  Aplicación FastAPI
  database.py              Conexión y sesiones
  models.py                Modelos de las tablas
  crear_bd.py              Creación de tablas faltantes
  clientes.py              Operaciones de clientes
  equipos.py               Operaciones de equipos
  tecnicos.py              Consulta de técnicos
  ordenes.py               Flujo de órdenes
  clasificador.py          Inferencia de categorías
  estimador.py             Inferencia de tiempo y costo
  test_validaciones.py     Suite automatizada de la API
  requirements.txt         Registro del entorno de desarrollo
  requirements-ci.txt      Dependencias para ejecutar las pruebas en CI

frontend/
  index.html               Estructura de la interfaz
  estilos.css              Estilos
  app.js                   Interacción con la API

ml/
  notebooks/               Exploración, entrenamiento y evaluación
  models/                  Modelos guardados
  data/                    Datos de los experimentos
  resultados/              Resultados de evaluación
  training/                Generación de datos sintéticos
```

## Ejecución local

Estos comandos corresponden al entorno de desarrollo ya configurado
en Ubuntu/WSL.

```bash
cd /home/saurin/sistema-servicios-ia/backend
/home/saurin/sistema-servicios-ia/backend/venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Esperar el mensaje `Application startup complete`.

- Interfaz: http://127.0.0.1:8000/app/
- Swagger: http://127.0.0.1:8000/docs

Mantener abierta la terminal. Para detener el servidor, presionar Ctrl + C.
Si los cambios de la interfaz no aparecen, recargar con Ctrl + F5.

### Datos y modelos necesarios

La ejecución completa utiliza:

- `backend/servicios.db`.
- `ml/models/modelo_tiempo.pkl`.
- `ml/models/modelo_costo.pkl`.
- La carpeta `ml/models/clasificador_beto_v1/beto/`, incluidos sus pesos.
- `ml/models/clasificador_beto_v1/clasificador.joblib`.
- `ml/models/clasificador_beto_v1/configuracion.json`.

La base local y algunos archivos de modelos están excluidos de Git.
Por tanto, clonar el repositorio no proporciona todos los archivos
necesarios para ejecutar la inferencia real.

`crear_bd.py` crea tablas faltantes; no agrega columnas a tablas existentes.
Los scripts de generación de datos deben revisarse antes de ejecutarlos:
el generador de entrenamiento incluye recreación de tablas.

`requirements.txt` registra los paquetes del entorno de desarrollo.
No constituye por sí solo una guía de instalación reproducible.
La instalación limpia de la aplicación completa sigue pendiente
de documentar y verificar.

## Flujo de trabajo

1. Registrar al cliente y su equipo.
2. Crear la orden con la descripción del cliente.
3. Consultar las sugerencias de IA.
4. Asignar técnico y confirmar la categoría.
5. Registrar observaciones.
6. Indicar los tipos de repuesto previstos y calcular estimaciones.
7. Registrar reparación, servicio listo y entrega.
8. Guardar el importe final y consultar las diferencias.

```text
Recibido → Diagnóstico → En reparación → Listo → Entregado
```

La confirmación del diagnóstico realiza el primer cambio de estado.
Los botones de avance gestionan las etapas posteriores.

## Reglas principales

- DNI de ocho dígitos y sin duplicados.
- Descripciones y observaciones con contenido.
- Equipos vinculados a clientes y órdenes vinculadas a equipos existentes.
- Diagnóstico editable en Recibido o Diagnóstico.
- Cambiar técnico o categoría borra la estimación vigente de la orden,
  pero conserva los cálculos anteriores en el historial.
- Estimación disponible únicamente en Diagnóstico.
- Observaciones disponibles en Diagnóstico, En reparación y Listo.
- Costo real registrable en Listo o Entregado, con valor no negativo.
- Sin saltos ni retrocesos entre estados.
- Entrega con fecha y cálculo del tiempo real.
- Repetir la entrega conserva su fecha y el historial.

La descripción del cliente se conserva separada de las observaciones
técnicas. Cada observación registra técnico y fecha.

Seleccionar un técnico identifica la asignación, pero no autentica
a la persona que utiliza el sistema.

## Inteligencia artificial

### Clasificación

Se utiliza `dccuchile/bert-base-spanish-wwm-cased` como extractor fijo
de representaciones de texto.

Se promedian los vectores de tokens excluyendo el padding y se aplica
una regresión logística. No se realizó ajuste fino de BETO.

Las once categorías son:

- Atasco de papel.
- Batería.
- Cabezal de tinta.
- Disco duro.
- Fuente de poder.
- Fusor láser.
- Pantalla.
- Placa madre.
- Sobrecalentamiento.
- Software.
- Teclado o touchpad.

Las puntuaciones ordenan sugerencias; no se han validado como
porcentajes de certeza del diagnóstico.

### Resultados registrados

| Evaluación | Modelo | Resultado |
|---|---|---:|
| Manual: 29 frases | TF-IDF | 14/29; 48.28 % |
| Manual: 29 frases | BETO fijo | 17/29; 58.62 % |
| Prueba sintética | BETO fijo | 95.88 % |
| Validación por familias: 20 frases | TF-IDF | 2/20; 10 % |
| Validación por familias: 20 frases | BETO fijo | 8/20; 40 % |

En la prueba sintética, 504 de los 800 textos de prueba aparecían
también en entrenamiento: un 63 %.

El experimento por familias utilizó 59 frases de entrenamiento y
20 de validación. No es directamente comparable con el experimento
de mayor tamaño.

Los resultados sintéticos no representan necesariamente el desempeño
con descripciones nuevas de clientes.

### Estimaciones

Los modelos utilizan tipo de equipo, marca, categoría, técnico,
experiencia, tipos de repuesto previstos y prioridad.

El tiempo representa la duración total prevista desde el ingreso
hasta la entrega. No representa horas efectivas de reparación ni
tiempo restante desde el cálculo.

El número de repuestos representa tipos distintos:
teclado y batería equivalen a dos tipos.

El costo real representa el importe final cobrado, no los gastos
internos del taller.

## Pruebas automatizadas

La suite contiene 18 pruebas que verifican:

- Rechazo de descripciones vacías, DNI duplicado y órdenes inexistentes.
- Restricciones de estados, costos y observaciones.
- Conservación de datos al repetir una entrega.
- Guardado y recálculo de estimaciones.
- Invalidación al cambiar categoría o técnico.
- Conservación de estimaciones al repetir el mismo diagnóstico.
- Rechazo de estimaciones fuera de Diagnóstico.
- Conservación del diagnóstico al consultar sugerencias.
- Respuesta y validaciones del endpoint de clasificación.
- Comparaciones con valores pendientes, positivos, negativos y cero.
- Conservación del historial al cambiar el diagnóstico y recalcular.

Cada prueba crea una base SQLite nueva en memoria.
Las respuestas de clasificación y estimación se simulan mediante mocks.

Estas pruebas no evalúan la precisión de los modelos, la carga real de
sus pesos ni el funcionamiento de la interfaz en un navegador.

### Ejecución local de pruebas

```bash
cd /home/saurin/sistema-servicios-ia/backend
/home/saurin/sistema-servicios-ia/backend/venv/bin/python -m unittest -v test_validaciones
```

Resultado local reportado el 3 de noviembre de 2026:

```text
Ran 18 tests in 1.628s

OK
```

No es necesario iniciar Uvicorn para ejecutar la suite.

### GitHub Actions

El workflow `Pruebas de API` ejecuta la suite en Ubuntu con Python 3.14.4.

Se activa al recibir un push, un pull request o una ejecución manual.
Instala las dependencias de pruebas y PyTorch para CPU.

No necesita la base de datos local ni los archivos de los modelos.
El resultado remoto se consulta en la pestaña Actions del repositorio.

## Validación manual

Se comprobó el recorrido completo desde el registro del cliente hasta
la entrega, además de búsqueda, filtros y paginación.

En Swagger se verificaron:

| Caso | Respuesta |
|---|---:|
| Descripción vacía | 422 |
| DNI duplicado | 409 |
| Orden inexistente | 404 |
| Retroceso desde Entregado | 409 |
| Costo negativo | 422 |
| Observación después de entregar | 409 |

### Ejemplo de prueba: orden 4006

| Concepto | Estimado | Real | Diferencia |
|---|---:|---:|---:|
| Tiempo en días | 1.84 | 0.0769 | -1.7631 |
| Costo en soles | 116.61 | 130.00 | 13.39 |

```text
Diferencia = valor real − valor estimado
```

La duración y el costo de esta demostración no corresponden a una
evaluación del modelo en una reparación real.

## Limitaciones y próximos pasos

- No existe inicio de sesión ni control de permisos por rol.
- Los modelos utilizan datos sintéticos y presentan errores conocidos.
- Los registros nuevos no reentrenan automáticamente los modelos.
- Falta automatizar pruebas de la interfaz e inferencia real.
- El bloqueo de botones no garantiza evitar duplicados ante todos
  los fallos de red.
- Falta validar una instalación limpia de la aplicación completa.
- Las estimaciones no guardan todavía la versión del modelo ni una
  copia completa de sus entradas.
- Las huellas SHA-256 identifican los archivos de modelos utilizados,
  pero todavía falta archivar sus versiones para reproducir cálculos antiguos.
- Se requiere ampliar y evaluar los datos con casos independientes
  revisados por técnicos.