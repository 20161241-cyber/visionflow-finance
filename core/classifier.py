"""
classifier.py — Motor de clasificación de gastos por palabras clave y Regex.

Categorías disponibles:
  - Alimentación
  - Hogar
  - Uso Personal
  - Entretenimiento
  - Gasto Hormiga  ← compras recurrentes de bajo valor (café, snacks, etc.)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


# ─── Categorías ───────────────────────────────────────────────────────────────
class Categoria(str, Enum):
    ALIMENTACION   = "Alimentación"
    HOGAR          = "Hogar"
    USO_PERSONAL   = "Uso Personal"
    ENTRETENIMIENTO = "Entretenimiento"
    GASTO_HORMIGA  = "Gasto Hormiga"
    SIN_CATEGORIA  = "Sin Categoría"


# ─── Diccionario de palabras clave por categoría ─────────────────────────────
# ¡EXTENSIBLE! Agrega palabras sin tocar la lógica.

PALABRAS_CLAVE: dict[Categoria, list[str]] = {

    Categoria.GASTO_HORMIGA: [
        # Tiendas de conveniencia
        "oxxo", "seven", "7-eleven", "circle k", "extra", "super 7",
        # Bebidas gasto rápido
        "café", "cafe", "capuchino", "expresso", "latte", "americano",
        "refresco", "coca", "pepsi", "sprite", "fanta", "agua mineral",
        "cerveza", "chela", "michelada", "clamato",
        # Snacks
        "papitas", "chips", "sabritas", "doritos", "cheetos", "takis",
        "palomitas", "gansito", "pingüino", "submarino", "roles",
        "dulces", "chicles", "chocolate", "barra",
        # Comida rápida pequeña
        "taco", "tacos", "quesadilla", "torta", "elote", "esquite",
        "tamale", "tamal", "gordita", "sope",
        # Propinas y misc
        "propina", "tip", "estacionamiento", "parquímetro", "caseta",
        "peaje", "lavado", "descargable",
    ],

    Categoria.ALIMENTACION: [
        # Supermercados
        "walmart", "soriana", "chedraui", "liverpool", "costco",
        "la comer", "city market", "superama", "bodega aurrera",
        # Productos alimenticios
        "leche", "pan", "huevo", "pollo", "carne", "res", "cerdo",
        "pescado", "atún", "sardina", "jamón", "queso", "mantequilla",
        "aceite", "arroz", "frijol", "pasta", "sopa", "verdura",
        "fruta", "manzana", "naranja", "plátano", "tomate", "jitomate",
        "zanahoria", "papa", "cebolla", "ajo", "chile", "cilantro",
        "sal", "azúcar", "harina", "tortilla", "tostada",
        "yogur", "crema", "aguacate", "guacamole",
        # Restaurantes / deliveries
        "restaurante", "restaurant", "comida", "menú", "platillo",
        "uber eats", "rappi", "didi food", "antojitos",
    ],

    Categoria.HOGAR: [
        # Limpieza
        "detergente", "jabón", "cloro", "pinol", "fabuloso", "ariel",
        "suavitel", "escoba", "trapeador", "jerga", "esponja",
        "bolsas basura", "papel higiénico", "servilletas", "kleenex",
        # Servicios
        "electricidad", "cfe", "agua", "gas", "internet", "telmex",
        "izzi", "megacable", "axtel", "totalplay", "renta", "alquiler",
        # Utensilios y muebles
        "sartén", "olla", "plato", "vaso", "tenedor", "cuchara",
        "mueble", "silla", "mesa", "lámpara", "foco", "pila", "extensión",
        # Ferretería
        "pintura", "martillo", "clavo", "tornillo", "cemento", "cable",
    ],

    Categoria.USO_PERSONAL: [
        # Higiene
        "shampoo", "acondicionador", "gel", "crema", "loción", "desodorante",
        "pasta dental", "cepillo", "hilo dental", "rasuradora", "gillette",
        "tampón", "toalla femenina", "colonia", "perfume",
        # Ropa y calzado
        "camisa", "pantalón", "vestido", "falda", "zapatos", "tenis",
        "calcetines", "ropa interior", "chamarra", "sudadera", "playera",
        # Salud y medicamentos
        "farmacia", "benavides", "similares", "del ahorro",
        "paracetamol", "ibuprofeno", "aspirina", "vitamina",
        "médico", "doctor", "consulta", "medicamento",
        # Transporte personal
        "uber", "didi", "taxi", "camión", "metro", "metrobús",
        "gasolina", "pemex", "bp", "shell",
        # Educación
        "libro", "cuaderno", "pluma", "lápiz", "libreta", "mochila",
        "colegiatura", "inscripción", "taller", "curso",
    ],

    Categoria.ENTRETENIMIENTO: [
        # Streaming
        "netflix", "spotify", "disney", "hbo", "amazon prime",
        "youtube premium", "apple tv", "crunchyroll",
        # Cine y eventos
        "cinepolis", "cinemex", "cine", "teatro", "concierto", "evento",
        "boletín", "boletazo", "ticketmaster",
        # Juegos y apps
        "steam", "playstation", "xbox", "nintendo", "videojuego",
        "app store", "google play", "suscripción",
        # Salidas sociales
        "bar", "club", "antro", "discoteca", "karaoke", "bowling",
        "parque", "museo", "zoológico", "acuario",
        # Viajes y turismo
        "hotel", "airbnb", "vuelo", "aerolínea", "viaje",
    ],
}

# Precompilar expresiones regulares para máxima velocidad
_PATRONES_COMPILADOS: dict[Categoria, re.Pattern] = {
    cat: re.compile(
        r"\b(" + "|".join(re.escape(kw) for kw in keywords) + r")\b",
        re.IGNORECASE,
    )
    for cat, keywords in PALABRAS_CLAVE.items()
}

# Umbral máximo para calificar como "Gasto Hormiga" por precio
UMBRAL_GASTO_HORMIGA_MXN = 80.0


# ─── Función de clasificación ─────────────────────────────────────────────────
def clasificar_articulo(nombre: str, precio: float = 0.0) -> Categoria:
    """
    Clasifica un artículo en una categoría usando palabras clave + heurísticas de precio.

    Prioridad:
      1. Gasto Hormiga por nombre (café, chips, etc.).
      2. Otras categorías por nombre.
      3. Si el precio es bajo Y no clasificado → Gasto Hormiga.

    Args:
        nombre: Nombre del artículo tal como apareció en el ticket.
        precio: Precio del artículo (MXN).

    Returns:
        Categoría asignada.
    """
    nombre_limpio = nombre.strip().lower()

    # 1. Verificar Gasto Hormiga primero (mayor prioridad)
    if _PATRONES_COMPILADOS[Categoria.GASTO_HORMIGA].search(nombre_limpio):
        return Categoria.GASTO_HORMIGA

    # 2. Revisar resto de categorías en orden de prioridad
    orden_prioridad = [
        Categoria.ALIMENTACION,
        Categoria.HOGAR,
        Categoria.USO_PERSONAL,
        Categoria.ENTRETENIMIENTO,
    ]
    for categoria in orden_prioridad:
        if _PATRONES_COMPILADOS[categoria].search(nombre_limpio):
            return categoria

    # 3. Heurística de precio bajo → Gasto Hormiga
    if 0 < precio <= UMBRAL_GASTO_HORMIGA_MXN:
        return Categoria.GASTO_HORMIGA

    return Categoria.SIN_CATEGORIA


def clasificar_lista(articulos: list) -> list:
    """
    Clasifica una lista de ArticuloTicket in-place.

    Args:
        articulos: Lista de ArticuloTicket (de ocr_engine.py).

    Returns:
        La misma lista con el campo `categoria` actualizado.
    """
    for art in articulos:
        art.categoria = clasificar_articulo(art.nombre, art.precio).value
    return articulos


# ─── Agregación por categoría ─────────────────────────────────────────────────
@dataclass
class ResumenCategorias:
    totales: dict[str, float]
    porcentajes: dict[str, float]
    total_general: float


def resumir_por_categoria(articulos: list) -> ResumenCategorias:
    """
    Agrupa los artículos y calcula totales y porcentajes por categoría.

    Args:
        articulos: Lista de ArticuloTicket clasificados.

    Returns:
        ResumenCategorias con totales y porcentajes.
    """
    totales: dict[str, float] = {}
    for art in articulos:
        totales[art.categoria] = totales.get(art.categoria, 0.0) + art.precio

    total_general = sum(totales.values()) or 1.0  # Evitar división por cero
    porcentajes = {cat: round(monto / total_general * 100, 1) for cat, monto in totales.items()}

    return ResumenCategorias(
        totales=totales,
        porcentajes=porcentajes,
        total_general=round(total_general, 2),
    )
