"""
consejos.py — Vista de Consejos de Ahorro y Asistente IA Groq.
"""

from __future__ import annotations
import flet as ft
from core.budget_engine import BudgetEngine
from ui.dashboard import _build_nav_bar
import os

# Flet no soporta importar AsyncGroq si no está instalado (como en algunos entornos), lo cargaremos dinámicamente
try:
    import groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False

# ─── Banco de consejos por situación ─────────────────────────────────────────

CONSEJOS_CRITICOS = [
    ("🚨", "Modo emergencia", "Tu saldo es crítico. Suspende todos los gastos no esenciales.", "#FF4444"),
    ("🥡", "Cocina en casa", "Cocinar en casa ahorra hasta $2,500/mes vs comer fuera.", "#FF6B6B"),
]

CONSEJOS_ADVERTENCIA = [
    ("⚠️", "Revisa tus Gastos Hormiga", "Los pequeños gastos son invisibles pero devastadores.", "#FFD166"),
    ("💧", "Lleva agua de casa", "Ahorra $600–$900 al mes en bebidas de conveniencia.", "#FBBF24"),
]

CONSEJOS_SALUDABLE = [
    ("🎯", "Regla 50/30/20", "50% necesidades básicas, 30% gastos personales, 20% ahorro.", "#00F5C4"),
    ("☕", "Café de olla en casa", "Un café casero cuesta $4 vs $45 en Starbucks.", "#34D399"),
]

CONSEJOS_HORMIGA = [
    ("🐜", "El efecto latte", "Si gastas $45 en café 3 veces/semana = $540/mes.", "#FF4444"),
]


class ConsejosView:
    def __init__(self, page: ft.Page, budget: BudgetEngine):
        self.page = page
        self.budget = budget
        
        # Estado del Chat IA
        self.chat_messages = []
        self.chat_listview = ft.ListView(expand=True, spacing=10, auto_scroll=True)
        self.chat_input = ft.TextField(
            hint_text="Pregunta cómo ahorrar...",
            autofocus=False,
            shift_enter=True,
            min_lines=1,
            max_lines=3,
            filled=True,
            expand=True,
            border_color="#7B61FF",
            focused_border_color="#00F5C4",
            border_radius=20,
            on_submit=self._enviar_mensaje,
        )

    def _seleccionar_consejos(self) -> list[tuple]:
        estado = self.budget.estado_presupuesto()
        alertas = self.budget.detectar_gastos_hormiga()
        consejos = []

        if estado.porcentaje_utilizado > 85:
            consejos.extend(CONSEJOS_CRITICOS)
        elif estado.porcentaje_utilizado > 60:
            consejos.extend(CONSEJOS_ADVERTENCIA)
        else:
            consejos.extend(CONSEJOS_SALUDABLE)

        if alertas:
            consejos.extend(CONSEJOS_HORMIGA)

        return consejos[:6]

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

    # ─── Lógica del Chat IA ──────────────────────────────────────────────────

    def _get_groq_client(self):
        if not HAS_GROQ:
            return None
        storage_dir = os.environ.get("FLET_APP_STORAGE_DATA", ".")
        key_file = os.path.join(storage_dir, "groq_api_key.txt")
        api_key = ""
        if os.path.exists(key_file):
            with open(key_file, "r") as f:
                api_key = f.read().strip()
        if not api_key:
            from core.config import GROQ_API_KEY
            api_key = GROQ_API_KEY
            
        if api_key:
            from groq import AsyncGroq
            return AsyncGroq(api_key=api_key)
        return None

    async def _guardar_api_key(self, e):
        key = self.api_key_input.value.strip()
        if key:
            storage_dir = os.environ.get("FLET_APP_STORAGE_DATA", ".")
            key_file = os.path.join(storage_dir, "groq_api_key.txt")
            with open(key_file, "w") as f:
                f.write(key)
            self.page.navigate("/consejos")

    async def _enviar_mensaje(self, e):
        texto = self.chat_input.value.strip()
        if not texto:
            return

        self.chat_input.value = ""
        self.page.update()

        # Mostrar mensaje del usuario
        self._add_message("user", texto)
        
        client = self._get_groq_client()
        if not client:
            self._add_message("assistant", "Error: No se encontró la clave de API de Groq o el módulo no está instalado.")
            return

        # Mostrar "Escribiendo..."
        loader = ft.ProgressRing(width=16, height=16, color="#00F5C4")
        loader_container = ft.Container(
            content=ft.Row([loader, ft.Text("Analizando tus finanzas...", size=12, color="#718096")], spacing=8),
            padding=ft.Padding.symmetric(horizontal=12, vertical=8)
        )
        self.chat_listview.controls.append(loader_container)
        self.page.update()

        # Contexto financiero actual
        estado = self.budget.estado_presupuesto()
        contexto_financiero = f"""
        Eres un asistente financiero empático llamado VisionFlow IA. Hablas en español de forma concisa y amigable.
        El usuario tiene un presupuesto de {estado.saldo_inicial}, ha gastado {estado.total_gastado} y le quedan {estado.saldo_actual} para los próximos {estado.dias_restantes} días. Su presupuesto diario es de {estado.presupuesto_diario}.
        """

        mensajes_api = [{"role": "system", "content": contexto_financiero}]
        for m in self.chat_messages:
            mensajes_api.append({"role": m["role"], "content": m["content"]})
        mensajes_api.append({"role": "user", "content": texto})

        try:
            chat_completion = await client.chat.completions.create(
                messages=mensajes_api,
                model="llama3-8b-8192",
                max_tokens=300,
            )
            respuesta = chat_completion.choices[0].message.content
        except Exception as ex:
            respuesta = f"Ups, tuve un problema de conexión: {ex}"

        # Remover loader
        self.chat_listview.controls.remove(loader_container)
        
        # Mostrar respuesta
        self._add_message("assistant", respuesta)

    def _add_message(self, role: str, content: str):
        if role == "user":
            self.chat_messages.append({"role": "user", "content": content})
            msg_ui = ft.Container(
                content=ft.Text(content, color="white", size=13),
                bgcolor="#7B61FF",
                padding=ft.Padding.symmetric(horizontal=14, vertical=10),
                border_radius=ft.border_radius.only(top_left=14, top_right=14, bottom_left=14, bottom_right=0),
                alignment=ft.alignment.Alignment.CENTER_RIGHT,
            )
            row = ft.Row([ft.Container(expand=True), msg_ui], alignment=ft.MainAxisAlignment.END)
        else:
            self.chat_messages.append({"role": "assistant", "content": content})
            msg_ui = ft.Container(
                content=ft.Text(content, color="#0A0F1E", size=13),
                bgcolor="#00F5C4",
                padding=ft.Padding.symmetric(horizontal=14, vertical=10),
                border_radius=ft.border_radius.only(top_left=14, top_right=14, bottom_left=0, bottom_right=14),
                alignment=ft.alignment.Alignment.CENTER_LEFT,
            )
            row = ft.Row([ft.Text("🤖", size=20), msg_ui, ft.Container(expand=True)], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START)
            
        self.chat_listview.controls.append(row)
        self.page.update()

    # ─── Build Principal ─────────────────────────────────────────────────────

    def build(self) -> ft.Control:
        nav_bar = _build_nav_bar(self.page, activo="/consejos")
        estado = self.budget.estado_presupuesto()
        consejos = self._seleccionar_consejos()

        # Tab 1: Consejos Estáticos
        ahorro_posible = max(estado.presupuesto_diario * 0.15, 0)
        tab_tips = ft.Container(
            content=ft.Column([
                ft.Container(height=4),
                ft.Container(
                    content=ft.Column([
                        ft.Text("💰 Si ahorras 15% diario...", size=13, color="#FFD166", weight=ft.FontWeight.W_600),
                        ft.Text(
                            f"${ahorro_posible:.2f}/día → ${ahorro_posible*30:.2f}/mes",
                            size=20, weight=ft.FontWeight.BOLD, color="#00F5C4", font_family="JetBrains",
                        ),
                        ft.Text("Fondo de emergencia 🎯", size=12, color="#718096"),
                    ], spacing=6),
                    bgcolor="#0D2518", border=ft.Border.all(1, "#00F5C4"), border_radius=16, padding=20,
                ),
                ft.Container(height=4),
                ft.Text("Consejos para ti hoy", size=14, weight=ft.FontWeight.W_600, color="#718096"),
                *[self._tarjeta_consejo(*c) for c in consejos],
            ], spacing=12, scroll=ft.ScrollMode.AUTO),
            padding=ft.Padding.symmetric(horizontal=20, vertical=10),
        )

        # Tab 2: Chat IA
        api_key_configured = bool(self._get_groq_client())
        
        if not api_key_configured:
            self.api_key_input = ft.TextField(
                hint_text="Ingresa tu API Key de Groq (gsk_...)",
                password=True,
                can_reveal_password=True,
                border_color="#7B61FF",
                focused_border_color="#00F5C4",
                border_radius=12,
            )
            tab_chat = ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.LOCK_ROUNDED, size=48, color="#00F5C4"),
                    ft.Text("Configurar Asistente IA", size=18, weight=ft.FontWeight.BOLD, color="white"),
                    ft.Text("Por seguridad, la clave se guardará localmente en tu dispositivo.", size=13, color="#718096", text_align=ft.TextAlign.CENTER),
                    ft.Container(height=16),
                    self.api_key_input,
                    ft.ElevatedButton("Guardar y Continuar", bgcolor="#00F5C4", color="#0A0F1E", on_click=self._guardar_api_key)
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.Padding.symmetric(horizontal=20, vertical=40),
            )
        else:
            if len(self.chat_messages) == 0:
                # Mensaje inicial
                self._add_message("assistant", "¡Hola! Soy tu asistente financiero impulsado por IA. Puedo analizar tu presupuesto y darte consejos personalizados. ¿En qué te puedo ayudar hoy?")
                
            tab_chat = ft.Container(
                content=ft.Column([
                    self.chat_listview,
                    ft.Row([
                        self.chat_input,
                        ft.IconButton(
                            icon=ft.Icons.SEND_ROUNDED,
                            icon_color="#00F5C4",
                            on_click=self._enviar_mensaje,
                        ),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ]),
                padding=ft.Padding.symmetric(horizontal=20, vertical=10),
            )

        self.tab_container = ft.Container(content=tab_tips, expand=True)

        self.btn_tips = ft.ElevatedButton("Tips Rápidos", color="#0A0F1E", bgcolor="#00F5C4", on_click=lambda e: on_tab_change(0))
        self.btn_chat = ft.ElevatedButton("Asistente IA", color="#718096", bgcolor="#111827", on_click=lambda e: on_tab_change(1))

        def on_tab_change(index):
            if index == 0:
                self.tab_container.content = tab_tips
                self.btn_tips.color = "#0A0F1E"
                self.btn_tips.bgcolor = "#00F5C4"
                self.btn_chat.color = "#718096"
                self.btn_chat.bgcolor = "#111827"
            else:
                self.tab_container.content = tab_chat
                self.btn_chat.color = "#0A0F1E"
                self.btn_chat.bgcolor = "#00F5C4"
                self.btn_tips.color = "#718096"
                self.btn_tips.bgcolor = "#111827"
            
            self.btn_tips.update()
            self.btn_chat.update()
            self.tab_container.update()

        tabs = ft.Row([self.btn_tips, self.btn_chat], alignment=ft.MainAxisAlignment.CENTER, spacing=20)

        return ft.Stack([
            ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.IconButton(ft.Icons.ARROW_BACK_IOS_ROUNDED, icon_color="#718096", on_click=lambda _: self.page.navigate("/")),
                        ft.Text("Consejos y Chat IA", size=18, weight=ft.FontWeight.BOLD, color="white"),
                    ]),
                    padding=ft.Padding.symmetric(horizontal=12, vertical=16),
                ),
                ft.Container(content=tabs),
                self.tab_container,
                ft.Container(height=80),
            ], expand=True),
            ft.Container(content=nav_bar, bottom=0, left=0, right=0),
        ], expand=True)
