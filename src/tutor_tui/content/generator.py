"""Generador de contenido educativo usando Ollama."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..llm.client import OllamaClient
from ..llm.prompts import (
    LAB_GENERATION_SYSTEM,
    QUIZ_GENERATION_SYSTEM,
    SYLLABUS_GENERATION_SYSTEM,
    UNIT_MATERIAL_SYSTEM,
    build_lab_prompt,
    build_quiz_prompt,
    build_syllabus_prompt,
    build_unit_material_prompt,
)

if TYPE_CHECKING:
    from ..core.course import Course, Unit


class ContentGenerationError(Exception):
    """Error en generación de contenido."""

    pass


class ContentGenerator:
    """Genera contenido educativo usando LLM."""

    def __init__(self, client: OllamaClient | None = None) -> None:
        """Inicializar generador."""
        self.client = client or OllamaClient()

    async def check_ollama(self) -> dict[str, Any]:
        """Verificar disponibilidad de Ollama."""
        return await self.client.check_connection()

    async def generate_syllabus(
        self,
        topic: str,
        level: str = "beginner",
        duration: str = "8 semanas",
        focus: str = "balanced",  # theory, practice, balanced
    ) -> dict[str, Any]:
        """Generar syllabus completo."""
        prompt = build_syllabus_prompt(topic, level, duration, focus)

        try:
            response = await self.client.generate(
                prompt=prompt,
                system=SYLLABUS_GENERATION_SYSTEM,
                temperature=0.7,
                max_tokens=8000,
            )

            # Extraer JSON de la respuesta
            content = response.content
            json_data = self._extract_json(content)

            if not json_data:
                raise ContentGenerationError("No se pudo extraer JSON válido de la respuesta")

            # Validar estructura mínima
            required_fields = ["title", "description", "units"]
            for field in required_fields:
                if field not in json_data:
                    raise ContentGenerationError(f"Campo requerido faltante: {field}")

            return json_data

        except json.JSONDecodeError as e:
            raise ContentGenerationError(f"JSON inválido: {e}")
        except Exception as e:
            raise ContentGenerationError(f"Error generando syllabus: {e}")

    async def generate_unit_material(
        self,
        course: Course,
        unit: Unit,
    ) -> str:
        """Generar material.md para una unidad."""
        # Obtener contexto de unidades adyacentes
        prev_unit = course.get_unit(unit.number - 1)
        next_unit = course.get_unit(unit.number + 1)

        prompt = build_unit_material_prompt(
            course_title=course.metadata.title,
            unit_title=unit.title,
            unit_description=unit.description,
            learning_objectives=unit.learning_objectives,
            previous_unit=prev_unit.title if prev_unit else None,
            next_unit=next_unit.title if next_unit else None,
        )

        try:
            response = await self.client.generate(
                prompt=prompt,
                system=UNIT_MATERIAL_SYSTEM,
                temperature=0.7,
                max_tokens=20000,
            )

            return response.content

        except Exception as e:
            raise ContentGenerationError(f"Error generando material: {e}")

    async def generate_quiz(
        self,
        unit: Unit,
        material_content: str,
        n_questions: int = 5,
    ) -> list[dict[str, Any]]:
        """Generar quiz.json para una unidad."""
        # Extraer resumen del material
        summary = self._extract_summary(material_content)

        prompt = build_quiz_prompt(
            unit_title=unit.title,
            material_summary=summary,
            n_questions=n_questions,
        )

        try:
            response = await self.client.generate(
                prompt=prompt,
                system=QUIZ_GENERATION_SYSTEM,
                temperature=0.7,
                max_tokens=4000,
            )

            json_data = self._extract_json(response.content)

            if not json_data:
                raise ContentGenerationError("No se pudo extraer JSON del quiz")

            if not isinstance(json_data, list):
                raise ContentGenerationError("El quiz debe ser una lista de preguntas")

            return json_data

        except Exception as e:
            raise ContentGenerationError(f"Error generando quiz: {e}")

    async def generate_lab_content(
        self,
        unit: Unit,
        lab: Any,  # Lab
        material_content: str,
    ) -> dict[str, Any]:
        """Generar contenido completo de un lab."""
        prompt = build_lab_prompt(
            lab_title=lab.title,
            lab_description=lab.description,
            difficulty=lab.difficulty,
            skills=lab.skills,
            unit_context=f"{unit.title}: {unit.description}",
        )

        try:
            response = await self.client.generate(
                prompt=prompt,
                system=LAB_GENERATION_SYSTEM,
                temperature=0.7,
                max_tokens=6000,
            )

            json_data = self._extract_json(response.content)

            if not json_data:
                raise ContentGenerationError("No se pudo extraer JSON del lab")

            return json_data

        except Exception as e:
            raise ContentGenerationError(f"Error generando lab: {e}")

    async def generate_full_course(
        self,
        topic: str,
        level: str,
        duration: str,
        focus: str,
        persistence: Any,  # CoursePersistence
    ) -> Course:
        """Generar curso completo con todas las unidades."""
        from ..core.course import Course, CourseMetadata, Unit, Lab

        # 1. Generar syllabus
        syllabus = await self.generate_syllabus(topic, level, duration, focus)

        # 2. Crear estructura del curso
        slug = self._slugify(syllabus["title"])

        # Procesar unidades
        units = []
        for unit_data in syllabus.get("units", []):
            # Procesar labs
            labs = []
            for lab_data in unit_data.get("labs", []):
                lab = Lab.from_dict(lab_data)
                labs.append(lab)

            unit = Unit.from_dict({**unit_data, "labs": []})
            unit.labs = labs
            units.append(unit)

        course = Course(
            slug=slug,
            metadata=CourseMetadata(
                title=syllabus["title"],
                description=syllabus["description"],
                level=syllabus.get("level", "beginner"),
                category=syllabus.get("category", "programming"),
                estimated_total_time=syllabus.get("estimated_total_time", 0),
                prerequisites=syllabus.get("prerequisites", []),
                learning_objectives=syllabus.get("learning_objectives", []),
                stack=syllabus.get("stack", []),
                tags=syllabus.get("tags", []),
            ),
            units=units,
        )

        # 3. Guardar estructura base
        persistence.create_course(course)
        course = persistence.load_course(slug)

        # 4. Generar contenido de cada unidad
        for unit in course.units:
            # Material
            material = await self.generate_unit_material(course, unit)
            if unit.material_path:
                unit.material_path.write_text(material, encoding="utf-8")

            # Quiz
            quiz = await self.generate_quiz(unit, material)
            if unit.quiz_path:
                unit.quiz_path.write_text(
                    json.dumps(quiz, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )

            # Labs
            for lab in unit.labs:
                lab_content = await self.generate_lab_content(unit, lab, material)

                # Guardar README
                if lab.readme_path and "readme" in lab_content:
                    lab.readme_path.write_text(
                        lab_content["readme"],
                        encoding="utf-8",
                    )

                # Guardar archivos starter
                if lab.starter_path and "starter_files" in lab_content:
                    lab.starter_path.mkdir(parents=True, exist_ok=True)
                    for filename, content in lab_content["starter_files"].items():
                        (lab.starter_path / filename).write_text(
                            content,
                            encoding="utf-8",
                        )

                # Guardar tests
                if lab.tests_path and "test_files" in lab_content:
                    lab.tests_path.mkdir(parents=True, exist_ok=True)
                    for filename, content in lab_content["test_files"].items():
                        (lab.tests_path / filename).write_text(
                            content,
                            encoding="utf-8",
                        )

                # Crear directorio submission vacío
                if lab.submission_path:
                    lab.submission_path.mkdir(parents=True, exist_ok=True)

        return course

    def _extract_json(self, text: str) -> Any | None:
        """Extraer objeto JSON de texto."""
        # Intentar parsear directamente
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Buscar bloque JSON en markdown
        json_pattern = r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```"
        matches = re.findall(json_pattern, text, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        # Buscar JSON inline
        patterns = [
            r"(\{[\s\S]*\"title\"[\s\S]*\"units\"[\s\S]*\})",
            r"(\[[\s\S]*\"id\"[\s\S]*\])",
            r"(\{[\s\S]*\"readme\"[\s\S]*\})",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue

        return None

    def _extract_summary(self, material: str, max_chars: int = 2000) -> str:
        """Extraer resumen del material para contexto."""
        lines = material.split("\n")
        summary_lines = []
        current_len = 0

        for line in lines:
            if line.startswith("#"):
                summary_lines.append(line)
                current_len += len(line)
            elif current_len < max_chars:
                summary_lines.append(line)
                current_len += len(line)

        return "\n".join(summary_lines[:50])  # Limitar a ~50 líneas

    def _slugify(self, text: str) -> str:
        """Convertir texto a slug."""
        import re
        text = text.lower()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[-\s]+", "-", text)
        return text[:50].strip("-")
