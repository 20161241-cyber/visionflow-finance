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
            # 1. Intentar variable de entorno
            url = os.getenv("SUPABASE_URL", "")
            key = os.getenv("SUPABASE_KEY", "")
            
            # 2. Intentar archivos locales si no hay variables de entorno
            if not url or not key:
                try:
                    current_dir = Path(__file__).parent.parent
                    url_file = current_dir / "supabase_url.txt"
                    key_file = current_dir / "supabase_key.txt"
                    if url_file.exists():
                        url = url_file.read_text().strip()
                    if key_file.exists():
                        key = key_file.read_text().strip()
                except Exception as e:
                    logger.warning("Error leyendo archivos supabase_url.txt / supabase_key.txt: %s", e)
            
            if url and key and key != "PEGAR_AQUI_TU_ANON_KEY":
                try:
                    self._client = create_client(url, key)
                    logger.info("Supabase conectado: %s", url[:40])
                except Exception as e:
                    logger.warning("Error al conectar Supabase: %s", e)
                    self._modo_offline = True
            else:
                logger.info("Variables o archivos SUPABASE_URL/KEY no configurados → modo offline")
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

    # ─── Recibos Avanzados e Inteligencia Artificial ─────────────────────────

    def guardar_recibo_completo(self, total: float, store_name: str, articulos: list) -> bool:
        """Guarda la cabecera del recibo y todos sus artículos individuales."""
        if self.offline:
            return False
            
        try:
            # 1. Insertar Recibo
            res = self._client.table("receipts").insert({
                "total_amount": total,
                "store_name": store_name
            }).execute()
            
            if not res.data:
                return False
                
            receipt_id = res.data[0]["id"]
            
            # 2. Insertar Artículos
            items_to_insert = []
            for art in articulos:
                items_to_insert.append({
                    "receipt_id": receipt_id,
                    "product_name": art.get("name", "Desconocido"),
                    "price": art.get("price", 0.0),
                    "category": art.get("category", "Otros")
                })
                
            if items_to_insert:
                self._client.table("receipt_items").insert(items_to_insert).execute()
                
            return True
        except Exception as e:
            logger.error("Error al guardar ticket en Supabase: %s", e)
            return False

    def obtener_historial_articulos(self) -> list:
        """Obtiene todos los artículos registrados para análisis predictivo."""
        if self.offline:
            return []
            
        try:
            res = self._client.table("receipt_items").select("*").execute()
            return res.data or []
        except Exception as e:
            logger.error("Error al obtener historial de articulos: %s", e)
            return []

    def guardar_insight(self, insight_type: str, product: str, message: str, savings: float = 0.0):
        if self.offline:
            return
            
        try:
            self._client.table("financial_insights").insert({
                "insight_type": insight_type,
                "target_product": product,
                "message": message,
                "potential_savings": savings
            }).execute()
        except Exception as e:
            logger.error("Error guardando insight financiero: %s", e)

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
