"""Estado del progreso del estudiante."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class QuizResult:
    """Resultado de un quiz."""

    question_id: str
    correct: bool
    answer: str
    score: float  # 0.0 - 1.0
    timestamp: datetime = field(default_factory=datetime.now)
    time_spent: int = 0  # segundos
    attempts: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Convertir a diccionario."""
        return {
            "question_id": self.question_id,
            "correct": self.correct,
            "answer": self.answer,
            "score": self.score,
            "timestamp": self.timestamp.isoformat(),
            "time_spent": self.time_spent,
            "attempts": self.attempts,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QuizResult:
        """Crear desde diccionario."""
        return cls(
            question_id=data["question_id"],
            correct=data["correct"],
            answer=data["answer"],
            score=data["score"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            time_spent=data.get("time_spent", 0),
            attempts=data.get("attempts", 1),
        )


@dataclass
class LabResult:
    """Resultado de un laboratorio."""

    lab_slug: str
    status: str  # not_started, in_progress, submitted, passed, failed
    score: float = 0.0
    max_score: float = 100.0
    passed_tests: int = 0
    total_tests: int = 0
    errors: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    timestamp: datetime | None = None
    time_spent: int = 0  # segundos
    attempts: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convertir a diccionario."""
        return {
            "lab_slug": self.lab_slug,
            "status": self.status,
            "score": self.score,
            "max_score": self.max_score,
            "passed_tests": self.passed_tests,
            "total_tests": self.total_tests,
            "errors": self.errors,
            "suggestions": self.suggestions,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "time_spent": self.time_spent,
            "attempts": self.attempts,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LabResult:
        """Crear desde diccionario."""
        ts = data.get("timestamp")
        return cls(
            lab_slug=data["lab_slug"],
            status=data["status"],
            score=data.get("score", 0.0),
            max_score=data.get("max_score", 100.0),
            passed_tests=data.get("passed_tests", 0),
            total_tests=data.get("total_tests", 0),
            errors=data.get("errors", []),
            suggestions=data.get("suggestions", []),
            timestamp=datetime.fromisoformat(ts) if ts else None,
            time_spent=data.get("time_spent", 0),
            attempts=data.get("attempts", 0),
        )


@dataclass
class UnitProgress:
    """Progreso en una unidad."""

    unit_number: int
    status: str = "not_started"  # not_started, reading, practicing, completed
    material_read: bool = False
    material_read_time: int = 0  # segundos
    quiz_results: list[QuizResult] = field(default_factory=list)
    lab_results: dict[str, LabResult] = field(default_factory=dict)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    notes: str = ""
    weak_points: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convertir a diccionario."""
        return {
            "unit_number": self.unit_number,
            "status": self.status,
            "material_read": self.material_read,
            "material_read_time": self.material_read_time,
            "quiz_results": [r.to_dict() for r in self.quiz_results],
            "lab_results": {k: v.to_dict() for k, v in self.lab_results.items()},
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "notes": self.notes,
            "weak_points": self.weak_points,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UnitProgress:
        """Crear desde diccionario."""
        lab_results = {
            k: LabResult.from_dict(v)
            for k, v in data.get("lab_results", {}).items()
        }
        started = data.get("started_at")
        completed = data.get("completed_at")

        return cls(
            unit_number=data["unit_number"],
            status=data.get("status", "not_started"),
            material_read=data.get("material_read", False),
            material_read_time=data.get("material_read_time", 0),
            quiz_results=[QuizResult.from_dict(r) for r in data.get("quiz_results", [])],
            lab_results=lab_results,
            started_at=datetime.fromisoformat(started) if started else None,
            completed_at=datetime.fromisoformat(completed) if completed else None,
            notes=data.get("notes", ""),
            weak_points=data.get("weak_points", []),
        )

    def get_quiz_score(self) -> float:
        """Calcular puntuación media del quiz."""
        if not self.quiz_results:
            return 0.0
        return sum(r.score for r in self.quiz_results) / len(self.quiz_results)

    def get_best_lab_result(self, lab_slug: str) -> LabResult | None:
        """Obtener mejor resultado de un lab."""
        return self.lab_results.get(lab_slug)


@dataclass
class CourseState:
    """Estado completo del curso para un estudiante."""

    course_slug: str
    current_unit: int = 1
    current_lab: str | None = None
    unit_progress: dict[int, UnitProgress] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    total_time_spent: int = 0  # segundos
    chat_history: list[dict[str, Any]] = field(default_factory=list)
    preferences: dict[str, Any] = field(default_factory=dict)
    skills_learned: list[str] = field(default_factory=list)
    skills_weak: list[str] = field(default_factory=list)
    version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        """Convertir a diccionario."""
        return {
            "course_slug": self.course_slug,
            "current_unit": self.current_unit,
            "current_lab": self.current_lab,
            "unit_progress": {
                str(k): v.to_dict() for k, v in self.unit_progress.items()
            },
            "started_at": self.started_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "total_time_spent": self.total_time_spent,
            "chat_history": self.chat_history,
            "preferences": self.preferences,
            "skills_learned": self.skills_learned,
            "skills_weak": self.skills_weak,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CourseState:
        """Crear desde diccionario."""
        unit_progress = {
            int(k): UnitProgress.from_dict(v)
            for k, v in data.get("unit_progress", {}).items()
        }

        return cls(
            course_slug=data["course_slug"],
            current_unit=data.get("current_unit", 1),
            current_lab=data.get("current_lab"),
            unit_progress=unit_progress,
            started_at=datetime.fromisoformat(data["started_at"]),
            last_accessed=datetime.fromisoformat(data["last_accessed"]),
            total_time_spent=data.get("total_time_spent", 0),
            chat_history=data.get("chat_history", []),
            preferences=data.get("preferences", {}),
            skills_learned=data.get("skills_learned", []),
            skills_weak=data.get("skills_weak", []),
            version=data.get("version", "1.0.0"),
        )

    def save(self, path: Path) -> None:
        """Guardar estado a disco."""
        import json

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: Path) -> CourseState:
        """Cargar estado desde disco."""
        import json

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def get_or_create_unit_progress(self, unit_number: int) -> UnitProgress:
        """Obtener o crear progreso de unidad."""
        if unit_number not in self.unit_progress:
            self.unit_progress[unit_number] = UnitProgress(
                unit_number=unit_number,
                started_at=datetime.now(),
            )
        return self.unit_progress[unit_number]

    def get_current_unit_progress(self) -> UnitProgress:
        """Obtener progreso de unidad actual."""
        return self.get_or_create_unit_progress(self.current_unit)

    def update_last_accessed(self) -> None:
        """Actualizar timestamp de último acceso."""
        self.last_accessed = datetime.now()

    def add_chat_message(self, role: str, content: str, metadata: dict | None = None) -> None:
        """Añadir mensaje al historial de chat."""
        msg: dict[str, Any] = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        if metadata:
            msg["metadata"] = metadata
        self.chat_history.append(msg)

        # Limitar historial (mantener últimos 100 mensajes)
        if len(self.chat_history) > 100:
            self.chat_history = self.chat_history[-100:]

    def get_chat_context(self, n: int = 10) -> list[dict[str, Any]]:
        """Obtener últimos N mensajes para contexto."""
        return self.chat_history[-n:] if self.chat_history else []
