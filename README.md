# Tutor TUI - Tutor de Cursos Técnicos con IA Local

Aplicación CLI/TUI para aprender tecnología con un tutor basado en LLM local (Ollama).

## Características

- **Offline-first**: Todo funciona sin internet usando modelos locales vía Ollama
- **Generación de cursos**: Crea cursos completos a partir de un tema
- **Material educativo extenso**: Unidades en Markdown con ejemplos y ejercicios
- **Tutor conversacional**: Chat interactivo con contexto del material
- **Labs prácticos**: Ejercicios en editor (vim/nvim) con corrección automática
- **Progreso persistente**: Guarda estado localmente, exporta/importa cursos
- **Evaluación automática**: Tests y feedback detallado

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

## Licencia

MIT
