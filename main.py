"""
VisionFlow Finance - Aplicación principal
Punto de entrada y navegación Flet multiplataforma.
"""

import os
import sys

# ─── Asegurar que el directorio raíz del proyecto esté en sys.path ────────────
# Esto es CRÍTICO para APK en Android: el runtime de Flet puede ejecutar
# main.py desde un directorio empaquetado donde los imports relativos
# como "from ui.dashboard import ..." fallan sin esta corrección.
_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

import flet as ft
from ui.dashboard import DashboardView
from ui.scanner import ScannerView
from ui.historial import HistorialView
from ui.consejos import ConsejosView
from ui.camera import CameraView
from core.budget_engine import BudgetEngine


def main(page: ft.Page):
    """Función principal de la aplicación Flet."""

    # ─── Configuración global de la página ───────────────────────────────────
    page.title = "VisionFlow Finance"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0A0F1E"
    page.padding = 0
    page.fonts = {
        "Sora": "https://fonts.gstatic.com/s/sora/v12/xMQOuFFYT72X5wkB_18qmnndmSdSnh-A.woff2",
        "JetBrains": "https://fonts.gstatic.com/s/jetbrainsmono/v18/tDbY2o-flEEny0FZhsfKu5WU4zr3E_BX0PnT8RD8yKxjPVmUsaaDhw.woff2",
    }
    page.theme = ft.Theme(
        font_family="Sora",
        color_scheme=ft.ColorScheme(
            primary="#00F5C4",
            secondary="#7B61FF",
            surface="#111827",
            on_primary="#0A0F1E",
        ),
    )

    # ─── Motor de presupuesto compartido ─────────────────────────────────────
    budget_engine = BudgetEngine()

    dashboard = DashboardView(page, budget_engine)
    scanner   = ScannerView(page, budget_engine)
    historial = HistorialView(page, budget_engine)
    consejos  = ConsejosView(page, budget_engine)
    camera_view = CameraView(page, on_capture=scanner._procesar_imagen)

    file_picker = ft.FilePicker()
    page.services.append(file_picker)
    
    # Inyectar el picker para que el scanner pueda llamarlo
    scanner.set_picker(file_picker)

    views_map = {
        "/":          dashboard,
        "/scanner":   scanner,
        "/historial": historial,
        "/consejos":  consejos,
        "/camera":    camera_view,
        "/config":    None,  # Handled specially below
    }

    def navigate(route: str):
        """Navega a una ruta específica reconstruyendo los controles."""
        page.overlay.clear()
        page.controls.clear()
        if route == "/config":
            view_content = dashboard._build_config_panel()
        else:
            view_obj = views_map.get(route, dashboard)
            view_content = view_obj.build()
        page.controls.append(view_content)
        page.update()

    # Inyectar función de navegación en la página para uso en vistas
    page.navigate = navigate

    # Cargar vista inicial
    navigate("/")


if __name__ == "__main__":
    ft.run(main, assets_dir="assets")