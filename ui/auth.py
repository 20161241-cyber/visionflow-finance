import flet as ft
from core.db_client import db

class AuthView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.es_registro = False

    def build(self) -> ft.Control:
        # Campos de texto
        self.tf_nombre = ft.TextField(label="Nombre", visible=False, border_color="#1F2937")
        self.tf_email = ft.TextField(label="Correo Electrónico", border_color="#1F2937")
        self.tf_password = ft.TextField(label="Contraseña", password=True, can_reveal_password=True, border_color="#1F2937")
        
        self.lbl_error = ft.Text(color="#FF4444", size=12)

        # Botón principal
        self.btn_accion = ft.ElevatedButton(
            "Iniciar Sesión",
            bgcolor="#00F5C4",
            color="#0A0F1E",
            on_click=self._manejar_auth,
            width=200
        )
        
        # Botón para cambiar de modo
        self.btn_cambiar_modo = ft.TextButton(
            "¿No tienes cuenta? Regístrate aquí",
            on_click=self._cambiar_modo,
            style=ft.ButtonStyle(color="#7B61FF")
        )

        tarjeta_auth = ft.Container(
            content=ft.Column([
                ft.Text("VisionFlow Finance", size=24, weight=ft.FontWeight.BOLD, color="white"),
                ft.Text("Inicia sesión o crea una cuenta", size=12, color="#718096"),
                ft.Container(height=10),
                self.tf_nombre,
                self.tf_email,
                self.tf_password,
                self.lbl_error,
                ft.Container(height=10),
                self.btn_accion,
                self.btn_cambiar_modo
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
            bgcolor="#111827",
            padding=30,
            border_radius=20,
            width=350,
            alignment=ft.alignment.Alignment.CENTER
        )

        return ft.Container(
            content=tarjeta_auth,
            alignment=ft.alignment.Alignment.CENTER,
            expand=True
        )

    def _cambiar_modo(self, e):
        self.es_registro = not self.es_registro
        if self.es_registro:
            self.tf_nombre.visible = True
            self.btn_accion.text = "Registrarse"
            self.btn_cambiar_modo.text = "¿Ya tienes cuenta? Inicia sesión"
        else:
            self.tf_nombre.visible = False
            self.btn_accion.text = "Iniciar Sesión"
            self.btn_cambiar_modo.text = "¿No tienes cuenta? Regístrate aquí"
        self.page.update()

    def _manejar_auth(self, e):
        email = self.tf_email.value.strip()
        password = self.tf_password.value.strip()
        nombre = self.tf_nombre.value.strip() if self.es_registro else ""

        if not email or not password:
            self.lbl_error.value = "Por favor, llena todos los campos obligatorios."
            self.page.update()
            return
            
        if self.es_registro and not nombre:
            self.lbl_error.value = "Por favor, ingresa tu nombre para el registro."
            self.page.update()
            return

        self.btn_accion.disabled = True
        self.lbl_error.value = "Conectando..."
        self.page.update()

        if self.es_registro:
            res = db.registrar_usuario(email, password, nombre)
        else:
            res = db.iniciar_sesion(email, password)

        self.btn_accion.disabled = False
        
        if res.get("exito"):
            self.lbl_error.value = ""
            self.page.navigate("/")
        else:
            error_msg = res.get("error", "Error desconocido.")
            self.lbl_error.value = f"Error: {error_msg}"
            self.page.update()
