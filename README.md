# Agente de estudio con Google ADK

Agente de inteligencia artificial hecho con Python y **Google Agent Development Kit (ADK)** que
ayuda a un estudiante a organizar sus tareas, entregas y exámenes, y a encontrar material para
estudiar.

No es un chatbot que solo genera texto: el agente interpreta lo que le pide el usuario, decide
qué herramienta necesita, la ejecuta y arma la respuesta con los resultados. Las tareas se guardan
en un archivo, así que el agente no inventa datos: responde con lo que devuelven las herramientas.

## Problema que resuelve

Un estudiante tiene muchas entregas y exámenes de distintas materias y le cuesta llevar la cuenta.
Con el agente puede:

- Registrar una entrega o examen con su materia y fecha.
- Preguntar qué tiene pendiente, qué vence primero o qué tiene de una materia.
- Marcar una tarea como hecha.
- Pedir material o explicaciones sobre un tema para estudiar.

## Modelo

El modelo se conecta con **LiteLLM** y **Ollama**, como vimos en clase:

```python
MODELO = "ollama_chat/qwen3:4b-instruct-2507-q4_K_M"
model=LiteLlm(MODELO)
```

En clase usamos `gemma4:31b-cloud`, pero los modelos `:cloud` de Ollama piden créditos pagos.
Por eso el agente usa **Qwen3 4B Instruct**, que corre local en la computadora, sin GPU, soporta
herramientas y funciona bien en español. Se usa la versión *instruct* y no `qwen3:4b`, porque esa
es la versión de razonamiento: escribe todo lo que piensa antes de responder y tarda mucho más.

Para usar otro modelo alcanza con cambiar la variable `MODELO` en `agente_estudio/agent.py`.

## Herramientas

Están en `agente_estudio/tools/tools.py`. Cada una tiene una responsabilidad distinta y valida
sus datos antes de actuar. Todas devuelven un diccionario con un `estado` (`ok`, `vacio` o
`error`) y un `mensaje`, así el agente sabe si salió bien y qué explicarle al usuario.

| Herramienta | Qué hace | Validaciones |
|---|---|---|
| `agregar_tarea(materia, descripcion, fecha_entrega)` | Registra una tarea nueva en `tareas.json`. | Materia o descripción vacías, fecha que no respeta el formato `AAAA-MM-DD`, fecha inexistente (por ejemplo, 32/13) o que ya pasó. |
| `listar_tareas(materia, solo_pendientes)` | Devuelve las tareas ordenadas por fecha, con los días que faltan para cada una. Se puede filtrar por materia. | Si no hay tareas, o no hay de esa materia, devuelve estado `vacio`. |
| `completar_tarea(busqueda)` | Marca como completada la tarea pendiente que coincide con la materia o con palabras de la descripción, por ejemplo `"cinemática"`. | Búsqueda vacía, ninguna tarea que coincida o varias que coinciden: en ese caso devuelve las opciones para que el agente pregunte cuál es. |
| `buscar_en_internet(consulta, max_resultados)` | Busca material de estudio en internet con DuckDuckGo (`ddgs`). | Consulta vacía, `max_resultados` fuera del rango 1 a 10, búsqueda sin resultados y buscador que no responde. |

Además, cada herramienta tiene un `try/except` que atrapa cualquier error inesperado y lo
devuelve como estado `error`, para que el agente no se corte.

## Instrucciones del agente

Están en `agente_estudio/agent.py` y definen:

- **Rol:** asistente de estudio.
- **Objetivo:** organizar tareas, entregas y exámenes, y encontrar material.
- **Qué herramienta usar en cada caso**, con ejemplos. Por ejemplo, si al pedir una tarea nueva
  falta la fecha, tiene que preguntarla y no inventarla.
- **Restricciones:**
  - No inventar tareas, fechas ni resultados.
  - No decir que registró o completó una tarea si la herramienta no devolvió `ok`.
  - Pedir los datos que faltan antes de registrar una tarea.
  - Explicar los errores con palabras simples.
  - Solo ayudar con temas de estudio.

## Estructura

```text
agent_adk_dario_ruizdiaz/
├── agente_estudio/
│   ├── __init__.py
│   ├── agent.py          # Modelo, instrucciones y herramientas del agente
│   └── tools/
│       ├── __init__.py
│       └── tools.py      # Las cuatro herramientas
├── requirements.txt
└── README.md
```

`tareas.json` se crea solo dentro de `agente_estudio/` cuando se agrega la primera tarea.

## Cómo usarlo

Requisitos: Python 3.12, [uv](https://docs.astral.sh/uv/) y [Ollama](https://ollama.com).

1. Clonar el repositorio:

   ```bash
   git clone https://github.com/veyrdric/agent_adk_dario_ruizdiaz.git
   cd agent_adk_dario_ruizdiaz
   ```

2. Crear y activar el entorno virtual:

   ```bash
   uv venv --python 3.12 env
   source env/bin/activate      # En Linux
   env\Scripts\activate         # En Windows
   ```

3. Instalar las dependencias:

   ```bash
   uv pip install -r requirements.txt
   ```

4. Descargar el modelo y comprobar que Ollama está activo:

   ```bash
   ollama pull qwen3:4b-instruct-2507-q4_K_M
   ollama ls
   ```

5. Levantar la interfaz web de ADK desde la carpeta del proyecto:

   ```bash
   adk web
   ```

6. Abrir http://localhost:8000 y elegir `agente_estudio` en el selector de agentes.

## Ejemplos para probar

Cada pedido hace que el agente use una herramienta distinta:

| Pedido | Herramienta que usa |
|---|---|
| "¿Qué tareas tengo pendientes?" | `listar_tareas` (con la lista vacía, responde que no hay tareas) |
| "Agregá el examen de Física para el 2026-12-10, tengo que estudiar cinemática" | `agregar_tarea` |
| "¿Qué tengo de Física?" | `listar_tareas` con `materia="Física"` |
| "Tengo que entregar un TP de Programación" | Ninguna: pregunta la fecha antes de registrarlo |
| "Ya rendí el examen de Física, marcalo como completado" | `completar_tarea` con `busqueda="Física"` |
| "Buscame material para estudiar cinemática" | `buscar_en_internet` |
| "Agregá una tarea de Química para el 32/13/2026" | Explica que la fecha no es válida y pide otra |
| "Contame un chiste" | Ninguna: responde que solo ayuda con temas de estudio |

En la interfaz web de ADK, a la izquierda, se ven las herramientas que llamó el agente, con los
argumentos que les pasó y lo que devolvieron.
