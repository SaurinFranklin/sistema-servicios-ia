# Sistema de servicios técnicos con IA

Prototipo desarrollado individualmente para gestionar servicios técnicos
de laptops, computadoras e impresoras.

Permite registrar clientes y equipos, gestionar órdenes de servicio,
consultar sugerencias de fallas y estimar tiempo y costo.

La IA brinda apoyo al diagnóstico. El técnico selecciona la categoría
confirmada y registra sus hallazgos.

## Estado del proyecto

El flujo principal está implementado y fue probado manualmente desde
la interfaz web y Swagger.

Fecha de esta revisión: 2 de noviembre de 2026.

El sistema utiliza datos de prueba y modelos entrenados con datos
sintéticos. Sus resultados no constituyen una validación en un taller real.

## Tecnologías

- Backend: Python y FastAPI.
- Persistencia: SQLite y SQLAlchemy.
- Interfaz: HTML, CSS y JavaScript.
- Clasificación de texto: BETO, PyTorch, Transformers y scikit-learn.
- Estimación de tiempo y costo: modelos de regresión XGBoost.
- Exploración y entrenamiento: notebooks de Jupyter.

El entorno utilizado durante el desarrollo emplea Python 3.14.4 y
PyTorch para CPU.

## Funciones implementadas

- Registro de clientes con validación de DNI duplicado.
- Registro de equipos asociados a un cliente.
- Búsqueda de clientes por DNI.
- Selección de equipos del cliente al crear una orden.
- Creación y consulta de órdenes.
- Listado paginado y filtro por estado.
- Búsqueda de órdenes por identificador.
- Ficha con cliente, equipo, técnico e historial.
- Consulta de las tres categorías sugeridas por la IA.
- Asignación de técnico y confirmación de categoría.
- Registro y consulta de observaciones técnicas.
- Estimación de tiempo y costo.
- Avance de estados del servicio.
- Registro de fecha de entrega y cálculo del tiempo real.
- Registro del importe final cobrado.
- Comparación entre valores estimados y reales.

## Organización del proyecto

```text
backend/
  main.py             Aplicación FastAPI y publicación del frontend
  database.py         Conexión y sesiones de base de datos
  models.py           Modelos de las tablas
  crear_bd.py         Creación de tablas faltantes
  clientes.py         Operaciones de clientes
  equipos.py          Operaciones de equipos
  tecnicos.py         Consulta de técnicos
  ordenes.py          Flujo de órdenes y consultas relacionadas
  clasificador.py     Inferencia con BETO y el clasificador
  estimador.py        Inferencia de tiempo y costo

frontend/
  index.html          Estructura de la interfaz
  estilos.css         Estilos y adaptación a pantallas pequeñas
  app.js              Consultas a la API e interacción

ml/
  notebooks/          Exploración, entrenamiento y evaluación
  models/             Modelos y configuración guardados
  data/               Datos utilizados en los experimentos
  resultados/         Resultados de evaluación
  training/           Código de generación de datos sintéticos
```

## Ejecución en el entorno de desarrollo existente

Esta guía corresponde al entorno local ya configurado. No describe
todavía una instalación desde cero en otra computadora.

En una terminal de Ubuntu/WSL:

```bash
cd /home/saurin/sistema-servicios-ia/backend
/home/saurin/sistema-servicios-ia/backend/venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Esperar el mensaje:

```text
Application startup complete.
```

Abrir en el navegador:

- Interfaz: http://127.0.0.1:8000/app/
- Documentación de la API: http://127.0.0.1:8000/docs

Mantener la terminal abierta mientras se utiliza la aplicación.
Para detener el servidor, presionar Ctrl + C.

Si los cambios del frontend no aparecen, recargar con Ctrl + F5.

### Archivos necesarios

El entorno de desarrollo utiliza:

- La base de datos `backend/servicios.db`.
- El modelo de tiempo `ml/models/modelo_tiempo.pkl`.
- El modelo de costo `ml/models/modelo_costo.pkl`.
- La carpeta `ml/models/clasificador_beto_v1/beto/`.
- El archivo `ml/models/clasificador_beto_v1/clasificador.joblib`.
- El archivo `ml/models/clasificador_beto_v1/configuracion.json`.

La clasificación carga BETO desde archivos locales.

El script `crear_bd.py` crea las tablas que faltan. No reemplaza una
herramienta de migraciones ni agrega columnas a tablas ya existentes.

## Flujo de uso

1. Registrar al cliente si todavía no existe.
2. Registrar su equipo.
3. Buscar al cliente por DNI y seleccionar el equipo.
4. Crear una orden con la descripción del problema.
5. Consultar las sugerencias de IA.
6. Seleccionar al técnico y confirmar la categoría de falla.
7. Registrar observaciones técnicas.
8. Indicar los tipos de repuesto previstos y calcular la estimación.
9. Avanzar por reparación, servicio listo y entrega.
10. Registrar el importe final cobrado y consultar la comparación.

Los estados siguen esta secuencia:

```text
Recibido → Diagnóstico → En reparación → Listo → Entregado
```

La confirmación del diagnóstico realiza el paso de Recibido a Diagnóstico.
Los botones de avance gestionan las etapas posteriores.

## Reglas del sistema

- El DNI debe tener ocho dígitos y no puede repetirse.
- Las descripciones y observaciones no pueden contener solo espacios.
- Una orden debe estar vinculada a un equipo existente.
- La IA no confirma automáticamente la categoría de falla.
- El diagnóstico puede modificarse en Recibido o Diagnóstico.
- Cambiar el técnico o la categoría deja las estimaciones pendientes
  de recalcular.
- Las estimaciones se calculan únicamente en Diagnóstico, con categoría
  confirmada y técnico asignado.
- Las observaciones se registran en Diagnóstico, En reparación o Listo.
- El costo real se registra cuando la orden está Lista o Entregada.
- El costo real no puede ser negativo.
- No se permiten saltos ni retrocesos en el flujo de estados.
- Al registrar la entrega se guarda su fecha y se calcula el tiempo real.

## Descripción del cliente y observaciones técnicas

La descripción inicial conserva lo reportado por el cliente.

Las observaciones técnicas se almacenan por separado, con el identificador
del técnico asignado y la fecha de registro. Una orden puede tener varias.

Elegir un técnico en la interfaz registra su asignación; no autentica
la identidad de la persona que está utilizando el sistema.

## Modelos de inteligencia artificial

### Clasificación de fallas

El prototipo utiliza el modelo:

```text
dccuchile/bert-base-spanish-wwm-cased
```

BETO funciona como extractor fijo de representaciones de texto. Se utiliza
el promedio de los vectores de tokens, excluyendo el padding, y una
regresión logística clasifica el vector resultante.

No se realizó ajuste fino de BETO para este prototipo.

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

Las puntuaciones permiten ordenar sugerencias. No se han validado como
porcentajes de certeza del diagnóstico.

### Resultados de clasificación registrados durante el desarrollo

| Evaluación | Modelo | Resultado |
|---|---|---:|
| Prueba manual de 29 frases | TF-IDF | 14/29, aproximadamente 48.28 % |
| Prueba manual de 29 frases | BETO fijo | 17/29, aproximadamente 58.62 % |
| Prueba sintética | BETO fijo | 95.88 % |
| Validación por familias de 20 frases | TF-IDF | 2/20, 10 % |
| Validación por familias de 20 frases | BETO fijo | 8/20, 40 % |

En la evaluación sintética, 504 de los 800 textos de prueba también
estaban presentes en entrenamiento: un 63 %.

La evaluación por familias utilizó otro conjunto pequeño, con 59 frases
de entrenamiento y 20 de validación. Sus resultados no son directamente
comparables con los del experimento de mayor tamaño.

Estas evaluaciones muestran que el rendimiento con datos sintéticos
no representa necesariamente el rendimiento con descripciones nuevas.

### Estimación de tiempo y costo

Los modelos utilizan:

- Tipo de equipo.
- Marca.
- Categoría confirmada.
- Técnico.
- Años de experiencia del técnico.
- Número de tipos de repuesto previstos.
- Prioridad.

El tiempo estimado representa la duración total prevista desde el ingreso
hasta la entrega. No representa horas efectivas de reparación ni días
restantes desde que se pulsa el botón de estimación.

El campo de repuestos cuenta tipos distintos: teclado y batería equivalen
a dos tipos, independientemente de la cantidad de unidades.

El costo real representa el importe final cobrado por el servicio.
No es una medida de los gastos internos del taller.

## Pruebas manuales realizadas

Se comprobó el recorrido desde el registro del cliente hasta la entrega,
incluyendo observaciones, estimaciones y costo final.

También se verificaron búsqueda por DNI, selección de equipos,
paginación, búsqueda de órdenes y filtro por estado.

Las siguientes pruebas de la API fueron ejecutadas manualmente por el
desarrollador desde Swagger:

| Caso | Respuesta esperada | Resultado reportado |
|---|---:|---|
| Descripción compuesta solo por espacios | 422 | Correcto |
| DNI duplicado | 409 | Correcto |
| Orden inexistente | 404 | Correcto |
| Retroceder de Entregado a En reparación | 409 | Correcto |
| Costo real negativo | 422 | Correcto |
| Observación posterior a la entrega | 409 | Correcto |

Después de las pruebas, se consultó la orden 4006 y se comprobó que
conservaba su estado, costo real, observación original e historial.

### Ejemplo de cierre de una orden de prueba

La orden 4006 presentó estos valores:

| Concepto | Estimado | Real | Diferencia |
|---|---:|---:|---:|
| Tiempo en días | 1.84 | 0.0769 | -1.7631 |
| Costo en soles | 116.61 | 130.00 | 13.39 |

La diferencia se calcula como:

```text
Diferencia = valor real − valor estimado
```

Un resultado positivo indica que el valor real fue mayor que el estimado.
Un resultado negativo indica que fue menor.

Esta orden se completó como parte de una demostración. Su duración y costo
no constituyen una evaluación del modelo en una reparación real.

## Limitaciones actuales

- Se trata de un prototipo local.
- No se ha implementado inicio de sesión ni control de permisos por rol.
- Los modelos se entrenaron con datos sintéticos y tienen errores conocidos.
- Los registros nuevos no reentrenan automáticamente los modelos.
- Las pruebas documentadas son manuales; no constituyen una suite automatizada.
- El bloqueo de botones evita clics repetidos durante una solicitud,
  pero no garantiza evitar duplicados ante todos los fallos de red.
- No se han validado despliegue público, carga concurrente ni uso productivo.
- Falta documentar y comprobar una instalación limpia en otra computadora.
- Las estimaciones guardadas no incluyen todavía la versión del modelo
  ni una copia completa de las entradas utilizadas para calcularlas.

## Próximas mejoras

- Automatizar las pruebas principales de la API.
- Documentar dependencias y reproducción del entorno.
- Implementar autenticación y permisos.
- Registrar la versión del modelo y las entradas de cada estimación.
- Ampliar los datos con casos revisados por técnicos.
- Evaluar con datos independientes, evitando compartir casos relacionados
  entre entrenamiento y prueba.