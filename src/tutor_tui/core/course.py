"""Modelos de datos para cursos y unidades."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Lab:
    """Un laboratorio/ejercicio práctico."""

    slug: str
    title: str
    description: str
    language: str = "python"
    lab_type: str = "full"  # full, bugfix, fill
    difficulty: str = "medium"  # easy, medium, hard
    prerequisites: list[str] = field(default_factory=list)
    estimated_time: int = 30  # minutos
    skills: list[str] = field(default_factory=list)

    # Paths (se establecen al cargar)
    path: Path | None = None
    readme_path: Path | None = None
    starter_path: Path | None = None
    submission_path: Path | None = None
    tests_path: Path | None = None
    grade_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convertir a diccionario."""
        return {
            "slug": self.slug,
            "title": self.title,
            "description": self.description,
            "language": self.language,
            "lab_type": self.lab_type,
            "difficulty": self.difficulty,
            "prerequisites": self.prerequisites,
            "estimated_time": self.estimated_time,
            "skills": self.skills,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Lab:
        """Crear desde diccionario."""
        return cls(
            slug=data["slug"],
            title=data["title"],
            description=data["description"],
            language=data.get("language", "python"),
            lab_type=data.get("lab_type", "full"),
            difficulty=data.get("difficulty", "medium"),
            prerequisites=data.get("prerequisites", []),
            estimated_time=data.get("estimated_time", 30),
            skills=data.get("skills", []),
        )


@dataclass
class QuizQuestion:
    """Una pregunta de quiz."""

    id: str
    question: str
    type: str  # multiple_choice, open, code
    options: list[dict[str, Any]] | None = None  # para multiple_choice
    correct_answer: str | None = None
    explanation: str = ""
    hint: str = ""
    points: int = 1
    tags: list[str] = field(default_factory=list)


@dataclass
class Unit:
    """Una unidad del curso."""

    number: int
    slug: str
    title: str
    description: str
    learning_objectives: list[str] = field(default_factory=list)
    estimated_time: int = 60  # minutos
    prerequisites: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    labs: list[Lab] = field(default_factory=list)
    quiz_path: Path | None = None
    material_path: Path | None = None

    # Contenido (se carga bajo demanda)
    material_content: str | None = None
    quiz_questions: list[QuizQuestion] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convertir a diccionario."""
        return {
            "number": self.number,
            "slug": self.slug,
            "title": self.title,
            "description": self.description,
            "learning_objectives": self.learning_objectives,
            "estimated_time": self.estimated_time,
            "prerequisites": self.prerequisites,
            "skills": self.skills,
            "labs": [lab.to_dict() for lab in self.labs],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Unit:
        """Crear desde diccionario."""
        labs = [Lab.from_dict(lab_data) for lab_data in data.get("labs", [])]
        return cls(
            number=data["number"],
            slug=data["slug"],
            title=data["title"],
            description=data["description"],
            learning_objectives=data.get("learning_objectives", []),
            estimated_time=data.get("estimated_time", 60),
            prerequisites=data.get("prerequisites", []),
            skills=data.get("skills", []),
            labs=labs,
        )


@dataclass
class CourseMetadata:
    """Metadata del curso."""

    title: str
    description: str
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    author: str = "Tutor TUI"
    language: str = "es"
    level: str = "beginner"  # beginner, intermediate, advanced
    category: str = "programming"
    estimated_total_time: int = 0  # minutos
    prerequisites: list[str] = field(default_factory=list)
    learning_objectives: list[str] = field(default_factory=list)
    stack: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convertir a diccionario."""
        return {
            "title": self.title,
            "description": self.description,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "author": self.author,
            "language": self.language,
            "level": self.level,
            "category": self.category,
            "estimated_total_time": self.estimated_total_time,
            "prerequisites": self.prerequisites,
            "learning_objectives": self.learning_objectives,
            "stack": self.stack,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CourseMetadata:
        """Crear desde diccionario."""
        return cls(
            title=data["title"],
            description=data["description"],
            version=data.get("version", "1.0.0"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            author=data.get("author", "Tutor TUI"),
            language=data.get("language", "es"),
            level=data.get("level", "beginner"),
            category=data.get("category", "programming"),
            estimated_total_time=data.get("estimated_total_time", 0),
            prerequisites=data.get("prerequisites", []),
            learning_objectives=data.get("learning_objectives", []),
            stack=data.get("stack", []),
            tags=data.get("tags", []),
        )


@dataclass
class Course:
    """Curso completo."""

    slug: str
    metadata: CourseMetadata
    units: list[Unit] = field(default_factory=list)
    path: Path | None = None

    # Archivos
    COURSE_FILE = "course.yaml"
    STATE_FILE = "state.json"

    def to_dict(self) -> dict[str, Any]:
        """Convertir a diccionario."""
        return {
            "slug": self.slug,
            "metadata": self.metadata.to_dict(),
            "units": [unit.to_dict() for unit in self.units],
        }

    def save(self) -> None:
        """Guardar curso a disco."""
        if self.path is None:
            raise ValueError("Course path not set")

        self.path.mkdir(parents=True, exist_ok=True)
        course_file = self.path / self.COURSE_FILE

        with open(course_file, "w", encoding="utf-8") as f:
            yaml.dump(
                self.to_dict(),
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        self.metadata.updated_at = datetime.now()

    @classmethod
    def load(cls, path: Path) -> Course:
        """Cargar curso desde disco."""
        course_file = path / cls.COURSE_FILE

        if not course_file.exists():
            raise FileNotFoundError(f"Course file not found: {course_file}")

        with open(course_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        metadata = CourseMetadata.from_dict(data["metadata"])
        units = [Unit.from_dict(unit_data) for unit_data in data.get("units", [])]

        course = cls(
            slug=data["slug"],
            metadata=metadata,
            units=units,
            path=path,
        )

        # Establecer paths de unidades y labs
        for unit in course.units:
            unit_slug = f"{unit.number:02d}-{unit.slug}"
            unit_path = path / "units" / unit_slug
            unit.material_path = unit_path / "material.md"
            unit.quiz_path = unit_path / "quiz.json"

            for lab in unit.labs:
                lab.path = unit_path / "labs" / lab.slug
                if lab.path:
                    lab.readme_path = lab.path / "README.md"
                    lab.starter_path = lab.path / "starter"
                    lab.submission_path = lab.path / "submission"
                    lab.tests_path = lab.path / "tests"
                    lab.grade_path = lab.path / "grade.json"

        return course

    def get_unit(self, number: int) -> Unit | None:
        """Obtener unidad por número."""
        for unit in self.units:
            if unit.number == number:
                return unit
        return None

    def get_current_unit(self, state: CourseState) -> Unit | None:
        """Obtener unidad actual según estado."""
        return self.get_unit(state.current_unit)


from .state import CourseState  # noqa: E402
