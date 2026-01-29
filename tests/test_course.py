"""Tests para modelos de curso."""

import tempfile
from pathlib import Path

import pytest

from tutor_tui.core.course import Course, CourseMetadata, Lab, Unit
from tutor_tui.core.persistence import CoursePersistence
from tutor_tui.core.state import CourseState, LabResult, QuizResult, UnitProgress


class TestCourseModels:
    """Tests para modelos de datos."""

    def test_course_metadata_serialization(self) -> None:
        """Test serialización de metadata."""
        meta = CourseMetadata(
            title="Test Course",
            description="A test course",
            level="intermediate",
        )

        data = meta.to_dict()
        restored = CourseMetadata.from_dict(data)

        assert restored.title == meta.title
        assert restored.level == meta.level

    def test_unit_serialization(self) -> None:
        """Test serialización de unidad."""
        unit = Unit(
            number=1,
            slug="intro",
            title="Introduction",
            labs=[Lab(slug="lab1", title="Lab 1", description="Test lab")],
        )

        data = unit.to_dict()
        restored = Unit.from_dict(data)

        assert restored.number == unit.number
        assert len(restored.labs) == 1

    def test_lab_result_serialization(self) -> None:
        """Test serialización de resultado de lab."""
        result = LabResult(
            lab_slug="test-lab",
            status="passed",
            score=85.0,
            passed_tests=5,
            total_tests=6,
        )

        data = result.to_dict()
        restored = LabResult.from_dict(data)

        assert restored.lab_slug == result.lab_slug
        assert restored.score == 85.0


class TestPersistence:
    """Tests para persistencia."""

    def test_save_and_load_course(self) -> None:
        """Test guardar y cargar curso."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = CoursePersistence(Path(tmpdir))

            course = Course(
                slug="test-course",
                metadata=CourseMetadata(
                    title="Test Course",
                    description="Test",
                ),
                units=[
                    Unit(number=1, slug="unit1", title="Unit 1"),
                ],
            )

            persistence.create_course(course)
            loaded = persistence.load_course("test-course")

            assert loaded.slug == course.slug
            assert loaded.metadata.title == course.metadata.title
            assert len(loaded.units) == 1

    def test_save_and_load_state(self) -> None:
        """Test guardar y cargar estado."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = CoursePersistence(Path(tmpdir))

            # Crear curso primero
            course = Course(
                slug="test-course",
                metadata=CourseMetadata(title="Test", description="Test"),
                units=[Unit(number=1, slug="u1", title="U1")],
            )
            persistence.create_course(course)

            # Crear y guardar estado
            state = CourseState(course_slug="test-course", current_unit=1)
            state.get_or_create_unit_progress(1)
            persistence.save_state(state)

            # Cargar estado
            loaded = persistence.load_state("test-course")
            assert loaded is not None
            assert loaded.course_slug == "test-course"
            assert loaded.current_unit == 1

    def test_list_courses(self) -> None:
        """Test listar cursos."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = CoursePersistence(Path(tmpdir))

            # Crear dos cursos
            for slug in ["course-a", "course-b"]:
                course = Course(
                    slug=slug,
                    metadata=CourseMetadata(title=slug, description="Test"),
                    units=[],
                )
                persistence.create_course(course)

            courses = persistence.list_courses()
            assert len(courses) == 2
            slugs = {c["slug"] for c in courses}
            assert slugs == {"course-a", "course-b"}

    def test_course_exists(self) -> None:
        """Test verificar existencia de curso."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = CoursePersistence(Path(tmpdir))

            assert not persistence.course_exists("nonexistent")

            course = Course(
                slug="existing",
                metadata=CourseMetadata(title="Existing", description="Test"),
                units=[],
            )
            persistence.create_course(course)

            assert persistence.course_exists("existing")
