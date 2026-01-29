"""Capa de persistencia para cursos y estado."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .course import Course
    from .state import CourseState


class CoursePersistence:
    """Maneja la persistencia de cursos y su estado."""

    def __init__(self, base_path: Path) -> None:
        """Inicializar con ruta base."""
        self.base_path = Path(base_path)
        self.courses_dir = self.base_path / "courses"
        self.courses_dir.mkdir(parents=True, exist_ok=True)

    def list_courses(self) -> list[dict]:
        """Listar cursos disponibles."""
        courses = []
        for course_dir in self.courses_dir.iterdir():
            if not course_dir.is_dir():
                continue

            course_file = course_dir / "course.yaml"
            state_file = course_dir / "state.json"

            if course_file.exists():
                try:
                    import yaml
                    with open(course_file, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)

                    meta = data.get("metadata", {})
                    courses.append({
                        "slug": data.get("slug", course_dir.name),
                        "title": meta.get("title", "Unknown"),
                        "level": meta.get("level", "unknown"),
                        "updated_at": meta.get("updated_at", ""),
                        "has_state": state_file.exists(),
                        "path": course_dir,
                    })
                except Exception:
                    continue

        return sorted(courses, key=lambda x: x["updated_at"], reverse=True)

    def course_exists(self, slug: str) -> bool:
        """Verificar si existe un curso."""
        course_dir = self.courses_dir / slug
        return (course_dir / "course.yaml").exists()

    def get_course_path(self, slug: str) -> Path:
        """Obtener ruta del curso."""
        return self.courses_dir / slug

    def create_course(self, course: Course) -> None:
        """Crear nuevo curso en disco."""
        course.path = self.get_course_path(course.slug)
        course.save()

        # Crear estructura de directorios
        for unit in course.units:
            unit_slug = f"{unit.number:02d}-{unit.slug}"
            unit_path = course.path / "units" / unit_slug
            unit_path.mkdir(parents=True, exist_ok=True)

            # Crear directorios de labs
            for lab in unit.labs:
                lab_path = unit_path / "labs" / lab.slug
                lab_path.mkdir(parents=True, exist_ok=True)
                (lab_path / "starter").mkdir(exist_ok=True)
                (lab_path / "submission").mkdir(exist_ok=True)
                (lab_path / "tests").mkdir(exist_ok=True)

        # Crear historial
        (course.path / "history").mkdir(exist_ok=True)
        (course.path / "exports").mkdir(exist_ok=True)

    def load_course(self, slug: str) -> Course:
        """Cargar curso desde disco."""
        from .course import Course
        course_path = self.get_course_path(slug)
        if not course_path.exists():
            raise FileNotFoundError(f"Course not found: {slug}")
        return Course.load(course_path)

    def save_course(self, course: Course) -> None:
        """Guardar curso a disco."""
        course.save()

    def load_state(self, slug: str) -> CourseState | None:
        """Cargar estado del curso."""
        from .state import CourseState
        state_file = self.get_course_path(slug) / "state.json"

        if not state_file.exists():
            return None

        try:
            return CourseState.load(state_file)
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def save_state(self, state: CourseState) -> None:
        """Guardar estado del curso."""
        state_file = self.get_course_path(state.course_slug) / "state.json"
        state.save(state_file)

    def create_initial_state(self, slug: str) -> CourseState:
        """Crear estado inicial para un curso."""
        from .state import CourseState
        state = CourseState(course_slug=slug)
        self.save_state(state)
        return state

    def delete_course(self, slug: str) -> None:
        """Eliminar curso completamente."""
        import shutil
        course_path = self.get_course_path(slug)
        if course_path.exists():
            shutil.rmtree(course_path)

    def get_chat_history_path(self, slug: str) -> Path:
        """Obtener ruta del historial de chat."""
        return self.get_course_path(slug) / "history" / "chat.jsonl"

    def append_chat_message(self, slug: str, message: dict) -> None:
        """Añadir mensaje al historial de chat."""
        import json
        chat_file = self.get_chat_history_path(slug)
        chat_file.parent.mkdir(parents=True, exist_ok=True)

        with open(chat_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(message, ensure_ascii=False) + "\n")

    def load_chat_history(self, slug: str, n: int = 100) -> list[dict]:
        """Cargar últimos N mensajes de chat."""
        import json
        chat_file = self.get_chat_history_path(slug)

        if not chat_file.exists():
            return []

        messages = []
        with open(chat_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        messages.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        return messages[-n:] if n > 0 else messages
