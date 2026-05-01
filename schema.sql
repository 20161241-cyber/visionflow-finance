-- ============================================================
-- VisionFlow Finance — Esquema de Base de Datos Supabase
-- Motor: PostgreSQL 15+ con Row Level Security (RLS)
-- ============================================================

-- ─── Extensiones ─────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- Búsqueda fuzzy en descripciones


-- ─── TABLA: perfiles de usuario ───────────────────────────────
-- Extiende auth.users de Supabase Auth
CREATE TABLE IF NOT EXISTS public.perfiles (
    id              UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    nombre          TEXT,
    email           TEXT UNIQUE NOT NULL,
    moneda          TEXT NOT NULL DEFAULT 'MXN',
    fecha_registro  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    avatar_url      TEXT
);

-- RLS: cada usuario solo ve su propio perfil
ALTER TABLE public.perfiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Perfil propio" ON public.perfiles
    FOR ALL USING (auth.uid() = id);

-- Trigger: crear perfil automáticamente al registrar usuario
CREATE OR REPLACE FUNCTION public.crear_perfil_nuevo_usuario()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    INSERT INTO public.perfiles (id, email)
    VALUES (NEW.id, NEW.email)
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.crear_perfil_nuevo_usuario();


-- ─── TABLA: presupuestos ───────────────────────────────────────
-- Una configuración activa por usuario (upsert)
CREATE TABLE IF NOT EXISTS public.presupuestos (
    id                       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id               UUID NOT NULL REFERENCES public.perfiles(id) ON DELETE CASCADE,
    saldo_inicial            NUMERIC(12, 2) NOT NULL CHECK (saldo_inicial > 0),
    fecha_proximo_ingreso    DATE NOT NULL,
    creado_en                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (usuario_id)  -- Un presupuesto activo por usuario
);

ALTER TABLE public.presupuestos ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Presupuesto propio" ON public.presupuestos
    FOR ALL USING (auth.uid() = usuario_id);

-- Trigger: actualizar timestamp automáticamente
CREATE OR REPLACE FUNCTION actualizar_timestamp()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.actualizado_en = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER actualizar_presupuesto_ts
    BEFORE UPDATE ON public.presupuestos
    FOR EACH ROW EXECUTE FUNCTION actualizar_timestamp();


-- ─── TABLA: transacciones ──────────────────────────────────────
-- Log completo de gastos registrados (manual o por OCR)
CREATE TABLE IF NOT EXISTS public.transacciones (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id      UUID NOT NULL REFERENCES public.perfiles(id) ON DELETE CASCADE,
    descripcion     TEXT NOT NULL,
    monto           NUMERIC(10, 2) NOT NULL CHECK (monto > 0),
    categoria       TEXT NOT NULL DEFAULT 'Sin Categoría',
    es_hormiga      BOOLEAN NOT NULL DEFAULT FALSE,
    imagen_url      TEXT,           -- URL del ticket en Supabase Storage
    fecha           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metodo          TEXT DEFAULT 'ocr' CHECK (metodo IN ('ocr', 'manual', 'importacion')),
    notas           TEXT
);

-- Índices para consultas frecuentes
CREATE INDEX IF NOT EXISTS idx_tx_usuario ON public.transacciones (usuario_id);
CREATE INDEX IF NOT EXISTS idx_tx_fecha   ON public.transacciones (fecha DESC);
CREATE INDEX IF NOT EXISTS idx_tx_categoria ON public.transacciones (categoria);
CREATE INDEX IF NOT EXISTS idx_tx_hormiga   ON public.transacciones (es_hormiga) WHERE es_hormiga = TRUE;
-- Índice de texto para búsqueda en descripción
CREATE INDEX IF NOT EXISTS idx_tx_descripcion_trgm
    ON public.transacciones USING GIN (descripcion gin_trgm_ops);

ALTER TABLE public.transacciones ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Transacciones propias" ON public.transacciones
    FOR ALL USING (auth.uid() = usuario_id);


-- ─── TABLA: tickets_ocr ────────────────────────────────────────
-- Almacena el resultado raw del OCR para auditoría
CREATE TABLE IF NOT EXISTS public.tickets_ocr (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id      UUID NOT NULL REFERENCES public.perfiles(id) ON DELETE CASCADE,
    imagen_url      TEXT NOT NULL,
    texto_raw       TEXT,           -- Texto extraído por Tesseract
    confianza_pct   NUMERIC(5, 2),  -- Porcentaje de confianza OCR
    total_detectado NUMERIC(10, 2),
    moneda          TEXT DEFAULT '$',
    procesado_en    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    articulos_json  JSONB           -- Array de artículos parseados
);

ALTER TABLE public.tickets_ocr ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Tickets propios" ON public.tickets_ocr
    FOR ALL USING (auth.uid() = usuario_id);


-- ─── VISTA: resumen_por_categoria ─────────────────────────────
-- Agrega gastos por categoría para el dashboard
CREATE OR REPLACE VIEW public.resumen_por_categoria AS
SELECT
    usuario_id,
    categoria,
    SUM(monto)                              AS total_monto,
    COUNT(*)                                AS num_transacciones,
    AVG(monto)                              AS promedio_monto,
    SUM(monto) FILTER (WHERE es_hormiga)    AS total_hormiga,
    DATE_TRUNC('month', fecha)              AS mes
FROM public.transacciones
GROUP BY usuario_id, categoria, DATE_TRUNC('month', fecha);


-- ─── VISTA: alertas_hormiga ────────────────────────────────────
-- Detecta gastos hormiga recurrentes (últimos 7 días)
CREATE OR REPLACE VIEW public.alertas_hormiga AS
SELECT
    usuario_id,
    categoria,
    COUNT(*)                        AS frecuencia_semanal,
    SUM(monto)                      AS gasto_semanal,
    ROUND(SUM(monto) / 7.0 * 30, 2) AS impacto_mensual_proyectado
FROM public.transacciones
WHERE
    es_hormiga = TRUE
    AND fecha >= NOW() - INTERVAL '7 days'
GROUP BY usuario_id, categoria
HAVING COUNT(*) >= 3
ORDER BY impacto_mensual_proyectado DESC;


-- ─── STORAGE BUCKET ───────────────────────────────────────────
-- Configurar en el Dashboard de Supabase o via API:
-- INSERT INTO storage.buckets (id, name, public)
-- VALUES ('tickets', 'tickets', false);

-- Política de acceso al Storage (ejecutar en SQL Editor de Supabase):
-- CREATE POLICY "Usuarios acceden a sus tickets"
-- ON storage.objects FOR ALL
-- USING (bucket_id = 'tickets' AND auth.uid()::text = (storage.foldername(name))[1]);


-- ─── DATOS DE EJEMPLO (desarrollo) ────────────────────────────
-- Descomentar para poblar la BD en entorno de dev

/*
INSERT INTO public.transacciones (usuario_id, descripcion, monto, categoria, es_hormiga) VALUES
    ('00000000-0000-0000-0000-000000000001', 'Coca Cola 600ml OXXO', 22.00, 'Gasto Hormiga', TRUE),
    ('00000000-0000-0000-0000-000000000001', 'Papitas Sabritas', 18.50, 'Gasto Hormiga', TRUE),
    ('00000000-0000-0000-0000-000000000001', 'Pollo entero Soriana', 125.00, 'Alimentación', FALSE),
    ('00000000-0000-0000-0000-000000000001', 'Detergente Ariel 1kg', 89.00, 'Hogar', FALSE),
    ('00000000-0000-0000-0000-000000000001', 'Netflix mensual', 199.00, 'Entretenimiento', FALSE),
    ('00000000-0000-0000-0000-000000000001', 'Café Latte Starbucks', 85.00, 'Gasto Hormiga', TRUE);
*/
