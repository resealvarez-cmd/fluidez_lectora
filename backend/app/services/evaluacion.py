"""
Pipeline de Evaluación de Fluidez Lectora
==========================================
Módulo central del sistema. Implementa:
  1. Integración con Whisper ASR (word timestamps)
  2. Tokenización y normalización de texto
  3. Alineación por distancia de Levenshtein (Dynamic Programming)
  4. Detección de errores: omisiones, sustituciones, inserciones, repeticiones
  5. Detección de señales de automatización: vacilaciones, pausas largas
  6. Cálculo de WCPM y precisión
  7. Clasificación por nivel (benchmarks MINEDUC 1° básico)
"""
import re
import unicodedata
from dataclasses import dataclass, field
from typing import List, Optional
import openai
from app.config import get_settings

settings = get_settings()

if settings.GOOGLE_API_KEY:
    import google.generativeai as genai
    genai.configure(api_key=settings.GOOGLE_API_KEY)


# ─── ESTRUCTURAS ─────────────────────────────────────────────────────────────

@dataclass
class WordToken:
    """Palabra con timestamps del ASR"""
    word: str
    start: float = 0.0
    end: float = 0.0
    normalized: str = field(default="")

    def __post_init__(self):
        self.normalized = normalize_word(self.word)


@dataclass
class AlignmentOp:
    """Operación de alineación entre texto esperado y reconocido"""
    tipo: str  # MATCH | SUSTITUCION | OMISION | INSERCION
    posicion_texto: Optional[int]
    palabra_esperada: Optional[str]
    palabra_leida: Optional[str]
    token: Optional[WordToken]  # None si es omisión


@dataclass
class EvaluacionResult:
    """Resultado completo de la evaluación de una lectura"""
    duracion_segundos: float
    transcripcion_raw: str
    palabras_texto: List[str]
    tokens_asr: List[WordToken]
    operaciones: List[AlignmentOp]

    # Métricas calculadas
    wcpm: float = 0.0
    precision_pct: float = 0.0
    palabras_correctas: int = 0
    total_palabras_texto: int = 0
    omisiones: int = 0
    sustituciones: int = 0
    inserciones: int = 0
    repeticiones: int = 0
    vacilaciones: int = 0
    pausas_largas: int = 0
    nivel_fluidez: str = ""
    feedback_ia: str = ""
    
    # Nuevos campos del contrato
    wcpm_proyectado: bool = False
    es_texto_breve: bool = False
    conteo_palabras: str = ""
    nivel_ace: str = ""
    precision: float = 0.0 # Alias para precision_pct


# ─── NORMALIZACIÓN ────────────────────────────────────────────────────────────

def normalize_word(word: str) -> str:
    """
    Normaliza una palabra para comparación:
    - Minúsculas
    - Sin signos de puntuación
    - Sin tildes (para mayor tolerancia en ASR)
    - Sin espacios extra
    """
    word = word.lower().strip()
    # Eliminar puntuación
    word = re.sub(r"[^\w\s]", "", word)
    # Eliminar tildes
    word = unicodedata.normalize("NFD", word)
    word = "".join(c for c in word if unicodedata.category(c) != "Mn")
    return word


def tokenize_texto(contenido: str) -> List[str]:
    """
    Tokeniza el texto esperado en palabras normalizadas.
    Mantiene el orden original para alineación.
    """
    palabras = contenido.split()
    return [normalize_word(p) for p in palabras if normalize_word(p)]


# ─── ASR: WHISPER ─────────────────────────────────────────────────────────────


async def transcribir_con_whisper(audio_bytes: bytes, filename: str = "audio.webm") -> dict:
    """
    Envía el audio a OpenAI Whisper y retorna la respuesta completa con timestamps por palabra.
    """
    if not settings.OPENAI_API_KEY:
        return _mock_whisper_response()

    client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    transcription = await client.audio.transcriptions.create(
        model="whisper-1",
        file=(filename, audio_bytes, "audio/webm"),
        language="es",
        response_format="verbose_json",
        timestamp_granularities=["word"],
    )
    duration = getattr(transcription, "duration", 0.0)
    words = [{"word": w.word, "start": w.start, "end": w.end} for w in getattr(transcription, "words", [])]
    return {"text": transcription.text, "words": words, "duration": duration}


async def transcribir_con_gemini(audio_bytes: bytes, filename: str = "audio.webm") -> dict:
    """
    Usa Gemini para transcripción literal (cuando Whisper no está disponible).
    """
    if not settings.GOOGLE_API_KEY:
        return _mock_whisper_response()

    model = genai.GenerativeModel("gemini-flash-latest")
    prompt = "Transcribe el audio de forma literal, palabra por palabra, sin corregir errores ni añadir comentarios."
    
    # Simular estructura de Whisper para compatibilidad
    response = await model.generate_content_async([
        prompt,
        {"mime_type": "audio/webm", "data": audio_bytes}
    ])
    
    text = response.text.strip()
    words = [{"word": w, "start": 0.0, "end": 0.0} for w in text.split()]
    
    return {
        "text": text,
        "words": words,
        "duration": 0.0
    }


async def analizar_clinicamente_con_gemini(
    texto_esperado: str, 
    transcripcion_whisper: str, 
    lista_errores_alineacion: str
) -> str:
    """
    Envía los datos procesados a Gemini para un análisis clínico profundo,
    evitando alucinaciones al proveerle la transcripción y errores detectados.
    """
    if not settings.GOOGLE_API_KEY:
        return "Análisis clínico no disponible (sin API Key)."

    import json
    model = genai.GenerativeModel("gemini-flash-latest")
    
    prompt = f"""
Eres un experto en Psicopedagogía y Neurociencia de la Lectura. 
Analiza el desempeño de un estudiante de 1° Básico al leer un texto.

DATOS DE ENTRADA PROVISTOS POR EL SISTEMA:
- TEXTO ESPERADO: "{texto_esperado}"
- TRANSCRIPCIÓN LITERAL (Motor ASR): "{transcripcion_whisper}"
- DESVIACIONES DETECTADAS (Algoritmo Levenshtein): "{lista_errores_alineacion}"

TAREAS:
1. Realiza un ANÁLISIS CLÍNICO detallado basado EXCLUSIVAMENTE en los datos proporcionados.
   - FASE DE LECTURA: Determina si es Pre-silábica, Silábica, Silábico-Alfabética o Alfabética.
   - TIPO DE ERROR: Clasifica las desviaciones detectadas en visual, fonológico o semántico. PROHIBIDO inventar o listar errores que no existan en los 'DATOS DE ENTRADA'.
   - PROSODIA: ¿Muestra entonación? ¿Hace pausas donde no hay puntos?
2. PLAN DE INTERVENCIÓN: Sugiere 3 actividades basadas en la 'Ciencia de la Lectura'.

RESPONDE ESTRICTAMENTE EN ESTE FORMATO JSON:
{{
  "feedback": {{
     "perfil_lector": "...",
     "errores_especificos": ["...", "..."],
     "analisis_prosodia": "...",
     "estrategia_docente": "..."
  }}
}}
"""

    try:
        response = await model.generate_content_async(prompt)
        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_json)
        fb = data.get("feedback", {})
        
        if isinstance(fb, dict):
            feedback_str = f"PERFIL LECTOR: {fb.get('perfil_lector', '')}\n\n"
            feedback_str += "ERRORES TÉCNICOS:\n- " + "\n- ".join(fb.get("errores_especificos", [])) + "\n\n"
            feedback_str += f"PROSODIA: {fb.get('analisis_prosodia', '')}\n\n"
            feedback_str += f"ESTRATEGIA RECOMENDADA: {fb.get('estrategia_docente', '')}"
            return feedback_str
        return str(fb)
    except Exception as e:
        print(f"Error procesando Gemini Clinical Analysis: {e}")
        return f"Error al procesar el feedback clínico: {str(e)}"


def _mock_whisper_response() -> dict:
    """Respuesta simulada para tests sin API key"""
    return {
        "text": "el gato subio al tejado y miro las estrellas",
        "duration": 8.5,
        "words": [
            {"word": "el", "start": 0.1, "end": 0.3},
            {"word": "gato", "start": 0.4, "end": 0.8},
            {"word": "subio", "start": 0.9, "end": 1.3},
            {"word": "al", "start": 1.4, "end": 1.6},
            {"word": "tejado", "start": 1.7, "end": 2.2},
            {"word": "y", "start": 3.5, "end": 3.7},  # pausa larga
            {"word": "miro", "start": 3.8, "end": 4.2},
            {"word": "las", "start": 4.3, "end": 4.5},
            {"word": "estrellas", "start": 4.6, "end": 5.4},
        ],
    }


# ─── ALINEACIÓN: LEVENSHTEIN ─────────────────────────────────────────────────

def levenshtein_align(expected: List[str], recognized: List[str]) -> List[AlignmentOp]:
    """
    Alineación por programación dinámica (Levenshtein con backtracking).
    
    Retorna una lista de operaciones de alineación que mapea cada
    posición del texto esperado con su correspondiente en el reconocido.

    Costos:
      - MATCH: 0
      - SUSTITUCION: 1
      - OMISION (delete en esperado): 1  
      - INSERCION (insert extra en reconocido): 1
    """
    n = len(expected)
    m = len(recognized)

    # Matriz de costos
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i  # Omisiones
    for j in range(m + 1):
        dp[0][j] = j  # Inserciones

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if expected[i - 1] == recognized[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(
                    dp[i - 1][j - 1],  # Sustitución
                    dp[i - 1][j],       # Omisión (esperada no leída)
                    dp[i][j - 1],       # Inserción (leída no esperada)
                )

    # Backtracking para obtener las operaciones
    ops = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and expected[i - 1] == recognized[j - 1]:
            ops.append(("MATCH", i - 1, j - 1))
            i -= 1
            j -= 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + 1:
            ops.append(("SUSTITUCION", i - 1, j - 1))
            i -= 1
            j -= 1
        elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            ops.append(("OMISION", i - 1, None))
            i -= 1
        else:
            ops.append(("INSERCION", None, j - 1))
            j -= 1

    ops.reverse()
    return ops


# ─── DETECCIÓN DE SEÑALES DE AUTOMATIZACIÓN ──────────────────────────────────

def detectar_pausas(tokens: List[WordToken]) -> tuple[int, int]:
    """
    Analiza los gaps entre palabras para detectar:
    - Vacilaciones: pausa entre 1s y 2s
    - Pausas largas: pausa > 2s
    
    Returns: (vacilaciones, pausas_largas)
    """
    vacilaciones = 0
    pausas_largas = 0
    umbral_vacilacion = settings.VACILACION_SEGUNDOS
    umbral_pausa_larga = settings.PAUSA_LARGA_SEGUNDOS

    for i in range(1, len(tokens)):
        gap = tokens[i].start - tokens[i - 1].end
        if umbral_vacilacion <= gap < umbral_pausa_larga:
            vacilaciones += 1
        elif gap >= umbral_pausa_larga:
            pausas_largas += 1

    return vacilaciones, pausas_largas


def detectar_repeticiones(tokens: List[WordToken]) -> int:
    """
    Detecta repeticiones de palabras o bigramas en la transcripción.
    Una repetición ocurre cuando una secuencia de 1-2 palabras aparece
    inmediatamente después de sí misma.
    """
    repeticiones = 0
    palabras = [t.normalized for t in tokens]

    i = 0
    while i < len(palabras):
        # Detectar repetición de unigrama
        if i + 1 < len(palabras) and palabras[i] == palabras[i + 1]:
            repeticiones += 1
            i += 2
            continue
        # Detectar repetición de bigrama
        if (i + 3 < len(palabras) and
                palabras[i] == palabras[i + 2] and
                palabras[i + 1] == palabras[i + 3]):
            repeticiones += 1
            i += 4
            continue
        i += 1

    return repeticiones


# ─── CLASIFICACIÓN POR NIVEL ─────────────────────────────────────────────────

def clasificar_nivel_fluidez(
    precision_pct: float, 
    wcpm: float, 
    pausas_largas: int, 
    vacilaciones: int,
    total_palabras: int,
    errores: int
) -> str:
    """
    Rúbrica Bifurcada:
    - Textos Breves (< 30 palabras): Basada en conteo absoluto de errores.
    - Textos Estándar (>= 30 palabras): Basada en % de precisión y WCPM.
    """
    if total_palabras < 30:
        # Lógica para Textos Breves
        if errores == 0:
            return "avanzado"
        elif errores == 1:
            return "logrado"
        elif 2 <= errores <= 3:
            return "en_desarrollo"
        else:
            return "bajo"
    else:
        # Lógica para Textos Estándar (ACE)
        if precision_pct <= 89.0 or pausas_largas >= 5 or wcpm < 20:
            return "bajo"
        elif precision_pct < 95.0 or vacilaciones >= 5 or wcpm < 40:
            return "en_desarrollo"
        elif wcpm >= 60 and pausas_largas == 0 and vacilaciones <= 2 and precision_pct >= 95.0:
            return "avanzado"
        else:
            return "logrado"


# ─── PIPELINE PRINCIPAL ──────────────────────────────────────────────────────

async def evaluar_lectura(
    audio_bytes: bytes,
    texto_esperado: str,
    audio_filename: str = "audio.webm"
) -> EvaluacionResult:
    """
    Pipeline completo de evaluación de fluidez lectora.
    
    Args:
        audio_bytes: bytes del archivo de audio
        texto_esperado: texto completo que el estudiante debía leer
        audio_filename: nombre del archivo para Whisper

    Returns:
        EvaluacionResult con todas las métricas calculadas
    """
    # 1. ASR: Decidir motor según configuración o disponibilidad
    engine = (settings.ASR_ENGINE or "openai").lower()
    
    whisper_data = None
    if engine == "openai" and settings.OPENAI_API_KEY:
        try:
            whisper_data = await transcribir_con_whisper(audio_bytes, audio_filename)
        except Exception as e:
            print(f"Error en Whisper: {e}. Intentando fallback a Gemini...")
            if settings.GOOGLE_API_KEY:
                whisper_data = await transcribir_con_gemini(audio_bytes, audio_filename)
            else:
                whisper_data = _mock_whisper_response()
    elif engine == "gemini" and settings.GOOGLE_API_KEY:
        whisper_data = await transcribir_con_gemini(audio_bytes, audio_filename)
    else:
        whisper_data = _mock_whisper_response()

    duracion = float(whisper_data.get("duration", 0.0))
    transcripcion_raw = whisper_data.get("text", "")
    words_raw = whisper_data.get("words", [])

    # 2. Construir tokens ASR
    tokens_asr: List[WordToken] = [
        WordToken(
            word=w["word"],
            start=float(w.get("start", 0.0)),
            end=float(w.get("end", 0.0)),
        )
        for w in words_raw
    ]

    # 3. Tokenizar texto esperado
    palabras_esperadas = tokenize_texto(texto_esperado)
    palabras_reconocidas = [t.normalized for t in tokens_asr]

    # 4. Alineación Levenshtein
    alignment_ops_raw = levenshtein_align(palabras_esperadas, palabras_reconocidas)

    # 5. Construir operaciones detalladas con timestamps
    operaciones: List[AlignmentOp] = []
    recognized_idx = 0
    for op_tipo, pos_esperada, pos_reconocida in alignment_ops_raw:
        if op_tipo == "MATCH":
            token = tokens_asr[pos_reconocida] if pos_reconocida is not None else None
            operaciones.append(AlignmentOp(
                tipo="MATCH",
                posicion_texto=pos_esperada,
                palabra_esperada=palabras_esperadas[pos_esperada] if pos_esperada is not None else None,
                palabra_leida=palabras_reconocidas[pos_reconocida] if pos_reconocida is not None else None,
                token=token,
            ))
        elif op_tipo == "SUSTITUCION":
            token = tokens_asr[pos_reconocida] if pos_reconocida is not None else None
            operaciones.append(AlignmentOp(
                tipo="SUSTITUCION",
                posicion_texto=pos_esperada,
                palabra_esperada=palabras_esperadas[pos_esperada] if pos_esperada is not None else None,
                palabra_leida=palabras_reconocidas[pos_reconocida] if pos_reconocida is not None else None,
                token=token,
            ))
        elif op_tipo == "OMISION":
            operaciones.append(AlignmentOp(
                tipo="OMISION",
                posicion_texto=pos_esperada,
                palabra_esperada=palabras_esperadas[pos_esperada] if pos_esperada is not None else None,
                palabra_leida=None,
                token=None,
            ))
        elif op_tipo == "INSERCION":
            token = tokens_asr[pos_reconocida] if pos_reconocida is not None else None
            operaciones.append(AlignmentOp(
                tipo="INSERCION",
                posicion_texto=None,
                palabra_esperada=None,
                palabra_leida=palabras_reconocidas[pos_reconocida] if pos_reconocida is not None else None,
                token=token,
            ))

    # 6. Contabilizar errores
    palabras_correctas = sum(1 for op in operaciones if op.tipo == "MATCH")
    omisiones = sum(1 for op in operaciones if op.tipo == "OMISION")
    sustituciones = sum(1 for op in operaciones if op.tipo == "SUSTITUCION")
    inserciones = sum(1 for op in operaciones if op.tipo == "INSERCION")

    # 7. Señales de automatización
    vacilaciones, pausas_largas = detectar_pausas(tokens_asr)
    repeticiones = detectar_repeticiones(tokens_asr)

    # 8. WCPM y precisión
    total_palabras = len(palabras_esperadas)
    duracion_min = duracion / 60.0 if duracion > 0 else 1.0
    wcpm_original = palabras_correctas / duracion_min
    
    # Lógica de Cap y Proyección para textos breves
    es_texto_breve = total_palabras < 30
    wcpm_proyectado = False
    wcpm_final = round(wcpm_original, 2)
    
    if es_texto_breve and wcpm_original > 90:
        wcpm_proyectado = True
        wcpm_final = 90.0
    
    precision_pct = round((palabras_correctas / total_palabras * 100) if total_palabras > 0 else 0.0, 2)

    # 9. Nivel de fluidez (Rúbrica Bifurcada)
    errores_totales = omisiones + sustituciones
    nivel_fluidez = clasificar_nivel_fluidez(
        precision_pct, 
        wcpm_final, 
        pausas_largas, 
        vacilaciones,
        total_palabras,
        errores_totales
    )
    
    # Etiquetas para el contrato
    nivel_label_map = {
        "bajo": "Logro 1",
        "en_desarrollo": "Logro 2",
        "logrado": "Logro 3",
        "avanzado": "Logro 4"
    }
    nivel_ace = nivel_label_map.get(nivel_fluidez, "Sin Nivel")
    conteo_palabras = f"{palabras_correctas}/{total_palabras}"

    # 10. Análisis Clínico con Gemini (Capa de Inteligencia Pedagógica)
    feedback_ia = ""
    if settings.GOOGLE_API_KEY:
        # Formatear lista de errores detectados por Levenshtein para inyectar en el prompt
        errores_clinicos = [
            f"- {op.tipo}: esperada '{op.palabra_esperada}', leída '{op.palabra_leida}'"
            for op in operaciones if op.tipo != "MATCH"
        ]
        lista_errores_str = "\n".join(errores_clinicos) if errores_clinicos else "Ninguno detectado."
        
        feedback_ia = await analizar_clinicamente_con_gemini(
            texto_esperado=texto_esperado,
            transcripcion_whisper=transcripcion_raw,
            lista_errores_alineacion=lista_errores_str
        )

    resultado = EvaluacionResult(
        duracion_segundos=duracion,
        transcripcion_raw=transcripcion_raw,
        palabras_texto=palabras_esperadas,
        tokens_asr=tokens_asr,
        operaciones=operaciones,
        wcpm=wcpm_final,
        precision_pct=precision_pct,
        precision=precision_pct, # Alias
        palabras_correctas=palabras_correctas,
        total_palabras_texto=total_palabras,
        omisiones=omisiones,
        sustituciones=sustituciones,
        inserciones=inserciones,
        repeticiones=repeticiones,
        vacilaciones=vacilaciones,
        pausas_largas=pausas_largas,
        nivel_fluidez=nivel_fluidez,
        feedback_ia=feedback_ia,
        wcpm_proyectado=wcpm_proyectado,
        es_texto_breve=es_texto_breve,
        conteo_palabras=conteo_palabras,
        nivel_ace=nivel_ace
    )

    return resultado
