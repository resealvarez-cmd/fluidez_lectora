# FluidezIA — MVP de Evaluación de Fluidez Lectora

## Estructura del proyecto

```
FLUIDEZ LECTORA/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   ├── database.py          # SQLAlchemy async engine
│   │   ├── models.py            # ORM models
│   │   ├── schemas.py           # Pydantic schemas
│   │   ├── routers/
│   │   │   ├── estudiantes.py   # CRUD + historial
│   │   │   ├── textos.py        # CRUD textos
│   │   │   └── lecturas.py      # Upload audio + evaluación
│   │   └── services/
│   │       └── evaluacion.py    # Pipeline ASR + Levenshtein + métricas
│   ├── tests/
│   │   └── test_evaluacion.py
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── index.html               # Panel Docente
    ├── estudiante.html          # Pantalla Estudiante
    ├── manifest.json            # PWA
    └── src/
        ├── styles.css
        ├── api.js               # Cliente API centralizado
        ├── docente.js
        └── estudiante.js
```

---

## Instalación rápida

### Backend

```bash
cd backend

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# → Edita .env con tu OPENAI_API_KEY

# Levantar servidor (SQLite en dev, sin Postgres necesario)
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# Opción A: servidor estático simple
python3 -m http.server 5500
# → Abre http://localhost:5500

# Opción B: VS Code Live Server
# Instala extensión "Live Server" → clic derecho en index.html → Open with Live Server
```

### Ejecutar tests

```bash
cd backend
pip install pytest pytest-asyncio
pytest tests/ -v
```

---

## Variables de entorno (.env)

| Variable | Descripción | Valor por defecto |
|---|---|---|
| `DATABASE_URL` | URL de PostgreSQL o SQLite | `sqlite+aiosqlite:///./fluidez_lectora.db` |
| `OPENAI_API_KEY` | API key de OpenAI (Whisper) | `""` (usa mock en dev) |
| `AUDIO_STORAGE_BUCKET` | Bucket Supabase Storage | `lecturas-audio` |
| `PAUSA_LARGA_SEGUNDOS` | Umbral de pausa larga | `2.0` |
| `VACILACION_SEGUNDOS` | Umbral de vacilación | `1.0` |

---

## API Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Estado del servidor |
| POST | `/api/estudiantes/` | Crear estudiante |
| GET | `/api/estudiantes/` | Listar estudiantes |
| GET | `/api/estudiantes/{id}/historial` | Historial de lecturas |
| POST | `/api/textos/` | Crear texto |
| GET | `/api/textos/` | Listar textos |
| POST | `/api/lecturas/` | Crear sesión de lectura |
| POST | `/api/lecturas/{id}/audio` | Subir audio → lanza evaluación |
| GET | `/api/lecturas/{id}` | Estado de la lectura (polling) |
| GET | `/api/lecturas/{id}/resultado` | Resultado completo |

Documentación interactiva: `http://localhost:8000/docs`

---

## Benchmarks WCPM (1° Básico — MINEDUC)

| Nivel | WCPM | Descripción |
|---|---|---|
| Bajo | < 20 | Lectura silábica/letra a letra |
| En desarrollo | 20–39 | Lectura con esfuerzo notable |
| Logrado | 40–59 | Lectura fluida esperada para el nivel |
| Avanzado | ≥ 60 | Por encima del nivel esperado |

---

## Flujo end-to-end

```
1. Docente crea texto → POST /api/textos/
2. Docente crea sesión → POST /api/lecturas/ { estudiante_id, texto_id }
3. Estudiante abre enlace → ve el texto en pantalla grande
4. Estudiante graba → MediaRecorder API → blob WebM
5. Frontend envía audio → POST /api/lecturas/{id}/audio
6. Backend guarda audio → lanza tarea async
7. Tarea: Whisper ASR → Levenshtein → métricas → DB
8. Frontend hace polling cada 2s → GET /api/lecturas/{id}
9. Al completarse → GET /api/lecturas/{id}/resultado
10. Estudiante ve WCPM, precisión, texto anotado con errores
11. Docente ve historial → GET /api/estudiantes/{id}/historial
```
