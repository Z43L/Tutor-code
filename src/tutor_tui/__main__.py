"""Punto de entrada principal."""

import sys


def main() -> int:
    """Ejecutar aplicación."""
    from .tui.app import TutorApp

    app = TutorApp()
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
