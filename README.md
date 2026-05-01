# 🧠 VisionFlow Finance — MVP

> Gestión inteligente de gastos para estudiantes y presupuestos ajustados.
> Elimina la entrada manual de datos mediante escaneo OCR de tickets de compra.

---

## 📁 Estructura del Proyecto

```
visionflow_finance/
│
├── main.py                   # Punto de entrada Flet + navegación de rutas
│
├── core/
│   ├── ocr_engine.py         # Motor OCR: preprocesamiento + extracción Tesseract
│   ├── classifier.py         # Clasificador por palabras clave + Regex
│   ├── budget_engine.py      # Presupuesto quincenal + detector Gasto Hormiga
│   └── db_client.py          # Cliente Supabase (Auth + DB + Storage)
│
├── ui/
│   ├── dashboard.py          # Vista principal: gráfico dona + alertas
│   ├── scanner.py            # Vista de escaneo de tickets
│   ├── historial.py          # Vista de historial de transacciones
│   └── consejos.py           # Vista de consejos de ahorro dinámicos
│
├── data/
│   ├── schema.sql            # Esquema PostgreSQL para Supabase
│   └── transacciones_cache.json  # Caché local (auto-generado)
│
├── assets/                   # Fuentes, íconos, imágenes estáticas
├── requirements.txt
└── .env.example
```

---

## ⚡ Instalación Rápida

### 1. Clonar y crear entorno virtual
```bash
git clone <repo>
cd visionflow_finance
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Instalar Tesseract OCR
```bash
# Ubuntu/Debian
sudo apt install tesseract-ocr tesseract-ocr-spa

# macOS
brew install tesseract tesseract-lang

# Windows
# Descargar instalador de: https://github.com/UB-Mannheim/tesseract/wiki
# Agregar a PATH o configurar TESSERACT_PATH en .env
```

### 3. Configurar variables de entorno
```bash
cp .env.example .env
# Editar .env con tus credenciales de Supabase
```

### 4. Ejecutar
```bash
python main.py
```

### 5. Build para Mobile (Android)
```bash
flet build apk --project "VisionFlow Finance"
```

---

## 🗄️ Configurar Supabase

1. Crea un proyecto en [supabase.com](https://supabase.com)
2. Ve a **SQL Editor** y ejecuta `data/schema.sql`
3. En **Storage**, crea un bucket llamado `tickets` (privado)
4. Copia la URL y clave `anon` a tu `.env`

---

## 🧩 Módulos Clave

### `ocr_engine.py` — Flujo de procesamiento
```
Imagen → Escala grises → CLAHE → Filtro bilateral
→ Umbralización adaptativa → Tesseract (PSM 6, spa+eng)
→ Regex extracción → ArticuloTicket[]
```

### `classifier.py` — Categorías
| Categoría | Ejemplos |
|-----------|---------|
| 🥗 Alimentación | Leche, Pollo, Soriana, UberEats |
| 🏠 Hogar | Detergente, CFE, Internet, Renta |
| 👤 Uso Personal | Shampoo, Gasolina, Farmacia, Libros |
| 🎮 Entretenimiento | Netflix, Cinépolis, Steam, Bar |
| 🐜 Gasto Hormiga | OXXO, Café, Papitas, Propina |

### `budget_engine.py` — Fórmula quincenal
```python
Presupuesto Diario = Saldo Actual / Días Restantes al cobro
Impacto Mensual Hormiga = (Gasto semanal / 7) × 30
```

---

## 🔧 Extensiones Recomendadas

### Reemplazar Tesseract por Google Cloud Vision (más preciso)
```python
from google.cloud import vision
client = vision.ImageAnnotatorClient()
# Usar client.text_detection() en lugar de pytesseract
```

### Agregar IA con Anthropic Claude
Para clasificación semántica avanzada, puedes conectar la API de Claude:
```python
import anthropic
client = anthropic.Anthropic()
# Enviar texto_raw del ticket para clasificación contextual
```

---

## 📱 Plataformas Soportadas
- ✅ **Desktop** (Windows, macOS, Linux) — `python main.py`
- ✅ **Android** — `flet build apk`
- ✅ **iOS** — `flet build ipa` (requiere Mac + Xcode)
- ✅ **Web** — `flet run --web`

---

## 📄 Licencia
MIT — Úsalo, modifícalo, compártelo.
