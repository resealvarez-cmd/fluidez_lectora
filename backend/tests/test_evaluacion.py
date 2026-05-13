"""Tests unitarios del motor de evaluación"""
import pytest
import asyncio
from app.services.evaluacion import (
    normalize_word, tokenize_texto, levenshtein_align,
    detectar_pausas, detectar_repeticiones, clasificar_nivel_fluidez,
    WordToken
)

# ── Normalización ─────────────────────────────────────────────────

def test_normalize_word_basic():
    assert normalize_word("Gato,") == "gato"

def test_normalize_word_tildes():
    assert normalize_word("María") == "maria"

def test_normalize_word_punctuation():
    assert normalize_word("¡Hola!") == "hola"

def test_tokenize_texto():
    t = "El gato sube al árbol."
    tokens = tokenize_texto(t)
    assert tokens == ["el", "gato", "sube", "al", "arbol"]

# ── Levenshtein ───────────────────────────────────────────────────

def test_align_perfect():
    expected = ["el", "gato", "sube"]
    recognized = ["el", "gato", "sube"]
    ops = levenshtein_align(expected, recognized)
    tipos = [o[0] for o in ops]
    assert all(t == "MATCH" for t in tipos)

def test_align_omision():
    expected = ["el", "gato", "sube"]
    recognized = ["el", "sube"]
    ops = levenshtein_align(expected, recognized)
    tipos = [o[0] for o in ops]
    assert "OMISION" in tipos
    assert tipos.count("MATCH") == 2

def test_align_sustitucion():
    expected = ["el", "gato", "sube"]
    recognized = ["el", "perro", "sube"]
    ops = levenshtein_align(expected, recognized)
    tipos = [o[0] for o in ops]
    assert "SUSTITUCION" in tipos

def test_align_insercion():
    expected = ["el", "gato"]
    recognized = ["el", "gran", "gato"]
    ops = levenshtein_align(expected, recognized)
    tipos = [o[0] for o in ops]
    assert "INSERCION" in tipos

# ── Pausas ────────────────────────────────────────────────────────

def test_detectar_pausas():
    tokens = [
        WordToken("el", 0.0, 0.3),
        WordToken("gato", 0.4, 0.8),
        WordToken("sube", 3.1, 3.6),   # gap = 2.3s → pausa larga
        WordToken("al", 4.8, 5.0),     # gap = 1.2s → vacilación
        WordToken("árbol", 5.1, 5.8),
    ]
    vac, pausas = detectar_pausas(tokens)
    assert pausas >= 1
    assert vac >= 1

# ── Repeticiones ──────────────────────────────────────────────────

def test_detectar_repeticiones():
    tokens = [
        WordToken("el", 0.0, 0.3),
        WordToken("el", 0.4, 0.7),
        WordToken("gato", 0.8, 1.2),
    ]
    rep = detectar_repeticiones(tokens)
    assert rep == 1

# ── Clasificación ─────────────────────────────────────────────────

def test_nivel_bajo():    assert clasificar_nivel_fluidez(15) == "bajo"
def test_nivel_desarrollo(): assert clasificar_nivel_fluidez(30) == "en_desarrollo"
def test_nivel_logrado(): assert clasificar_nivel_fluidez(50) == "logrado"
def test_nivel_avanzado(): assert clasificar_nivel_fluidez(70) == "avanzado"

# ── Pipeline async (sin API key) ──────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_mock():
    from app.services.evaluacion import evaluar_lectura
    # Sin API key usa mock response
    resultado = await evaluar_lectura(
        audio_bytes=b"fake_audio",
        texto_esperado="el gato subio al tejado y miro las estrellas",
    )
    assert resultado.wcpm > 0
    assert 0 <= resultado.precision_pct <= 100
    assert resultado.nivel_fluidez in ("bajo", "en_desarrollo", "logrado", "avanzado")
    assert resultado.total_palabras_texto == 9
