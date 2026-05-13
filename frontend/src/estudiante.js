/* ── Estudiante JS ── */
const params = new URLSearchParams(location.search);
const LECTURA_ID = params.get('lectura_id');
const TEXTO_ID = params.get('texto_id');

let mediaRecorder, audioChunks = [], timerInterval, segundos = 0;
let textoData = null;

async function init() {
  if (!LECTURA_ID || !TEXTO_ID) {
    document.getElementById('wait-text').innerHTML = '<strong>Aún no hay una lectura activa.</strong><br><br>Pídele a tu profesor que te comparta el código QR o el enlace directo para comenzar.';
    document.querySelector('.loading-dots').style.display = 'none';
    return;
  }
  try {
    textoData = await api.get(`/api/textos/${TEXTO_ID}`);
    mostrarPantallaLectura();
  } catch {
    document.getElementById('wait-text').textContent = 'Error al cargar el texto. Contacta a tu profe.';
    document.querySelector('.loading-dots').style.display = 'none';
  }
}

function mostrarPantallaLectura() {
  document.getElementById('screen-espera').classList.add('hidden');
  document.getElementById('screen-lectura').classList.remove('hidden');
  document.getElementById('lectura-titulo').textContent = textoData.titulo;
  document.getElementById('lectura-palabras').textContent = `${textoData.palabras_totales} palabras`;

  const display = document.getElementById('texto-display');
  display.innerHTML = textoData.contenido
    .split(' ')
    .map((w, i) => `<span class="palabra" id="p-${i}">${w}</span>`)
    .join(' ');
}

async function iniciarGrabacion() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
    mediaRecorder.start(250);

    document.getElementById('rec-state-idle').classList.add('hidden');
    document.getElementById('rec-state-recording').classList.remove('hidden');

    segundos = 0;
    timerInterval = setInterval(() => {
      segundos++;
      const m = Math.floor(segundos / 60);
      const s = String(segundos % 60).padStart(2, '0');
      document.getElementById('rec-timer').textContent = `${m}:${s}`;
    }, 1000);
  } catch {
    alert('No se pudo acceder al micrófono. Verifica los permisos.');
  }
}

async function detenerGrabacion() {
  clearInterval(timerInterval);
  mediaRecorder.stop();
  mediaRecorder.stream.getTracks().forEach(t => t.stop());

  document.getElementById('rec-state-recording').classList.add('hidden');
  document.getElementById('rec-state-procesando').classList.remove('hidden');

  mediaRecorder.onstop = async () => {
    const blob = new Blob(audioChunks, { type: 'audio/webm' });
    try {
      await api.subirAudio(LECTURA_ID, blob);
      const resultado = await pollResultado(LECTURA_ID, (estado) => {
        console.log('Estado:', estado);
      });
      mostrarResultado(resultado);
    } catch (e) {
      document.getElementById('rec-state-procesando').innerHTML =
        `<p style="color:#ff6b6b">❌ Error: ${e.message}</p><button class="btn btn-ghost" onclick="location.reload()">Reintentar</button>`;
    }
  };
}

function mostrarResultado(resultado) {
  document.getElementById('screen-lectura').classList.add('hidden');
  document.getElementById('screen-resultado').classList.remove('hidden');

  if (typeof confetti === 'function') {
    confetti({
      particleCount: 150,
      spread: 70,
      origin: { y: 0.6 },
      colors: ['#2563eb', '#10b981', '#f59e0b', '#ef4444']
    });
  }
}

function volverADocente() { window.close(); }
function nuevaLectura() { location.href = location.href.split('?')[0]; }

init();
