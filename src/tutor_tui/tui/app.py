"""Aplicación TUI principal."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import (
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    RichLog,
    Static,
)

from ..config import get_config
from ..content.generator import ContentGenerationError, ContentGenerator
from ..core.persistence import CoursePersistence
from ..llm.client import OllamaClient

if TYPE_CHECKING:
    from ..core.course import Course
    from ..core.state import CourseState


class CommandInput(Input):
    """Input de comandos con historial."""

    BINDINGS = [
        ("up", "history_prev", "Previous"),
        ("down", "history_next", "Next"),
    ]

    def __init__(self) -> None:
        super().__init__(placeholder="Escribe un comando (help para ayuda)")
        self.history: list[str] = []
        self.history_index = 0

    def action_history_prev(self) -> None:
        """Navegar a comando anterior."""
        if self.history and self.history_index > 0:
            self.history_index -= 1
            self.value = self.history[self.history_index]

    def action_history_next(self) -> None:
        """Navegar a comando siguiente."""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.value = self.history[self.history_index]
        else:
            self.history_index = len(self.history)
            self.value = ""

    def add_to_history(self, cmd: str) -> None:
        """Añadir comando al historial."""
        if cmd and (not self.history or self.history[-1] != cmd):
            self.history.append(cmd)
        self.history_index = len(self.history)


class StatusBar(Static):
    """Barra de estado del curso."""

    course_name = reactive("No hay curso activo")
    current_unit = reactive("-")
    progress = reactive("0%")

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label(self.course_name, id="status-course")
            yield Label(f"  |  Unidad: {self.current_unit}", id="status-unit")
            yield Label(f"  |  Progreso: {self.progress}", id="status-progress")

    def watch_course_name(self, value: str) -> None:
        """Actualizar cuando cambia el curso."""
        label = self.query_one("#status-course", Label)
        label.update(f"Curso: {value}")

    def watch_current_unit(self, value: str) -> None:
        """Actualizar cuando cambia la unidad."""
        label = self.query_one("#status-unit", Label)
        label.update(f"  |  Unidad: {value}")

    def watch_progress(self, value: str) -> None:
        """Actualizar cuando cambia el progreso."""
        label = self.query_one("#status-progress", Label)
        label.update(f"  |  Progreso: {value}")

    def update_status(self, course: str | None, unit: int | None, prog: float | None) -> None:
        """Actualizar todos los valores."""
        self.course_name = course or "No hay curso activo"
        self.current_unit = str(unit) if unit else "-"
        self.progress = f"{prog:.0f}%" if prog is not None else "0%"


class OutputLog(RichLog):
    """Área de salida con formato Rich."""

    def __init__(self) -> None:
        super().__init__(highlight=True, markup=True, wrap=True)
        self.border_title = "Salida"

    def write_system(self, message: str) -> None:
        """Escribir mensaje del sistema."""
        self.write(f"[dim][sys][/dim] {message}")

    def write_error(self, message: str) -> None:
        """Escribir mensaje de error."""
        self.write(f"[red][error][/red] {message}")

    def write_success(self, message: str) -> None:
        """Escribir mensaje de éxito."""
        self.write(f"[green][ok][/green] {message}")

    def write_info(self, message: str) -> None:
        """Escribir información."""
        self.write(f"[blue][info][/blue] {message}")

    def write_tutor(self, message: str) -> None:
        """Escribir mensaje del tutor."""
        self.write(f"[cyan bold]Tutor:[/cyan bold] {message}")

    def write_user(self, message: str) -> None:
        """Escribir mensaje del usuario."""
        self.write(f"[yellow bold]Tú:[/yellow bold] {message}")

    def write_warning(self, message: str) -> None:
        """Escribir advertencia."""
        self.write(f"[yellow][warn][/yellow] {message}")


class CourseListScreen:
    """Pantalla de lista de cursos (implemementación simple en log por ahora)."""

    pass


class TutorApp(App):
    """Aplicación principal del Tutor TUI."""

    CSS = """
    Screen {
        align: center middle;
    }

    #main-container {
        width: 100%;
        height: 100%;
    }

    #output-panel {
        width: 100%;
        height: 1fr;
        border: solid $primary;
    }

    #status-bar {
        width: 100%;
        height: auto;
        padding: 0 1;
        background: $surface;
        color: $text;
    }

    #input-panel {
        width: 100%;
        height: auto;
        padding: 0 1;
    }

    CommandInput {
        width: 100%;
    }

    OutputLog {
        padding: 0 1;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Salir"),
        ("ctrl+q", "quit", "Salir"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.config = get_config()
        self.persistence = CoursePersistence(self.config.data_dir)
        self.content_generator = ContentGenerator()
        self.current_course: Course | None = None
        self.current_state: CourseState | None = None
        self.pending_action: str | None = None
        self.pending_data: dict | None = None

    def compose(self) -> ComposeResult:
        """Componer interfaz."""
        yield Header(show_clock=True)

        with Vertical(id="main-container"):
            yield StatusBar(id="status-bar")

            output = OutputLog(id="output-panel")
            output.border_title = "Bienvenido a Tutor TUI"
            yield output

            with Horizontal(id="input-panel"):
                yield CommandInput()

        yield Footer()

    def on_mount(self) -> None:
        """Al montar la app."""
        self.show_welcome()

    def show_welcome(self) -> None:
        """Mostrar mensaje de bienvenida."""
        log = self.query_one(OutputLog)
        log.clear()
        log.write("""
[cyan bold]╔══════════════════════════════════════════════════════════════╗
║                    Bienvenido a Tutor TUI                     ║
║              Tu tutor de programación con IA local           ║
╚══════════════════════════════════════════════════════════════╝[/cyan bold]

""")
        log.write_info("Escribe [bold]new[/bold] para crear un curso o [bold]resume[/bold] para continuar")
        log.write_info("Escribe [bold]help[/bold] para ver todos los comandos disponibles")

    def get_output_log(self) -> OutputLog:
        """Obtener el log de salida."""
        return self.query_one(OutputLog)

    def get_status_bar(self) -> StatusBar:
        """Obtener la barra de estado."""
        return self.query_one(StatusBar)

    def update_status(self) -> None:
        """Actualizar barra de estado."""
        status = self.get_status_bar()
        if self.current_course and self.current_state:
            # Calcular progreso
            total_units = len(self.current_course.units)
            completed = sum(
                1 for p in self.current_state.unit_progress.values()
                if p.status == "completed"
            )
            progress = (completed / total_units * 100) if total_units > 0 else 0
            status.update_status(
                self.current_course.metadata.title,
                self.current_state.current_unit,
                progress
            )
        else:
            status.update_status(None, None, None)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Procesar comando ingresado."""
        input_widget = self.query_one(CommandInput)
        command = event.value.strip()

        if not command:
            return

        input_widget.add_to_history(command)
        input_widget.value = ""

        log = self.get_output_log()
        log.write_user(command)

        await self.process_command(command)

    async def process_command(self, command: str) -> None:
        """Procesar comando del usuario."""
        log = self.get_output_log()
        parts = command.split()
        cmd = parts[0].lower()
        args = parts[1:]

        # Comandos disponibles
        handlers = {
            "help": self.cmd_help,
            "new": self.cmd_new,
            "resume": self.cmd_resume,
            "list": self.cmd_list,
            "quit": self.cmd_quit,
            "exit": self.cmd_quit,
            "q": self.cmd_quit,
            "unit": self.cmd_unit,
            "read": self.cmd_read,
            "ask": self.cmd_ask,
            "quiz": self.cmd_quiz,
            "lab": self.cmd_lab,
            "edit": self.cmd_edit,
            "submit": self.cmd_submit,
            "progress": self.cmd_progress,
            "export": self.cmd_export,
            "import": self.cmd_import,
            "delete": self.cmd_delete,
        }

        handler = handlers.get(cmd)
        if handler:
            await handler(args)
        else:
            log.write_error(f"Comando desconocido: {cmd}")
            log.write_info("Escribe 'help' para ver los comandos disponibles")

    # ========== Comandos ==========

    async def cmd_help(self, args: list[str]) -> None:
        """Mostrar ayuda."""
        log = self.get_output_log()
        help_text = """
[bold green]Comandos disponibles:[/bold green]

[bold]Gestión de cursos:[/bold]
  [cyan]new[/cyan]              - Crear nuevo curso (wizard)
  [cyan]resume[/cyan]           - Listar y reanudar cursos existentes
  [cyan]list[/cyan]             - Listar todos los cursos
  [cyan]delete <slug>[/cyan]    - Eliminar un curso

[bold]Navegación:[/bold]
  [cyan]unit <n>[/cyan]         - Cambiar a unidad N
  [cyan]read[/cyan]             - Leer material de la unidad actual
  [cyan]progress[/cyan]         - Ver progreso del curso

[bold]Interacción:[/bold]
  [cyan]ask <pregunta>[/cyan]   - Preguntar al tutor
  [cyan]quiz[/cyan]             - Iniciar quiz de la unidad

[bold]Práctica:[/bold]
  [cyan]lab[/cyan]              - Listar labs de la unidad
  [cyan]lab <n>[/cyan]          - Seleccionar lab N
  [cyan]edit[/cyan]             - Abrir editor en el lab actual
  [cyan]submit[/cyan]           - Evaluar y entregar lab

[bold]Import/Export:[/bold]
  [cyan]export[/cyan]           - Exportar curso a ZIP
  [cyan]import <ruta>[/cyan]    - Importar curso desde ZIP

[bold]General:[/bold]
  [cyan]help[/cyan]             - Mostrar esta ayuda
  [cyan]quit, exit, q[/cyan]    - Salir de la aplicación
"""
        log.write(help_text)

    async def cmd_new(self, args: list[str]) -> None:
        """Crear nuevo curso - wizard interactivo."""
        log = self.get_output_log()

        # Verificar conexión con Ollama primero
        log.write_info("Verificando conexión con Ollama...")
        try:
            status = await self.content_generator.check_ollama()
            if not status.get("ok"):
                log.write_error(f"No se pudo conectar con Ollama: {status.get('error')}")
                log.write_info("Asegúrate de que Ollama esté corriendo en http://localhost:11434")
                log.write_info("O ajusta OLLAMA_HOST si usas otro endpoint")
                return

            models = status.get("data", {}).get("models", [])
            if not models:
                log.write_error("Ollama está corriendo pero no hay modelos disponibles")
                log.write_info("Descarga un modelo con: ollama pull llama3.1")
                return

            model_names = [m.get("name", m.get("model", "unknown")) for m in models]
            log.write_success(f"Ollama conectado. Modelos disponibles: {', '.join(model_names[:3])}")

        except Exception as e:
            log.write_error(f"Error verificando Ollama: {e}")
            return

        log.write_info("\nCreando nuevo curso...")
        self.pending_action = "new_course_topic"
        log.write_tutor("¿Qué tema quieres aprender?")
        log.write_info("Ejemplos: Python, Rust, Docker, Kubernetes, Machine Learning, etc.")

    async def cmd_resume(self, args: list[str]) -> None:
        """Listar y cargar cursos existentes."""
        log = self.get_output_log()
        courses = self.persistence.list_courses()

        if not courses:
            log.write_info("No hay cursos guardados. Usa 'new' para crear uno.")
            return

        log.write("[bold]Cursos disponibles:[/bold]\n")
        for i, course in enumerate(courses, 1):
            status = "[green]●[/green]" if course["has_state"] else "[dim]○[/dim]"
            log.write(f"  {status} {i}. [bold]{course['title']}[/bold] ({course['slug']}) - {course['level']}")

        if len(args) >= 1:
            # Cargar curso específico
            selection = args[0]
            try:
                idx = int(selection) - 1
                if 0 <= idx < len(courses):
                    await self.load_course(courses[idx]["slug"])
                else:
                    log.write_error("Número de curso inválido")
            except ValueError:
                # Buscar por slug
                await self.load_course(selection)
        else:
            log.write_info("Escribe 'resume <número>' o 'resume <slug>' para cargar")

    async def cmd_list(self, args: list[str]) -> None:
        """Listar cursos."""
        await self.cmd_resume(args)

    async def cmd_quit(self, args: list[str]) -> None:
        """Salir de la aplicación."""
        self.exit()

    async def cmd_unit(self, args: list[str]) -> None:
        """Cambiar de unidad."""
        log = self.get_output_log()

        if not self.current_course:
            log.write_error("No hay curso activo. Usa 'resume' primero.")
            return

        if not args:
            # Listar unidades
            log.write(f"[bold]Unidades en {self.current_course.metadata.title}:[/bold]\n")
            for unit in self.current_course.units:
                log.write(f"  {unit.number}. [bold]{unit.title}[/bold]")
            log.write_info("Escribe 'unit <n>' para cambiar de unidad")
            return

        try:
            unit_num = int(args[0])
            unit = self.current_course.get_unit(unit_num)
            if unit:
                if self.current_state:
                    self.current_state.current_unit = unit_num
                    self.persistence.save_state(self.current_state)
                self.update_status()
                log.write_success(f"Unidad cambiada a: {unit.title}")
                log.write_info("Escribe 'read' para ver el material")
            else:
                log.write_error(f"Unidad {unit_num} no existe")
        except ValueError:
            log.write_error("Número de unidad inválido")

    async def cmd_read(self, args: list[str]) -> None:
        """Leer material de la unidad actual."""
        log = self.get_output_log()

        if not self.current_course or not self.current_state:
            log.write_error("No hay curso activo")
            return

        unit = self.current_course.get_current_unit(self.current_state)
        if not unit:
            log.write_error("No hay unidad activa")
            return

        if unit.material_path and unit.material_path.exists():
            content = unit.material_path.read_text(encoding="utf-8")
            log.write(f"\n[bold cyan]{'='*60}[/bold cyan]")
            log.write(f"[bold cyan]  {unit.title}[/bold cyan]")
            log.write(f"[bold cyan]{'='*60}[/bold cyan]\n")
            # Mostrar primeras 50 líneas por ahora
            lines = content.split("\n")[:50]
            log.write("\n".join(lines))
            if len(content.split("\n")) > 50:
                log.write("\n[yellow]... (usa 'read' para ver más o abre el archivo directamente)[/yellow]")
        else:
            log.write_error(f"Material no encontrado: {unit.material_path}")

    async def cmd_ask(self, args: list[str]) -> None:
        """Preguntar al tutor con contexto del material."""
        log = self.get_output_log()
        question = " ".join(args)

        if not question:
            log.write_info("Escribe 'ask <tu pregunta>' para consultar al tutor")
            return

        if not self.current_course or not self.current_state:
            log.write_info("No hay curso activo. El tutor responderá sin contexto específico.")

        # Verificar Ollama
        try:
            status = await self.content_generator.check_ollama()
            if not status.get("ok"):
                log.write_error("Ollama no está disponible. No se puede consultar al tutor.")
                log.write_info("Asegúrate de que Ollama esté corriendo")
                return
        except Exception:
            log.write_error("Error verificando Ollama")
            return

        # Preparar contexto
        context = ""
        unit_title = "N/A"
        unit_desc = "N/A"

        if self.current_course and self.current_state:
            unit = self.current_course.get_current_unit(self.current_state)
            if unit and unit.material_path and unit.material_path.exists():
                # Leer material y extraer contexto relevante
                material = unit.material_path.read_text(encoding="utf-8")
                # Extraer párrafos relevantes (heurística simple: buscar keywords)
                keywords = question.lower().split()
                relevant_lines = []
                for line in material.split("\n")[:100]:  # Limitar a primeras 100 líneas
                    line_lower = line.lower()
                    if any(kw in line_lower for kw in keywords if len(kw) > 3):
                        relevant_lines.append(line)

                context = "\n".join(relevant_lines[:20])  # Top 20 líneas relevantes
                unit_title = unit.title
                unit_desc = unit.description

        # Construir mensajes para Ollama
        from ..llm.client import Message
        from ..llm.prompts import TUTOR_SYSTEM

        system_prompt = TUTOR_SYSTEM.format(
            course_title=self.current_course.metadata.title if self.current_course else "Curso General",
            unit_title=unit_title,
            unit_description=unit_desc,
        )

        user_prompt = f"""Contexto del material:
{context[:1500]}

Pregunta del estudiante: {question}"""

        log.write_tutor("Pensando...")

        self.set_loading(True)
        try:
            messages = [
                Message(role="system", content=system_prompt),
                Message(role="user", content=user_prompt),
            ]

            response = await self.content_generator.client.chat(
                messages=messages,
                temperature=0.7,
            )

            # Mostrar respuesta
            log.write(f"\n[cyan bold]Tutor:[/cyan bold]")
            log.write(response.content)

            # Guardar en historial
            if self.current_course and self.current_state:
                self.current_state.add_chat_message("user", question)
                self.current_state.add_chat_message("assistant", response.content)
                self.persistence.save_state(self.current_state)

        except Exception as e:
            log.write_error(f"Error consultando al tutor: {e}")
        finally:
            self.set_loading(False)

    async def cmd_quiz(self, args: list[str]) -> None:
        """Iniciar quiz interactivo."""
        import json
        log = self.get_output_log()

        if not self.current_course or not self.current_state:
            log.write_error("No hay curso activo")
            return

        unit = self.current_course.get_current_unit(self.current_state)
        if not unit:
            log.write_error("No hay unidad activa")
            return

        # Cargar preguntas
        if not unit.quiz_path or not unit.quiz_path.exists():
            log.write_error("Esta unidad no tiene quiz")
            return

        try:
            questions = json.loads(unit.quiz_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError) as e:
            log.write_error(f"Error cargando quiz: {e}")
            return

        if not questions:
            log.write_error("El quiz está vacío")
            return

        log.write(f"\n[bold cyan]Quiz: {unit.title}[/bold cyan]")
        log.write(f"{len(questions)} preguntas\n")

        # Estado del quiz
        progress = self.current_state.get_or_create_unit_progress(unit.number)
        current_q = 0
        score = 0

        while current_q < len(questions):
            q = questions[current_q]
            q_id = q.get("id", f"q{current_q}")
            q_text = q.get("question", "Pregunta sin texto")
            q_type = q.get("type", "multiple_choice")
            options = q.get("options", [])
            correct = q.get("correct_answer", "")
            explanation = q.get("explanation", "")
            hint = q.get("hint", "")

            log.write(f"\n[bold]Pregunta {current_q + 1}/{len(questions)}:[/bold]")
            log.write(f"{q_text}\n")

            if q_type == "multiple_choice" and options:
                for i, opt in enumerate(options):
                    opt_text = opt.get("text", f"Opción {i+1}")
                    log.write(f"  {chr(97+i)}) {opt_text}")

            # Esperar respuesta del usuario
            log.write_info("\nEscribe tu respuesta (a, b, c...) o 'hint' para pista")
            log.write_info("Para terminar, escribe 'quiz_stop'")

            self.pending_action = "quiz_answer"
            self.pending_data = {
                "question_idx": current_q,
                "question": q,
                "score": score,
                "questions": questions,
                "progress": progress,
            }
            return  # Pausar y esperar respuesta

        # Calcular resultado final
        final_score = (score / len(questions) * 100) if questions else 0
        log.write(f"\n[bold cyan]Quiz completado[/bold cyan]")
        log.write(f"Puntuación: {final_score:.0f}% ({score}/{len(questions)})")

        # Guardar resultado
        from ..core.state import QuizResult
        quiz_result = QuizResult(
            question_id="final",
            correct=final_score >= 70,
            answer=f"{score}/{len(questions)}",
            score=final_score / 100,
        )
        progress.quiz_results.append(quiz_result)
        self.persistence.save_state(self.current_state)

        if final_score >= 70:
            log.write_success("¡Buen trabajo! Has dominado los conceptos de esta unidad.")
        else:
            log.write_info("Sigue practicando. Revisa el material con 'read' y vuelve a intentarlo.")

    async def cmd_lab(self, args: list[str]) -> None:
        """Gestionar labs."""
        log = self.get_output_log()

        if not self.current_course or not self.current_state:
            log.write_error("No hay curso activo")
            return

        unit = self.current_course.get_current_unit(self.current_state)
        if not unit:
            log.write_error("No hay unidad activa")
            return

        if not unit.labs:
            log.write_info("Esta unidad no tiene labs prácticos")
            return

        if not args:
            # Listar labs
            log.write(f"[bold]Labs en {unit.title}:[/bold]\n")
            for lab in unit.labs:
                status = ""
                if self.current_state:
                    progress = self.current_state.get_or_create_unit_progress(unit.number)
                    result = progress.lab_results.get(lab.slug)
                    if result:
                        status_map = {
                            "not_started": "[dim]○[/dim]",
                            "in_progress": "[yellow]◐[/yellow]",
                            "submitted": "[blue]●[/blue]",
                            "passed": "[green]✓[/green]",
                            "failed": "[red]✗[/red]",
                        }
                        status = f" {status_map.get(result.status, '○')}"
                log.write(f"  {status} [bold]{lab.slug}[/bold]: {lab.title} ({lab.difficulty})")
            log.write_info("Escribe 'lab <slug>' o 'lab <número>' para seleccionar")
        else:
            # Seleccionar lab
            selection = args[0]
            lab = None

            # Buscar por número
            try:
                idx = int(selection) - 1
                if 0 <= idx < len(unit.labs):
                    lab = unit.labs[idx]
            except ValueError:
                # Buscar por slug
                for l in unit.labs:
                    if l.slug == selection:
                        lab = l
                        break

            if lab:
                if self.current_state:
                    self.current_state.current_lab = lab.slug
                    self.persistence.save_state(self.current_state)
                log.write_success(f"Lab seleccionado: {lab.title}")
                log.write_info("Escribe 'edit' para abrir el editor o 'read' para ver el README")
            else:
                log.write_error(f"Lab no encontrado: {selection}")

    async def cmd_edit(self, args: list[str]) -> None:
        """Abrir editor en el lab."""
        import os
        log = self.get_output_log()

        if not self.current_course or not self.current_state:
            log.write_error("No hay curso activo")
            return

        unit = self.current_course.get_current_unit(self.current_state)
        if not unit:
            log.write_error("No hay unidad activa")
            return

        # Verificar que hay un lab seleccionado
        if not self.current_state.current_lab:
            log.write_error("No hay lab seleccionado. Usa 'lab' primero.")
            return

        # Encontrar el lab
        lab = None
        for l in unit.labs:
            if l.slug == self.current_state.current_lab:
                lab = l
                break

        if not lab:
            log.write_error(f"Lab no encontrado: {self.current_state.current_lab}")
            return

        if not lab.submission_path:
            log.write_error("Lab no tiene path de submission")
            return

        from ..labs.workspace import LabWorkspace

        workspace = LabWorkspace(lab, editor=self.config.editor)

        # Guardar hash para detectar cambios
        pre_hash = workspace.get_submission_hash()

        log.write_info(f"Abriendo editor en: {lab.submission_path}")
        log.write_info("Edita los archivos, guarda y sal del editor para continuar...")

        # Pausar TUI temporalmente y abrir editor
        self.set_loading(True)
        log.write("[dim]Editor abierto. Presiona :q para salir y continuar...[/dim]")

        # Limpiar pantalla para el editor
        if hasattr(self, 'console'):
            self.console.clear()

        # Ejecutar editor
        try:
            returncode = workspace.open_editor()

            if returncode != 0:
                log.write_warning(f"El editor cerró con código: {returncode}")

            # Verificar cambios
            post_hash = workspace.get_submission_hash()
            has_changes = pre_hash != post_hash

            if has_changes:
                log.write_success("¡Archivos modificados! Usa 'submit' para evaluar tu solución")

                # Actualizar estado
                progress = self.current_state.get_or_create_unit_progress(unit.number)
                if lab.slug not in progress.lab_results:
                    from ..core.state import LabResult
                    progress.lab_results[lab.slug] = LabResult(
                        lab_slug=lab.slug,
                        status="in_progress",
                    )
                else:
                    progress.lab_results[lab.slug].status = "in_progress"

                self.persistence.save_state(self.current_state)
            else:
                log.write_info("No se detectaron cambios en los archivos")

        except Exception as e:
            log.write_error(f"Error abriendo editor: {e}")
            log.write_info("Verifica que tengas nvim/vim instalado o configura EDITOR")
        finally:
            self.set_loading(False)
            # Refrescar pantalla
            self.refresh()

    async def cmd_submit(self, args: list[str]) -> None:
        """Evaluar lab."""
        log = self.get_output_log()

        if not self.current_course or not self.current_state:
            log.write_error("No hay curso activo")
            return

        unit = self.current_course.get_current_unit(self.current_state)
        if not unit:
            log.write_error("No hay unidad activa")
            return

        if not self.current_state.current_lab:
            log.write_error("No hay lab seleccionado. Usa 'lab <slug>' primero.")
            return

        # Encontrar lab
        lab = None
        for l in unit.labs:
            if l.slug == self.current_state.current_lab:
                lab = l
                break

        if not lab:
            log.write_error(f"Lab no encontrado: {self.current_state.current_lab}")
            return

        log.write_info(f"Evaluando lab: {lab.title}")
        log.write_info("Ejecutando tests... (esto puede tomar unos segundos)")

        self.set_loading(True)

        try:
            from ..labs.evaluator import get_evaluator

            evaluator = get_evaluator(lab)
            result = evaluator.evaluate()

            # Actualizar estado
            from ..core.state import LabResult
            progress = self.current_state.get_or_create_unit_progress(unit.number)

            lab_result = LabResult(
                lab_slug=lab.slug,
                status="passed" if result.passed else "failed",
                score=result.score,
                max_score=result.max_score,
                passed_tests=result.passed_tests,
                total_tests=result.total_tests,
                errors=result.errors,
                suggestions=result.suggestions,
            )
            progress.lab_results[lab.slug] = lab_result
            self.persistence.save_state(self.current_state)

            # Mostrar resultados
            log.write(f"\n[bold cyan]{'='*50}[/bold cyan]")
            log.write(f"[bold]Resultados de evaluación[/bold]")
            log.write(f"[bold cyan]{'='*50}[/bold cyan]\n")

            score_color = "green" if result.passed else "red"
            log.write(f"Puntuación: [{score_color}]{result.score:.1f}%[/{score_color}] / {result.max_score:.1f}%")
            log.write(f"Tests: {result.passed_tests}/{result.total_tests} pasados")
            log.write(f"Estado: [{score_color}]{'APROBADO' if result.passed else 'NO APROBADO'}[/{score_color}]")
            log.write(f"Tiempo: {result.execution_time:.2f}s")

            if result.errors:
                log.write("\n[red bold]Errores encontrados:[/red bold]")
                for i, error in enumerate(result.errors[:5], 1):
                    log.write(f"  {i}. {error[:100]}")
                if len(result.errors) > 5:
                    log.write(f"  ... y {len(result.errors) - 5} más")

            if result.warnings:
                log.write("\n[yellow bold]Advertencias:[/yellow bold]")
                for warning in result.warnings[:3]:
                    log.write(f"  ⚠ {warning}")

            if result.suggestions:
                log.write("\n[cyan bold]Sugerencias de mejora:[/cyan bold]")
                for suggestion in result.suggestions[:3]:
                    log.write(f"  💡 {suggestion}")

            # Detalle de rubrica
            if result.rubric:
                log.write("\n[dim]Desglose de puntuación:[/dim]")
                for key, value in result.rubric.items():
                    log.write(f"  {key}: {value:.1f}")

            log.write(f"\n[bold]{'='*50}[/bold]")

            if result.passed:
                log.write_success("¡Felicitaciones! Has completado este lab.")
                log.write_info("Escribe 'lab' para ver otros labs o 'unit <n>' para continuar")
            else:
                log.write_info("\nNo te desanimes. Revisa los errores y usa 'edit' para corregir.")
                log.write_info("Escribe 'ask <pregunta>' si necesitas ayuda del tutor")

        except Exception as e:
            log.write_error(f"Error evaluando: {e}")
            import traceback
            log.write(f"[dim]{traceback.format_exc()[:200]}[/dim]")
        finally:
            self.set_loading(False)

    async def cmd_progress(self, args: list[str]) -> None:
        """Ver progreso."""
        log = self.get_output_log()

        if not self.current_course or not self.current_state:
            log.write_error("No hay curso activo")
            return

        total_units = len(self.current_course.units)
        completed = sum(
            1 for p in self.current_state.unit_progress.values()
            if p.status == "completed"
        )
        in_progress = sum(
            1 for p in self.current_state.unit_progress.values()
            if p.status not in ("not_started", "completed")
        )

        log.write(f"\n[bold cyan]Progreso de: {self.current_course.metadata.title}[/bold cyan]\n")
        log.write(f"  Unidades completadas: [green]{completed}/{total_units}[/green]")
        log.write(f"  En progreso: [yellow]{in_progress}[/yellow]")
        log.write(f"  Unidad actual: {self.current_state.current_unit}")

        # Detalle por unidad
        log.write("\n[bold]Detalle por unidad:[/bold]")
        for unit in self.current_course.units:
            progress = self.current_state.unit_progress.get(unit.number)
            if progress:
                status_color = {
                    "not_started": "dim",
                    "reading": "yellow",
                    "practicing": "blue",
                    "completed": "green",
                }.get(progress.status, "white")
                log.write(f"  [{status_color}]●[/{status_color}] {unit.number}. {unit.title} ({progress.status})")
            else:
                log.write(f"  [dim]○ {unit.number}. {unit.title} (not_started)[/dim]")

    async def cmd_export(self, args: list[str]) -> None:
        """Exportar curso."""
        log = self.get_output_log()

        if not self.current_course:
            log.write_error("No hay curso activo para exportar. Usa 'resume' primero.")
            return

        from ..export_import.manager import ExportImportManager

        manager = ExportImportManager(self.config.courses_dir)

        try:
            log.write_info(f"Exportando curso: {self.current_course.metadata.title}")
            export_path = manager.export_course(
                self.current_course.slug,
                include_history=False,
            )

            log.write_success(f"Curso exportado exitosamente")
            log.write_info(f"Archivo: {export_path}")

            # Mostrar info del manifest
            file_size = export_path.stat().st_size
            log.write_info(f"Tamaño: {file_size / 1024:.1f} KB")

        except Exception as e:
            log.write_error(f"Error exportando: {e}")

    async def cmd_import(self, args: list[str]) -> None:
        """Importar curso."""
        log = self.get_output_log()

        if not args:
            # Listar exports disponibles
            from ..export_import.manager import ExportImportManager
            manager = ExportImportManager(self.config.courses_dir)
            exports = manager.list_exports()

            if exports:
                log.write("[bold]Exports disponibles:[/bold]\n")
                for i, export in enumerate(exports[:10], 1):
                    size_kb = export["size"] / 1024
                    log.write(f"  {i}. {export['filename']} ({size_kb:.1f} KB)")
                log.write_info("\nEscribe 'import <número>' o 'import <ruta>'")
            else:
                log.write_info("No hay archivos de export en el directorio de exports")
                log.write_info("Escribe 'import <ruta_al_zip>' para importar")
            return

        # Importar desde ruta
        from ..export_import.manager import ExportImportManager, ExportImportError

        manager = ExportImportManager(self.config.courses_dir)

        # Puede ser número de la lista o ruta
        import_path = args[0]
        try:
            idx = int(import_path) - 1
            exports = manager.list_exports()
            if 0 <= idx < len(exports):
                import_path = exports[idx]["path"]
            else:
                log.write_error("Número de export inválido")
                return
        except ValueError:
            pass  # Es una ruta

        import_path = Path(import_path)

        if not import_path.exists():
            log.write_error(f"Archivo no encontrado: {import_path}")
            return

        # Validar primero
        log.write_info("Validando archivo...")
        validation = manager.validate_export(import_path)

        if not validation["valid"]:
            log.write_error("El archivo no es válido:")
            for error in validation["errors"]:
                log.write(f"  ✗ {error}")
            return

        if validation["warnings"]:
            log.write_warning("Advertencias:")
            for warning in validation["warnings"]:
                log.write(f"  ⚠ {warning}")

        # Mostrar info del curso a importar
        manifest = validation.get("manifest", {})
        log.write(f"\n[bold]Curso a importar:[/bold]")
        log.write(f"  Título: {manifest.get('course_title', 'Desconocido')}")
        log.write(f"  Slug: {manifest.get('course_slug', 'Desconocido')}")
        log.write(f"  Fecha export: {manifest.get('export_date', 'Desconocido')}")

        # Verificar si existe
        slug = manifest.get("course_slug")
        if slug and self.persistence.course_exists(slug):
            log.write_warning(f"\nEl curso '{slug}' ya existe.")
            log.write_info("Escribe 'import_confirm' para sobrescribir o cualquier otro comando para cancelar")
            self.pending_action = "import_confirm"
            self.pending_data = {"path": str(import_path)}
            return

        # Importar directamente
        try:
            imported_slug = manager.import_course(import_path)
            log.write_success(f"\nCurso importado: {imported_slug}")
            log.write_info("Escribe 'resume' para cargarlo")
        except ExportImportError as e:
            log.write_error(f"Error importando: {e}")

    async def cmd_delete(self, args: list[str]) -> None:
        """Eliminar curso."""
        log = self.get_output_log()

        if not args:
            log.write_error("Especifica el slug del curso a eliminar: delete <slug>")
            return

        slug = args[0]
        if not self.persistence.course_exists(slug):
            log.write_error(f"Curso no encontrado: {slug}")
            return

        log.write(f"[red]¿Eliminar curso '{slug}'? Esto no se puede deshacer.[/red]")
        log.write_info("Escribe 'delete_confirm' para confirmar o cualquier otro comando para cancelar")
        self.pending_action = "delete_confirm"
        self.pending_data = {"slug": slug}

    # ========== Helpers ==========

    async def load_course(self, slug: str) -> None:
        """Cargar curso y su estado."""
        log = self.get_output_log()

        try:
            from ..core.course import Course
            self.current_course = Course.load(self.persistence.get_course_path(slug))
            self.current_state = self.persistence.load_state(slug)

            if self.current_state is None:
                self.current_state = self.persistence.create_initial_state(slug)

            self.update_status()
            log.write_success(f"Curso cargado: {self.current_course.metadata.title}")
            log.write_info(f"Unidad actual: {self.current_state.current_unit}")
            log.write_info("Escribe 'read' para ver el material o 'unit <n>' para cambiar")

        except FileNotFoundError:
            log.write_error(f"Curso no encontrado: {slug}")
        except Exception as e:
            log.write_error(f"Error al cargar curso: {e}")

    async def handle_pending(self, text: str) -> bool:
        """Manejar respuestas pendientes de wizards."""
        if not self.pending_action:
            return False

        log = self.get_output_log()
        action = self.pending_action
        data = self.pending_data or {}

        if action == "delete_confirm":
            if text.lower() == "delete_confirm":
                slug = data.get("slug")
                if slug:
                    self.persistence.delete_course(slug)
                    if self.current_course and self.current_course.slug == slug:
                        self.current_course = None
                        self.current_state = None
                        self.update_status()
                    log.write_success(f"Curso eliminado: {slug}")
            else:
                log.write_info("Eliminación cancelada")

            self.pending_action = None
            self.pending_data = None
            return True

        if action == "new_course_topic":
            # Guardar tema y pasar a nivel
            topic = text.strip()
            if not topic:
                log.write_error("El tema no puede estar vacío")
                return True

            self.pending_action = "new_course_level"
            self.pending_data = {"topic": topic}
            log.write_tutor(f"Tema seleccionado: {topic}")
            log.write_info("¿Qué nivel deseas? (beginner/intermediate/advanced)")
            return True

        if action == "new_course_level":
            level = text.strip().lower()
            valid_levels = ["beginner", "intermediate", "advanced"]
            if level not in valid_levels:
                log.write_error(f"Nivel inválido. Opciones: {', '.join(valid_levels)}")
                return True

            self.pending_action = "new_course_duration"
            self.pending_data["level"] = level
            log.write_tutor(f"Nivel: {level}")
            log.write_info("¿Cuánto tiempo tienes disponible? (ej: 2 semanas, 1 mes)")
            return True

        if action == "new_course_duration":
            duration = text.strip()
            if not duration:
                duration = "4 semanas"

            self.pending_action = "new_course_focus"
            self.pending_data["duration"] = duration
            log.write_tutor(f"Duración: {duration}")
            log.write_info("¿Prefieres enfoque en teoría, práctica, o equilibrado?")
            return True

        if action == "new_course_focus":
            focus_map = {
                "teoria": "theory",
                "practica": "practice",
                "equilibrado": "balanced",
                "theory": "theory",
                "practice": "practice",
                "balanced": "balanced",
                "t": "theory",
                "p": "practice",
                "e": "balanced",
            }
            focus_input = text.strip().lower()
            focus = focus_map.get(focus_input, "balanced")

            self.pending_data["focus"] = focus
            topic = self.pending_data["topic"]
            level = self.pending_data["level"]
            duration = self.pending_data["duration"]

            log.write_tutor("Perfecto. Generando curso con Ollama...")
            log.write_info(f"Tema: {topic}, Nivel: {level}, Duración: {duration}, Enfoque: {focus}")
            log.write_info("Esto puede tomar unos minutos...")

            # Generar curso completo
            self.set_loading(True)
            try:
                course = await self.content_generator.generate_full_course(
                    topic=topic,
                    level=level,
                    duration=duration,
                    focus=focus,
                    persistence=self.persistence,
                )

                self.current_course = course
                self.current_state = self.persistence.load_state(course.slug)

                self.update_status()
                log.write_success(f"\n✓ Curso generado: {course.metadata.title}")
                log.write_info(f"  - {len(course.units)} unidades")
                total_labs = sum(len(u.labs) for u in course.units)
                log.write_info(f"  - {total_labs} laboratorios")
                log.write_info(f"  - Duración estimada: {course.metadata.estimated_total_time} minutos")
                log.write_info("\nEscribe 'read' para comenzar con la unidad 1")

            except ContentGenerationError as e:
                log.write_error(f"Error generando curso: {e}")
                log.write_info("Intenta de nuevo con un tema más específico o verifica Ollama")
            except Exception as e:
                log.write_error(f"Error inesperado: {e}")
            finally:
                self.set_loading(False)

            self.pending_action = None
            self.pending_data = None
            return True

        if action == "import_confirm":
            if text.lower() == "import_confirm":
                from ..export_import.manager import ExportImportManager, ExportImportError

                zip_path = Path(data.get("path", ""))
                if zip_path.exists():
                    try:
                        manager = ExportImportManager(self.config.courses_dir)
                        imported_slug = manager.import_course(zip_path, force=True)
                        log.write_success(f"Curso importado: {imported_slug}")
                        log.write_info("Escribe 'resume' para cargarlo")
                    except ExportImportError as e:
                        log.write_error(f"Error importando: {e}")
                else:
                    log.write_error("Archivo no encontrado")
            else:
                log.write_info("Importación cancelada")

            self.pending_action = None
            self.pending_data = None
            return True

        if action == "quiz_answer":
            answer = text.strip().lower()

            if answer == "quiz_stop":
                log.write_info("Quiz cancelado")
                self.pending_action = None
                self.pending_data = None
                return True

            q_data = data.get("question", {})
            q_idx = data.get("question_idx", 0)
            score = data.get("score", 0)
            questions = data.get("questions", [])
            progress = data.get("progress")

            q_type = q_data.get("type", "multiple_choice")
            options = q_data.get("options", [])
            correct_answer = q_data.get("correct_answer", "")
            explanation = q_data.get("explanation", "")

            # Verificar respuesta
            is_correct = False
            user_answer = answer

            if answer == "hint":
                hint = q_data.get("hint", "No hay pista disponible")
                log.write_info(f"Pista: {hint}")
                return True  # Mantener en modo quiz

            if q_type == "multiple_choice":
                # Convertir a/b/c a índice
                if len(answer) == 1 and answer[0] in "abcdefghijklmnopqrstuvwxyz":
                    opt_idx = ord(answer[0]) - ord('a')
                    if 0 <= opt_idx < len(options):
                        user_answer = options[opt_idx].get("text", answer)
                        is_correct = options[opt_idx].get("correct", False)
                else:
                    # Intentar match por texto
                    for opt in options:
                        if answer in opt.get("text", "").lower():
                            is_correct = opt.get("correct", False)
                            break
            else:
                # Open o code: match directo o parcial
                is_correct = answer.lower() == correct_answer.lower()

            # Mostrar resultado
            if is_correct:
                log.write_success("¡Correcto!")
                score += 1
            else:
                log.write_error(f"Incorrecto. La respuesta era: {correct_answer}")

            if explanation:
                log.write_info(f"Explicación: {explanation}")

            # Guardar resultado
            from ..core.state import QuizResult
            quiz_result = QuizResult(
                question_id=q_data.get("id", f"q{q_idx}"),
                correct=is_correct,
                answer=user_answer,
                score=1.0 if is_correct else 0.0,
            )
            if progress:
                progress.quiz_results.append(quiz_result)
                self.persistence.save_state(self.current_state)

            # Avanzar a siguiente pregunta o terminar
            next_q = q_idx + 1
            if next_q >= len(questions):
                # Terminar quiz
                final_score = (score / len(questions) * 100) if questions else 0
                log.write(f"\n[bold cyan]Quiz completado[/bold cyan]")
                log.write(f"Puntuación: {final_score:.0f}% ({score}/{len(questions)})")

                if final_score >= 70:
                    log.write_success("¡Buen trabajo!")
                else:
                    log.write_info("Sigue practicando con 'read'")

                self.pending_action = None
                self.pending_data = None
            else:
                # Preparar siguiente pregunta
                self.pending_action = "quiz_answer"
                self.pending_data = {
                    "question_idx": next_q,
                    "question": questions[next_q],
                    "score": score,
                    "questions": questions,
                    "progress": progress,
                }
                # Mostrar siguiente pregunta inmediatamente
                self._show_quiz_question(questions[next_q], next_q, len(questions))

            return True

        return False

    def _show_quiz_question(self, q: dict, idx: int, total: int) -> None:
        """Mostrar una pregunta de quiz."""
        log = self.get_output_log()
        q_text = q.get("question", "Pregunta sin texto")
        options = q.get("options", [])

        log.write(f"\n[bold]Pregunta {idx + 1}/{total}:[/bold]")
        log.write(f"{q_text}\n")

        if options:
            for i, opt in enumerate(options):
                opt_text = opt.get("text", f"Opción {i+1}")
                log.write(f"  {chr(97+i)}) {opt_text}")

        log.write_info("\nEscribe tu respuesta (a, b, c...) o 'hint' para pista")

    def set_loading(self, loading: bool) -> None:
        """Mostrar/ocultar indicador de carga."""
        input_widget = self.query_one(CommandInput)
        if loading:
            input_widget.disabled = True
            input_widget.placeholder = "Generando contenido... espera por favor"
        else:
            input_widget.disabled = False
            input_widget.placeholder = "Escribe un comando (help para ayuda)"

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Procesar input con soporte para wizards."""
        input_widget = self.query_one(CommandInput)
        text = event.value.strip()

        if not text:
            return

        # Verificar si hay acción pendiente
        if await self.handle_pending(text):
            input_widget.value = ""
            return

        # Procesar como comando normal
        await super().on_input_submitted(event)
