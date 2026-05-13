-- ═══════════════════════════════════════════════════════════════
-- FLUIDEZ LECTORA — Schema completo para Supabase (PostgreSQL)
-- Ejecutar en: Supabase Dashboard → SQL Editor → New Query
-- ═══════════════════════════════════════════════════════════════

-- ── 1. EXTENSIONES ──────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── 2. COLEGIOS ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS colegios (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre      TEXT NOT NULL,
    rbd         TEXT UNIQUE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── 3. USUARIOS (docentes / admin) ──────────────────────────────
CREATE TABLE IF NOT EXISTS usuarios (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email            TEXT UNIQUE NOT NULL,
    nombre           TEXT NOT NULL,
    hashed_password  TEXT NOT NULL DEFAULT '',
    rol              TEXT NOT NULL DEFAULT 'docente',
    colegio_id       UUID REFERENCES colegios(id) ON DELETE SET NULL,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ── 4. ESTUDIANTES ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS estudiantes (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre            TEXT NOT NULL,
    apellido          TEXT NOT NULL,
    curso             TEXT NOT NULL,
    colegio_id        UUID REFERENCES colegios(id) ON DELETE SET NULL,
    fecha_nacimiento  DATE,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- ── 5. TEXTOS ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS textos (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    titulo      TEXT NOT NULL,
    contenido   TEXT NOT NULL,
    nivel       TEXT NOT NULL DEFAULT '1basico',
    docente_id  UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── 6. LECTURAS (sesión de grabación) ───────────────────────────
CREATE TABLE IF NOT EXISTS lecturas (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    estudiante_id       UUID NOT NULL REFERENCES estudiantes(id) ON DELETE CASCADE,
    texto_id            UUID NOT NULL REFERENCES textos(id),
    audio_url           TEXT,
    audio_path          TEXT,
    duracion_segundos   FLOAT,
    transcripcion_raw   TEXT,
    estado              TEXT NOT NULL DEFAULT 'pendiente',
    error_mensaje       TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ── 7. MÉTRICAS ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS metricas (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lectura_id            UUID NOT NULL UNIQUE REFERENCES lecturas(id) ON DELETE CASCADE,
    wcpm                  FLOAT NOT NULL,
    precision_pct         FLOAT NOT NULL,
    total_palabras_texto  INT NOT NULL,
    palabras_correctas    INT NOT NULL,
    omisiones             INT DEFAULT 0,
    sustituciones         INT DEFAULT 0,
    inserciones           INT DEFAULT 0,
    repeticiones          INT DEFAULT 0,
    vacilaciones          INT DEFAULT 0,
    pausas_largas         INT DEFAULT 0,
    nivel_fluidez         TEXT,
    created_at            TIMESTAMPTZ DEFAULT NOW()
);

-- ── 8. ERRORES DETALLADOS ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS errores_detalle (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lectura_id        UUID NOT NULL REFERENCES lecturas(id) ON DELETE CASCADE,
    tipo              TEXT NOT NULL,
    posicion_en_texto INT,
    palabra_esperada  TEXT,
    palabra_leida     TEXT,
    timestamp_inicio  FLOAT,
    timestamp_fin     FLOAT,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- ── 9. ÍNDICES ───────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_lecturas_estudiante   ON lecturas(estudiante_id);
CREATE INDEX IF NOT EXISTS idx_lecturas_texto        ON lecturas(texto_id);
CREATE INDEX IF NOT EXISTS idx_lecturas_estado       ON lecturas(estado);
CREATE INDEX IF NOT EXISTS idx_metricas_lectura      ON metricas(lectura_id);
CREATE INDEX IF NOT EXISTS idx_errores_lectura       ON errores_detalle(lectura_id);
CREATE INDEX IF NOT EXISTS idx_estudiantes_colegio   ON estudiantes(colegio_id);
CREATE INDEX IF NOT EXISTS idx_textos_docente        ON textos(docente_id);

-- ── 10. DATOS DE PRUEBA ──────────────────────────────────────────
-- Colegio demo
INSERT INTO colegios (nombre, rbd) VALUES ('Colegio Demo', '99999')
ON CONFLICT (rbd) DO NOTHING;

-- Texto de ejemplo para 1° básico
INSERT INTO textos (titulo, contenido, nivel) VALUES (
    'El gato y la luna',
    'El gato subió al tejado. Desde allí miró la luna. La luna brillaba mucho. El gato maulló tres veces. Luego bajó despacio.',
    '1basico'
) ON CONFLICT DO NOTHING;
