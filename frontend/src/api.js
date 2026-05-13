/**
 * API Client — Fluidez Lectora
 * Centraliza todas las llamadas al backend FastAPI
 */
const API_BASE = "http://localhost:8001";

const api = {
  _token: () => localStorage.getItem('fl_token'),

  async get(path) {
    const headers = {};
    const t = api._token();
    if (t) headers['Authorization'] = `Bearer ${t}`;
    const r = await fetch(API_BASE + path, { headers });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  async post(path, body) {
    const headers = { "Content-Type": "application/json" };
    const t = api._token();
    if (t) headers['Authorization'] = `Bearer ${t}`;
    const r = await fetch(API_BASE + path, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  async delete(path) {
    const headers = {};
    const t = api._token();
    if (t) headers['Authorization'] = `Bearer ${t}`;
    const r = await fetch(API_BASE + path, { method: "DELETE", headers });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  async upload(path, formData) {
    const headers = {};
    const t = api._token();
    if (t) headers['Authorization'] = `Bearer ${t}`;
    const r = await fetch(API_BASE + path, { method: "POST", headers, body: formData });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },

  // ── Auth
  login: (email, password) => api.post('/api/auth/login', { email, password }),
  register: (nombre, email, password) => api.post('/api/auth/register', { nombre, email, password }),
  logout: () => { localStorage.removeItem('fl_token'); localStorage.removeItem('fl_usuario'); window.location.href = '/login.html'; },
  getUsuario: () => JSON.parse(localStorage.getItem('fl_usuario') || 'null'),

  // ── Estudiantes
  getEstudiantes: () => api.get("/api/estudiantes/"),
  crearEstudiante: (d) => api.post("/api/estudiantes/", d),
  getLecturas: () => api.get("/api/lecturas/"),
  getHistorial: (id) => api.get(`/api/estudiantes/${id}/historial`),

  // ── Textos
  getTextos: () => api.get("/api/textos/"),
  crearTexto: (d) => api.post("/api/textos/", d),

  // ── Lecturas
  crearLectura: (d) => api.post("/api/lecturas/", d),
  getLectura: (id) => api.get(`/api/lecturas/${id}`),
  getResultado: (id) => api.get(`/api/lecturas/${id}/resultado`),
  reanalizarLectura: (id) => api.post(`/api/lecturas/${id}/reanalizar`, {}),
  subirAudio: (id, blob) => {
    const fd = new FormData();
    fd.append("audio", blob, "audio.webm");
    return api.upload(`/api/lecturas/${id}/audio`, fd);
  },

  // ── Health
  health: () => api.get("/health"),
};

// Poll hasta completado o error
async function pollResultado(lecturaId, onUpdate, maxMs = 60000) {
  const start = Date.now();
  while (Date.now() - start < maxMs) {
    const l = await api.getLectura(lecturaId);
    onUpdate(l.estado);
    if (l.estado === "completado") return api.getResultado(lecturaId);
    if (l.estado === "error") throw new Error(l.error_mensaje || "Error al procesar");
    await new Promise(res => setTimeout(res, 2000));
  }
  throw new Error("Tiempo de espera agotado");
}
