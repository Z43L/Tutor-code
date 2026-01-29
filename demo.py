#!/usr/bin/env python3
"""Script de demo para probar el sistema sin la TUI completa."""

import asyncio
import tempfile
from pathlib import Path

# Demo de creación de curso
async def demo_course_creation():
    """Demo de creación de curso con Ollama."""
    print("="*60)
    print("DEMO: Creación de curso")
    print("="*60)

    # Simular estructura
    from src.tutor_tui.core.course import Course, CourseMetadata, Unit, Lab
    from src.tutor_tui.core.persistence import CoursePersistence

    with tempfile.TemporaryDirectory() as tmpdir:
        persistence = CoursePersistence(Path(tmpdir))

        # Crear curso de ejemplo
        course = Course(
            slug="python-basico",
            metadata=CourseMetadata(
                title="Python Básico",
                description="Curso introductorio de Python para principiantes",
                level="beginner",
                category="programming",
                estimated_total_time=240,
                stack=["Python 3.11", "pytest"],
                learning_objectives=[
                    "Entender sintaxis básica de Python",
                    "Trabajar con variables y tipos de datos",
                    "Crear funciones y estructuras de control",
                ],
            ),
            units=[
                Unit(
                    number=1,
                    slug="introduccion",
                    title="Introducción a Python",
                    description="Historia, instalación y primeros pasos",
                    learning_objectives=["Instalar Python", "Ejecutar primer script"],
                    labs=[
                        Lab(
                            slug="lab-01-hello",
                            title="Hola Mundo",
                            description="Crear tu primer programa en Python",
                            difficulty="easy",
                            estimated_time=15,
                            skills=["print", "strings"],
                        )
                    ],
                ),
                Unit(
                    number=2,
                    slug="variables",
                    title="Variables y Tipos de Datos",
                    description="Enteros, floats, strings, booleanos",
                    learning_objectives=["Declarar variables", "Convertir tipos"],
                    labs=[
                        Lab(
                            slug="lab-02-calculadora",
                            title="Mini Calculadora",
                            description="Operaciones aritméticas básicas",
                            difficulty="easy",
                            estimated_time=30,
                            skills=["operadores", "input", "variables"],
                        )
                    ],
                ),
            ],
        )

        # Guardar
        persistence.create_course(course)
        print(f"✓ Curso creado: {course.metadata.title}")
        print(f"  Slug: {course.slug}")
        print(f"  Unidades: {len(course.units)}")
        print(f"  Labs: {sum(len(u.labs) for u in course.units)}")

        # Listar cursos
        courses = persistence.list_courses()
        print(f"\n✓ Cursos listados: {len(courses)}")
        for c in courses:
            print(f"  - {c['title']} ({c['slug']})")

        # Cargar y verificar
        loaded = persistence.load_course(course.slug)
        print(f"\n✓ Curso cargado: {loaded.metadata.title}")

        # Crear estado
        from src.tutor_tui.core.state import CourseState
        state = persistence.create_initial_state(course.slug)
        state.current_unit = 1
        persistence.save_state(state)
        print(f"✓ Estado guardado (unidad actual: {state.current_unit})")

        return True


def demo_evaluator():
    """Demo del evaluador."""
    print("\n" + "="*60)
    print("DEMO: Evaluador Python")
    print("="*60)

    import tempfile
    from src.tutor_tui.core.course import Lab
    from src.tutor_tui.labs.evaluator import PythonEvaluator

    with tempfile.TemporaryDirectory() as tmpdir:
        # Crear estructura de lab
        lab_dir = Path(tmpdir)
        submission_dir = lab_dir / "submission"
        tests_dir = lab_dir / "tests"
        submission_dir.mkdir()
        tests_dir.mkdir()

        # Crear archivo de solución
        (submission_dir / "solution.py").write_text("""
def suma(a, b):
    return a + b

def resta(a, b):
    return a - b
""")

        # Crear tests
        (tests_dir / "test_solution.py").write_text("""
import sys
sys.path.insert(0, 'submission')

from solution import suma, resta

def test_suma():
    assert suma(2, 3) == 5
    assert suma(-1, 1) == 0

def test_resta():
    assert resta(5, 3) == 2
    assert resta(0, 5) == -5
""")

        # Crear lab
        lab = Lab(
            slug="test-lab",
            title="Test Lab",
            description="Lab de prueba",
        )
        lab.submission_path = submission_dir
        lab.tests_path = tests_dir
        lab.grade_path = lab_dir / "grade.json"

        # Evaluar
        evaluator = PythonEvaluator(lab)
        result = evaluator.evaluate()

        print(f"Puntuación: {result.score:.1f}%")
        print(f"Tests: {result.passed_tests}/{result.total_tests}")
        print(f"Pasó: {'Sí' if result.passed else 'No'}")

        if result.errors:
            print(f"Errores: {len(result.errors)}")
        if result.warnings:
            print(f"Advertencias: {len(result.warnings)}")

        return result.passed


def demo_export_import():
    """Demo de export/import."""
    print("\n" + "="*60)
    print("DEMO: Export/Import")
    print("="*60)

    import tempfile
    from src.tutor_tui.core.course import Course, CourseMetadata, Unit
    from src.tutor_tui.core.persistence import CoursePersistence
    from src.tutor_tui.export_import.manager import ExportImportManager

    with tempfile.TemporaryDirectory() as tmpdir:
        courses_dir = Path(tmpdir) / "courses"
        courses_dir.mkdir()

        # Crear curso
        persistence = CoursePersistence(courses_dir)
        course = Course(
            slug="demo-course",
            metadata=CourseMetadata(title="Demo", description="Demo"),
            units=[Unit(number=1, slug="u1", title="Unit 1")],
        )
        persistence.create_course(course)
        print(f"✓ Curso creado: {course.slug}")

        # Exportar
        manager = ExportImportManager(courses_dir)
        export_path = manager.export_course(course.slug)
        print(f"✓ Exportado a: {export_path.name}")

        # Validar
        validation = manager.validate_export(export_path)
        print(f"✓ Validación: {'OK' if validation['valid'] else 'FALLIDA'}")

        # Eliminar y re-importar
        persistence.delete_course(course.slug)
        print(f"✓ Curso eliminado")

        imported_slug = manager.import_course(export_path)
        print(f"✓ Curso importado: {imported_slug}")

        # Verificar
        assert persistence.course_exists(imported_slug)
        print(f"✓ Verificación exitosa")

        return True


async def main():
    """Ejecutar todas las demos."""
    print("\n")
    print("╔" + "═"*58 + "╗")
    print("║" + " "*15 + "TUTOR TUI - DEMO" + " "*27 + "║")
    print("║" + " "*10 + "Sistema de Tutoría con IA Local" + " "*17 + "║")
    print("╚" + "═"*58 + "╝")
    print()

    try:
        # Demo 1: Course creation
        result1 = await demo_course_creation()

        # Demo 2: Evaluator
        result2 = demo_evaluator()

        # Demo 3: Export/Import
        result3 = demo_export_import()

        print("\n" + "="*60)
        print("RESUMEN DE DEMOS")
        print("="*60)
        print(f"✓ Creación de curso: {'OK' if result1 else 'FALLIDO'}")
        print(f"✓ Evaluador: {'OK' if result2 else 'FALLIDO'}")
        print(f"✓ Export/Import: {'OK' if result3 else 'FALLIDO'}")
        print()
        print("Para ejecutar la TUI completa:")
        print("  pip install -e .")
        print("  tutor")
        print()
        print("Requisitos:")
        print("  - Ollama corriendo en http://localhost:11434")
        print("  - Modelo descargado (ej: ollama pull llama3.1)")
        print("  - nvim/vim instalado")
        print()

    except Exception as e:
        print(f"\n✗ Error en demo: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
