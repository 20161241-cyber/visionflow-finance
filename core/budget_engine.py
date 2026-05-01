"""
budget_engine.py — Motor de presupuesto quincenal y detector de Gastos Hormiga.

Responsabilidades:
  - Calcular el "Presupuesto Diario de Supervivencia".
  - Detectar patrones de Gastos Hormiga y proyectar su impacto mensual.
  - Mantener el estado de transacciones en memoria (+ sync con Supabase).
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Estructuras de datos ─────────────────────────────────────────────────────

@dataclass
class Transaccion:
    id: str
    fecha: str                  # ISO 8601: "2025-06-15"
    descripcion: str
    monto: float
    categoria: str
    es_hormiga: bool = False
    imagen_url: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AlertaHormiga:
    categoria_hormiga: str
    frecuencia_semanal: int
    gasto_semanal: float
    impacto_mensual_proyectado: float
    mensaje: str


@dataclass
class EstadoPresupuesto:
    saldo_inicial: float
    saldo_actual: float
    fecha_proximo_ingreso: str      # ISO 8601
    dias_restantes: int
    presupuesto_diario: float
    total_gastado: float
    porcentaje_utilizado: float
    meta_nombre: str = ""
    meta_monto: float = 0.0


# ─── Utilidad: directorio de datos persistente ────────────────────────────────

def _obtener_directorio_datos() -> Path:
    """
    Retorna un directorio donde la app puede escribir datos persistentes.
    
    En Android (Flet APK), usa la variable de entorno FLET_APP_STORAGE_DATA.
    En desktop/desarrollo, usa el directorio 'data/' relativo al proyecto.
    """
    # Flet inyecta esta variable en APKs empaquetados
    flet_storage = os.environ.get("FLET_APP_STORAGE_DATA")
    if flet_storage:
        return Path(flet_storage)
    
    # Fallback: directorio relativo al archivo actual (desktop/desarrollo)
    directorio = Path(os.path.dirname(os.path.abspath(__file__))).parent / "data"
    directorio.mkdir(exist_ok=True)
    return directorio


# ─── Motor Principal ──────────────────────────────────────────────────────────

class BudgetEngine:
    """
    Motor central de presupuesto.

    Almacena transacciones en memoria + archivo JSON local como caché
    (Supabase sync es opcional y se inyecta desde db_client.py).
    """

    def __init__(
        self,
        saldo_inicial: float = 5000.0,
        fecha_proximo_ingreso: Optional[date] = None,
    ):
        # Path dinámico que funciona tanto en Android como Desktop
        self.CACHE_PATH = _obtener_directorio_datos() / "transacciones_cache.json"
        
        self.saldo_inicial = saldo_inicial
        self.fecha_proximo_ingreso: date = fecha_proximo_ingreso or self._siguiente_quincena()
        self.transacciones: list = []
        self.meta_nombre = ""
        self.meta_monto = 0.0
        self._cargar_cache()

    # ─── Quincenas ───────────────────────────────────────────────────────────

    @staticmethod
    def _siguiente_quincena() -> date:
        """Calcula el próximo día 15 o 30 del mes actual."""
        hoy = date.today()
        if hoy.day < 15:
            return hoy.replace(day=15)
        elif hoy.day < 30:
            try:
                return hoy.replace(day=30)
            except ValueError:
                # Meses con menos de 30 días → último día
                return hoy.replace(day=28)
        else:
            # Ya pasó la quincena → siguiente mes día 15
            siguiente = hoy.replace(month=hoy.month % 12 + 1, day=15) if hoy.month < 12 \
                        else hoy.replace(year=hoy.year + 1, month=1, day=15)
            return siguiente

    def dias_para_cobro(self) -> int:
        """Días restantes hasta el próximo ingreso (mínimo 1)."""
        delta = (self.fecha_proximo_ingreso - date.today()).days
        return max(delta, 1)

    # ─── Transacciones ───────────────────────────────────────────────────────

    def agregar_transaccion(
        self,
        descripcion: str,
        monto: float,
        categoria: str,
        es_hormiga: bool = False,
        imagen_url: str = "",
    ) -> Transaccion:
        """Registra una nueva transacción y actualiza el saldo."""
        import uuid
        tx = Transaccion(
            id=str(uuid.uuid4())[:8],
            fecha=datetime.now().isoformat(timespec="seconds"),
            descripcion=descripcion,
            monto=round(monto, 2),
            categoria=categoria,
            es_hormiga=es_hormiga,
            imagen_url=imagen_url,
        )
        self.transacciones.append(tx)
        self._guardar_cache()
        logger.info("Transacción registrada: %s $%.2f [%s]", descripcion, monto, categoria)
        return tx

    def total_gastado(self) -> float:
        """Suma de todas las transacciones registradas."""
        return round(sum(t.monto for t in self.transacciones), 2)

    def saldo_actual(self) -> float:
        """Saldo disponible restante."""
        return round(self.saldo_inicial - self.total_gastado(), 2)

    # ─── Presupuesto Diario de Supervivencia ─────────────────────────────────

    def calcular_presupuesto_diario(self) -> float:
        """
        Presupuesto Diario de Supervivencia = Saldo Actual / Días Restantes.

        Si el saldo es negativo, retorna 0.0 con advertencia.
        """
        saldo = self.saldo_actual() - self.meta_monto
        dias = self.dias_para_cobro()

        if saldo <= 0:
            logger.warning("¡Saldo agotado o meta muy alta! Saldo: %.2f", saldo)
            return 0.0

        presupuesto = round(saldo / dias, 2)
        logger.info("Presupuesto diario (descontando meta): $%.2f (%d días)", presupuesto, dias)
        return presupuesto

    def estado_presupuesto(self) -> EstadoPresupuesto:
        """Snapshot completo del estado financiero actual."""
        gastado = self.total_gastado()
        saldo = self.saldo_actual()
        pct = round((gastado / self.saldo_inicial) * 100, 1) if self.saldo_inicial > 0 else 0.0

        return EstadoPresupuesto(
            saldo_inicial=self.saldo_inicial,
            saldo_actual=saldo,
            fecha_proximo_ingreso=str(self.fecha_proximo_ingreso),
            dias_restantes=self.dias_para_cobro(),
            presupuesto_diario=self.calcular_presupuesto_diario(),
            total_gastado=gastado,
            porcentaje_utilizado=pct,
            meta_nombre=self.meta_nombre,
            meta_monto=self.meta_monto,
        )

    # ─── Detector de Gastos Hormiga ──────────────────────────────────────────

    def detectar_gastos_hormiga(
        self,
        ventana_dias: int = 7,
        umbral_frecuencia: int = 3,
    ) -> list:
        """
        Identifica compras recurrentes de bajo valor en los últimos `ventana_dias`.

        Lógica:
          - Filtrar transacciones marcadas como `es_hormiga`.
          - Agrupar por categoría.
          - Si aparece ≥ umbral_frecuencia veces → generar alerta.
          - Proyectar impacto mensual = (gasto_semanal / 7) × 30.

        Args:
            ventana_dias: Ventana de análisis en días.
            umbral_frecuencia: Mínimo de ocurrencias para activar alerta.

        Returns:
            Lista de AlertaHormiga ordenada por impacto mensual descendente.
        """
        desde = datetime.now() - timedelta(days=ventana_dias)
        alertas = []

        # Filtrar hormiga en ventana de tiempo
        hormiga_reciente = [
            t for t in self.transacciones
            if t.es_hormiga
            and datetime.fromisoformat(t.fecha) >= desde
        ]

        # Agrupar por categoría
        grupos = {}
        for tx in hormiga_reciente:
            grupos.setdefault(tx.categoria, []).append(tx)

        for categoria, txs in grupos.items():
            if len(txs) < umbral_frecuencia:
                continue

            gasto_semanal = round(sum(t.monto for t in txs), 2)
            impacto_mensual = round((gasto_semanal / ventana_dias) * 30, 2)

            mensaje = (
                f"⚠️ Gasto Hormiga detectado en '{categoria}': "
                f"${gasto_semanal:.2f} esta semana → "
                f"Proyección mensual: ${impacto_mensual:.2f} MXN"
            )

            alertas.append(AlertaHormiga(
                categoria_hormiga=categoria,
                frecuencia_semanal=len(txs),
                gasto_semanal=gasto_semanal,
                impacto_mensual_proyectado=impacto_mensual,
                mensaje=mensaje,
            ))

        # Ordenar por mayor impacto
        alertas.sort(key=lambda a: a.impacto_mensual_proyectado, reverse=True)
        return alertas

    # ─── Gastos por categoría (para gráfico) ─────────────────────────────────

    def gastos_por_categoria(self) -> dict:
        """Suma de gastos agrupados por categoría."""
        resultado = {}
        for tx in self.transacciones:
            resultado[tx.categoria] = round(resultado.get(tx.categoria, 0.0) + tx.monto, 2)
        return resultado

    # ─── Caché local JSON ─────────────────────────────────────────────────────

    def _guardar_cache(self):
        """Persiste transacciones en archivo JSON local."""
        try:
            self.CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "saldo_inicial": self.saldo_inicial,
                "fecha_proximo_ingreso": str(self.fecha_proximo_ingreso),
                "meta_nombre": self.meta_nombre,
                "meta_monto": self.meta_monto,
                "transacciones": [t.to_dict() for t in self.transacciones],
            }
            self.CACHE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        except Exception as e:
            logger.warning("No se pudo guardar caché: %s", e)

    def _cargar_cache(self):
        """Carga transacciones desde el archivo JSON local si existe."""
        try:
            if not self.CACHE_PATH.exists():
                return
            data = json.loads(self.CACHE_PATH.read_text())
            self.saldo_inicial = data.get("saldo_inicial", self.saldo_inicial)
            self.meta_nombre = data.get("meta_nombre", "")
            self.meta_monto = data.get("meta_monto", 0.0)
            fecha_str = data.get("fecha_proximo_ingreso")
            if fecha_str:
                self.fecha_proximo_ingreso = date.fromisoformat(fecha_str)
            self.transacciones = [Transaccion(**t) for t in data.get("transacciones", [])]
            logger.info("Caché cargada: %d transacciones", len(self.transacciones))
        except Exception as e:
            logger.warning("Error al cargar caché: %s", e)

    def resetear(self, nuevo_saldo: float, nueva_fecha_cobro: Optional[date] = None):
        """Reinicia el presupuesto (inicio de quincena)."""
        self.saldo_inicial = nuevo_saldo
        self.fecha_proximo_ingreso = nueva_fecha_cobro or self._siguiente_quincena()
        self.transacciones.clear()
        self.meta_nombre = ""
        self.meta_monto = 0.0
        self._guardar_cache()
        logger.info("Presupuesto reseteado. Saldo: %.2f", nuevo_saldo)

    # ─── Metas de Ahorro ───────────────────────────────────────────────────────
    def fijar_meta(self, nombre: str, monto: float):
        """Fija una meta de ahorro que será descontada del presupuesto."""
        self.meta_nombre = nombre
        self.meta_monto = monto
        self._guardar_cache()

    def eliminar_meta(self):
        """Elimina la meta actual."""
        self.meta_nombre = ""
        self.meta_monto = 0.0
        self._guardar_cache()

    # ─── Algoritmo Predictivo ────────────────────────────────────────────────
    def analisis_predictivo(self) -> dict:
        """
        Analiza el historial de transacciones y genera una proyección para la "Fecha de Quiebra".
        """
        import flet as ft
        from datetime import datetime, timedelta, date
        hoy = date.today()
        dias_restantes = self.dias_para_cobro()
        saldo = self.saldo_actual() - self.meta_monto
        
        # Calcular Burn Rate (gasto promedio de los últimos 7 días con transacciones)
        fechas_gastos = {}
        for t in self.transacciones:
            f = datetime.fromisoformat(t.fecha).date()
            if f <= hoy:
                fechas_gastos[f] = fechas_gastos.get(f, 0.0) + t.monto
                
        dias_con_gasto = len(fechas_gastos)
        burn_rate = sum(fechas_gastos.values()) / dias_con_gasto if dias_con_gasto > 0 else 0.0
        
        burn_rate_ideal = saldo / dias_restantes if dias_restantes > 0 and saldo > 0 else 0.0
        
        # Proyectar fecha de quiebra
        fecha_quiebra = "Desconocida"
        alerta = None
        
        if burn_rate > 0:
            dias_para_quiebra = int((self.saldo_actual() - self.meta_monto) / burn_rate) if (self.saldo_actual() - self.meta_monto) > 0 else 0
            fecha_q_obj = hoy + timedelta(days=dias_para_quiebra)
            fecha_quiebra = fecha_q_obj.isoformat()
            
            if fecha_q_obj < self.fecha_proximo_ingreso and (self.saldo_actual() - self.meta_monto) > 0:
                alerta = f"🚨 Alerta Crítica: A tu ritmo actual (${burn_rate:.2f}/día), tu saldo llegará a cero el {fecha_q_obj.strftime('%d/%m')}."
            elif burn_rate > burn_rate_ideal and saldo > 0:
                alerta = f"⚠️ Advertencia: Estás gastando más rápido que lo ideal (${burn_rate_ideal:.2f}/día)."
                
        # Generar puntos de gráfico
        data_ideal = []
        data_real = []
        saldo_simulado_ideal = self.saldo_actual() - self.meta_monto
        saldo_simulado_real = self.saldo_actual() - self.meta_monto
        
        for i in range(min(dias_restantes + 1, 15)):
            data_ideal.append({"x": i, "y": max(0, saldo_simulado_ideal)})
            data_real.append({"x": i, "y": max(0, saldo_simulado_real)})
            saldo_simulado_ideal -= burn_rate_ideal
            saldo_simulado_real -= burn_rate
            
        return {
            "burn_rate": burn_rate,
            "burn_rate_ideal": burn_rate_ideal,
            "fecha_quiebra": fecha_quiebra,
            "alerta": alerta,
            "data_ideal": data_ideal,
            "data_real": data_real,
            "dias_restantes": dias_restantes
        }

    # ─── Insights e Inteligencia Artificial ──────────────────────────────────
    def generar_insights_inteligentes(self) -> list[str]:
        """Analiza el historial completo de Supabase para encontrar compras recurrentes (Hormigas)."""
        from core.db_client import db
        articulos = db.obtener_historial_articulos()
        
        if not articulos:
            return []
            
        frecuencias = {}
        for art in articulos:
            nombre = art.get("product_name", "").lower().strip()
            if nombre:
                frecuencias[nombre] = frecuencias.get(nombre, 0) + 1
                
        nuevos_insights = []
        for nombre, count in frecuencias.items():
            if count >= 3:
                insight_msg = f"Detectamos que compras '{nombre.title()}' frecuentemente ({count} veces). ¿Podrías reducirlo o buscar una marca blanca?"
                db.guardar_insight("HORMIGA_DETECTED", nombre.title(), insight_msg, 0.0)
                nuevos_insights.append(insight_msg)
                
        return nuevos_insights
