"""
scanner.py — Vista de escaneo de tickets con FilePicker (Soporte Móvil/Web).

Flujo de usuario:
  1. Usuario presiona el botón de adjuntar.
  2. En móvil, el OS pregunta si desea usar la Cámara o la Galería.
  3. Se ejecuta el OCR (ocr_engine.py).
  4. Se clasifican los artículos (classifier.py).
  5. Se muestra el resumen con opción de confirmar.
  6. Al confirmar, se registran las transacciones en BudgetEngine.
"""

from __future__ import annotations

import os
import flet as ft
from core.budget_engine import BudgetEngine
from core.classifier import clasificar_lista, resumir_por_categoria
from ui.dashboard import _build_nav_bar, COLORES_CATEGORIA


class ScannerView:
    def __init__(self, page: ft.Page, budget: BudgetEngine):
        self.page = page
        self.budget = budget
        self._resultado_ocr = None
        self._procesando = False
        self._picker = None

    def set_picker(self, picker: ft.FilePicker):
        """Inyecta el FilePicker global instanciado en main.py."""
        self._picker = picker

    # ─── Abrir selector nativo (Cámara o Galería) ────────────────────────────
    def _abrir_selector(self, e):
        """Abre el FilePicker. En móviles, el OS da la opción de usar la Cámara."""
        if self._picker:
            self._picker.pick_files(
                allow_multiple=False,
                file_type=ft.FilePickerFileType.IMAGE,
                dialog_title="Selecciona o toma una foto del ticket"
            )

    # ─── Procesar imagen ─────────────────────────────────────────────────────
    def _procesar_imagen(self, ruta: str):
        """Ejecuta OCR + clasificación y actualiza la UI."""
        self._procesando = True
        self.page.navigate("/scanner")

        try:
            from core.ocr_engine import extraer_texto_ticket
            resultado = extraer_texto_ticket(ruta)
            clasificar_lista(resultado.articulos)
            self._resultado_ocr = resultado
        except Exception as e:
            self._resultado_ocr = None
            self.page.overlay.append(
                ft.SnackBar(
                    ft.Text(f"Error al procesar imagen: {e}", color="white"),
                    bgcolor="#DC2626",
                    open=True,
                )
            )
            self.page.update()

        self._procesando = False
        self.page.navigate("/scanner")

    def _confirmar_gasto(self, _):
        """Registra todos los artículos del ticket como transacciones."""
        if not self._resultado_ocr:
            return

        for art in self._resultado_ocr.articulos:
            self.budget.agregar_transaccion(
                descripcion=art.nombre,
                monto=art.precio,
                categoria=art.categoria,
                es_hormiga=(art.categoria == "Gasto Hormiga"),
            )

        self._resultado_ocr = None
        self.page.navigate("/")

    # ─── Build ───────────────────────────────────────────────────────────────
    def build(self) -> ft.Control:
        nav_bar = _build_nav_bar(self.page, activo="/scanner")

        if self._resultado_ocr:
            return self._build_resultado(nav_bar)

        return self._build_captura(nav_bar)

    def _build_captura(self, nav_bar) -> ft.Control:
        """Pantalla inicial de selección de imagen."""

        area_drop = ft.Container(
            content=ft.Column([
                # Ícono principal
                ft.Container(
                    content=ft.Icon(ft.Icons.CAMERA_ALT_ROUNDED, size=64, color="#00F5C4"),
                    bgcolor="#0D2518",
                    border_radius=50,
                    padding=24,
                ),
                ft.Text("Escanear Ticket", size=22, weight=ft.FontWeight.BOLD, color="white"),
                ft.Text(
                    "Toma una foto con tu cámara o\nselecciona desde tu galería",
                    size=13,
                    color="#718096",
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=16),

                # ── Botón Único FilePicker (Cámara/Galería) ──
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.PHOTO_CAMERA_ROUNDED, color="#0A0F1E", size=20),
                        ft.Text("Tomar Foto / Elegir", size=14, color="#0A0F1E",
                                weight=ft.FontWeight.BOLD),
                    ], alignment=ft.MainAxisAlignment.CENTER, spacing=8),
                    bgcolor="#00F5C4",
                    height=56,
                    width=250,
                    border_radius=14,
                    alignment=ft.alignment.center,
                    on_click=self._abrir_selector,
                ),

                ft.Container(height=16),

                # ── Info ──
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.PHONE_ANDROID_ROUNDED, color="#4A5568", size=16),
                        ft.Text(
                            "Optimizado para tu teléfono celular",
                            size=11, color="#4A5568",
                        ),
                    ], spacing=6),
                    padding=ft.padding.symmetric(horizontal=20),
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8),
            alignment=ft.alignment.center,
            expand=True,
        )

        if self._procesando:
            area_drop = ft.Container(
                content=ft.Column([
                    ft.ProgressRing(color="#00F5C4", width=60, height=60),
                    ft.Text("Analizando ticket...", size=16, color="#00F5C4"),
                    ft.Text("OCR en proceso", size=12, color="#718096"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=16),
                alignment=ft.alignment.center,
                expand=True,
            )

        return ft.Stack([
            ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK_IOS_ROUNDED,
                            icon_color="#718096",
                            on_click=lambda _: self.page.navigate("/"),
                        ),
                        ft.Text("Escanear Ticket", size=18, weight=ft.FontWeight.BOLD, color="white"),
                    ]),
                    padding=ft.padding.symmetric(horizontal=12, vertical=16),
                ),
                area_drop,
                ft.Container(height=80),
            ], expand=True),
            ft.Container(content=nav_bar, bottom=0, left=0, right=0),
        ], expand=True)

    def _build_resultado(self, nav_bar) -> ft.Control:
        """Pantalla de revisión de resultado OCR antes de confirmar."""
        res = self._resultado_ocr
        resumen = resumir_por_categoria(res.articulos)

        filas_articulos = []
        for art in res.articulos:
            color = COLORES_CATEGORIA.get(art.categoria, "#888")
            filas_articulos.append(
                ft.Container(
                    content=ft.Row([
                        ft.Container(width=4, height=40, bgcolor=color, border_radius=2),
                        ft.Column([
                            ft.Text(art.nombre, size=13, color="white", max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(art.categoria, size=11, color=color),
                        ], expand=True, spacing=2),
                        ft.Text(f"${art.precio:.2f}", size=14, color="white", weight=ft.FontWeight.BOLD),
                    ], spacing=12),
                    bgcolor="#111827",
                    border_radius=10,
                    padding=ft.padding.symmetric(horizontal=14, vertical=8),
                )
            )

        return ft.Stack([
            ft.Column([
                # Header
                ft.Container(
                    content=ft.Row([
                        ft.IconButton(
                            icon=ft.Icons.CLOSE,
                            icon_color="#718096",
                            on_click=lambda _: self._cancelar(),
                        ),
                        ft.Text("Resultado OCR", size=18, weight=ft.FontWeight.BOLD, color="white"),
                        ft.Container(
                            content=ft.Text(f"{res.confianza:.0f}%", size=11, color="#0A0F1E", weight=ft.FontWeight.BOLD),
                            bgcolor="#00F5C4" if res.confianza > 70 else "#FFD166",
                            border_radius=20,
                            padding=ft.padding.symmetric(horizontal=10, vertical=4),
                        ),
                    ]),
                    padding=ft.padding.symmetric(horizontal=12, vertical=16),
                ),
                # Total detectado
                ft.Container(
                    content=ft.Row([
                        ft.Column([
                            ft.Text("Total detectado", size=12, color="#718096"),
                            ft.Text(f"{res.moneda}{res.total:.2f}", size=36,
                                    weight=ft.FontWeight.BOLD, color="#00F5C4",
                                    font_family="JetBrains"),
                        ]),
                        ft.Column([
                            ft.Text("Artículos", size=12, color="#718096"),
                            ft.Text(str(len(res.articulos)), size=36,
                                    weight=ft.FontWeight.BOLD, color="white"),
                        ]),
                    ], alignment=ft.MainAxisAlignment.SPACE_AROUND),
                    bgcolor="#111827",
                    border_radius=16,
                    padding=20,
                    margin=ft.margin.symmetric(horizontal=20),
                ),
                ft.Container(height=8),
                # Lista artículos
                ft.Container(
                    content=ft.Column([
                        ft.Text("Artículos detectados", size=14, weight=ft.FontWeight.W_600, color="white"),
                        ft.Container(height=8),
                        *filas_articulos,
                    ], spacing=6, scroll=ft.ScrollMode.AUTO),
                    bgcolor="#111827",
                    border_radius=16,
                    padding=20,
                    margin=ft.margin.symmetric(horizontal=20),
                    height=320,
                ),
                ft.Container(height=12),
                # Botón confirmar
                ft.Container(
                    content=ft.Container(
                        content=ft.Text("✅ Confirmar y Registrar", size=14, color="#0A0F1E",
                                        weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                        bgcolor="#00F5C4",
                        height=56,
                        border_radius=16,
                        alignment=ft.alignment.center,
                        on_click=self._confirmar_gasto,
                    ),
                    margin=ft.margin.symmetric(horizontal=20),
                ),
                ft.Container(height=80),
            ], scroll=ft.ScrollMode.AUTO, expand=True),
            ft.Container(content=nav_bar, bottom=0, left=0, right=0),
        ], expand=True)

    def _cancelar(self):
        self._resultado_ocr = None
        self.page.navigate("/scanner")
