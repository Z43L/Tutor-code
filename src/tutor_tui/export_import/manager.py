"""Gestión de export/import de cursos."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ExportManifest:
    """Manifiesto de exportación."""

    version: str = "1.0.0"
    export_date: datetime = field(default_factory=datetime.now)
    course_slug: str = ""
    course_title: str = ""
    checksums: dict[str, str] = field(default_factory=dict)
    files: list[str] = field(default_factory=list)
    includes_state: bool = True
    includes_history: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convertir a diccionario."""
        return {
            "version": self.version,
            "export_date": self.export_date.isoformat(),
            "course_slug": self.course_slug,
            "course_title": self.course_title,
            "checksums": self.checksums,
            "files": self.files,
            "includes_state": self.includes_state,
            "includes_history": self.includes_history,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExportManifest":
        """Crear desde diccionario."""
        return cls(
            version=data.get("version", "1.0.0"),
            export_date=datetime.fromisoformat(data["export_date"]),
            course_slug=data.get("course_slug", ""),
            course_title=data.get("course_title", ""),
            checksums=data.get("checksums", {}),
            files=data.get("files", []),
            includes_state=data.get("includes_state", True),
            includes_history=data.get("includes_history", False),
        )


class ExportImportError(Exception):
    """Error en operación de export/import."""

    pass


class ExportImportManager:
    """Gestiona exportación e importación de cursos."""

    MANIFEST_FILENAME = "manifest.json"

    def __init__(self, courses_dir: Path) -> None:
        """Inicializar manager."""
        self.courses_dir = Path(courses_dir)
        self.exports_dir = self.courses_dir / "_exports"
        self.exports_dir.mkdir(parents=True, exist_ok=True)

    def export_course(
        self,
        slug: str,
        output_path: Path | None = None,
        include_history: bool = False,
    ) -> Path:
        """Exportar curso a ZIP."""
        course_path = self.courses_dir / slug

        if not course_path.exists():
            raise ExportImportError(f"Curso no encontrado: {slug}")

        # Determinar nombre del archivo de salida
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{slug}_{timestamp}.zip"
            output_path = self.exports_dir / filename

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Leer metadata del curso
        try:
            import yaml
            course_file = course_path / "course.yaml"
            with open(course_file, "r", encoding="utf-8") as f:
                course_data = yaml.safe_load(f)
                course_title = course_data.get("metadata", {}).get("title", slug)
        except Exception:
            course_title = slug

        # Crear manifest y recopilar archivos
        manifest = ExportManifest(
            course_slug=slug,
            course_title=course_title,
            includes_state=True,
            includes_history=include_history,
        )

        files_to_zip: list[tuple[Path, str]] = []  # (source_path, zip_path)
        checksums: dict[str, str] = {}

        # Recopilar archivos del curso
        for item in course_path.rglob("*"):
            if item.is_file():
                # Saltar historial si no se incluye
                if not include_history and "history" in str(item.relative_to(course_path)):
                    continue

                rel_path = item.relative_to(course_path)
                zip_path = f"{slug}/{rel_path}"

                files_to_zip.append((item, zip_path))
                manifest.files.append(str(rel_path))

                # Calcular checksum
                checksums[str(rel_path)] = self._calculate_checksum(item)

        manifest.checksums = checksums

        # Crear ZIP
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Escribir manifest
            manifest_data = json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False)
            zf.writestr(f"{slug}/{self.MANIFEST_FILENAME}", manifest_data)

            # Escribir archivos
            for source_path, zip_path in files_to_zip:
                zf.write(source_path, zip_path)

        return output_path

    def import_course(self, zip_path: Path, force: bool = False) -> str:
        """Importar curso desde ZIP. Retorna slug del curso importado."""
        zip_path = Path(zip_path)

        if not zip_path.exists():
            raise ExportImportError(f"Archivo no encontrado: {zip_path}")

        if not zipfile.is_zipfile(zip_path):
            raise ExportImportError(f"No es un archivo ZIP válido: {zip_path}")

        # Extraer y validar
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tmp_path)

            # Buscar manifest
            manifest_path = None
            extracted_course_dir = None

            for item in tmp_path.iterdir():
                if item.is_dir():
                    candidate = item / self.MANIFEST_FILENAME
                    if candidate.exists():
                        manifest_path = candidate
                        extracted_course_dir = item
                        break

            if not manifest_path:
                raise ExportImportError("No se encontró manifest.json en el ZIP")

            # Leer manifest
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = ExportManifest.from_dict(json.load(f))
            except (json.JSONDecodeError, KeyError) as e:
                raise ExportImportError(f"Manifest inválido: {e}")

            slug = manifest.course_slug

            # Verificar si ya existe
            target_path = self.courses_dir / slug
            if target_path.exists() and not force:
                raise ExportImportError(
                    f"El curso '{slug}' ya existe. Usa force=True para sobrescribir."
                )

            # Validar checksums si existen
            if manifest.checksums:
                for rel_path, expected_checksum in manifest.checksums.items():
                    file_path = extracted_course_dir / rel_path
                    if file_path.exists():
                        actual_checksum = self._calculate_checksum(file_path)
                        if actual_checksum != expected_checksum:
                            raise ExportImportError(
                                f"Checksum inválido para {rel_path}: "
                                f"esperado {expected_checksum[:8]}..., "
                                f"obtenido {actual_checksum[:8]}..."
                            )

            # Copiar al destino final
            if target_path.exists():
                shutil.rmtree(target_path)

            shutil.copytree(extracted_course_dir, target_path)

            return slug

    def list_exports(self) -> list[dict[str, Any]]:
        """Listar archivos de export disponibles."""
        exports = []

        if not self.exports_dir.exists():
            return exports

        for zip_file in sorted(self.exports_dir.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                stat = zip_file.stat()
                exports.append({
                    "filename": zip_file.name,
                    "path": str(zip_file),
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
            except Exception:
                pass

        return exports

    def validate_export(self, zip_path: Path) -> dict[str, Any]:
        """Validar un archivo de export sin importarlo."""
        result = {
            "valid": False,
            "manifest": None,
            "errors": [],
            "warnings": [],
        }

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                # Buscar manifest
                manifest_name = None
                for name in zf.namelist():
                    if name.endswith(self.MANIFEST_FILENAME):
                        manifest_name = name
                        break

                if not manifest_name:
                    result["errors"].append("No se encontró manifest.json")
                    return result

                # Leer manifest
                try:
                    manifest_data = json.loads(zf.read(manifest_name))
                    manifest = ExportManifest.from_dict(manifest_data)
                    result["manifest"] = manifest.to_dict()
                except (json.JSONDecodeError, KeyError) as e:
                    result["errors"].append(f"Manifest inválido: {e}")
                    return result

                # Verificar archivos listados
                zip_files = set(zf.namelist())
                for file_path in manifest.files:
                    expected_path = f"{manifest.course_slug}/{file_path}"
                    if expected_path not in zip_files:
                        result["warnings"].append(f"Archivo faltante: {file_path}")

                # Verificar checksums si existen (muestreo)
                checked = 0
                for rel_path, expected_checksum in list(manifest.checksums.items())[:5]:
                    full_path = f"{manifest.course_slug}/{rel_path}"
                    if full_path in zip_files:
                        content = zf.read(full_path)
                        actual_checksum = hashlib.md5(content).hexdigest()
                        if actual_checksum != expected_checksum:
                            result["errors"].append(f"Checksum inválido: {rel_path}")
                        checked += 1

                result["valid"] = len(result["errors"]) == 0
                result["checked_files"] = checked

        except zipfile.BadZipFile:
            result["errors"].append("Archivo ZIP corrupto")
        except Exception as e:
            result["errors"].append(f"Error validando: {e}")

        return result

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calcular MD5 checksum de archivo."""
        hasher = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def delete_export(self, filename: str) -> bool:
        """Eliminar archivo de export."""
        file_path = self.exports_dir / filename
        if file_path.exists():
            file_path.unlink()
            return True
        return False
