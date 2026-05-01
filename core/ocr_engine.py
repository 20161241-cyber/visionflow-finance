"""
ocr_engine.py — Motor de OCR para procesamiento de tickets de compra.

Flujo:
  1. Preprocesar imagen (escala de grises, umbralización, eliminación de ruido).
  2. Extraer texto raw con Tesseract (si disponible).
  3. Parsear artículos y precios mediante Regex.
  4. Detectar símbolo de moneda y Total final.

Dependencias: pytesseract (opcional en móvil), Pillow
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from pathlib import Path

# ─── Import condicional de pytesseract ────────────────────────────────────────
# En Android, Tesseract no está disponible. La app debe funcionar sin él.
try:
    import pytesseract
    TESSERACT_DISPONIBLE = True
except ImportError:
    TESSERACT_DISPONIBLE = False

try:
    from PIL import Image, ImageEnhance, ImageFilter
    PIL_DISPONIBLE = True
except ImportError:
    PIL_DISPONIBLE = False

# ─── Logging ─────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

# ─── Patrones Regex ───────────────────────────────────────────────────────────
# Detecta precios: "$12.50", "12.50", "$ 12,50"
PRECIO_PATRON = re.compile(
    r"\$?\s*(\d{1,6}[.,]\d{2})\b"
)

# Detecta línea de Total o Subtotal
TOTAL_PATRON = re.compile(
    r"(?:total|importe|subtotal|suma|a\s*pagar)[^\d]*(\d{1,6}[.,]\d{2})",
    re.IGNORECASE,
)

# Línea con artículo + precio al final: "Coca Cola 600ml   28.50"
ARTICULO_PATRON = re.compile(
    r"^(.+?)\s{2,}(\d{1,6}[.,]\d{2})\s*$"
)

# Símbolo de moneda detectado
MONEDA_PATRON = re.compile(r"(\$|€|£|MXN|USD|EUR)")


# ─── Estructuras de Datos ─────────────────────────────────────────────────────
@dataclass
class ArticuloTicket:
    nombre: str
    precio: float
    categoria: str = "Sin categoría"


@dataclass
class ResultadoOCR:
    texto_raw: str
    moneda: str
    total: float
    articulos: list = field(default_factory=list)
    confianza: float = 0.0
    exito: bool = True
    error: str = ""


# ─── Preprocesamiento de Imagen ───────────────────────────────────────────────
def preprocesar_imagen(ruta_imagen):
    """
    Preprocesa la imagen del ticket para maximizar la precisión del OCR (Versión PIL/Móvil).

    Pasos:
      - Convertir a escala de grises.
      - Aumentar contraste.
      - Aplicar filtro de nitidez.
      - Binarización simple.

    Args:
        ruta_imagen: Ruta al archivo de imagen (jpg, png, webp).

    Returns:
        Objeto PIL.Image procesado listo para Tesseract.
    """
    if not PIL_DISPONIBLE:
        raise ImportError("Pillow no está instalado. Instálalo con: pip install Pillow")

    ruta = Path(ruta_imagen)
    if not ruta.exists():
        raise FileNotFoundError(f"Imagen no encontrada: {ruta}")

    # Cargar imagen con PIL
    try:
        imagen = Image.open(str(ruta))
        # Convertir a escala de grises
        gris = imagen.convert("L")
        
        # Aumentar contraste
        enhancer = ImageEnhance.Contrast(gris)
        contraste = enhancer.enhance(2.0)
        
        # Filtro para enfocar bordes de texto
        enfocada = contraste.filter(ImageFilter.SHARPEN)
        
        # Umbralización simple para texto oscuro en fondo claro
        binarizada = enfocada.point(lambda x: 0 if x < 140 else 255, '1')
        
        logger.info("Imagen preprocesada (PIL): tamaño=%s", binarizada.size)
        return binarizada
    except Exception as e:
        raise ValueError(f"Error procesando la imagen con PIL: {e}")


def _normalizar_precio(texto_precio: str) -> float:
    """Convierte '12,50' o '12.50' a float 12.50."""
    limpio = texto_precio.strip().replace(",", ".")
    try:
        return round(float(limpio), 2)
    except ValueError:
        return 0.0


# ─── Extracción OCR Principal ─────────────────────────────────────────────────
def extraer_texto_ticket(ruta_imagen) -> ResultadoOCR:
    """
    Extrae y estructura la información de un ticket de compra.

    Args:
        ruta_imagen: Ruta local a la imagen del ticket.

    Returns:
        ResultadoOCR con total, moneda detectada y lista de artículos.
    """
    import base64
    import json
    import os
    from groq import Groq
    
    logger.info("Iniciando extracción Vision AI para: %s", ruta_imagen)
    
    try:
        current_dir = Path(__file__).parent.parent
        key_file = current_dir / "groq_api_key.txt"
        api_key = key_file.read_text().strip() if key_file.exists() else os.getenv("GROQ_API_KEY")
    except Exception:
        api_key = None
        
    if not api_key:
        return ResultadoOCR("", "$", 0.0, exito=False, error="No se encontró GROQ_API_KEY")
        
    try:
        client = Groq(api_key=api_key)
        with open(ruta_imagen, "rb") as img:
            base64_img = base64.b64encode(img.read()).decode("utf-8")
            
        prompt = """Eres un experto OCR de finanzas. Extrae de este recibo el total y los artículos.
RESPONDE SÓLO CON JSON VÁLIDO.
{
  "total": 120.50,
  "articulos": [
    {"nombre": "Leche", "precio": 35.0, "categoria": "Despensa"}
  ]
}"""
        response = client.chat.completions.create(
            model="llama-3.2-90b-vision-preview",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
                ]
            }],
            temperature=0.0
        )
        
        json_str = response.choices[0].message.content.strip()
        if json_str.startswith("```json"): json_str = json_str[7:-3]
        if json_str.startswith("```"): json_str = json_str[3:-3]
        
        data = json.loads(json_str)
        articulos = [
            ArticuloTicket(a.get("nombre", "Item"), float(a.get("precio", 0.0)), a.get("categoria", "Otros"))
            for a in data.get("articulos", [])
        ]
        total = float(data.get("total", sum(a.precio for a in articulos)))
        
        return ResultadoOCR(
            texto_raw=json_str,
            moneda="$",
            total=total,
            articulos=articulos,
            confianza=99.0,
            exito=True
        )
    except Exception as e:
        logger.error("Error en Vision API: %s", e)
        return ResultadoOCR("", "$", 0.0, exito=False, error=str(e))

def _extraer_fallback_pil(ruta_imagen):
    pass


def _detectar_moneda(texto: str) -> str:
    """Detecta el símbolo de moneda predominante en el texto."""
    match = MONEDA_PATRON.search(texto)
    if match:
        return match.group(1)
    # Por defecto MXN para mercado mexicano
    return "$"


def _extraer_total(texto: str) -> float:
    """
    Extrae el valor del Total del ticket.
    Estrategia: buscar patrón TOTAL primero; si falla, tomar el mayor precio.
    """
    # Estrategia 1: patrón "Total: 150.00"
    match = TOTAL_PATRON.search(texto)
    if match:
        return _normalizar_precio(match.group(1))

    # Estrategia 2: el precio más alto mencionado (heurística)
    precios = [_normalizar_precio(m.group(1)) for m in PRECIO_PATRON.finditer(texto)]
    if precios:
        return max(precios)

    return 0.0


def _parsear_articulos(texto: str) -> list:
    """
    Parsea líneas del ticket para extraer artículos y precios.

    Formato esperado: "Nombre Artículo   12.50"
    Tolerante a variaciones de espaciado y caracteres OCR erróneos.
    """
    articulos = []
    lineas = texto.splitlines()

    # Palabras que indican línea a ignorar
    IGNORAR = {
        "total", "subtotal", "iva", "descuento", "cambio", "efectivo",
        "tarjeta", "gracias", "ticket", "folio", "cajero", "rfc",
        "fecha", "hora", "tel", "www", "com", "mx",
    }

    for linea in lineas:
        linea_limpia = linea.strip()
        if len(linea_limpia) < 4:
            continue

        # Omitir líneas de resumen
        primera_palabra = linea_limpia.split()[0].lower() if linea_limpia.split() else ""
        if primera_palabra in IGNORAR:
            continue

        # Intentar extraer artículo + precio
        match = ARTICULO_PATRON.match(linea_limpia)
        if match:
            nombre = match.group(1).strip()
            precio = _normalizar_precio(match.group(2))
            if precio > 0 and len(nombre) > 2:
                articulos.append(ArticuloTicket(nombre=nombre, precio=precio))
            continue

        # Fallback: línea con precio al final (menos separación)
        precios_en_linea = PRECIO_PATRON.findall(linea_limpia)
        if precios_en_linea and len(linea_limpia) > 5:
            ultimo_precio = precios_en_linea[-1]
            nombre_candidato = PRECIO_PATRON.sub("", linea_limpia).strip().rstrip("-–")
            if len(nombre_candidato) > 2:
                articulos.append(
                    ArticuloTicket(
                        nombre=nombre_candidato,
                        precio=_normalizar_precio(ultimo_precio),
                    )
                )

    logger.info("Artículos detectados: %d", len(articulos))
    return articulos


# ─── Utilidad: Guardar imagen preprocesada (debug) ────────────────────────────
def guardar_debug(ruta_imagen, ruta_salida=None) -> str:
    """Guarda la imagen preprocesada para inspección visual en depuración."""
    procesada = preprocesar_imagen(ruta_imagen)
    if ruta_salida is None:
        ruta_salida = Path(ruta_imagen).parent / f"debug_{Path(ruta_imagen).name}"
    procesada.save(str(ruta_salida))
    logger.info("Imagen debug guardada: %s", ruta_salida)
    return str(ruta_salida)


# ─── Punto de entrada rápido para pruebas ────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Uso: python ocr_engine.py <ruta_imagen>")
        sys.exit(1)

    resultado = extraer_texto_ticket(sys.argv[1])
    print(f"\n{'='*50}")
    print(f"  Moneda : {resultado.moneda}")
    print(f"  Total  : {resultado.moneda}{resultado.total:.2f}")
    print(f"  Confianza OCR: {resultado.confianza:.1f}%")
    print(f"  Artículos ({len(resultado.articulos)}):")
    for art in resultado.articulos:
        print(f"    • {art.nombre:<30} {resultado.moneda}{art.precio:.2f}")
    print(f"{'='*50}\n")
