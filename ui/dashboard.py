"""
dashboard.py — Vista principal del Dashboard.

Muestra:
  - Presupuesto diario de supervivencia.
  - Gráfico circular de gastos por categoría.
  - Alertas de Gastos Hormiga.
  - Botón flotante de cámara.
  - Botón de ajustar presupuesto.
"""

from __future__ import annotations
import math
import flet as ft
from datetime import date, timedelta
from core.budget_engine import BudgetEngine

# Paleta de colores por categoría
COLORES_CATEGORIA = {
    "Alimentación":    "#00F5C4",
    "Hogar":           "#7B61FF",
    "Uso Personal":    "#FF6B6B",
    "Entretenimiento": "#FFD166",
    "Gasto Hormiga":   "#FF4444",
    "Sin Categoría":   "#4A5568",
}


class DashboardView:
    def __init__(self, page: ft.Page, budget: BudgetEngine):
        self.page = page
        self.budget = budget

    # ─── Gráfico de dona SVG ─────────────────────────────────────────────────
    def _construir_dona(self, gastos: dict[str, float]) -> ft.Control:
        """Genera un gráfico de dona con SVG puro."""
        if not gastos:
            # Estado vacío
            return ft.Container(
                content=ft.Column([
                    ft.Text("📊", size=48),
                    ft.Text("Sin gastos aún", color="#4A5568", size=14),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.alignment.center,
                height=200,
            )

        total = sum(gastos.values()) or 1
        radio_ext, radio_int = 80, 50
        cx, cy = 100, 100
        segmentos_svg = []
        angulo_inicio = -90.0

        def polar(r, deg):
            rad = math.radians(deg)
            return cx + r * math.cos(rad), cy + r * math.sin(rad)

        for categoria, monto in gastos.items():
            pct = monto / total
            angulo_fin = angulo_inicio + pct * 360

            # Arco externo
            x1e, y1e = polar(radio_ext, angulo_inicio)
            x2e, y2e = polar(radio_ext, angulo_fin)
            # Arco interno
            x1i, y1i = polar(radio_int, angulo_fin)
            x2i, y2i = polar(radio_int, angulo_inicio)

            arco_largo = 1 if (angulo_fin - angulo_inicio) > 180 else 0
            color = COLORES_CATEGORIA.get(categoria, "#888")

            path = (
                f"M {x1e:.1f} {y1e:.1f} "
                f"A {radio_ext} {radio_ext} 0 {arco_largo} 1 {x2e:.1f} {y2e:.1f} "
                f"L {x1i:.1f} {y1i:.1f} "
                f"A {radio_int} {radio_int} 0 {arco_largo} 0 {x2i:.1f} {y2i:.1f} Z"
            )
            segmentos_svg.append(f'<path d="{path}" fill="{color}" opacity="0.92"/>')
            angulo_inicio = angulo_fin

        svg_content = f"""
        <svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
          {''.join(segmentos_svg)}
          <circle cx="{cx}" cy="{cy}" r="32" fill="#111827"/>
          <text x="{cx}" y="{cy-8}" text-anchor="middle" fill="#00F5C4"
                font-family="sans-serif" font-size="11" font-weight="bold">GASTOS</text>
          <text x="{cx}" y="{cy+10}" text-anchor="middle" fill="white"
                font-family="sans-serif" font-size="14" font-weight="bold">
            ${total:.0f}
          </text>
        </svg>"""

        return ft.Container(
            content=ft.Image(src_base64=_svg_to_b64(svg_content), width=200, height=200),
            alignment=ft.alignment.center,
        )

    # ─── Leyenda de categorías ─────────────────────────────────────────────────
    def _leyenda(self, gastos: dict[str, float]) -> ft.Control:
        total = sum(gastos.values()) or 1
        items = []
        for cat, monto in gastos.items():
            pct = round(monto / total * 100, 1)
            color = COLORES_CATEGORIA.get(cat, "#888")
            items.append(
                ft.Row([
                    ft.Container(width=10, height=10, bgcolor=color, border_radius=2),
                    ft.Text(cat, size=12, color="#CBD5E0", expand=True),
                    ft.Text(f"${monto:.2f}", size=12, color="white", weight=ft.FontWeight.BOLD),
                    ft.Text(f"{pct}%", size=11, color="#718096"),
                ], spacing=8)
            )
        return ft.Column(items, spacing=6)

    # ─── Tarjeta de alerta hormiga ────────────────────────────────────────────
    def _tarjeta_hormiga(self, alerta) -> ft.Control:
        return ft.Container(
            content=ft.Row([
                ft.Text("🐜", size=24),
                ft.Column([
                    ft.Text(alerta.categoria_hormiga, size=13, weight=ft.FontWeight.BOLD, color="#FF4444"),
                    ft.Text(
                        f"${alerta.gasto_semanal:.2f}/sem → ${alerta.impacto_mensual_proyectado:.2f}/mes",
                        size=12, color="#FC8181",
                    ),
                ], spacing=2, expand=True),
            ], spacing=12),
            bgcolor="#2D1B1B",
            border=ft.border.all(1, "#FF4444"),
            border_radius=12,
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
        )

    # ─── Panel de configuración de presupuesto ───────────────────────────────
    def _build_config_panel(self) -> ft.Control:
        """Panel para ajustar presupuesto inicial y días."""
        estado = self.budget.estado_presupuesto()

        saldo_input = ft.TextField(
            value=str(int(self.budget.saldo_inicial)),
            label="Presupuesto inicial ($)",
            prefix=ft.Text("$ ", color="#718096"),
            border_color="#7B61FF",
            focused_border_color="#00F5C4",
            color="white",
            label_style=ft.TextStyle(color="#718096"),
            width=260,
            border_radius=14,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        dias_input = ft.TextField(
            value=str(self.budget.dias_para_cobro()),
            label="Días hasta próximo ingreso",
            border_color="#7B61FF",
            focused_border_color="#00F5C4",
            color="white",
            label_style=ft.TextStyle(color="#718096"),
            width=260,
            border_radius=14,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        def guardar_config(e):
            try:
                nuevo_saldo = float(saldo_input.value)
                dias = int(dias_input.value)
                if nuevo_saldo <= 0 or dias <= 0:
                    raise ValueError("Los valores deben ser positivos")
                nueva_fecha = date.today() + timedelta(days=dias)
                self.budget.saldo_inicial = nuevo_saldo
                self.budget.fecha_proximo_ingreso = nueva_fecha
                self.budget._guardar_cache()
                self.page.navigate("/")
            except ValueError:
                pass  # Ignorar valores inválidos

        def cancelar(e):
            self.page.navigate("/")

        nav_bar = _build_nav_bar(self.page, activo="/")

        return ft.Stack([
            ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK_IOS_ROUNDED,
                            icon_color="#718096",
                            on_click=cancelar,
                        ),
                        ft.Text("Ajustar Presupuesto", size=18, weight=ft.FontWeight.BOLD, color="white"),
                    ]),
                    padding=ft.padding.symmetric(horizontal=12, vertical=16),
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Container(
                            content=ft.Column([
                                ft.Text("⚙️", size=40),
                                ft.Text("Configurar Presupuesto",
                                        size=20, weight=ft.FontWeight.BOLD, color="white"),
                                ft.Text("Establece tu monto disponible y los días\nhasta tu próximo ingreso.",
                                        size=13, color="#718096", text_align=ft.TextAlign.CENTER),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                            padding=ft.padding.symmetric(vertical=20),
                        ),
                        ft.Container(
                            content=ft.Column([
                                saldo_input,
                                ft.Container(height=4),
                                dias_input,
                                ft.Container(height=16),
                                ft.Container(
                                    content=ft.Text("💾 Guardar Configuración", size=14,
                                                    color="#0A0F1E", weight=ft.FontWeight.BOLD,
                                                    text_align=ft.TextAlign.CENTER),
                                    bgcolor="#00F5C4",
                                    height=52,
                                    width=260,
                                    border_radius=14,
                                    alignment=ft.alignment.center,
                                    on_click=guardar_config,
                                ),
                                ft.Container(height=8),
                                ft.Container(
                                    content=ft.Text("Cancelar", size=13,
                                                    color="#718096",
                                                    text_align=ft.TextAlign.CENTER),
                                    height=40,
                                    width=260,
                                    border_radius=14,
                                    alignment=ft.alignment.center,
                                    on_click=cancelar,
                                ),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
                            bgcolor="#111827",
                            border_radius=20,
                            padding=24,
                            margin=ft.margin.symmetric(horizontal=20),
                        ),
                        ft.Container(height=20),
                        ft.Container(
                            content=ft.Column([
                                ft.Text("📌 Valores actuales", size=13,
                                        weight=ft.FontWeight.W_600, color="#718096"),
                                ft.Row([
                                    ft.Text("Saldo inicial:", size=12, color="#718096"),
                                    ft.Text(f"${estado.saldo_inicial:.2f}", size=12,
                                            color="#00F5C4", weight=ft.FontWeight.BOLD),
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ft.Row([
                                    ft.Text("Días restantes:", size=12, color="#718096"),
                                    ft.Text(f"{estado.dias_restantes} días", size=12,
                                            color="#00F5C4", weight=ft.FontWeight.BOLD),
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ft.Row([
                                    ft.Text("Total gastado:", size=12, color="#718096"),
                                    ft.Text(f"${estado.total_gastado:.2f}", size=12,
                                            color="#FF6B6B", weight=ft.FontWeight.BOLD),
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ], spacing=8),
                            bgcolor="#0D1117",
                            border_radius=12,
                            padding=ft.padding.symmetric(horizontal=16, vertical=12),
                            margin=ft.margin.symmetric(horizontal=20),
                        ),
                    ], spacing=8, scroll=ft.ScrollMode.AUTO),
                    expand=True,
                ),
                ft.Container(height=80),
            ], expand=True),
            ft.Container(content=nav_bar, bottom=0, left=0, right=0),
        ], expand=True)

    # ─── Build principal ──────────────────────────────────────────────────────
    def build(self) -> ft.Control:
        estado = self.budget.estado_presupuesto()
        gastos = self.budget.gastos_por_categoria()
        alertas = self.budget.detectar_gastos_hormiga()

        # ── Header ──
        header = ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.Text("VisionFlow", size=11, color="#718096", font_family="Sora"),
                    ft.Text("Finance", size=22, weight=ft.FontWeight.BOLD, color="white"),
                ], spacing=0),
                ft.Container(expand=True),
                ft.IconButton(
                    icon=ft.Icons.SETTINGS_ROUNDED,
                    icon_color="#718096",
                    tooltip="Ajustar presupuesto",
                    on_click=lambda _: self.page.navigate("/config"),
                ),
            ]),
            padding=ft.padding.symmetric(horizontal=20, vertical=16),
        )

        # ── Tarjeta presupuesto diario ──
        semaforo_color = (
            "#00F5C4" if estado.porcentaje_utilizado < 60
            else "#FFD166" if estado.porcentaje_utilizado < 85
            else "#FF4444"
        )
        tarjeta_presupuesto = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Presupuesto diario", size=12, color="#718096"),
                    ft.Container(
                        content=ft.Text(
                            f"{estado.dias_restantes}d restantes",
                            size=11, color="#0A0F1E", weight=ft.FontWeight.BOLD,
                        ),
                        bgcolor=semaforo_color,
                        border_radius=20,
                        padding=ft.padding.symmetric(horizontal=10, vertical=4),
                    ),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Text(
                    f"${estado.presupuesto_diario:.2f}",
                    size=42,
                    weight=ft.FontWeight.BOLD,
                    color=semaforo_color,
                    font_family="JetBrains",
                ),
                ft.ProgressBar(
                    value=min(estado.porcentaje_utilizado / 100, 1.0),
                    bgcolor="#1F2937",
                    color=semaforo_color,
                    bar_height=6,
                    border_radius=3,
                ),
                ft.Row([
                    ft.Text(f"Gastado: ${estado.total_gastado:.2f}", size=11, color="#718096"),
                    ft.Text(f"Disponible: ${estado.saldo_actual:.2f}", size=11, color="#718096"),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ], spacing=10),
            bgcolor="#111827",
            border_radius=20,
            padding=20,
            margin=ft.margin.symmetric(horizontal=20),
        )

        # ── Sección gráfico ──
        seccion_grafico = ft.Container(
            content=ft.Column([
                ft.Text("Distribución de gastos", size=14, weight=ft.FontWeight.W_600, color="white"),
                ft.Row([
                    self._construir_dona(gastos),
                    ft.Container(content=self._leyenda(gastos), expand=True),
                ], alignment=ft.MainAxisAlignment.START),
            ], spacing=12),
            bgcolor="#111827",
            border_radius=20,
            padding=20,
            margin=ft.margin.symmetric(horizontal=20),
        )

        # ── Alertas Hormiga ──
        alertas_section = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("🐜 Gastos Hormiga", size=14, weight=ft.FontWeight.W_600, color="#FF4444"),
                    ft.Text(f"({len(alertas)})", size=12, color="#718096"),
                ]),
                *([self._tarjeta_hormiga(a) for a in alertas]
                  if alertas
                  else [ft.Text("✅ Sin alertas esta semana", size=13, color="#48BB78")]),
            ], spacing=10),
            bgcolor="#111827",
            border_radius=20,
            padding=20,
            margin=ft.margin.symmetric(horizontal=20),
        ) if alertas else ft.Container(
            content=ft.Row([
                ft.Text("✅", size=20),
                ft.Text("Sin alertas de Gasto Hormiga esta semana", size=13, color="#48BB78"),
            ], spacing=10),
            bgcolor="#0D2518",
            border_radius=12,
            padding=ft.padding.symmetric(horizontal=20, vertical=14),
            margin=ft.margin.symmetric(horizontal=20),
        )

        # ── Navegación inferior ──
        nav_bar = _build_nav_bar(self.page, activo="/")

        # ── FAB escanear ──
        fab = ft.FloatingActionButton(
            icon=ft.Icons.CAMERA_ALT_ROUNDED,
            bgcolor="#00F5C4",
            foreground_color="#0A0F1E",
            on_click=lambda _: self.page.navigate("/scanner"),
            elevation=8,
        )

        return ft.Stack([
            ft.Column([
                header,
                ft.Container(height=8),
                tarjeta_presupuesto,
                ft.Container(height=12),
                seccion_grafico,
                ft.Container(height=12),
                alertas_section,
                ft.Container(height=80),  # Espacio para nav bar
            ], scroll=ft.ScrollMode.AUTO, expand=True),
            ft.Container(content=nav_bar, bottom=0, left=0, right=0),
            ft.Container(content=fab, bottom=70, right=24),
        ], expand=True)


# ─── Utilidades compartidas ───────────────────────────────────────────────────

def _svg_to_b64(svg: str) -> str:
    """Convierte SVG a base64 para usar en ft.Image."""
    import base64
    return base64.b64encode(svg.encode()).decode()


def _build_nav_bar(page: ft.Page, activo: str) -> ft.Control:
    """Barra de navegación inferior compartida entre vistas."""
    items = [
        ("/",          ft.Icons.HOME_ROUNDED,       "Inicio"),
        ("/historial", ft.Icons.RECEIPT_LONG,       "Historial"),
        ("/scanner",   ft.Icons.CAMERA_ALT_ROUNDED, "Escanear"),
        ("/consejos",  ft.Icons.LIGHTBULB_ROUNDED,  "Consejos"),
    ]

    def nav_item(ruta, icono, label):
        is_active = ruta == activo
        return ft.GestureDetector(
            content=ft.Column([
                ft.Icon(
                    icono,
                    color="#00F5C4" if is_active else "#4A5568",
                    size=22,
                ),
                ft.Text(
                    label,
                    size=10,
                    color="#00F5C4" if is_active else "#4A5568",
                ),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
            on_tap=lambda _, r=ruta: page.navigate(r),
        )

    return ft.Container(
        content=ft.Row(
            [nav_item(r, i, l) for r, i, l in items],
            alignment=ft.MainAxisAlignment.SPACE_AROUND,
        ),
        bgcolor="#0D1117",
        border=ft.border.only(top=ft.BorderSide(1, "#1F2937")),
        padding=ft.padding.symmetric(vertical=12, horizontal=16),
    )
