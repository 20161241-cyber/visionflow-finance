"""
db_client.py — Cliente Supabase para sincronización en la nube.

Maneja:
  - Autenticación de usuarios.
  - Guardado de transacciones en PostgreSQL vía Supabase REST API.
  - Upload de imágenes de tickets al bucket de Storage.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Intentar importar supabase; si no está, operar en modo offline
try:
    from supabase import create_client, Client
    SUPABASE_DISPONIBLE = True
except ImportError:
    SUPABASE_DISPONIBLE = False
    logger.warning("supabase-py no instalado. Operando en modo offline.")


class SupabaseClient:
    """
    Wrapper del cliente Supabase con manejo graceful de modo offline.

    Configuración via variables de entorno:
      SUPABASE_URL  → URL del proyecto Supabase.
      SUPABASE_KEY  → Clave anon o service_role.
    """

    def __init__(self):
        self._client: Optional[object] = None
        self._usuario_id: Optional[str] = None
        self._modo_offline = not SUPABASE_DISPONIBLE

        if SUPABASE_DISPONIBLE:
            url = os.getenv("SUPABASE_URL", "")
            key = os.getenv("SUPABASE_KEY", "")
            if url and key:
                try:
                    self._client = create_client(url, key)
                    logger.info("Supabase conectado: %s", url[:40])
                except Exception as e:
                    logger.warning("Error al conectar Supabase: %s", e)
                    self._modo_offline = True
            else:
                logger.info("Variables SUPABASE_URL/KEY no configuradas → modo offline")
                self._modo_offline = True

    @property
    def offline(self) -> bool:
        return self._modo_offline

    # ─── Autenticación ────────────────────────────────────────────────────────

    def registrar_usuario(self, email: str, password: str) -> dict:
        """Crea un nuevo usuario en Supabase Auth."""
        if self.offline:
            return {"exito": False, "error": "Modo offline"}
        try:
            resp = self._client.auth.sign_up({"email": email, "password": password})
            self._usuario_id = resp.user.id if resp.user else None
            return {"exito": True, "usuario_id": self._usuario_id}
        except Exception as e:
            return {"exito": False, "error": str(e)}

    def iniciar_sesion(self, email: str, password: str) -> dict:
        """Autentica un usuario existente."""
        if self.offline:
            return {"exito": False, "error": "Modo offline"}
        try:
            resp = self._client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
            self._usuario_id = resp.user.id if resp.user else None
            return {"exito": True, "usuario_id": self._usuario_id}
        except Exception as e:
            return {"exito": False, "error": str(e)}

    def cerrar_sesion(self):
        if not self.offline:
            self._client.auth.sign_out()
        self._usuario_id = None

    # ─── Transacciones ────────────────────────────────────────────────────────

    def guardar_transaccion(self, transaccion_dict: dict) -> dict:
        """
        Inserta una transacción en la tabla `transacciones`.

        Args:
            transaccion_dict: dict con campos de Transaccion.

        Returns:
            dict con exito: bool y datos insertados o error.
        """
        if self.offline:
            return {"exito": False, "error": "Modo offline"}
        try:
            payload = {**transaccion_dict, "usuario_id": self._usuario_id}
            resp = self._client.table("transacciones").insert(payload).execute()
            return {"exito": True, "data": resp.data}
        except Exception as e:
            logger.error("Error guardando transacción: %s", e)
            return {"exito": False, "error": str(e)}

    def obtener_transacciones(self, limite: int = 100) -> list[dict]:
        """Recupera las últimas transacciones del usuario."""
        if self.offline or not self._usuario_id:
            return []
        try:
            resp = (
                self._client.table("transacciones")
                .select("*")
                .eq("usuario_id", self._usuario_id)
                .order("fecha", desc=True)
                .limit(limite)
                .execute()
            )
            return resp.data or []
        except Exception as e:
            logger.error("Error obteniendo transacciones: %s", e)
            return []

    # ─── Storage de Imágenes ──────────────────────────────────────────────────

    def subir_imagen_ticket(self, ruta_local: str | Path, nombre_archivo: str) -> str:
        """
        Sube la imagen del ticket al bucket 'tickets' de Supabase Storage.

        Returns:
            URL pública de la imagen subida, o "" si falla.
        """
        if self.offline:
            return ""
        try:
            ruta = Path(ruta_local)
            with ruta.open("rb") as f:
                self._client.storage.from_("tickets").upload(
                    path=f"tickets/{self._usuario_id}/{nombre_archivo}",
                    file=f,
                    file_options={"content-type": "image/jpeg"},
                )
            url = self._client.storage.from_("tickets").get_public_url(
                f"tickets/{self._usuario_id}/{nombre_archivo}"
            )
            return url
        except Exception as e:
            logger.warning("No se pudo subir imagen: %s", e)
            return ""

    # ─── Presupuesto ──────────────────────────────────────────────────────────

    def guardar_presupuesto(self, saldo_inicial: float, fecha_cobro: str) -> dict:
        """Guarda o actualiza la configuración de presupuesto del usuario."""
        if self.offline:
            return {"exito": False}
        try:
            resp = (
                self._client.table("presupuestos")
                .upsert({
                    "usuario_id": self._usuario_id,
                    "saldo_inicial": saldo_inicial,
                    "fecha_proximo_ingreso": fecha_cobro,
                })
                .execute()
            )
            return {"exito": True, "data": resp.data}
        except Exception as e:
            return {"exito": False, "error": str(e)}


# Instancia global singleton
db = SupabaseClient()
