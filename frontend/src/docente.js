/* ── Docente JS ── */
let textos = [], estudiantes = [];

// ── Auth Guard ────────────────────────────────────────────────────
const _usuario = api.getUsuario();
if (!localStorage.getItem('fl_token') || !_usuario) {
  window.location.href = '/login.html';
}

async function init() {
  try {
    // Mostrar nombre del docente en sidebar
    const logotitle = document.querySelector('.logo-title');
    if (logotitle && _usuario) logotitle.textContent = _usuario.nombre.split(' ')[0];
    
    await checkHealth();
    await loadTextos();
    await loadEstudiantes();
    await loadResultados();
  } catch (err) {
    console.error("Error en init:", err);
    setStatus(false);
  }
}

async function checkHealth() {
  try {
    await api.health();
    setStatus(true);
  } catch { setStatus(false); }
}

function setStatus(ok) {
  const el = document.getElementById('apiStatus');
  if (!el) return;
  el.innerHTML = ok
    ? '<span class="dot ok"></span><span class="label" style="color:var(--success)">Conectado</span>'
    : '<span class="dot error"></span><span class="label" style="color:var(--danger)">Error de Conexión</span>';
}

async function generarFichaIndividualPDF(lecturaId) {
  try {
    showToast('Generando Ficha Clínica...', 'info');
    const l = resultadosList.find(r => r.id === lecturaId);
    if (!l) return;

    const jspdfLib = window.jspdf;
    const doc = new jspdfLib.jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
    const W = doc.internal.pageSize.getWidth();
    const H = doc.internal.pageSize.getHeight();
    
    // --- PÁGINA 1: RESUMEN Y MÉTRICAS ---
    // Encabezado
    doc.setFillColor(30, 41, 59); 
    doc.rect(0, 0, W, 45, 'F');
    doc.setTextColor(255, 255, 255);
    doc.setFontSize(22); doc.setFont('helvetica', 'bold');
    doc.text('INFORME DE DESEMPEÑO LECTOR', 15, 20);
    doc.setFontSize(10); doc.setFont('helvetica', 'normal');
    doc.text('ANÁLISIS PSICOPEDAGÓGICO IA — PROFEIC', 15, 28);
    
    // Datos Alumno
    doc.setFillColor(248, 250, 252); doc.rect(0, 45, W, 25, 'F');
    doc.setTextColor(30, 41, 59);
    doc.setFontSize(11); doc.setFont('helvetica', 'bold');
    doc.text(`ESTUDIANTE: ${l.estudiante.toUpperCase()}`, 15, 55);
    
    // Fix Invalid Date bug
    const fechaLectura = l.created_at ? new Date(l.created_at).toLocaleDateString('es-CL') : new Date().toLocaleDateString('es-CL');
    doc.text(`CURSO: ${l.curso}   |   FECHA: ${fechaLectura}`, 15, 62);
    
    // Métricas en tabla (Contrato irrompible)
    const m = l.metricas || {};
    const labelVelocidad = m.es_texto_breve ? 'Velocidad Proyectada' : 'Velocidad (Palabras por Minuto)';
    const valorVelocidad = m.wcpm_proyectado ? `${Math.round(m.wcpm)}*` : Math.round(m.wcpm || 0);
    
    const tableBody = [
      [labelVelocidad, valorVelocidad, m.nivel_ace || nivelLabel(m.nivel_fluidez)],
      ['Precisión de Decodificación', `${Math.round(m.precision_pct || 0)}%`, '-'],
      ['Palabras Leídas Correctamente', m.conteo_palabras || '-', '-'],
      ['Texto Evaluado', l.texto_titulo || 'Sin título', '-']
    ];

    doc.autoTable({
      startY: 75,
      head: [['Métrica de Evaluación', 'Resultado Obtenido', 'Nivel de Logro ACE']],
      body: tableBody,
      theme: 'grid',
      headStyles: { fillColor: [30, 41, 59], fontStyle: 'bold' },
      styles: { fontSize: 10, cellPadding: 5 }
    });

    // Nota al pie si es proyectado
    if (m.wcpm_proyectado) {
      doc.setFontSize(8); doc.setFont('helvetica', 'italic');
      doc.text('* Velocidad estimada basada en un texto breve.', 15, doc.lastAutoTable.finalY + 5);
    }

    // Diagnóstico con manejo de páginas
    let y = doc.lastAutoTable.finalY + 15;
    doc.setFontSize(14); doc.setFont('helvetica', 'bold');
    doc.text('Diagnóstico Pedagógico y Estrategia', 15, y);
    
    y += 8;
    doc.setFontSize(10); doc.setFont('helvetica', 'normal');
    doc.setTextColor(50, 50, 50);
    
    const feedback = l.feedback_ia || "No hay diagnóstico disponible para esta lectura.";
    const splitText = doc.splitTextToSize(feedback, W - 30);
    
    // Loop para manejar el texto largo y saltos de página
    for (let i = 0; i < splitText.length; i++) {
      if (y > H - 20) {
        doc.addPage();
        y = 20; // Margen superior en nueva página
      }
      doc.text(splitText[i], 15, y);
      y += 6; // Interlineado
    }
    
    // Pie de página (en todas las páginas)
    const pageCount = doc.internal.getNumberOfPages();
    for (let i = 1; i <= pageCount; i++) {
      doc.setPage(i);
      doc.setFontSize(8); doc.setTextColor(150);
      doc.text(`Página ${i} de ${pageCount} — Generado por FluidezIA`, W/2, 285, {align: 'center'});
    }

    doc.save(`Informe_${l.estudiante.replace(/\s/g, '_')}.pdf`);
    showToast('✅ Informe generado correctamente', 'success');
  } catch (err) {
    console.error("Error PDF:", err);
    showToast('Error al generar el PDF detallado', 'error');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  console.log("FluidezIA: Iniciando aplicación...");
  init().catch(err => {
    console.error("Error crítico en inicio:", err);
    setStatus(false);
  });
});

// ── Textos ────────────────────────────────────────────────────────
async function loadTextos() {
  try {
    textos = await api.getTextos();
    renderTextos();
    populateTextSelect();
  } catch (e) { showToast('Error cargando textos', 'error'); }
}

function filtrarTextos() {
  renderTextos();
}

function renderTextos() {
  const el = document.getElementById('lista-textos');
  const filtroNivel = document.getElementById('filtro-nivel-textos')?.value;
  let filtrados = textos;
  if (filtroNivel) filtrados = filtrados.filter(t => t.nivel === filtroNivel);

  if (!filtrados.length) {
    el.innerHTML = '<div class="empty-state"><div class="empty-icon">📄</div><p>No hay textos para mostrar.</p></div>';
    return;
  }
  el.innerHTML = filtrados.map(t => `
    <div class="card text-card">
      <div class="card-badge">${t.nivel}</div>
      <h3 class="card-title">${t.titulo}</h3>
      <p class="card-excerpt">${t.contenido.substring(0, 100)}${t.contenido.length > 100 ? '…' : ''}</p>
      <div class="card-footer">
        <span class="chip">${t.palabras_totales} palabras</span>
        <button class="btn btn-sm btn-ghost" onclick="usarTextoEnSesion('${t.id}')">Usar en sesión →</button>
      </div>
    </div>
  `).join('');
}

async function crearTexto(e) {
  e.preventDefault();
  const data = {
    titulo: document.getElementById('txt-titulo').value.trim(),
    contenido: document.getElementById('txt-contenido').value.trim(),
    nivel: document.getElementById('txt-nivel').value,
  };
  try {
    const t = await api.crearTexto(data);
    textos.unshift(t);
    renderTextos();
    populateTextSelect();
    closeModal('modal-nuevo-texto');
    e.target.reset();
    showToast('Texto creado ✓', 'success');
  } catch { showToast('Error al crear texto', 'error'); }
}

// ── Estudiantes ───────────────────────────────────────────────────
async function loadEstudiantes() {
  try {
    estudiantes = await api.getEstudiantes();
    renderEstudiantes();
    populateStudentSelects();
    populateCursoSelects();
  } catch (e) { showToast('Error cargando estudiantes', 'error'); }
}

function renderEstudiantes() {
  const tbody = document.getElementById('lista-estudiantes');
  const filtroCurso = document.getElementById('filtro-curso-estudiantes')?.value;
  let filtrados = estudiantes;
  if (filtroCurso) filtrados = filtrados.filter(e => e.curso === filtroCurso);

  if (!filtrados.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty-cell">Sin estudiantes para mostrar</td></tr>';
    return;
  }
  tbody.innerHTML = filtrados.map(est => `
    <tr>
      <td>${est.nombre}</td>
      <td>${est.apellido}</td>
      <td><span class="chip">${est.curso}</span></td>
      <td>—</td>
      <td>—</td>
      <td>
        <button class="btn btn-sm" onclick="verHistorial('${est.id}', '${est.nombre} ${est.apellido}')">Ver historial</button>
        <button class="btn btn-sm btn-primary" onclick="iniciarSesionDirecta('${est.id}')">Evaluar</button>
      </td>
    </tr>
  `).join('');
}

async function crearEstudiante(e) {
  e.preventDefault();
  const data = {
    nombre: document.getElementById('est-nombre').value.trim(),
    apellido: document.getElementById('est-apellido').value.trim(),
    curso: document.getElementById('est-curso').value,
  };
  try {
    const est = await api.crearEstudiante(data);
    estudiantes.push(est);
    renderEstudiantes();
    populateStudentSelects();
    populateCursoSelects();
    const sel = document.getElementById('sel-estudiante');
    if(sel) sel.value = est.id;
    closeModal('modal-nuevo-estudiante');
    e.target.reset();
    showToast('Estudiante registrado ✓', 'success');
  } catch { showToast('Error al registrar', 'error'); }
}

// ── Sesión ────────────────────────────────────────────────────────
function populateStudentSelects() {
  const opts = '<option value="">— Selecciona —</option>' +
    estudiantes.map(e => `<option value="${e.id}">${e.nombre} ${e.apellido} (${e.curso})</option>`).join('');
  const selEst = document.getElementById('sel-estudiante');
  if (selEst) selEst.innerHTML = opts;
  const filtro = document.getElementById('filtro-estudiante-resultados');
  if (filtro) filtro.innerHTML = '<option value="">Todos</option>' +
    estudiantes.map(e => `<option value="${e.id}">${e.nombre} ${e.apellido}</option>`).join('');
}

function populateCursoSelects() {
  const cursos = [...new Set(estudiantes.map(e => e.curso))].sort();
  const cursoOpts = '<option value="">— Selecciona un curso —</option>' +
    cursos.map(c => `<option value="${c}">${c}</option>`).join('');

  // Selector en "Evaluar Fluidez"
  const selCurso = document.getElementById('sel-curso-masivo');
  if (selCurso) selCurso.innerHTML = cursoOpts;

  // Selector de filtro en "Estudiantes"
  const filtroEst = document.getElementById('filtro-curso-estudiantes');
  if (filtroEst) filtroEst.innerHTML = '<option value="">Todos los cursos</option>' +
    cursos.map(c => `<option value="${c}">${c}</option>`).join('');

  // Selector de filtro en "Resultados"
  const filtroRes = document.getElementById('filtro-curso-resultados');
  if (filtroRes) filtroRes.innerHTML = '<option value="">Todos los cursos</option>' +
    cursos.map(c => `<option value="${c}">${c}</option>`).join('');
}

function populateTextSelect() {
  document.getElementById('sel-texto').innerHTML =
    '<option value="">— Selecciona un texto —</option>' +
    textos.map(t => `<option value="${t.id}">${t.titulo} (${t.palabras_totales} pal.)</option>`).join('');
}

document.addEventListener('change', function(e) {
  if (e.target.id === 'sel-texto') {
    const t = textos.find(x => x.id === e.target.value);
    const prev = document.getElementById('texto-preview-sesion');
    if (t) {
      document.getElementById('texto-preview-content').textContent = t.contenido;
      document.getElementById('texto-preview-meta').textContent = `${t.palabras_totales} palabras · ${t.nivel}`;
      prev.style.display = 'block';
    } else { prev.style.display = 'none'; }
  }
  if (e.target.id === 'txt-contenido') {
    const words = e.target.value.trim().split(/\s+/).filter(Boolean).length;
    document.getElementById('word-count').textContent = `${words} palabras`;
  }
});

// ── Resultados ────────────────────────────────────────────────────
let resultadosList = [];

async function loadResultados() {
  try {
    resultadosList = await api.getLecturas();
    renderResultados();
  } catch (e) { showToast('Error cargando resultados', 'error'); }
}

function filtrarResultados() {
  renderResultados();
}

function renderResultados() {
  const container = document.getElementById('lista-resultados');
  if (!container) return;
  
  const filtroEst = document.getElementById('filtro-estudiante-resultados').value;
  const filtroCurso = document.getElementById('filtro-curso-resultados').value;
  const filtroEstado = document.getElementById('filtro-estado-resultados').value;
  
  let filtrados = resultadosList;
  if (filtroEst) filtrados = filtrados.filter(r => r.estudiante === document.getElementById('filtro-estudiante-resultados').options[document.getElementById('filtro-estudiante-resultados').selectedIndex].text);
  if (filtroCurso) filtrados = filtrados.filter(r => r.curso === filtroCurso);
  if (filtroEstado) filtrados = filtrados.filter(r => r.estado === filtroEstado);

  if (!filtrados.length) {
    container.innerHTML = '<div class="empty-state"><div class="empty-icon">📊</div><p>No hay evaluaciones todavía.</p></div>';
    return;
  }

  container.innerHTML = `<table class="data-table"><thead><tr><th>Fecha</th><th>Estudiante</th><th>Curso</th><th>Texto</th><th>Estado</th><th>PPM</th><th>Precisión</th><th>Logro ACE</th><th style="text-align:right">Acciones</th></tr></thead><tbody>
    ${filtrados.map(r => `<tr>
      <td>${new Date(r.fecha).toLocaleDateString('es-CL')}</td>
      <td><strong>${r.estudiante}</strong></td>
      <td><span class="chip">${r.curso}</span></td>
      <td>${r.texto_titulo}</td>
      <td><span class="chip ${r.estado === 'completado' ? 'success' : (r.estado==='error'?'error':'')}">${r.estado.toUpperCase()}</span></td>
      <td>${r.metricas ? `<strong>${r.metricas.wcpm}${r.metricas.wcpm_proyectado ? '*' : ''}</strong>` : '—'}</td>
      <td>${r.metricas ? `${Math.round(r.metricas.precision_pct)}%` : '—'}</td>
      <td>${r.metricas ? `<span class="chip nivel-${r.metricas.nivel_fluidez || 'bajo'}">${r.metricas.nivel_ace || nivelLabel(r.metricas.nivel_fluidez)}</span>` : '—'}</td>
      <td style="text-align:right; display:flex; gap:8px; justify-content:flex-end;">
        <button class="btn btn-sm btn-ghost" onclick="verResultadoDetalle('${r.id}', '${r.estudiante}')" title="Ver informe">👁️</button>
        <button class="btn btn-sm btn-ghost" onclick="eliminarLectura('${r.id}')" title="Borrar registro" style="color:var(--error)">🗑️</button>
      </td>
    </tr>`).join('')}
  </tbody></table>`;
}

async function eliminarLectura(id) {
  if (!confirm('¿Seguro que quieres borrar este registro?')) return;
  try {
    await api.delete(`/api/lecturas/${id}`);
    resultadosList = resultadosList.filter(r => r.id !== id);
    renderResultados();
    showToast('Registro eliminado', 'success');
  } catch (e) {
    showToast('No se pudo eliminar', 'error');
  }
}

async function generarReporteCurso() {
  const curso = document.getElementById('filtro-curso-resultados').value;
  if (!curso) {
    showToast('Selecciona un curso primero', 'info');
    return;
  }
  
  const lecturasCurso = resultadosList.filter(r => r.curso === curso && r.estado === 'completado');
  if (!lecturasCurso.length) {
    showToast('No hay evaluaciones completadas para este curso', 'info');
    return;
  }

  // Cálculos de grupo
  const avgWCPM = lecturasCurso.reduce((acc, r) => acc + (r.metricas?.wcpm || 0), 0) / lecturasCurso.length;
  const avgPrec = lecturasCurso.reduce((acc, r) => acc + (r.metricas?.precision_pct || 0), 0) / lecturasCurso.length;
  
  // Abrir modal de reporte de curso (usaremos el mismo modal de resultados pero con otro contenido)
  document.getElementById('resultado-modal-title').innerHTML = `
    <div style="display:flex; align-items:center; gap:12px;">
      <div style="background:var(--secondary); color:white; width:40px; height:40px; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:20px;">📊</div>
      <div>
        <div style="font-size:18px; font-weight:900;">Reporte Consolidado: ${curso}</div>
        <div style="font-size:12px; color:var(--text2); font-weight:500;">ANÁLISIS DE RENDIMIENTO GRUPAL</div>
      </div>
    </div>
  `;

  document.getElementById('resultado-modal-body').innerHTML = `
    <div style="padding: 32px; background: #f8fafc;">
      <div class="cards-grid" style="grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 32px;">
        <div class="card" style="padding:24px; text-align:center;">
          <div style="font-size:40px; font-weight:900; color:var(--accent);">${Math.round(avgWCPM)}</div>
          <div style="font-size:11px; font-weight:900; color:var(--text2); text-transform:uppercase;">Promedio PPM</div>
        </div>
        <div class="card" style="padding:24px; text-align:center;">
          <div style="font-size:40px; font-weight:900; color:var(--secondary);">${Math.round(avgPrec)}%</div>
          <div style="font-size:11px; font-weight:900; color:var(--text2); text-transform:uppercase;">Promedio Precisión</div>
        </div>
        <div class="card" style="padding:24px; text-align:center;">
          <div style="font-size:40px; font-weight:900; color:var(--text);">${lecturasCurso.length}</div>
          <div style="font-size:11px; font-weight:900; color:var(--text2); text-transform:uppercase;">Alumnos Evaluados</div>
        </div>
      </div>

      <div class="card" style="padding:32px; background:white;">
        <h4 style="margin-top:0; margin-bottom:24px; display:flex; align-items:center; gap:10px;">
          <span>📈</span> Detalle por Estudiante
        </h4>
        <table class="data-table">
          <thead>
            <tr>
              <th>Estudiante</th>
              <th>Velocidad (PPM)</th>
              <th>Precisión</th>
              <th>Nivel ACE</th>
            </tr>
          </thead>
          <tbody>
            ${lecturasCurso.map(r => `
              <tr>
                <td><strong>${r.estudiante}</strong></td>
                <td>${Math.round(r.metricas.wcpm)}</td>
                <td>${Math.round(r.metricas.precision_pct)}%</td>
                <td><span class="chip nivel-${r.metricas.nivel_fluidez}">${nivelLabel(r.metricas.nivel_fluidez)}</span></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
      
      <div style="margin-top:24px; text-align:right;">
        <button class="btn btn-primary" onclick="generarReportePDF()">⬇️ Descargar Reporte Completo (PDF)</button>
      </div>
    </div>
  `;
  openModal('modal-resultado');
}

async function verResultadoDetalle(id, nombreEstudiante) {
  try {
    const res = await api.getResultado(id);
    const m = res.metricas || { wcpm: 0, precision_pct: 0, nivel_fluidez: 'bajo' };
    const l = res.lectura;
    const errores = res.errores || [];
    
    document.getElementById('resultado-modal-title').innerHTML = `
      <div style="display:flex; align-items:center; gap:12px;">
        <div style="background:var(--accent); color:white; width:40px; height:40px; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:20px;">👤</div>
        <div>
          <div style="font-size:18px; font-weight:900;">${nombreEstudiante}</div>
          <div style="font-size:12px; color:var(--text2); font-weight:500;">INFORME DE DESEMPEÑO LECTOR</div>
        </div>
      </div>
    `;
    
    document.getElementById('resultado-modal-body').innerHTML = `
      <div style="padding: 0; display: grid; grid-template-columns: 1.6fr 1fr; gap: 0; background: #ffffff; min-height: 600px;">
        
        <!-- COLUMNA IZQUIERDA: LECTURA -->
        <div style="padding: 40px; background: white; overflow-y: auto; max-height: 75vh;">
          <div style="margin-bottom: 40px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
              <h4 style="font-size:11px; text-transform:uppercase; letter-spacing:1.5px; color:var(--text2); margin:0;">
                📖 Lectura de Texto: <span style="color:var(--accent); font-weight:900;">${l.texto_titulo || 'Sin título'}</span>
              </h4>
              <span style="font-size:11px; color:var(--text2); font-weight:600;">FECHA: ${new Date(l.created_at).toLocaleDateString()}</span>
            </div>
            
            <div style="padding: 40px; line-height: 2.4; font-size: 22px; font-family: 'Merriweather', serif; background: #fffdfa; border: 1px solid #f8fafc; box-shadow: 0 4px 20px rgba(0,0,0,0.03); border-radius: 20px; color: #1e293b;">
              ${renderErrorMap(res)}
            </div>
          </div>

          <h4 style="font-size:11px; text-transform:uppercase; letter-spacing:1.5px; color:var(--text2); margin-bottom:20px; display:flex; align-items:center; gap:8px;">
            <span>🔍</span> Análisis de Errores Identificados
          </h4>
          <div style="display:grid; grid-template-columns: 1fr 1fr; gap:16px;">
            ${errores.length ? errores.map(e => `
              <div style="padding:16px; background:#fff1f2; border-radius:12px; border:1px solid #ffe4e6; display:flex; justify-content:space-between; align-items:center; box-shadow: 0 2px 5px rgba(225,29,72,0.05);">
                <div>
                  <div style="font-size:9px; color:#e11d48; font-weight:900; text-transform:uppercase;">${e.tipo}</div>
                  <div style="font-size:15px; color:#1e293b; font-weight:700;">${e.palabra_esperada || '-'}</div>
                </div>
                <div style="font-size:18px; color:#fda4af;">→</div>
                <div style="text-align:right;">
                  <div style="font-size:9px; color:#e11d48; font-weight:500;">LEÍDO</div>
                  <div style="font-size:15px; color:#e11d48; font-weight:900;">${e.palabra_leida || '(omisión)'}</div>
                </div>
              </div>
            `).join('') : '<div style="grid-column: span 2; padding:30px; text-align:center; color:var(--text2); border:2px dashed var(--border); border-radius:15px;">No se detectaron errores. ¡Lectura impecable!</div>'}
          </div>
        </div>

        <!-- COLUMNA DERECHA: DASHBOARD MÉTRICAS -->
        <div style="padding: 40px; background: #f8fafc; border-left: 1px solid var(--border); display: flex; flex-direction: column; gap: 30px; overflow-y: auto; max-height: 75vh;">
          
          <!-- KPI DASHBOARD -->
          <div style="display:grid; grid-template-columns:1fr; gap:15px;">
            <div class="card" style="padding:24px; background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); color:white; border-radius:24px; box-shadow: 0 15px 30px -10px rgba(15,23,42,0.3);">
              <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:15px;">
                <span style="font-size:10px; font-weight:800; letter-spacing:1px; opacity:0.7;">${m.es_texto_breve ? 'VELOCIDAD PROYECTADA' : 'VELOCIDAD LECTORA'}</span>
                <span class="chip" style="background:rgba(255,255,255,0.15); border:1px solid rgba(255,255,255,0.2); color:white; font-size:9px;">${m.nivel_ace || nivelLabel(m.nivel_fluidez)}</span>
              </div>
              <div style="display:flex; align-items:baseline; gap:10px;">
                <span style="font-size:48px; font-weight:900;">${Math.round(m.wcpm || 0)}${m.wcpm_proyectado ? '*' : ''}</span>
                <span style="font-size:12px; font-weight:600; opacity:0.6;">PPM</span>
              </div>
              ${m.wcpm_proyectado ? '<div style="font-size:10px; opacity:0.6; margin-top:4px;">* Basado en texto breve</div>' : ''}
            </div>

            <div class="card" style="padding:24px; background: white; border-radius:24px; border:1px solid var(--border); display:flex; justify-content:space-between; align-items:center;">
              <div>
                <div style="font-size:10px; font-weight:800; color:var(--text2); letter-spacing:1px; margin-bottom:5px;">PRECISIÓN</div>
                <div style="font-size:28px; font-weight:900; color:var(--accent);">${Math.round(m.precision_pct || 0)}%</div>
                <div style="font-size:10px; color:var(--text2); margin-top:2px;">${m.conteo_palabras || '-'} palabras</div>
              </div>
              <div style="width:50px; height:50px; border-radius:50%; background:#f0f9ff; display:flex; align-items:center; justify-content:center; font-size:24px;">🎯</div>
            </div>
          </div>

          <!-- IA INSIGHT CARD -->
          <div class="card" style="padding:30px; background: white; border-radius:24px; border:1px solid var(--border); box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); flex:1; display:flex; flex-direction:column;">
            <div style="display:flex; align-items:center; gap:10px; margin-bottom:20px;">
              <div style="background:var(--accent); color:white; width:30px; height:30px; border-radius:8px; display:flex; align-items:center; justify-content:center;">🧠</div>
              <h4 style="margin:0; font-size:13px; font-weight:900; letter-spacing:0.5px; color:var(--text);">ESTRATEGIA PEDAGÓGICA IA</h4>
            </div>
            <div style="background: #f8fafc; padding: 20px; border-radius:16px; border: 1px solid #f1f5f9; color: #334155; line-height: 1.7; font-size: 13.5px; font-style: italic; white-space: pre-line; flex:1;">
              ${l.feedback_ia || 'Haz clic en Re-analizar para obtener el diagnóstico profundo.'}
            </div>
            <div style="margin-top:24px; display:grid; grid-template-columns:1fr 1fr; gap:12px;">
               <button class="btn btn-ghost" style="height:44px; font-size:11px;" onclick="reanalizarConIA('${l.id}')">🔄 Re-analizar</button>
               <button class="btn btn-primary" style="height:44px; font-size:11px;" onclick="generarFichaIndividualPDF('${l.id}')">⬇️ Ficha PDF</button>
            </div>
          </div>
        </div>

      </div>
    `;
    openModal('modal-resultado');
  } catch (e) {
    console.error(e);
    showToast('Error al cargar detalle', 'error');
  }
}

async function reanalizarConIA(id) {
  try {
    showToast('Iniciando re-análisis pedagógico...', 'info');
    await api.reanalizarLectura(id);
    closeModal('modal-resultado');
    showToast('Procesando con nuevo motor. Refresca en unos segundos.', 'success');
    setTimeout(() => loadResultados(), 5000);
  } catch (e) {
    showToast('Error al re-analizar', 'error');
  }
}

function renderErrorMap(res) {
  const texto = res.lectura.transcripcion_raw || "";
  const palabras = texto.split(' ');
  const errores = res.errores || [];
  
  return palabras.map(p => {
    const norm = p.toLowerCase().replace(/[^\w\s]/g, "");
    // Buscar si esta palabra (limpia) coincide con alguna esperada que tuvo error
    const tieneError = errores.find(e => e.palabra_esperada && e.palabra_esperada.toLowerCase().replace(/[^\w\s]/g, "") === norm);
    
    if (tieneError) {
      const color = tieneError.tipo === 'sustitucion' ? '#f59e0b' : (tieneError.tipo === 'insercion' ? '#3b82f6' : '#ef4444');
      return `<span style="background: ${color}15; border-bottom: 2px solid ${color}; padding: 2px 4px; border-radius: 4px; color: ${color}; font-weight: 700; cursor: help;" title="${tieneError.tipo.toUpperCase()}: esperada '${tieneError.palabra_esperada || '-'}'">${p}</span>`;
    }
    return `<span>${p}</span>`;
  }).join(' ');
}

function filtrarResultados() {
  renderResultados();
}

// ── Lógica de Sesión Masiva ───────────────────────────────────────
function renderPanelCurso() {
  const textoId = document.getElementById('sel-texto').value;
  const curso = document.getElementById('sel-curso-masivo').value;
  const panel = document.getElementById('panel-curso-container');
  const tbody = document.getElementById('tbody-curso-masivo');

  if (!textoId || !curso) {
    panel.classList.add('hidden');
    return;
  }

  panel.classList.remove('hidden');
  const estudiantesCurso = estudiantes.filter(e => e.curso === curso);

  if (!estudiantesCurso.length) {
    tbody.innerHTML = '<tr><td colspan="2" class="empty-cell">No hay estudiantes registrados en este curso.</td></tr>';
    return;
  }

  tbody.innerHTML = estudiantesCurso.map(est => `
    <tr>
      <td><strong>${est.nombre} ${est.apellido}</strong></td>
      <td style="display: flex; gap: 8px;">
        <button class="btn btn-sm btn-primary" onclick="iniciarSesionEstudiante('${est.id}', '${textoId}')">🎙️ Evaluar Ahora</button>
        <button class="btn btn-sm btn-ghost" onclick="copiarEnlaceEstudiante('${est.id}', '${textoId}')">🔗 Copiar Enlace</button>
      </td>
    </tr>
  `).join('');
}

async function iniciarSesionEstudiante(estId, textoId) {
  try {
    const est = estudiantes.find(e => e.id === estId);
    const lectura = await api.crearLectura({ estudiante_id: estId, texto_id: textoId });
    const url = `${location.origin}/estudiante.html?lectura_id=${lectura.id}&texto_id=${textoId}`;

    // Mostrar modal QR
    document.getElementById('qr-modal-titulo').textContent = `📖 ${est ? est.nombre + ' ' + est.apellido : 'Estudiante'}`;
    document.getElementById('qr-modal-url').textContent = url;
    const qrContainer = document.getElementById('qr-modal-container');
    qrContainer.innerHTML = '';
    new QRCode(qrContainer, {
      text: url,
      width: 200,
      height: 200,
      colorDark: '#0F172A',
      colorLight: '#ffffff',
      correctLevel: QRCode.CorrectLevel.H
    });
    openModal('modal-qr-sesion');
    showToast(`Sesión lista para ${est ? est.nombre : 'el estudiante'} ✓`, 'success');
  } catch {
    showToast('Error al crear la sesión', 'error');
  }
}

function copiarUrlQR() {
  const url = document.getElementById('qr-modal-url').textContent;
  navigator.clipboard.writeText(url);
  showToast('Enlace copiado al portapapeles ✓', 'success');
}

async function copiarEnlaceEstudiante(estId, textoId) {
  try {
    const lectura = await api.crearLectura({ estudiante_id: estId, texto_id: textoId });
    const url = `${location.origin}/estudiante.html?lectura_id=${lectura.id}&texto_id=${textoId}`;
    await navigator.clipboard.writeText(url);
    showToast('Enlace copiado al portapapeles ✓', 'success');
  } catch {
    showToast('Error al crear el enlace', 'error');
  }
}

// ── UI Helpers ────────────────────────────────────────────────────
function iniciarSesionDirecta(estId) {
  const est = estudiantes.find(e => e.id === estId);
  if (est) {
    document.getElementById('sel-curso-masivo').value = est.curso;
    renderPanelCurso();
  }
  showSection('sesion');
}

function usarTextoEnSesion(textoId) {
  document.getElementById('sel-texto').value = textoId;
  renderPanelCurso();
  showSection('sesion');
}

// ── Historial ─────────────────────────────────────────────────────
let historialChart = null;

async function verHistorial(estId, nombre) {
  try {
    const hist = await api.getHistorial(estId);
    // Ordenar por fecha ascendente para el gráfico
    const histSorted = [...hist].sort((a, b) => new Date(a.fecha) - new Date(b.fecha));
    
    document.getElementById('historial-modal-title').textContent = `Evolución: ${nombre}`;
    const tableContainer = document.getElementById('historial-tabla-container');
    
    if (!hist.length) {
      tableContainer.innerHTML = '<p class="empty-cell">Sin lecturas completadas aún.</p>';
      if (historialChart) historialChart.destroy();
    } else {
      tableContainer.innerHTML = `<table class="data-table"><thead><tr><th>Fecha</th><th>Texto</th><th>PPM</th><th>Precisión</th><th>Nivel</th></tr></thead><tbody>
        ${hist.map(h => `<tr>
          <td>${new Date(h.fecha).toLocaleDateString('es-CL')}</td>
          <td>${h.texto_titulo}</td>
          <td><strong>${h.wcpm}</strong></td>
          <td>${h.precision_pct}%</td>
          <td><span class="chip nivel-${h.nivel_fluidez}">${nivelLabel(h.nivel_fluidez)}</span></td>
        </tr>`).join('')}
      </tbody></table>`;

      // Renderizar Gráfico
      const ctx = document.getElementById('chart-evolucion').getContext('2d');
      if (historialChart) historialChart.destroy();
      
      historialChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: histSorted.map(h => new Date(h.fecha).toLocaleDateString('es-CL', {day:'numeric', month:'short'})),
          datasets: [{
            label: 'PPM (Palabras por Minuto)',
            data: histSorted.map(h => h.wcpm),
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            borderWidth: 3,
            tension: 0.3,
            fill: true,
            pointRadius: 5,
            pointBackgroundColor: '#3b82f6'
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' } },
            x: { grid: { display: false } }
          }
        }
      });
    }
    openModal('modal-historial');
  } catch (e) { 
    console.error(e);
    showToast('Error al cargar historial', 'error'); 
  }
}

function nivelLabel(n) {
  return { bajo: 'Logro 1 (Bajo)', en_desarrollo: 'Logro 2 (En desarrollo)', logrado: 'Logro 3 (Logrado)', avanzado: 'Logro 4 (Avanzado)' }[n] || n;
}

function showSection(name) {
  document.querySelectorAll('.section').forEach(s => s.classList.add('hidden'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById(`section-${name}`).classList.remove('hidden');
  document.getElementById(`nav-${name}`)?.classList.add('active');
  document.getElementById('topbarTitle').textContent =
    { textos: 'Biblioteca Textos', estudiantes: 'Estudiantes', sesion: 'Evaluar Fluidez', resultados: 'Resultados' }[name];
  if (name === 'resultados') loadResultados();
}

function openModal(id) { document.getElementById(id).classList.remove('hidden'); }
function closeModal(id) { document.getElementById(id).classList.add('hidden'); }

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
}

function showToast(msg, type = 'info') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = `toast show ${type}`;
  setTimeout(() => t.className = 'toast', 3000);
}

document.querySelectorAll('.modal-overlay').forEach(m => {
  m.addEventListener('click', e => { if (e.target === m) m.classList.add('hidden'); });
});

// ── Reporte PDF ──────────────────────────────────────────────────
function abrirModalReporte() {
  // Poblar selects con datos reales
  const cursos = [...new Set(estudiantes.map(e => e.curso))].sort();
  const selectCurso = document.getElementById('reporte-curso');
  selectCurso.innerHTML = '<option value="">Todos los cursos</option>' +
    cursos.map(c => `<option value="${c}">${c}</option>`).join('');

  const selectTexto = document.getElementById('reporte-texto');
  selectTexto.innerHTML = '<option value="">Todos los textos</option>' +
    textos.map(t => `<option value="${t.id}">${t.titulo}</option>`).join('');

  openModal('modal-reporte');
}

async function generarReportePDF() {
  const cursoFiltro = document.getElementById('reporte-curso').value;
  const textoFiltro = document.getElementById('reporte-texto').value;
  const colegio = document.getElementById('reporte-colegio').value || 'Establecimiento Educacional';

  showToast('Generando reporte...', 'info');

  // Traer resultados si no están cargados
  if (!resultadosList.length) {
    try { resultadosList = await api.getLecturas(); } catch { showToast('Error al cargar datos', 'error'); return; }
  }

  let datos = resultadosList.filter(r => r.estado === 'completado' && r.metricas);
  if (cursoFiltro) datos = datos.filter(r => r.curso === cursoFiltro);
  if (textoFiltro) datos = datos.filter(r => r.texto_id === textoFiltro);

  if (!datos.length) { showToast('No hay evaluaciones completadas con esos filtros', 'error'); return; }

  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
  const W = doc.internal.pageSize.getWidth();
  const fecha = new Date().toLocaleDateString('es-CL', { year: 'numeric', month: 'long', day: 'numeric' });
  const textoNombre = textoFiltro ? (textos.find(t => t.id === textoFiltro)?.titulo || '') : 'Todos los textos';

  // ── Encabezado ──
  doc.setFillColor(15, 23, 42); // navy
  doc.rect(0, 0, W, 40, 'F');
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(18); doc.setFont('helvetica', 'bold');
  doc.text('EVALUACIÓN DE FLUIDEZ LECTORA', W / 2, 16, { align: 'center' });
  doc.setFontSize(11); doc.setFont('helvetica', 'normal');
  doc.text(colegio, W / 2, 25, { align: 'center' });
  doc.setFontSize(10);
  doc.text(`Fecha: ${fecha}  |  Curso: ${cursoFiltro || 'Todos'}  |  Texto: ${textoNombre}`, W / 2, 33, { align: 'center' });

  // ── Estadísticas Resumen ──
  const ppms = datos.map(r => r.metricas.wcpm);
  const ppmPromedio = (ppms.reduce((a, b) => a + b, 0) / ppms.length).toFixed(1);
  const precPromedio = (datos.reduce((a, r) => a + r.metricas.precision_pct, 0) / datos.length).toFixed(1);
  const logros = datos.map(r => r.metricas.nivel_fluidez);
  const contar = (l) => logros.filter(x => x === l).length;

  doc.setTextColor(15, 23, 42);
  doc.setFontSize(12); doc.setFont('helvetica', 'bold');
  doc.text('Resumen del Curso', 14, 52);

  doc.autoTable({
    startY: 56,
    head: [['Estudiantes Evaluados', 'PPM Promedio', 'Precisión Promedio', 'Logro 1', 'Logro 2', 'Logro 3', 'Logro 4']],
    body: [[datos.length, ppmPromedio, `${precPromedio}%`, contar('bajo'), contar('en_desarrollo'), contar('logrado'), contar('avanzado')]],
    styles: { fontSize: 10, halign: 'center' },
    headStyles: { fillColor: [15, 23, 42], textColor: 255, fontStyle: 'bold' },
    alternateRowStyles: { fillColor: [248, 250, 252] },
    margin: { left: 14, right: 14 },
  });

  // ── Tabla Individual ──
  const startY2 = doc.lastAutoTable.finalY + 12;
  doc.setFontSize(12); doc.setFont('helvetica', 'bold');
  doc.text('Detalle por Estudiante', 14, startY2);

  const logroMap = { bajo: 'Logro 1 — Bajo', en_desarrollo: 'Logro 2 — En Desarrollo', logrado: 'Logro 3 — Logrado', avanzado: 'Logro 4 — Avanzado' };
  const rows = datos.map(r => [
    r.estudiante,
    r.curso,
    r.texto_titulo?.substring(0, 30) || '—',
    new Date(r.fecha).toLocaleDateString('es-CL'),
    Math.round(r.metricas.wcpm),
    `${Math.round(r.metricas.precision_pct)}%`,
    logroMap[r.metricas.nivel_fluidez] || '—',
  ]);

  doc.autoTable({
    startY: startY2 + 4,
    head: [['Estudiante', 'Curso', 'Texto', 'Fecha', 'PPM', 'Precisión', 'Logro ACE']],
    body: rows,
    styles: { fontSize: 9 },
    headStyles: { fillColor: [37, 99, 235], textColor: 255, fontStyle: 'bold' },
    columnStyles: {
      0: { cellWidth: 45 }, 1: { cellWidth: 14, halign: 'center' },
      2: { cellWidth: 40 }, 3: { cellWidth: 22, halign: 'center' },
      4: { cellWidth: 14, halign: 'center' }, 5: { cellWidth: 18, halign: 'center' },
      6: { cellWidth: 32 }
    },
    alternateRowStyles: { fillColor: [248, 250, 252] },
    margin: { left: 14, right: 14 },
  });

  // ── Pie de página ──
  const pageCount = doc.internal.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.setFontSize(8); doc.setTextColor(150, 150, 150);
    doc.text(`FluidezIA — Evaluación de Fluidez Lectora  |  Página ${i} de ${pageCount}`, W / 2, 290, { align: 'center' });
  }

  const filename = `reporte_fluidez_${cursoFiltro || 'todos'}_${new Date().toISOString().slice(0,10)}.pdf`;
  doc.save(filename);
  closeModal('modal-reporte');
  showToast('✅ Reporte descargado correctamente', 'success');
}

// init(); // Removido para usar DOMContentLoaded
