"""Evaluadores para labs."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..core.course import Lab
    from ..core.state import LabResult


@dataclass
class GradeResult:
    """Resultado de evaluación."""

    score: float  # 0-100
    max_score: float = 100.0
    passed: bool = False
    passed_tests: int = 0
    total_tests: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    test_details: list[dict[str, Any]] = field(default_factory=list)
    rubric: dict[str, float] = field(default_factory=dict)
    diff_hints: list[str] = field(default_factory=list)
    execution_time: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convertir a diccionario."""
        return {
            "score": self.score,
            "max_score": self.max_score,
            "passed": self.passed,
            "passed_tests": self.passed_tests,
            "total_tests": self.total_tests,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "test_details": self.test_details,
            "rubric": self.rubric,
            "diff_hints": self.diff_hints,
            "execution_time": self.execution_time,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GradeResult":
        """Crear desde diccionario."""
        return cls(
            score=data.get("score", 0.0),
            max_score=data.get("max_score", 100.0),
            passed=data.get("passed", False),
            passed_tests=data.get("passed_tests", 0),
            total_tests=data.get("total_tests", 0),
            errors=data.get("errors", []),
            warnings=data.get("warnings", []),
            suggestions=data.get("suggestions", []),
            test_details=data.get("test_details", []),
            rubric=data.get("rubric", {}),
            diff_hints=data.get("diff_hints", []),
            execution_time=data.get("execution_time", 0.0),
        )


class Evaluator(ABC):
    """Interfaz base para evaluadores."""

    def __init__(self, lab: Lab, timeout: int = 30) -> None:
        """Inicializar evaluador."""
        self.lab = lab
        self.timeout = timeout

    @abstractmethod
    def evaluate(self) -> GradeResult:
        """Evaluar el lab y retornar resultado."""
        pass

    @property
    @abstractmethod
    def language(self) -> str:
        """Lenguaje soportado."""
        pass

    def save_grade(self, result: GradeResult) -> None:
        """Guardar resultado a grade.json."""
        if self.lab.grade_path:
            self.lab.grade_path.write_text(
                json.dumps(result.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

    def load_grade(self) -> GradeResult | None:
        """Cargar resultado de grade.json."""
        if self.lab.grade_path and self.lab.grade_path.exists():
            try:
                data = json.loads(self.lab.grade_path.read_text(encoding="utf-8"))
                return GradeResult.from_dict(data)
            except (json.JSONDecodeError, KeyError):
                return None
        return None


class PythonEvaluator(Evaluator):
    """Evaluador para labs de Python."""

    @property
    def language(self) -> str:
        return "python"

    def evaluate(self) -> GradeResult:
        """Evaluar lab de Python."""
        if not self.lab.submission_path or not self.lab.tests_path:
            return GradeResult(
                score=0.0,
                errors=["Lab mal configurado: falta submission_path o tests_path"],
            )

        # Verificar tests
        test_files = list(self.lab.tests_path.rglob("test*.py"))
        if not test_files:
            return GradeResult(
                score=0.0,
                errors=["No se encontraron archivos de test"],
            )

        # Verificar que hay archivos de submission (cualquier tipo)
        submission_files = [p for p in self.lab.submission_path.rglob("*") if p.is_file()]
        if not submission_files:
            return GradeResult(
                score=0.0,
                errors=["La carpeta de entrega está vacía"],
            )

        # Ejecutar evaluación
        result = self._run_tests()

        # Añadir análisis de código
        code_analysis = self._analyze_code(submission_files)
        result.warnings.extend(code_analysis["warnings"])
        result.suggestions.extend(code_analysis["suggestions"])

        # Calcular score final con rubrica
        result = self._apply_rubric(result)

        # Guardar resultado
        self.save_grade(result)

        return result

    def _run_tests(self) -> GradeResult:
        """Ejecutar tests con pytest."""
        import time

        start_time = time.time()

        # Crear directorio temporal para ejecución aislada
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)

            # Copiar submission
            submission_copy = work_dir / "submission"
            if self.lab.submission_path:
                self._copy_tree(self.lab.submission_path, submission_copy)

            # Copiar tests
            tests_copy = work_dir / "tests"
            if self.lab.tests_path:
                self._copy_tree(self.lab.tests_path, tests_copy)

            # Crear __init__.py si no existen
            (submission_copy / "__init__.py").touch(exist_ok=True)
            (tests_copy / "__init__.py").touch(exist_ok=True)

            # Intentar ejecutar con pytest
            try:
                return self._run_pytest(tests_copy, work_dir, start_time)
            except Exception as e:
                # Fallback a unittest si pytest falla
                return self._run_unittest(tests_copy, work_dir, start_time, str(e))

    def _run_pytest(self, tests_dir: Path, work_dir: Path, start_time: float) -> GradeResult:
        """Ejecutar tests con pytest."""
        import time

        cmd = [
            sys.executable, "-m", "pytest",
            str(tests_dir),
            "-v",
            "--tb=short",
            "--json-report", "--json-report-file=-",  # Salida JSON a stdout
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=work_dir,
            )
        except subprocess.TimeoutExpired:
            return GradeResult(
                score=0.0,
                errors=[f"Timeout: los tests tardaron más de {self.timeout}s"],
                execution_time=time.time() - start_time,
            )
        except FileNotFoundError:
            # pytest no instalado, intentar con unittest
            raise  # Deja que el caller maneje esto

        execution_time = time.time() - start_time

        # Parsear resultado
        return self._parse_pytest_output(result, execution_time)

    def _parse_pytest_output(self, result: subprocess.CompletedProcess, exec_time: float) -> GradeResult:
        """Parsear salida de pytest."""
        errors = []
        test_details = []
        passed_tests = 0
        total_tests = 0

        # Intentar parsear JSON report
        try:
            # Buscar JSON en stdout
            for line in result.stdout.split("\n"):
                if line.strip().startswith("{"):
                    data = json.loads(line)
                    tests = data.get("tests", [])
                    for test in tests:
                        total_tests += 1
                        outcome = test.get("outcome", "unknown")
                        nodeid = test.get("nodeid", "unknown")

                        if outcome == "passed":
                            passed_tests += 1
                            test_details.append({
                                "name": nodeid,
                                "status": "passed",
                                "message": "",
                            })
                        else:
                            # Extraer mensaje de error
                            call = test.get("call", {})
                            crash = call.get("crash", {})
                            message = crash.get("message", call.get("longrepr", "Error desconocido"))
                            test_details.append({
                                "name": nodeid,
                                "status": outcome,
                                "message": str(message)[:500],
                            })
                            errors.append(f"{nodeid}: {message}")

                    break
        except json.JSONDecodeError:
            pass

        # Fallback: contar desde stdout
        if total_tests == 0:
            stdout = result.stdout
            if "passed" in stdout:
                import re
                # Buscar "X passed" o "X passed, Y failed"
                match = re.search(r"(\d+) passed", stdout)
                if match:
                    passed_tests = int(match.group(1))

                match = re.search(r"(\d+) failed", stdout)
                if match:
                    failed = int(match.group(1))
                    total_tests = passed_tests + failed
                else:
                    total_tests = passed_tests

        # Calcular score
        score = (passed_tests / total_tests * 100) if total_tests > 0 else 0.0

        return GradeResult(
            score=score,
            passed=score >= 70.0,
            passed_tests=passed_tests,
            total_tests=total_tests,
            errors=errors[:10],  # Limitar errores
            test_details=test_details,
            execution_time=exec_time,
        )

    def _run_unittest(
        self,
        tests_dir: Path,
        work_dir: Path,
        start_time: float,
        previous_error: str = "",
    ) -> GradeResult:
        """Ejecutar tests con unittest como fallback."""
        import time
        import unittest

        # Añadir paths al sys.path
        sys.path.insert(0, str(work_dir / "submission"))
        sys.path.insert(0, str(tests_dir))

        try:
            loader = unittest.TestLoader()
            suite = loader.discover(str(tests_dir), pattern="test*.py")

            runner = unittest.TextTestRunner(verbosity=2, stream=subprocess.PIPE)
            result = runner.run(suite)

            execution_time = time.time() - start_time

            # Contar tests
            total_tests = result.testsRun
            passed_tests = total_tests - len(result.failures) - len(result.errors)
            score = (passed_tests / total_tests * 100) if total_tests > 0 else 0.0

            # Recopilar errores
            errors = []
            for test, trace in result.failures + result.errors:
                errors.append(f"{test}: {trace[:200]}")

            return GradeResult(
                score=score,
                passed=score >= 70.0 and result.wasSuccessful(),
                passed_tests=passed_tests,
                total_tests=total_tests,
                errors=errors,
                execution_time=execution_time,
            )

        except Exception as e:
            return GradeResult(
                score=0.0,
                errors=[f"Error ejecutando tests: {e}", previous_error][:2],
                execution_time=time.time() - start_time,
            )
        finally:
            sys.path.pop(0)
            sys.path.pop(0)

    def _analyze_code(self, files: list[Path]) -> dict[str, list[str]]:
        """Analizar calidad del código."""
        warnings = []
        suggestions = []

        for file_path in files:
            try:
                content = file_path.read_text(encoding="utf-8")
                lines = content.split("\n")

                # Verificar docstrings
                if '"""' not in content and "'''" not in content:
                    warnings.append(f"{file_path.name}: Falta docstring")

                # Verificar longitud de líneas
                long_lines = [i for i, line in enumerate(lines, 1) if len(line) > 100]
                if long_lines:
                    warnings.append(f"{file_path.name}: Líneas muy largas en: {long_lines[:3]}")

                # Verificar funciones muy largas (heurística simple)
                if lines.count("def ") > 0:
                    suggestions.append(f"{file_path.name}: Asegúrate de que las funciones tengan una sola responsabilidad")

                # Verificar imports no usados (heurística simple)
                imports = [line for line in lines if line.startswith("import ") or line.startswith("from ")]
                if len(imports) > 10:
                    suggestions.append(f"{file_path.name}: Considera reducir el número de imports")

            except Exception:
                pass

        return {"warnings": warnings, "suggestions": suggestions}

    def _apply_rubric(self, result: GradeResult) -> GradeResult:
        """Aplicar rubrica de evaluación."""
        # Rubrica base: 70% tests, 30% calidad de código
        test_score = (result.passed_tests / result.total_tests * 70) if result.total_tests > 0 else 0

        # Penalizaciones por warnings
        quality_penalty = min(len(result.warnings) * 2, 20)  # Max 20 puntos de penalización

        # Score final
        final_score = max(0, test_score + 30 - quality_penalty)

        result.score = round(final_score, 1)
        result.passed = final_score >= 70.0
        result.rubric = {
            "tests": round(test_score, 1),
            "base_quality": 30.0,
            "penalty": -quality_penalty,
            "final": result.score,
        }

        return result

    def _copy_tree(self, src: Path, dst: Path) -> None:
        """Copiar directorio recursivamente."""
        import shutil
        if src.exists():
            shutil.copytree(src, dst, dirs_exist_ok=True)


class JavaScriptEvaluator(Evaluator):
    """Evaluador simple para labs de JavaScript."""

    @property
    def language(self) -> str:
        return "javascript"

    def evaluate(self) -> GradeResult:
        """Ejecutar tests con Node."""
        if not self.lab.submission_path or not self.lab.tests_path:
            return GradeResult(
                score=0.0,
                errors=["Lab mal configurado: falta submission_path o tests_path"],
            )

        submission_files = list(self.lab.submission_path.rglob("*.js"))
        test_files = list(self.lab.tests_path.rglob("test*.js"))
        if not submission_files:
            return GradeResult(
                score=0.0,
                errors=["No se encontraron archivos .js en la carpeta de entrega"],
            )
        if not test_files:
            return GradeResult(score=0.0, errors=["No se encontraron archivos de test .js"])

        try:
            result = subprocess.run(
                ["node", str(test_files[0])],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.lab.tests_path.parent,
            )
        except FileNotFoundError:
            return GradeResult(score=0.0, errors=["Node.js no está instalado o no está en PATH"])
        except subprocess.TimeoutExpired:
            return GradeResult(score=0.0, errors=[f"Timeout: más de {self.timeout}s ejecutando tests"])

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        passed = result.returncode == 0
        passed_tests = 0
        total_tests = 0

        # Si el test imprime JSON, úsalo
        try:
            if stdout:
                data = json.loads(stdout.splitlines()[-1])
                passed_tests = int(data.get("passed", 0))
                total_tests = int(data.get("total", passed_tests))
                passed = passed_tests == total_tests and result.returncode == 0
        except Exception:
            pass

        errors = []
        if not passed:
            if stderr:
                errors.append(stderr)
            if stdout:
                errors.append(stdout)

        grade = GradeResult(
            score=100.0 if passed else 0.0,
            passed=passed,
            passed_tests=passed_tests,
            total_tests=total_tests or (passed_tests if passed_tests else len(test_files)),
            errors=errors[:5],
        )

        self.save_grade(grade)
        return grade


def get_evaluator(lab: Lab) -> Evaluator:
    """Factory para obtener evaluador apropiado."""
    # Detectar lenguaje por archivos en tests
    if lab.tests_path and lab.tests_path.exists():
        if any(lab.tests_path.rglob("*.py")):
            return PythonEvaluator(lab)
        if any(lab.tests_path.rglob("*.js")):
            return JavaScriptEvaluator(lab)

    # Default a Python si no se detecta
    return PythonEvaluator(lab)
