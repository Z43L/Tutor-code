"""Gestión de workspaces para laboratorios."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.course import Lab


class WorkspaceError(Exception):
    """Error en operación de workspace."""

    pass


class LabWorkspace:
    """Gestiona un workspace para un laboratorio."""

    def __init__(self, lab: Lab, editor: str = "nvim") -> None:
        """Inicializar workspace."""
        self.lab = lab
        self.editor = editor
        self.submission_path = lab.submission_path
        self.starter_path = lab.starter_path

    def ensure_submission_dir(self) -> Path:
        """Asegurar que existe directorio de submission."""
        if not self.submission_path:
            raise WorkspaceError("Lab no tiene submission_path definido")

        self.submission_path.mkdir(parents=True, exist_ok=True)
        return self.submission_path

    def initialize_from_starter(self) -> None:
        """Copiar archivos starter a submission si submission está vacío."""
        submission_dir = self.ensure_submission_dir()

        # Verificar si submission está vacío
        if any(submission_dir.iterdir()):
            return  # Ya hay archivos, no sobrescribir

        # Copiar archivos starter
        if self.starter_path and self.starter_path.exists():
            for item in self.starter_path.iterdir():
                if item.is_file():
                    shutil.copy2(item, submission_dir / item.name)
                elif item.is_dir():
                    shutil.copytree(item, submission_dir / item.name, dirs_exist_ok=True)

    def open_editor(self) -> int:
        """Abrir editor en el workspace."""
        submission_dir = self.ensure_submission_dir()

        # Inicializar desde starter si es necesario
        self.initialize_from_starter()

        # Detectar qué editor usar
        editor = self._detect_editor()

        # Construir comando
        cmd = [editor]

        # Para nvim/vim, abrir directamente el directorio
        if editor in ("nvim", "vim", "vi"):
            cmd.append(str(submission_dir))

            # Si hay archivos starter, abrir el primero en modo edición
            starter_files = list(submission_dir.iterdir()) if submission_dir.exists() else []
            if starter_files:
                # Ordenar: .py primero, luego README, luego el resto
                py_files = [f for f in starter_files if f.suffix == ".py"]
                readme_files = [f for f in starter_files if "readme" in f.name.lower()]

                if py_files:
                    cmd.append(str(py_files[0]))
                elif readme_files:
                    cmd.append(str(readme_files[0]))
                else:
                    cmd.append(str(starter_files[0]))
        else:
            # Para otros editores, abrir el directorio
            cmd.append(str(submission_dir))

        # Ejecutar editor y esperar
        try:
            result = subprocess.run(cmd, check=False)
            return result.returncode
        except FileNotFoundError:
            raise WorkspaceError(f"Editor no encontrado: {editor}")
        except Exception as e:
            raise WorkspaceError(f"Error ejecutando editor: {e}")

    def _detect_editor(self) -> str:
        """Detectar qué editor usar."""
        # 1. Usar el configurado
        if self.editor:
            return self.editor

        # 2. Detectar desde variable de entorno
        import os
        for env_var in ["EDITOR", "VISUAL"]:
            editor = os.getenv(env_var)
            if editor:
                return editor.split()[0]  # Tomar primer comando si hay argumentos

        # 3. Intentar detectar nvim/vim
        for cmd in ["nvim", "vim", "vi", "nano"]:
            if shutil.which(cmd):
                return cmd

        # 4. Fallback
        return "vi"

    def get_submission_files(self) -> list[Path]:
        """Obtener lista de archivos en submission."""
        if not self.submission_path or not self.submission_path.exists():
            return []

        files = []
        for item in self.submission_path.rglob("*"):
            if item.is_file():
                files.append(item)

        return sorted(files)

    def get_submission_hash(self) -> str:
        """Calcular hash del contenido actual para detectar cambios."""
        files = self.get_submission_files()
        if not files:
            return ""

        hasher = hashlib.md5()
        for file_path in sorted(files):
            try:
                content = file_path.read_bytes()
                hasher.update(content)
                hasher.update(str(file_path.relative_to(self.submission_path)).encode())
            except Exception:
                pass

        return hasher.hexdigest()[:16]

    def has_changes_since(self, previous_hash: str) -> bool:
        """Verificar si hay cambios desde un hash anterior."""
        current_hash = self.get_submission_hash()
        return current_hash != previous_hash

    def read_submission_content(self) -> dict[str, str]:
        """Leer contenido de todos los archivos de submission."""
        content = {}
        for file_path in self.get_submission_files():
            try:
                rel_path = str(file_path.relative_to(self.submission_path))
                content[rel_path] = file_path.read_text(encoding="utf-8")
            except Exception:
                pass
        return content

    def get_main_file(self) -> Path | None:
        """Obtener archivo principal del submission."""
        files = self.get_submission_files()
        if not files:
            return None

        # Prioridad: main.py, archivo con nombre del lab, cualquier .py, primer archivo
        main_candidates = [
            f for f in files
            if f.name in ("main.py", "solution.py", "exercise.py", f"{self.lab.slug}.py")
        ]
        if main_candidates:
            return main_candidates[0]

        py_files = [f for f in files if f.suffix == ".py"]
        if py_files:
            return py_files[0]

        return files[0]

    def reset_to_starter(self) -> None:
        """Restablecer submission a archivos starter originales."""
        if not self.submission_path:
            return

        # Limpiar submission
        if self.submission_path.exists():
            shutil.rmtree(self.submission_path)

        # Re-crear desde starter
        self.initialize_from_starter()
