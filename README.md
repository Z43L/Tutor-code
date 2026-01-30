# Tutor TUI - Tutor de Cursos Técnicos con IA Local

Aplicación CLI/TUI para aprender tecnología con un tutor basado en LLM local (Ollama).

## Características

- **Offline-first**: Todo funciona sin internet usando modelos locales vía Ollama
- **Generación de cursos**: Crea cursos completos a partir de un tema
- **Material educativo extenso**: Unidades en Markdown con ejemplos y ejercicios
- **Tutor conversacional**: Chat interactivo con contexto del material
- **Labs prácticos**: Ejercicios en editor (vim/nvim) con corrección automática y generación con IA (Ollama)
- **Progreso persistente**: Guarda estado localmente, exporta/importa cursos
- **Evaluación automática**: Tests y feedback detallado
- **Soporte multi-lenguaje en labs**: Python, JS/TS, C, C++, Go, Java, SQL (y más) con tipos de lab `full`, `bugfix`, `fill`

## Requisitos

- Python 3.11+
- Ollama instalado y corriendo localmente
- vim/nvim para labs prácticos

## Instalación

```bash
# Clonar o copiar el proyecto
cd tutor-tui

# Instalar dependencias
pip install -e .

# O con requirements.txt
pip install -r requirements.txt
```

## Uso

```bash
# Iniciar la aplicación
tutor

# O con argumentos
tutor --help
```

### Comandos principales

| Comando | Descripción |
|---------|-------------|
| `new` | Crear nuevo curso (wizard interactivo) |
| `resume` | Listar y reanudar cursos existentes |
| `unit <n>` | Cambiar a unidad N |
| `read` | Ver material de la unidad actual |
| `ask <pregunta>` | Preguntar al tutor |
| `quiz` | Iniciar quiz de la unidad |
| `lab` | Listar labs disponibles |
| `edit` | Abrir editor en el lab actual |
| `submit` | Evaluar lab y ver feedback |
| `progress` | Ver progreso del curso |
| `export` | Exportar curso a ZIP |
| `import <zip>` | Importar curso desde ZIP |
| `help` | Mostrar ayuda |
| `quit` | Salir |

### Variables de entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `OLLAMA_HOST` | URL del servidor Ollama | `http://localhost:11434` |
| `OLLAMA_MODEL` | Modelo por defecto | `llama3.1` |
| `EDITOR` | Editor para labs | `nvim` |
| `TUTOR_DATA_DIR` | Directorio de datos | `~/.local/share/tutor-tui` |

## Tutorial rápido

1. **Inicia la app**
   ```bash
   tutor
   ```
   Verás el banner y el prompt. Todos los comandos llevan `/` al inicio.

2. **Crea un curso**
   ```text
   /new
   ```
   - Tema, nivel y stack a tu elección.
   - Semanas: de 2 a 100.
   - El curso se genera con Ollama; si no hay IA, se usa un esquema básico.

3. **Lee el material**
   ```text
   /read
   ```
   - Navega por páginas con Enter/n (siguiente), p (anterior), número (ir a página), q (salir).
   - Pantalla se limpia y muestra el banner en cada paso.

4. **Cambia de unidad**
   ```text
   /unit 2
   ```

5. **Crea/abre un lab**
   ```text
   /lab lab02 bugfix lang=cpp
   ```
   - `lab_type`: `full` (archivo vacío en submission), `bugfix` (código roto), `fill` (TODOs).
   - `lang`: python, javascript/typescript, c, cpp, go, java, sql, etc.
   - Si Ollama está disponible, el lab (README, starter, tests) se genera con IA usando el contexto de la unidad; `submission/` no trae la solución en `full`.

6. **Edita**
   ```text
   /edit
   ```
   Abre el editor en `submission/`.

7. **Evalúa**
   ```text
   /submit
   ```
   Corre los tests del lab y muestra feedback.

8. **Pregunta al tutor**
   ```text
   ¿Qué es un iterador en Python?
   ```
   (sin `/`, es una pregunta al tutor con contexto de la unidad).

9. **Exporta/importa**
   ```text
   /export
   /import ruta/del/zip
   ```

Para un tutorial más detallado, consulta `docs/USAGE.md`.

## Estructura de cursos

```
courses/
  <course_slug>/
    course.yaml          # Metadata del curso
    state.json           # Estado del estudiante
    units/
      01-<slug>/
        material.md      # Contenido educativo
        quiz.json        # Preguntas
        labs/
          lab-01/
            README.md    # Enunciado
            starter/     # Archivos iniciales
            submission/  # Trabajo del estudiante
            tests/       # Tests de evaluación
            grade.json   # Resultados
    history/
      chat.jsonl         # Historial de chat
```

## Arquitectura

```
src/tutor_tui/
├── tui/           # Interfaz textual (Textual)
├── core/          # Lógica central, estado, persistencia
├── llm/           # Cliente Ollama, prompts
├── content/       # Generación de contenido
├── labs/          # Workspaces, evaluadores
└── export_import/ # ZIP, manifest, import
```

## Flujo de trabajo típico

1. **Iniciar**: `tutor` → aparece TUI de bienvenida
2. **Nuevo curso**: Escribe `new` → wizard de creación
3. **Generar**: El sistema genera syllabus y unidades vía Ollama
4. **Leer**: `read` para ver material de la unidad actual
5. **Practicar**: `lab` → `edit` para abrir ejercicio
6. **Evaluar**: `submit` para corrección automática
7. **Continuar**: `unit 2` para siguiente unidad
8. **Exportar**: `export` para respaldar progreso

## Tutorial completo

### Paso a paso

1) **Inicia la app**
```bash
tutor
```

2) **Crea un curso con `/new`**
- Tema, nivel y stack libres.
- Semanas entre 2 y 100.
- Si Ollama está activo, genera syllabus/material con IA; sin IA se usa un esquema básico.

3) **Lee el material con `/read`**
- Navega: Enter/n (siguiente), p (anterior), número (ir a página), q (salir).
- Cada paso limpia pantalla y reimprime banner/logo.

4) **Cambia de unidad con `/unit <n>`**

5) **Labs con `/lab`**
- Ejemplos:
  - `/lab` (abre actual o crea `lab01`)
  - `/lab lab02 full lang=python`
  - `/lab lab03 bugfix lang=cpp`
  - `/lab fill lang=typescript`
- Tipos: `full` (submission vacío/placeholder), `bugfix` (código roto), `fill` (TODOs).
- Lenguajes: python, javascript/typescript, c, cpp, go, java, sql (y otros si la IA genera archivos).
- Generación con IA: si hay Ollama, se crean README, starters y tests con contexto de la unidad. Si falla, queda la estructura vacía.

6) **Edita con `/edit`** (abre `submission/`).

7) **Evalúa con `/submit`** (ejecuta tests y muestra score/errores/sugerencias).

8) **Pregunta al tutor** escribiendo texto sin `/`; usa `/model` para ver/seleccionar modelo de Ollama.

9) **Exporta/Importa** con `/export` y `/import <zip>`.

### Tips y requisitos
- Asegura que Ollama esté corriendo y tenga el modelo configurado antes de generar cursos/labs.
- Para labs compilados (C/C++/Go/Java) necesitas toolchains instalados.
- Los comandos muestran feedback con colores (ℹ, ✓, ✗); si algo falla, revisa el mensaje y reintenta.

## Licencia

MIT
