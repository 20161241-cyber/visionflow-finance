"""
camera.py — Vista de cámara en vivo para captura de tickets.
"""

from __future__ import annotations
import flet as ft
import flet_camera as fc
import tempfile
import os

class CameraView:
    def __init__(self, page: ft.Page, on_capture=None):
        self.page = page
        self.on_capture = on_capture
        if self.page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS] or getattr(self.page, 'web', False):
            self.camera = fc.Camera(
                expand=True,
                preview_enabled=True,
            )
        else:
            self.camera = None

    async def _tomar_foto(self, e):
        """Captura la foto desde flet_camera y la guarda temporalmente."""
        if not self.camera:
            self.page.overlay.append(
                ft.SnackBar(ft.Text("La cámara nativa solo está soportada en Android/iOS/Web."), open=True, bgcolor="#FF4444")
            )
            self.page.update()
            return
        try:
            image_bytes = await self.camera.take_picture()
            if image_bytes:
                # Guardar en un archivo temporal
                temp_dir = tempfile.gettempdir()
                temp_path = os.path.join(temp_dir, "visionflow_ticket.jpg")
                with open(temp_path, "wb") as f:
                    f.write(image_bytes)
                
                # Ejecutar el callback con la ruta
                if self.on_capture:
                    self.on_capture(temp_path)
        except Exception as ex:
            self.page.overlay.append(
                ft.SnackBar(ft.Text(f"Error de cámara: {ex}"), open=True, bgcolor="#FF4444")
            )
            self.page.update()

    def build(self) -> ft.Control:
        content_control = self.camera if self.camera else ft.Container(
            content=ft.Text("Cámara no soportada en Desktop.\nUsa el botón Galería o compila el APK.", text_align=ft.TextAlign.CENTER, color="white"),
            alignment=ft.Alignment.CENTER,
            bgcolor="black",
        )
        return ft.Stack([
            ft.Container(
                content=content_control,
                expand=True,
                alignment=ft.Alignment.CENTER,
            ),
            # Botón flotante para cerrar
            ft.Container(
                content=ft.IconButton(
                    icon=ft.Icons.CLOSE,
                    icon_size=30,
                    icon_color="white",
                    on_click=lambda _: self.page.navigate("/scanner")
                ),
                top=20,
                left=20,
            ),
            # Botón flotante para tomar foto
            ft.Container(
                content=ft.FloatingActionButton(
                    icon=ft.Icons.CAMERA,
                    bgcolor="#00F5C4",
                    on_click=self._tomar_foto,
                ),
                bottom=40,
                right=self.page.window.width / 2 - 28 if self.page.window.width else 100, # Centro aprox
                alignment=ft.Alignment.BOTTOM_CENTER,
            )
        ], expand=True)
