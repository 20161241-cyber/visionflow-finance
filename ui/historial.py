"""
historial.py — Vista de historial de transacciones.
"""

from __future__ import annotations
from datetime import datetime
import flet as ft
from core.budget_engine import BudgetEngine
from ui.dashboard import _build_nav_bar, COLORES_CATEGORIA


class HistorialView:
    def __init__(self, page: ft.Page, budget: BudgetEngine):
        self.page = page
        self.budget = budget

    def _tarjeta_tx(self, tx) -> ft.Control:
        color = COLORES_CATEGORIA.get(tx.categoria, "#888")
        try:
            fecha_dt = datetime.fromisoformat(tx.fecha)
            fecha_str = fecha_dt.strftime("%d %b, %H:%M")
        except Exception:
            fecha_str = tx.fecha[:10]

        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Text(_emoji_categoria(tx.categoria), size=20),
                    bgcolor=f"{color}22",
                    border_radius=12,
                    padding=10,
                    width=48,
                    height=48,
                    alignment=ft.alignment.Alignment.CENTER,
                ),
                ft.Column([
                    ft.Text(tx.descripcion, size=13, color="white",
                            max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(f"{tx.categoria} · {fecha_str}", size=11, color="#718096"),
                ], expand=True, spacing=2),
                ft.Text(f"-${tx.monto:.2f}", size=14, color="#FF6B6B",
                        weight=ft.FontWeight.BOLD),
            ], spacing=12),
            bgcolor="#111827",
            border_radius=12,
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        )

    def build(self) -> ft.Control:
        nav_bar = _build_nav_bar(self.page, activo="/historial")
        txs = list(reversed(self.budget.transacciones))

        contenido = (
            [self._tarjeta_tx(t) for t in txs]
            if txs
            else [ft.Container(
                content=ft.Column([
                    ft.Text("📋", size=48),
                    ft.Text("Sin transacciones aún", size=16, color="#4A5568"),
                    ft.Text("Escanea tu primer ticket 📸", size=13, color="#718096"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                alignment=ft.alignment.Alignment.CENTER,
                expand=True,
            )]
        )

        return ft.Stack([
            ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.IconButton(ft.Icons.ARROW_BACK_IOS_ROUNDED, icon_color="#718096",
                                      on_click=lambda _: self.page.navigate("/")),
                        ft.Text("Historial", size=18, weight=ft.FontWeight.BOLD, color="white"),
                        ft.Container(
                            content=ft.Text(str(len(txs)), size=11, color="#0A0F1E",
                                            weight=ft.FontWeight.BOLD),
                            bgcolor="#7B61FF",
                            border_radius=20,
                            padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                        ),
                    ]),
                    padding=ft.Padding.symmetric(horizontal=12, vertical=16),
                ),
                ft.Container(
                    content=ft.Column(contenido, spacing=8, scroll=ft.ScrollMode.AUTO),
                    padding=ft.Padding.symmetric(horizontal=20),
                    expand=True,
                ),
                ft.Container(height=80),
            ], expand=True),
            ft.Container(content=nav_bar, bottom=0, left=0, right=0),
        ], expand=True)


def _emoji_categoria(cat: str) -> str:
    return {
        "Alimentación":     "🥗",
        "Hogar":            "🏠",
        "Uso Personal":     "👤",
        "Entretenimiento":  "🎮",
        "Gasto Hormiga":    "🐜",
    }.get(cat, "💳")
