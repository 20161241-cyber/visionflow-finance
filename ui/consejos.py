"""
consejos.py — Vista de Consejos de Ahorro generados dinámicamente.
Los consejos se adaptan al estado financiero del usuario.
"""

from __future__ import annotations
import flet as ft
from core.budget_engine import BudgetEngine
from ui.dashboard import _build_nav_bar


# ─── Banco de consejos por situación ─────────────────────────────────────────

CONSEJOS_CRITICOS = [
    ("🚨", "Modo emergencia", "Tu saldo es crítico. Suspende todos los gastos no esenciales hoy mismo. Solo alimentación básica.", "#FF4444"),
    ("🥡", "Cocina en casa", "Cocinar en casa ahorra hasta $2,500/mes vs comer fuera. Un arroz con huevo cuesta $15 vs $80 en la calle.", "#FF6B6B"),
    ("📵", "Desactiva notificaciones de apps", "Cada notificación de Rappi o UberEats es una trampa psicológica. Desactívalas hasta cobrar.", "#FC8181"),
]

CONSEJOS_ADVERTENCIA = [
    ("⚠️", "Revisa tus Gastos Hormiga", "Los pequeños gastos ($15–$80) son invisibles pero devastadores. $50 diarios = $1,500/mes.", "#FFD166"),
    ("💧", "Lleva agua de casa", "Una botella reutilizable ahorra $600–$900 al mes en bebidas de conveniencia.", "#FBBF24"),
    ("🛒", "Lista antes de comprar", "Ir al súper sin lista aumenta el gasto hasta 40%. Escribe EXACTAMENTE lo que necesitas.", "#F59E0B"),
    ("🏧", "Retira efectivo semanal", "Pagar con efectivo duele más psicológicamente. Limítate a un sobre con tu presupuesto semanal.", "#FFD166"),
]

CONSEJOS_SALUDABLE = [
    ("🎯", "Regla 50/30/20", "50% necesidades básicas, 30% gastos personales, 20% ahorro. Ajusta según tu quincena.", "#00F5C4"),
    ("☕", "Café de olla en casa", "Un café de preparación casera cuesta $4 vs $45 en Starbucks. Ahorro de $1,200/mes.", "#34D399"),
    ("📦", "Compra al mayoreo", "Frijol, arroz, aceite y papel higiénico al mayoreo = 30% más barato que tiendita.", "#10B981"),
    ("🎮", "Entretenimiento gratuito", "YouTube, podcasts, bibliotecas públicas, parques. El ocio no tiene que costar nada.", "#00F5C4"),
    ("🤝", "Comparte suscripciones", "Netflix, Spotify Duo, etc. Dividir entre 2–4 personas puede ahorrarte $150–$300/mes.", "#6EE7B7"),
]

CONSEJOS_HORMIGA = [
    ("🐜", "El efecto latte", "Si gastas $45 en café 3 veces/semana = $540/mes = $6,480/año. ¿Vale la pena?", "#FF4444"),
    ("🏪", "Evita las tiendas de conveniencia", "OXXO cobra hasta 40% más que el súper. Planifica y compra en volumen.", "#FF6B6B"),
    ("🧾", "Fotografía cada ticket", "La conciencia es el primer paso. VisionFlow te ayuda a ver exactamente a dónde va tu dinero.", "#FC8181"),
]


class ConsejosView:
    def __init__(self, page: ft.Page, budget: BudgetEngine):
        self.page = page
        self.budget = budget

    def _seleccionar_consejos(self) -> list[tuple]:
        """Selecciona consejos según el estado financiero actual."""
        estado = self.budget.estado_presupuesto()
        alertas = self.budget.detectar_gastos_hormiga()
        consejos = []

        # Consejos críticos si gasto > 85%
        if estado.porcentaje_utilizado > 85:
            consejos.extend(CONSEJOS_CRITICOS)
        elif estado.porcentaje_utilizado > 60:
            consejos.extend(CONSEJOS_ADVERTENCIA)
        else:
            consejos.extend(CONSEJOS_SALUDABLE)

        # Siempre agregar consejos hormiga si hay alertas
        if alertas:
            consejos.extend(CONSEJOS_HORMIGA)

        return consejos[:6]  # Máximo 6 consejos

    def _tarjeta_consejo(self, emoji: str, titulo: str, cuerpo: str, color: str) -> ft.Control:
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(emoji, size=24),
                    ft.Text(titulo, size=14, weight=ft.FontWeight.BOLD, color=color),
                ], spacing=10),
                ft.Text(cuerpo, size=13, color="#CBD5E0"),
            ], spacing=8),
            bgcolor="#111827",
            border=ft.Border.only(left=ft.BorderSide(3, color)),
            border_radius=12,
            padding=ft.Padding.symmetric(horizontal=16, vertical=14),
        )

    def _meta_ahorro(self, estado) -> ft.Control:
        """Tarjeta de meta de ahorro proyectada."""
        ahorro_posible = max(estado.presupuesto_diario * 0.15, 0)
        proyeccion_mensual = round(ahorro_posible * 30, 2)
        return ft.Container(
            content=ft.Column([
                ft.Text("💰 Si ahorras 15% diario...", size=13, color="#FFD166",
                        weight=ft.FontWeight.W_600),
                ft.Text(
                    f"${ahorro_posible:.2f}/día → ${proyeccion_mensual:.2f}/mes",
                    size=20, weight=ft.FontWeight.BOLD, color="#00F5C4",
                    font_family="JetBrains",
                ),
                ft.Text("Un fondo de emergencia en 3 meses 🎯", size=12, color="#718096"),
            ], spacing=6),
            bgcolor="#0D2518",
            border=ft.Border.all(1, "#00F5C4"),
            border_radius=16,
            padding=20,
        )

    def build(self) -> ft.Control:
        nav_bar = _build_nav_bar(self.page, activo="/consejos")
        estado = self.budget.estado_presupuesto()
        consejos = self._seleccionar_consejos()

        return ft.Stack([
            ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.IconButton(ft.Icons.ARROW_BACK_IOS_ROUNDED, icon_color="#718096",
                                      on_click=lambda _: self.page.navigate("/")),
                        ft.Text("Consejos de Ahorro", size=18, weight=ft.FontWeight.BOLD, color="white"),
                    ]),
                    padding=ft.Padding.symmetric(horizontal=12, vertical=16),
                ),
                ft.Container(
                    content=ft.Column([
                        self._meta_ahorro(estado),
                        ft.Container(height=4),
                        ft.Text("Consejos para ti hoy", size=14, weight=ft.FontWeight.W_600,
                                color="#718096"),
                        *[self._tarjeta_consejo(*c) for c in consejos],
                    ], spacing=12, scroll=ft.ScrollMode.AUTO),
                    padding=ft.Padding.symmetric(horizontal=20),
                    expand=True,
                ),
                ft.Container(height=80),
            ], expand=True),
            ft.Container(content=nav_bar, bottom=0, left=0, right=0),
        ], expand=True)
