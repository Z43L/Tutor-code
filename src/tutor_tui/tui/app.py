"""Aplicación de consola simple - BullCode Tutor."""

import asyncio
import sys
import json
import subprocess
import shutil
from pathlib import Path

# Importaciones necesarias
from ..config import get_config
from ..content.generator import ContentGenerationError, ContentGenerator
from ..core.persistence import CoursePersistence
from ..llm.client import OllamaClient

if sys.platform == "win32":
    import colorama
    colorama.init()


class TutorApp:
    """Tutor de consola simple."""

    def __init__(self) -> None:
        self.config = get_config()
        self.persistence = CoursePersistence(self.config.data_dir)
        self.content_generator = ContentGenerator()
        self.current_course = None
        self.current_state = None
        self.current_unit = None
        self.pending_action = None
        self.pending_data = None
        self.ollama_model = self.config.ollama_model

    def print_logo(self) -> None:
        """Imprimir logo del toro."""
        print("\033[38;5;208m" + r"""
        ,     ,
        |\---/|
        | o_o |
         \_^_/
        / 6 6\
        \_YY_/
        """ + "\033[0m")

    def print_header(self) -> None:
        """Imprimir encabezado."""
        print("\033[33m" + "="*50 + "\033[0m")
        print("\033[33m" + "           ¡BullCode Tutor!" + "\033[0m")
        print("\033[33m" + "    Tu tutor de programación con IA local" + "\033[0m")
        print("\033[33m" + "="*50 + "\033[0m")
        print()

    def print_info(self, message: str) -> None:
        """Imprimir mensaje informativo."""
        print(f"\033[38;5;208mℹ {message}\033[0m")

    def print_success(self, message: str) -> None:
        """Imprimir mensaje de éxito."""
        print(f"\033[32m✓ {message}\033[0m")

    def print_error(self, message: str) -> None:
        """Imprimir mensaje de error."""
        print(f"\033[31m✗ {message}\033[0m")

    def print_tutor(self, message: str) -> None:
        """Imprimir mensaje del tutor."""
        print(f"\033[36m🤖 Tutor: {message}\033[0m")

    def print_user(self, message: str) -> None:
        """Imprimir mensaje del usuario."""
        print(f"\033[33m👤 Tú: {message}\033[0m")

    def get_input(self, prompt: str = "> ") -> str:
        """Obtener input del usuario."""
        try:
            return input(f"\033[38;5;208m{prompt}\033[0m").strip()
        except KeyboardInterrupt:
            print("\n\033[33m¡Hasta luego!\033[0m")
            sys.exit(0)
        except EOFError:
            print("\n\033[33m¡Hasta luego!\033[0m")
            sys.exit(0)

    def show_welcome(self) -> None:
        """Mostrar mensaje de bienvenida."""
        self.print_logo()
        self.print_header()
        self.print_info("Escribe 'new' para crear un curso")
        self.print_info("Escribe 'resume' para continuar un curso")
        self.print_info("Escribe 'help' para ver todos los comandos")
        print()

    async def run(self) -> None:
        """Ejecutar la aplicación."""
        self.show_welcome()

        while True:
            try:
                command = self.get_input()
                if not command:
                    continue

                await self.process_command(command)

            except KeyboardInterrupt:
                print("\n\033[33m¡Hasta luego!\033[0m")
                break
            except Exception as e:
                self.print_error(f"Error: {e}")
                continue

    async def process_command(self, command: str) -> None:
        """Procesar comando del usuario."""
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
            "model": self.cmd_model,
        }

        handler = handlers.get(cmd)
        if handler:
            await handler(args)
        else:
            self.print_error(f"Comando desconocido: {cmd}")
            self.print_info("Escribe '/help' para ver los comandos disponibles")

    async def cmd_help(self, args) -> None:
        """Mostrar ayuda."""
        print("\033[32m🤖 BullCode Tutor - Comandos disponibles\033[0m")
        print()
        print("\033[33m💬 Interacción principal:\033[0m")
        print("  \033[36m[texto cualquiera]\033[0m     - Preguntar al tutor (comando por defecto)")
        print("  \033[36m¿Dudas sobre React?\033[0m     - Ejemplo: cualquier pregunta")
        print()
        print("\033[33m📚 Gestión de cursos:\033[0m")
        print("  \033[36m/new\033[0m                   - Crear nuevo curso")
        print("  \033[36m/resume\033[0m                - Listar y reanudar cursos existentes")
        print("  \033[36m/list\033[0m                  - Listar todos los cursos")
        print("  \033[36m/delete <slug>\033[0m         - Eliminar un curso")
        print()
        print("\033[33m📖 Navegación y contenido:\033[0m")
        print("  \033[36m/unit <n>\033[0m              - Cambiar a unidad N")
        print("  \033[36m/read\033[0m                  - Leer material de la unidad actual")
        print("  \033[36m/progress\033[0m              - Ver progreso del curso")
        print()
        print("\033[33m🧠 Práctica y evaluación:\033[0m")
        print("  \033[36m/quiz\033[0m                  - Iniciar quiz de la unidad")
        print("  \033[36m/lab\033[0m                   - Listar labs de la unidad")
        print("  \033[36m/lab <n>\033[0m               - Seleccionar lab N")
        print("  \033[36m/edit\033[0m                  - Abrir editor en el lab actual")
        print("  \033[36m/submit\033[0m                - Evaluar y entregar lab")
        print()
        print("\033[33m🤖 Ollama:\033[0m")
        print("  \033[36m/model\033[0m                - Ver modelo actual y disponibles")
        print("  \033[36m/model <nombre>\033[0m       - Seleccionar modelo de Ollama")
        print()
        print("\033[33m💾 Import/Export:\033[0m")
        print("  \033[36m/export\033[0m                - Exportar curso a ZIP")
        print("  \033[36m/import <ruta>\033[0m         - Importar curso desde ZIP")
        print()
        print("\033[33mGeneral:\033[0m")
        print("  \033[36m/help\033[0m             - Mostrar esta ayuda")
        print("  \033[36m/quit, /exit, /q\033[0m    - Salir de la aplicación")
        print()
        print("\033[37m💡 Tip: Simplemente escribe tu pregunta para hablar con el tutor\033[0m")

    async def cmd_new(self, args) -> None:
        """Crear nuevo curso con asistente completo."""
        self.print_info("🚀 Creando nuevo curso...")
        print()

        # Recopilar información del curso
        self.print_tutor("¿Qué tema quieres aprender?")
        self.print_info("Ejemplos: Python, React, Machine Learning, DevOps, etc.")
        topic = self.get_input("Tema: ").strip()
        if not topic:
            return

        self.print_tutor(f"Tema seleccionado: {topic}")
        print()

        self.print_tutor("¿Qué nivel deseas? (beginner/intermediate/advanced)")
        level = self.get_input("Nivel: ").lower().strip()
        while level not in ["beginner", "intermediate", "advanced"]:
            self.print_error("Por favor elige: beginner, intermediate, o advanced")
            level = self.get_input("Nivel: ").lower().strip()

        self.print_tutor(f"Nivel seleccionado: {level}")
        print()

        self.print_tutor("¿Cuántas semanas tienes disponibles? (2-16)")
        weeks_input = self.get_input("Semanas: ").strip()
        try:
            weeks = int(weeks_input)
            if not 2 <= weeks <= 16:
                raise ValueError()
        except ValueError:
            self.print_error("Por favor ingresa un número entre 2 y 16")
            return

        self.print_tutor(f"Duración: {weeks} semanas")
        print()

        self.print_tutor("¿Qué stack tecnológico te interesa?")
        self.print_info("Ejemplos: Python, JavaScript, Java, C++, web development, etc.")
        stack = self.get_input("Stack: ").strip()
        if not stack:
            stack = topic  # Usar el tema como stack por defecto

        self.print_tutor(f"Stack seleccionado: {stack}")
        print()

        self.print_tutor("¿Prefieres enfoque teórico o práctico? (theory/practice/balanced)")
        focus = self.get_input("Enfoque: ").lower().strip()
        while focus not in ["theory", "practice", "balanced", "t", "p", "b"]:
            self.print_error("Por favor elige: theory, practice, o balanced")
            focus = self.get_input("Enfoque: ").lower().strip()

        # Normalizar respuesta
        focus_map = {"t": "theory", "p": "practice", "b": "balanced"}
        focus = focus_map.get(focus, focus)

        self.print_tutor(f"Enfoque: {focus}")
        print()

        # Generar syllabus usando Ollama
        self.print_info("🤖 Generando syllabus con IA local...")
        
        # Verificar si Ollama está disponible
        try:
            ollama_status = await self.content_generator.check_ollama()
            if not ollama_status.get("ok", False):
                self.print_error("Ollama no está disponible. Generando curso básico...")
                course_data = self._generate_basic_syllabus(topic, level, weeks, stack, focus)
            else:
                # Verificar si el modelo está disponible
                available_models = ollama_status.get("data", {}).get("models", [])
                model_names = [m.get("name", "") for m in available_models]
                if self.ollama_model not in model_names:
                    self.print_error(f"Modelo '{self.ollama_model}' no encontrado. Modelos disponibles: {', '.join(model_names[:5])}")
                    self.print_info("Generando curso básico como alternativa...")
                    course_data = self._generate_basic_syllabus(topic, level, weeks, stack, focus)
                else:
                    course_data = await self.content_generator.generate_syllabus(
                        topic=topic,
                        level=level,
                        duration=f"{weeks} semanas",
                        focus=focus
                    )
        except Exception as e:
            self.print_error(f"Error generando syllabus: {e}")
            self.print_info("Generando curso básico como alternativa...")
            course_data = self._generate_basic_syllabus(topic, level, weeks, stack, focus)
        

        # Confirmar creación
        confirm = self.get_input("¿Crear este curso? (y/n): ").lower().strip()
        if confirm not in ["y", "yes", "s", "si"]:
            self.print_info("Creación cancelada.")
            return

        # Crear el curso en disco
        try:
            from ..core.course import Course, CourseMetadata, Unit, Lab
            
            # Crear metadata
            metadata = CourseMetadata(
                title=course_data.get("title", topic),
                description=course_data.get("description", ""),
                level=level,
                estimated_total_time=weeks * 7 * 60,  # semanas * 7 días * 60 min/día
                stack=[stack] if stack else [],
                learning_objectives=course_data.get("learning_objectives", []),
                prerequisites=course_data.get("prerequisites", [])
            )
            
            # Crear unidades
            units = []
            for i, unit_data in enumerate(course_data.get("units", []), 1):
                labs = []
                for lab_data in unit_data.get("labs", []):
                    labs.append(
                        Lab(
                            slug=lab_data.get("slug", f"lab-{i:02d}"),
                            title=lab_data.get("title", f"Lab {i}"),
                            description=lab_data.get("description", ""),
                            difficulty=lab_data.get("difficulty", "medium"),
                            estimated_time=lab_data.get("estimated_time", 30),
                            skills=lab_data.get("skills", []),
                        )
                    )

                unit = Unit(
                    number=i,
                    slug=unit_data.get("slug", f"unit-{i}"),
                    title=unit_data.get("title", f"Unidad {i}"),
                    description=unit_data.get("description", ""),
                    learning_objectives=unit_data.get("learning_objectives", []),
                    estimated_time=unit_data.get("estimated_time", 60),
                    skills=unit_data.get("skills", []),
                    labs=labs,
                )
                units.append(unit)
            
            # Crear objeto Course
            course = Course(
                slug=course_data.get("slug", topic.lower().replace(" ", "-")),
                metadata=metadata,
                units=units
            )
            
            self.persistence.create_course(course)
            self.print_success(f"✅ Curso '{course.metadata.title}' creado exitosamente!")
            self.print_info(f"Slug: {course.slug}")
            self.print_info(f"Ubicación: {course.path}")
            print()

            # Cargar el curso
            await self.load_course(course.slug)

        except Exception as e:
            self.print_error(f"Error creando curso: {e}")

    def _generate_basic_syllabus(self, topic: str, level: str, weeks: int, stack: str, focus: str) -> dict:
        """Generar un syllabus básico cuando Ollama no está disponible."""
        # Crear estructura básica del curso
        units = []
        
        # Definir unidades básicas según el nivel
        if level == "beginner":
            unit_templates = [
                {
                    "slug": "introduccion",
                    "title": f"Introducción a {topic}",
                    "description": f"Conceptos básicos y fundamentos de {topic}",
                    "objectives": [f"Comprender los conceptos básicos de {topic}", "Instalar el entorno de desarrollo"],
                    "labs": [
                        {
                            "slug": "setup-entorno",
                            "title": "Configuración del entorno",
                            "description": "Instalar y configurar las herramientas necesarias",
                            "difficulty": "easy",
                            "estimated_time": 30
                        }
                    ]
                },
                {
                    "slug": "primeros-pasos",
                    "title": "Primeros pasos",
                    "description": "Tu primera aplicación práctica",
                    "objectives": [f"Crear tu primera aplicación en {topic}", "Comprender la estructura básica"],
                    "labs": [
                        {
                            "slug": "hola-mundo",
                            "title": "Hola Mundo",
                            "description": "Crear tu primera aplicación",
                            "difficulty": "easy",
                            "estimated_time": 45
                        }
                    ]
                }
            ]
        elif level == "intermediate":
            unit_templates = [
                {
                    "slug": "conceptos-avanzados",
                    "title": f"Conceptos avanzados de {topic}",
                    "description": f"Profundizar en {topic} con conceptos intermedios",
                    "objectives": [f"Aplicar conceptos avanzados de {topic}", "Resolver problemas complejos"],
                    "labs": [
                        {
                            "slug": "proyecto-medio",
                            "title": "Proyecto intermedio",
                            "description": "Aplicar conocimientos en un proyecto real",
                            "difficulty": "medium",
                            "estimated_time": 90
                        }
                    ]
                }
            ]
        else:  # advanced
            unit_templates = [
                {
                    "slug": "arquitectura-avanzada",
                    "title": f"Arquitectura avanzada en {topic}",
                    "description": f"Patrones y arquitecturas avanzadas para {topic}",
                    "objectives": [f"Implementar patrones de diseño avanzados", "Optimizar rendimiento"],
                    "labs": [
                        {
                            "slug": "proyecto-avanzado",
                            "title": "Proyecto avanzado",
                            "description": "Desarrollar una aplicación compleja con mejores prácticas",
                            "difficulty": "hard",
                            "estimated_time": 120
                        }
                    ]
                }
            ]
        
        # Crear unidades
        for i, template in enumerate(unit_templates, 1):
            unit = {
                "number": i,
                "slug": template["slug"],
                "title": template["title"],
                "description": template["description"],
                "learning_objectives": template["objectives"],
                "estimated_time": 60,
                "prerequisites": [],
                "skills": [f"{topic} {level}"],
                "labs": template["labs"]
            }
            units.append(unit)
        
        # Crear estructura del curso
        course_data = {
            "title": f"Curso de {topic} - Nivel {level}",
            "description": f"Aprende {topic} desde cero hasta nivel {level}. Este curso cubre los fundamentos y conceptos avanzados con enfoque práctico.",
            "level": level,
            "category": "programming",
            "estimated_total_time": weeks * 40,  # 40 horas por semana
            "prerequisites": [],
            "learning_objectives": [
                f"Comprender los conceptos fundamentales de {topic}",
                f"Desarrollar habilidades prácticas en {topic}",
                "Aplicar conocimientos en proyectos reales"
            ],
            "stack": [stack] if stack != topic else [topic],
            "tags": [topic.lower(), level, stack.lower()],
            "units": units
        }
        
        return course_data

    def _generate_basic_material(self, unit) -> str:
        """Generar material básico para una unidad cuando Ollama no está disponible."""
        material = f"""# Unidad {unit.number}: {unit.title}

## Descripción
{unit.description}

## Objetivos de Aprendizaje
"""
        
        for i, objective in enumerate(unit.learning_objectives, 1):
            material += f"{i}. {objective}\n"
        
        material += f"""

## Contenido Principal

### Introducción
Esta unidad cubre los conceptos fundamentales de {unit.title.lower()}.

### Conceptos Clave
- Concepto 1: Descripción básica
- Concepto 2: Explicación detallada
- Concepto 3: Ejemplos prácticos

### Ejemplos Prácticos
```python
# Ejemplo básico
print("Hola, mundo!")
```

### Errores Comunes
1. Error típico 1: Cómo evitarlo
2. Error típico 2: Solución recomendada

### Checklist de Aprendizaje
- [ ] Entender los conceptos básicos
- [ ] Practicar con ejemplos
- [ ] Resolver problemas relacionados
- [ ] Completar los labs de práctica

## Próximos Pasos
Una vez completada esta unidad, podrás:
- Aplicar los conceptos aprendidos
- Resolver problemas más complejos
- Avanzar a la siguiente unidad

## Recursos Adicionales
- Documentación oficial
- Tutoriales en línea
- Comunidad de desarrolladores

---
*Material generado automáticamente. Para contenido más detallado, configura Ollama.*
"""
        
        return material

    def show_welcome(self) -> None:
        """Mostrar mensaje de bienvenida."""
        self.print_logo()
        self.print_header()
        self.print_info("Escribe tu pregunta directamente o usa /comando para acciones específicas")
        self.print_info("Ejemplos: '¿Qué es React?' o '/help' para ver todos los comandos")
        print()

    async def run(self) -> None:
        """Ejecutar la aplicación."""
        self.show_welcome()

        while True:
            try:
                command = self.get_input()
                if not command:
                    continue

                await self.process_command(command)

            except KeyboardInterrupt:
                print("\n\033[33m¡Hasta luego!\033[0m")
                break
            except Exception as e:
                self.print_error(f"Error: {e}")
                continue

    async def process_command(self, command: str) -> None:
        """Procesar comando del usuario."""
        # Si no empieza con /, tratar como pregunta al tutor
        if not command.startswith('/'):
            await self.cmd_ask([command])
            return

        # Remover el / y procesar como comando
        command = command[1:]
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
            "model": self.cmd_model,
        }

        handler = handlers.get(cmd)
        if handler:
            await handler(args)
        else:
            self.print_error(f"Comando desconocido: {cmd}")
            self.print_info("Escribe '/help' para ver los comandos disponibles")

    async def cmd_resume(self, args) -> None:
        """Listar y reanudar cursos existentes."""
        courses = self.persistence.list_courses()

        if not courses:
            self.print_info("No hay cursos guardados. Usa 'new' para crear uno.")
            return

        print("\033[32m📚 Cursos disponibles:\033[0m")
        for i, course in enumerate(courses, 1):
            status_icon = "\033[32m●\033[0m" if course["has_state"] else "\033[37m○\033[0m"
            progress = f" ({course.get('progress', 0)}%)" if course.get("progress") else ""
            print(f"  {status_icon} {i}. \033[33m{course['title']}\033[0m ({course['slug']}) - {course['level']}{progress}")

        print()

        if len(args) >= 1:
            selection = args[0]
            try:
                idx = int(selection) - 1
                if 0 <= idx < len(courses):
                    await self.load_course(courses[idx]["slug"])
                else:
                    self.print_error("Número de curso inválido")
            except ValueError:
                # Intentar cargar por slug
                matching_courses = [c for c in courses if c["slug"] == selection]
                if matching_courses:
                    await self.load_course(selection)
                else:
                    self.print_error(f"Curso '{selection}' no encontrado")
        else:
            self.print_info("Usa 'resume <número>' o 'resume <slug>' para cargar un curso")
            self.print_info("O simplemente 'resume' para ver la lista")

    async def cmd_quit(self, args) -> None:
        """Salir."""
        self.print_success("¡Hasta luego!")
        sys.exit(0)

    async def cmd_unit(self, args) -> None:
        """Cambiar a una unidad específica."""
        if not self.current_course:
            self.print_error("No hay curso cargado. Usa 'resume' para cargar uno.")
            return

        if not args:
            self.print_error("Especifica el número de unidad. Ejemplo: unit 1")
            return

        try:
            unit_num = int(args[0])
        except ValueError:
            self.print_error("Número de unidad inválido")
            return

        if not 1 <= unit_num <= len(self.current_course.units):
            self.print_error(f"Unidad {unit_num} no existe. Hay {len(self.current_course.units)} unidades.")
            return

        # Cambiar unidad
        self.current_unit = self.current_course.units[unit_num - 1]
        self.current_state.current_unit = unit_num

        # Marcar como iniciada si no lo estaba
        self._get_unit_progress(unit_num)

        self.persistence.save_state(self.current_state)
        
        self.print_success(f"Unidad {unit_num}: {self.current_unit.title}")
        self.print_info("Usa 'read' para ver el material")

    async def cmd_read(self, args) -> None:
        """Leer material de la unidad actual."""
        if not self.current_course or not self.current_unit:
            self.print_error("No hay unidad seleccionada. Usa '/unit <n>' para seleccionar una.")
            return

        material_path = self.current_unit.material_path
        if not material_path or not material_path.exists():
            self.print_info("Material no encontrado. Generando...")
            
            # Generar material usando IA o fallback
            try:
                # Verificar si Ollama está disponible
                ollama_available = False
                try:
                    status = await self.content_generator.check_ollama()
                    ollama_available = status.get("ok", False)
                except Exception:
                    ollama_available = False

                if ollama_available:
                    self.print_info("Generando material con IA...")
                    material_content = await self.content_generator.generate_unit_material(
                        self.current_course, self.current_unit
                    )
                else:
                    # Generar material básico
                    self.print_info("Generando material básico...")
                    material_content = self._generate_basic_material(self.current_unit)

                # Guardar el material
                material_path.parent.mkdir(parents=True, exist_ok=True)
                with open(material_path, "w", encoding="utf-8") as f:
                    f.write(material_content)
                
                self.print_success("Material generado exitosamente!")
                
            except Exception as e:
                self.print_error(f"Error generando material: {e}")
                return

        # Leer y mostrar material con paginación simple
        try:
            with open(material_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Mostrar en páginas
            lines = content.split('\n')
            page_size = 30
            total_pages = (len(lines) - 1) // page_size + 1
            
            for page in range(total_pages):
                start_line = page * page_size
                end_line = min((page + 1) * page_size, len(lines))
                
                print(f"\033[36m=== Unidad {self.current_unit.number}: {self.current_unit.title} (Página {page+1}/{total_pages}) ===\033[0m")
                print()
                
                for line in lines[start_line:end_line]:
                    print(line)
                
                print()
                
                if page < total_pages - 1:
                    response = self.get_input("Presiona Enter para continuar, 'q' para salir: ")
                    if response.lower() in ['q', 'quit']:
                        break

            # Marcar como leído
            progress = self._get_unit_progress(self.current_unit.number)
            if progress:
                progress.material_read = True
                progress.status = progress.status or "reading"

            self.persistence.save_state(self.current_state)
            
        except Exception as e:
            self.print_error(f"Error leyendo material: {e}")

    def _generate_basic_material(self, unit) -> str:
        """Generar material básico para una unidad."""
        content = f"""# Unidad {unit.number}: {unit.title}

## Descripción
{unit.description}

## Objetivos de Aprendizaje
"""
        
        for i, objective in enumerate(unit.learning_objectives, 1):
            content += f"{i}. {objective}\n"
        
        content += f"""
## Contenido Principal

### Introducción
Esta unidad cubre los conceptos fundamentales de {unit.title.lower()}.

### Conceptos Clave
- Concepto 1: Descripción básica
- Concepto 2: Explicación detallada
- Concepto 3: Ejemplos prácticos

### Ejemplos Prácticos
```python
# Ejemplo básico
print("Hola, mundo!")
```

### Errores Comunes
1. Error típico 1: Cómo evitarlo
2. Error típico 2: Solución recomendada

### Checklist de Aprendizaje
- [ ] Entender los conceptos básicos
- [ ] Practicar con ejemplos
- [ ] Resolver problemas relacionados
- [ ] Completar los labs de práctica

## Próximos Pasos
Una vez completada esta unidad, podrás:
- Aplicar los conceptos aprendidos
- Resolver problemas más complejos
- Avanzar a la siguiente unidad

## Recursos Adicionales
- Documentación oficial
- Tutoriales en línea
- Comunidad de desarrolladores

---
*Material generado automáticamente. Para contenido más detallado, configura Ollama.*
"""
        return content

    def _ensure_unit_progress_dict(self) -> None:
        """Asegurar que unit_progress sea un diccionario."""
        if not self.current_state:
            return
        if isinstance(self.current_state.unit_progress, dict):
            return

        from ..core.state import UnitProgress

        new_progress: dict[int, UnitProgress] = {}
        for item in self.current_state.unit_progress:
            if isinstance(item, UnitProgress):
                new_progress[item.unit_number] = item
            elif isinstance(item, dict):
                progress = UnitProgress.from_dict(item)
                new_progress[progress.unit_number] = progress

        self.current_state.unit_progress = new_progress

    def _get_unit_progress(self, unit_number: int):
        """Obtener o crear progreso de unidad."""
        if not self.current_state:
            return None

        self._ensure_unit_progress_dict()
        from ..core.state import UnitProgress

        progress = self.current_state.unit_progress.get(unit_number)
        if progress is None:
            progress = UnitProgress(unit_number=unit_number)
            self.current_state.unit_progress[unit_number] = progress
        return progress

    def _get_unit_path(self, unit) -> Path:
        """Obtener ruta física de la unidad."""
        if self.current_course and self.current_course.path:
            course_path = self.current_course.path
        elif self.current_course:
            course_path = self.persistence.get_course_path(self.current_course.slug)
        else:
            raise ValueError("No hay curso cargado")

        unit_slug = f"{unit.number:02d}-{unit.slug}"
        return course_path / "units" / unit_slug

    def _ensure_lab_structure(self, unit_path: Path, lab_slug: str, lab_title: str) -> Path:
        """Crear estructura de lab si no existe."""
        lab_path = unit_path / "labs" / lab_slug
        lab_path.mkdir(parents=True, exist_ok=True)
        (lab_path / "starter").mkdir(exist_ok=True)
        (lab_path / "submission").mkdir(exist_ok=True)
        (lab_path / "tests").mkdir(exist_ok=True)

        readme_path = lab_path / "README.md"
        if not readme_path.exists():
            readme_content = f"""# {lab_title}

## Objetivo
Completar el ejercicio práctico relacionado con la unidad actual.

## Instrucciones
1. Revisa el material de la unidad con `/read`.
2. Implementa la solución en la carpeta `submission/`.
3. Ejecuta `/submit` para evaluar tu solución.

## Criterios de evaluación
- Correctitud de la solución
- Calidad del código
- Cumplimiento de requisitos
"""
            readme_path.write_text(readme_content, encoding="utf-8")

        grade_path = lab_path / "grade.json"
        if not grade_path.exists():
            grade_path.write_text("{}", encoding="utf-8")

        return lab_path

    async def cmd_progress(self, args) -> None:
        """Mostrar progreso del curso."""
        if not self.current_course or not self.current_state:
            self.print_error("No hay curso cargado.")
            return

        print(f"\033[32m📊 Progreso de '{self.current_course.metadata.title}'\033[0m")
        print()

        self._ensure_unit_progress_dict()
        total_units = len(self.current_course.units)
        completed_units = sum(
            1 for up in self.current_state.unit_progress.values() if up.status == "completed"
        )
        overall_progress = (completed_units / total_units * 100) if total_units > 0 else 0

        print(f"\033[33mProgreso general: {overall_progress:.1f}%\033[0m ({completed_units}/{total_units} unidades)")
        print()

        for unit in self.current_course.units:
            progress = self.current_state.unit_progress.get(unit.number)
            
            if progress:
                status_icon = {
                    "not_started": "○",
                    "reading": "📖",
                    "practicing": "💻", 
                    "completed": "✅"
                }.get(progress.status, "○")
                
                status_color = {
                    "not_started": "\033[37m",
                    "reading": "\033[36m",
                    "practicing": "\033[33m",
                    "completed": "\033[32m"
                }.get(progress.status, "\033[37m")
                
                material_status = "📄" if progress.material_read else "📭"
                quiz_count = len(progress.quiz_results)
                lab_count = len(progress.lab_results)
                
                print(f"  {status_color}{status_icon}\033[0m Unidad {unit.number}: {unit.title}")
                print(f"    {material_status} Material leído: {'Sí' if progress.material_read else 'No'}")
                print(f"    🧠 Quizzes completados: {quiz_count}")
                print(f"    💻 Labs completados: {lab_count}")
                if progress.completed_at:
                    print(f"    ✅ Completada: {progress.completed_at.strftime('%Y-%m-%d')}")
                print()
            else:
                print(f"  \033[37m○\033[0m Unidad {unit.number}: {unit.title} (no iniciada)")
                print()

    async def load_course(self, slug: str) -> None:
        """Cargar curso y su estado."""
        try:
            # Cargar curso
            self.current_course = self.persistence.load_course(slug)
            
            # Cargar estado
            self.current_state = self.persistence.load_state(slug)
            if self.current_state is None:
                # Crear estado inicial si no existe
                from ..core.state import CourseState
                self.current_state = CourseState(course_slug=slug)
                self.persistence.save_state(self.current_state)
            
            # Normalizar estado
            self._ensure_unit_progress_dict()

            # Establecer unidad actual
            if self.current_state.current_unit > 0 and self.current_state.current_unit <= len(self.current_course.units):
                self.current_unit = self.current_course.units[self.current_state.current_unit - 1]
            else:
                self.current_unit = self.current_course.units[0] if self.current_course.units else None
            
            self.print_success(f"Curso '{self.current_course.metadata.title}' cargado!")
            self.print_info(f"Unidad actual: {self.current_unit.title if self.current_unit else 'Ninguna'}")
            
        except Exception as e:
            self.print_error(f"Error cargando curso: {e}")
            self.current_course = None
            self.current_state = None
            self.current_unit = None


    async def cmd_ask(self, args) -> None:
        """Preguntar al tutor sobre el material actual."""
        question = " ".join(args) if args else ""
        
        if not question:
            self.print_error("¿Qué quieres preguntarle al tutor?")
            return

        if not self.current_course or not self.current_unit:
            self.print_error("No hay unidad seleccionada. Usa '/unit <n>' para seleccionar una.")
            return

        # Obtener contexto del material actual
        context = ""
        if self.current_unit.material_path and self.current_unit.material_path.exists():
            try:
                with open(self.current_unit.material_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Tomar los primeros 2000 caracteres como contexto
                    context = content[:2000] + "..." if len(content) > 2000 else content
            except Exception:
                context = "No se pudo cargar el contexto del material."

        # Preparar el prompt para el tutor
        system_prompt = f"""Eres un tutor experto en {self.current_course.metadata.title}.
Estás enseñando la unidad "{self.current_unit.title}" a un estudiante de nivel {self.current_course.metadata.level}.

Contexto del material actual:
{context}

Responde de manera pedagógica, clara y concisa. Si la pregunta no está relacionada con el material actual, redirígela al tema correspondiente.
Adapta tu respuesta al nivel del estudiante."""

        user_prompt = f"Pregunta del estudiante: {question}"

        try:
            self.print_tutor("Pensando...")
            
            # Verificar si Ollama está disponible
            ollama_available = False
            try:
                from ..llm.client import OllamaClient
                client = OllamaClient()
                status = await client.check_connection()
                ollama_available = status.get("ok", False)
            except:
                ollama_available = False

            if not ollama_available:
                # Respuesta básica sin IA
                self.print_tutor("Lo siento, no tengo acceso a IA en este momento. Te recomiendo revisar el material de la unidad actual con '/read' o cambiar a otra unidad con '/unit <n>'.")
                return

            # Crear cliente LLM
            from ..llm.client import OllamaClient, Message
            client = OllamaClient()
            
            response = await client.chat(
                messages=[
                    Message(role="system", content=system_prompt),
                    Message(role="user", content=user_prompt)
                ]
            )
            
            self.print_tutor(response.content)
            
        except Exception as e:
            self.print_error(f"Error consultando al tutor: {e}")
            self.print_info("Asegúrate de que Ollama esté ejecutándose en localhost:11434")

    def show_welcome(self) -> None:
        """Mostrar mensaje de bienvenida."""
        self.print_logo()
        self.print_header()
        self.print_info("Escribe cualquier pregunta para hablar con el tutor")
        self.print_info("O usa comandos con / al inicio: /help, /new, /read, etc.")
        print()

    async def run(self) -> None:
        """Ejecutar la aplicación."""
        self.show_welcome()

        while True:
            try:
                command = self.get_input()
                if not command:
                    continue

                await self.process_command(command)

            except KeyboardInterrupt:
                print("\n\033[33m¡Hasta luego!\033[0m")
                break
            except Exception as e:
                self.print_error(f"Error: {e}")
                continue

    async def process_command(self, command: str) -> None:
        """Procesar comando del usuario."""
        # Si no empieza con /, es una pregunta al tutor
        if not command.startswith('/'):
            await self.cmd_ask([command])
            return

        # Remover el / del comando
        command = command[1:]
        
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
            "model": self.cmd_model,
        }

        handler = handlers.get(cmd)
        if handler:
            await handler(args)
        else:
            self.print_error(f"Comando desconocido: {cmd}")
            self.print_info("Escribe '/help' para ver los comandos disponibles")

    # Placeholder para otros comandos
    async def cmd_list(self, args) -> None:
        """Listar cursos (alias de resume)."""
        await self.cmd_resume([])

    async def cmd_quiz(self, args) -> None:
        """Ejecutar quiz de la unidad actual."""
        if not self.current_course or not self.current_unit:
            self.print_error("No hay unidad seleccionada. Usa '/unit <n>' para seleccionar una.")
            return

        quiz_path = self.current_unit.quiz_path
        material_path = self.current_unit.material_path

        # Asegurar material
        if not material_path or not material_path.exists():
            self.print_info("Material no encontrado. Generando...")
            await self.cmd_read([])

        # Generar quiz si no existe
        if not quiz_path or not quiz_path.exists():
            try:
                if material_path and material_path.exists():
                    material_content = material_path.read_text(encoding="utf-8")
                else:
                    material_content = ""

                status = await self.content_generator.check_ollama()
                if status.get("ok", False):
                    self.print_info("Generando quiz con IA...")
                    quiz_data = await self.content_generator.generate_quiz(
                        self.current_unit, material_content, n_questions=5
                    )
                else:
                    quiz_data = [
                        {
                            "id": "q1",
                            "question": f"¿Cuál es el objetivo principal de la unidad {self.current_unit.title}?",
                            "options": [
                                "Comprender los conceptos básicos",
                                "Optimizar rendimiento",
                                "Crear una app completa",
                                "Ninguna de las anteriores",
                            ],
                            "answer": "Comprender los conceptos básicos",
                            "explanation": "El objetivo principal suele ser dominar los fundamentos de la unidad.",
                        }
                    ]

                quiz_path.parent.mkdir(parents=True, exist_ok=True)
                quiz_path.write_text(
                    json.dumps(quiz_data, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
            except Exception as e:
                self.print_error(f"Error generando quiz: {e}")
                return

        # Ejecutar quiz
        try:
            quiz_data = json.loads(quiz_path.read_text(encoding="utf-8"))
        except Exception as e:
            self.print_error(f"Quiz inválido: {e}")
            return

        if not isinstance(quiz_data, list) or not quiz_data:
            self.print_error("El quiz está vacío o tiene formato inválido")
            return

        from ..core.state import QuizResult

        correct_count = 0
        self.print_info("Iniciando quiz...")
        for idx, q in enumerate(quiz_data, 1):
            question = q.get("question", f"Pregunta {idx}")
            options = q.get("options") or q.get("choices") or []
            answer_key = q.get("answer") or q.get("correct_answer") or q.get("correct")

            print(f"\033[36mQ{idx}: {question}\033[0m")
            if options:
                for opt_idx, opt in enumerate(options, 1):
                    print(f"  {opt_idx}. {opt}")

            user_answer = self.get_input("Respuesta: ").strip()

            # Normalizar respuesta
            if options and user_answer.isdigit():
                opt_idx = int(user_answer) - 1
                if 0 <= opt_idx < len(options):
                    user_answer = options[opt_idx]

            is_correct = False
            if answer_key is not None:
                is_correct = str(user_answer).strip().lower() == str(answer_key).strip().lower()

            if is_correct:
                correct_count += 1
                print("\033[32m✓ Correcto\033[0m")
            else:
                print("\033[31m✗ Incorrecto\033[0m")
                if answer_key is not None:
                    print(f"Respuesta correcta: {answer_key}")

            result = QuizResult(
                question_id=str(q.get("id", idx)),
                correct=is_correct,
                answer=str(user_answer),
                score=1.0 if is_correct else 0.0,
            )

            progress = self._get_unit_progress(self.current_unit.number)
            if progress:
                progress.quiz_results.append(result)

        self.persistence.save_state(self.current_state)
        total = len(quiz_data)
        score_pct = (correct_count / total * 100) if total else 0
        self.print_success(f"Quiz completado: {correct_count}/{total} ({score_pct:.1f}%)")

    async def cmd_lab(self, args) -> None:
        """Seleccionar o crear lab de la unidad actual y abrir editor."""
        if not self.current_course or not self.current_unit:
            self.print_error("No hay unidad seleccionada. Usa '/unit <n>' para seleccionar una.")
            return

        unit_path = self._get_unit_path(self.current_unit)
        labs_dir = unit_path / "labs"
        labs_dir.mkdir(parents=True, exist_ok=True)

        # Obtener labs desde el modelo o el disco
        labs = []
        if getattr(self.current_unit, "labs", None):
            labs = [lab.slug for lab in self.current_unit.labs]
        else:
            labs = sorted([p.name for p in labs_dir.iterdir() if p.is_dir()]) if labs_dir.exists() else []

        if not labs:
            labs = ["lab-01"]

        selected_lab = None
        if args:
            selection = args[0]
            try:
                idx = int(selection) - 1
                if 0 <= idx < len(labs):
                    selected_lab = labs[idx]
                else:
                    self.print_error("Número de lab inválido")
                    return
            except ValueError:
                if selection in labs:
                    selected_lab = selection
                else:
                    self.print_error(f"Lab '{selection}' no encontrado")
                    return
        else:
            selected_lab = labs[0]

        lab_title = f"Lab {selected_lab} - {self.current_unit.title}"
        lab_path = self._ensure_lab_structure(unit_path, selected_lab, lab_title)

        # Crear starter y tests básicos si no existen
        starter_file = lab_path / "starter" / "main.py"
        if not starter_file.exists():
            starter_file.write_text(
                """def solve():\n    return "ok"\n\nif __name__ == '__main__':\n    print(solve())\n""",
                encoding="utf-8",
            )

        test_file = lab_path / "tests" / "test_main.py"
        if not test_file.exists():
            test_file.write_text(
                """from submission.main import solve\n\n\ndef test_solve():\n    assert solve() == 'ok'\n""",
                encoding="utf-8",
            )

        # Actualizar estado
        self._ensure_unit_progress_dict()
        self.current_state.current_lab = selected_lab
        progress = self._get_unit_progress(self.current_unit.number)
        if progress:
            progress.status = "practicing"
        self.persistence.save_state(self.current_state)

        self.print_success(f"Lab seleccionado: {selected_lab}")
        self.print_info(f"Ruta: {lab_path}")

        # Abrir editor automáticamente
        await self.cmd_edit([])

    async def cmd_edit(self, args) -> None:
        """Abrir editor en el lab actual (submission/)."""
        if not self.current_course or not self.current_unit:
            self.print_error("No hay unidad seleccionada. Usa '/unit <n>' primero.")
            return

        if not self.current_state or not self.current_state.current_lab:
            self.print_error("No hay lab seleccionado. Usa '/lab' para crear o seleccionar uno.")
            return

        unit_path = self._get_unit_path(self.current_unit)
        lab_slug = self.current_state.current_lab
        lab_path = self._ensure_lab_structure(unit_path, lab_slug, f"Lab {lab_slug}")

        from ..core.course import Lab
        from ..labs.workspace import LabWorkspace

        lab = Lab(slug=lab_slug, title=f"Lab {lab_slug}", description="")
        lab.path = lab_path
        lab.readme_path = lab_path / "README.md"
        lab.starter_path = lab_path / "starter"
        lab.submission_path = lab_path / "submission"
        lab.tests_path = lab_path / "tests"
        lab.grade_path = lab_path / "grade.json"

        workspace = LabWorkspace(lab, editor=self.config.editor)

        self.print_info(f"Abriendo editor en {lab.submission_path}...")
        try:
            workspace.open_editor()
        except Exception as e:
            self.print_error(f"Error abriendo editor: {e}")

    async def cmd_submit(self, args) -> None:
        """Ejecutar corrección automática del lab actual."""
        if not self.current_course or not self.current_unit:
            self.print_error("No hay unidad seleccionada. Usa '/unit <n>' primero.")
            return

        if not self.current_state or not self.current_state.current_lab:
            self.print_error("No hay lab seleccionado. Usa '/lab' primero.")
            return

        unit_path = self._get_unit_path(self.current_unit)
        lab_slug = self.current_state.current_lab
        lab_path = self._ensure_lab_structure(unit_path, lab_slug, f"Lab {lab_slug}")

        from ..core.course import Lab
        from ..labs.evaluator import PythonEvaluator
        from ..core.state import LabResult

        lab = Lab(slug=lab_slug, title=f"Lab {lab_slug}", description="")
        lab.path = lab_path
        lab.readme_path = lab_path / "README.md"
        lab.starter_path = lab_path / "starter"
        lab.submission_path = lab_path / "submission"
        lab.tests_path = lab_path / "tests"
        lab.grade_path = lab_path / "grade.json"

        evaluator = PythonEvaluator(lab)
        result = evaluator.evaluate()

        lab_result = LabResult(
            lab_slug=lab_slug,
            status="passed" if result.passed else "failed",
            score=result.score,
            max_score=result.max_score,
            passed_tests=result.passed_tests,
            total_tests=result.total_tests,
            errors=result.errors,
            suggestions=result.suggestions,
        )

        progress = self._get_unit_progress(self.current_unit.number)
        if progress:
            progress.lab_results[lab_slug] = lab_result

        self.persistence.save_state(self.current_state)

        status = "✅ Aprobado" if result.passed else "❌ Reprobado"
        self.print_info(status)
        self.print_info(f"Score: {result.score:.1f}/{result.max_score:.1f}")
        if result.errors:
            self.print_error("Errores:")
            for err in result.errors[:5]:
                print(f"  - {err}")
        if result.suggestions:
            self.print_info("Sugerencias:")
            for sug in result.suggestions[:5]:
                print(f"  - {sug}")

    async def cmd_export(self, args) -> None:
        """Exportar curso a ZIP."""
        if not self.current_course and not args:
            self.print_error("No hay curso cargado. Usa '/resume' para cargar uno.")
            return

        from ..export_import.manager import ExportImportManager

        slug = args[0] if args else self.current_course.slug
        manager = ExportImportManager(self.persistence.courses_dir)

        try:
            output_path = manager.export_course(slug)
            self.print_success(f"Curso exportado: {output_path}")
        except Exception as e:
            self.print_error(f"Error exportando curso: {e}")

    async def cmd_import(self, args) -> None:
        """Importar curso desde ZIP."""
        if not args:
            self.print_error("Especifica la ruta del ZIP. Ejemplo: /import C:\\ruta\\curso.zip")
            return

        from ..export_import.manager import ExportImportManager

        zip_path = Path(args[0])
        manager = ExportImportManager(self.persistence.courses_dir)

        try:
            slug = manager.import_course(zip_path, force=False)
            self.print_success(f"Curso importado: {slug}")
            await self.load_course(slug)
        except Exception as e:
            self.print_error(f"Error importando curso: {e}")

    async def cmd_delete(self, args) -> None:
        """Eliminar curso."""
        if not args and not self.current_course:
            self.print_error("Especifica un slug o carga un curso primero.")
            return

        slug = args[0] if args else self.current_course.slug
        confirm = self.get_input(f"¿Eliminar curso '{slug}'? (y/n): ").lower().strip()
        if confirm not in ["y", "yes", "s", "si"]:
            self.print_info("Eliminación cancelada.")
            return

        try:
            self.persistence.delete_course(slug)
            self.print_success(f"Curso '{slug}' eliminado.")
            if self.current_course and self.current_course.slug == slug:
                self.current_course = None
                self.current_state = None
                self.current_unit = None
        except Exception as e:
            self.print_error(f"Error eliminando curso: {e}")


    async def process_command(self, command: str) -> None:
        """Procesar comando del usuario."""
        # Si no empieza con /, tratar como pregunta al tutor
        if not command.startswith('/'):
            await self.cmd_ask([command])
            return

        # Remover el / y procesar como comando
        command = command[1:]
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
            "model": self.cmd_model,
        }

        handler = handlers.get(cmd)
        if handler:
            await handler(args)
        else:
            self.print_error(f"Comando desconocido: {cmd}")
            self.print_info("Escribe '/help' para ver los comandos disponibles")

    async def cmd_ask(self, args) -> None:
        """Preguntar al tutor sobre el material actual."""
        question = " ".join(args) if args else ""
        
        if not question:
            self.print_error("¿Qué quieres preguntarle al tutor?")
            return

        if not self.current_course or not self.current_unit:
            self.print_error("No hay unidad seleccionada. Usa '/unit <n>' para seleccionar una.")
            return

        # Obtener contexto del material actual
        context = ""
        if self.current_unit.material_path and self.current_unit.material_path.exists():
            try:
                with open(self.current_unit.material_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Tomar los primeros 2000 caracteres como contexto
                    context = content[:2000] + "..." if len(content) > 2000 else content
            except Exception:
                context = "No se pudo cargar el contexto del material."

        # Preparar el prompt para el tutor
        system_prompt = f"""Eres un tutor experto en {self.current_course.metadata.title}.
Estás enseñando la unidad "{self.current_unit.title}" a un estudiante de nivel {self.current_course.metadata.level}.

Contexto del material actual:
{context}

Responde de manera pedagógica, clara y concisa. Si la pregunta no está relacionada con el material actual, redirígela al tema correspondiente.
Adapta tu respuesta al nivel del estudiante."""

        user_prompt = f"Pregunta del estudiante: {question}"

        try:
            self.print_tutor("Pensando...")
            
            # Verificar si Ollama está disponible y el modelo existe
            ollama_status = await self.content_generator.check_ollama()
            if not ollama_status.get("ok", False):
                self.print_tutor("Lo siento, no tengo acceso a IA en este momento. Te recomiendo revisar el material de la unidad actual con '/read' o cambiar a otra unidad con '/unit <n>'.")
                return

            # Verificar si el modelo está disponible
            available_models = ollama_status.get("data", {}).get("models", [])
            model_names = [m.get("name", "") for m in available_models]
            if self.ollama_model not in model_names:
                self.print_tutor(f"Lo siento, el modelo '{self.ollama_model}' no está disponible. Modelos disponibles: {', '.join(model_names[:3])}. Te recomiendo revisar el material con '/read'.")
                return

            # Crear cliente LLM
            from ..llm.client import OllamaClient, Message
            client = OllamaClient(model=self.ollama_model)
            
            response = await client.chat(
                messages=[
                    Message(role="system", content=system_prompt),
                    Message(role="user", content=user_prompt)
                ]
            )
            
            self.print_tutor(response.content)
            
        except Exception as e:
            self.print_error(f"Error consultando al tutor: {e}")
            self.print_info("Asegúrate de que Ollama esté ejecutándose en localhost:11434")

    async def cmd_model(self, args) -> None:
        """Seleccionar modelo de Ollama."""
        self.print_info("🔍 Verificando modelos disponibles en Ollama...")
        
        try:
            # Verificar conexión con Ollama
            status = await self.content_generator.check_ollama()
            if not status.get("ok", False):
                self.print_error("No se puede conectar con Ollama. Asegúrate de que esté ejecutándose.")
                self.print_info("Instala Ollama desde: https://ollama.ai")
                return
            
            models_data = status.get("data", {})
            available_models = models_data.get("models", [])
            
            if not available_models:
                self.print_error("No hay modelos disponibles en Ollama.")
                self.print_info("Ejecuta: ollama pull llama2  (o cualquier modelo que quieras)")
                return
            
            # Mostrar modelos disponibles
            print("\033[32m🤖 Modelos disponibles en Ollama:\033[0m")
            print()
            
            current_model = self.ollama_model
            
            for i, model in enumerate(available_models, 1):
                model_name = model.get("name", "desconocido")
                size = model.get("size", 0)
                size_gb = size / (1024**3) if size else 0
                
                # Marcar modelo actual
                marker = " \033[32m← actual\033[0m" if model_name == current_model else ""
                
                print(f"  {i}. \033[36m{model_name}\033[0m ({size_gb:.1f} GB){marker}")
            
            print()
            
            if len(args) >= 1:
                # Seleccionar modelo por nombre o número
                selection = args[0]
                selected_model = None
                
                try:
                    # Intentar como número
                    idx = int(selection) - 1
                    if 0 <= idx < len(available_models):
                        selected_model = available_models[idx].get("name")
                except ValueError:
                    # Intentar como nombre
                    for model in available_models:
                        if model.get("name") == selection:
                            selected_model = selection
                            break
                
                if selected_model:
                    self.ollama_model = selected_model
                    # Actualizar cliente del generador
                    try:
                        self.content_generator.client.model = selected_model
                    except Exception:
                        pass

                    self.print_success(f"Modelo seleccionado: {selected_model}")
                    self.print_info("Este cambio aplica a la sesión actual")
                else:
                    self.print_error(f"Modelo '{selection}' no encontrado")
            else:
                self.print_info("Usa '/model <número>' o '/model <nombre>' para seleccionar un modelo")
                self.print_info("Ejemplos: '/model 1' o '/model llama2'")
                
        except Exception as e:
            self.print_error(f"Error consultando modelos: {e}")


async def main():
    """Función principal."""
    tutor = TutorApp()
    await tutor.run()


if __name__ == "__main__":
    asyncio.run(main())
