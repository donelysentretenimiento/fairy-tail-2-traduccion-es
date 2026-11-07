/* Interfaz del instalador. NO realiza ninguna operación crítica: solo muestra el estado y envía órdenes al núcleo nativo (C#).
   Protocolo JS -> C#: {cmd: 'init'|'browse'|'analyze'|'install'|'cancel'|'restore'|'openFolder'|'launchGame'|'exit', ...}
   C# -> JS: {type: 'init'|'browse'|'analysis'|'progress'|'done'|'error', ...} */
(() => {
  'use strict';
  const $ = (s, r = document) => r.querySelector(s);
  const esc = (t) => String(t).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  // ---------- puente ----------
  const nativo = window.chrome && window.chrome.webview;
  const enviar = (msg) => { if (nativo) nativo.postMessage(JSON.stringify(msg)); else if (window.__mock) window.__mock.recibir(msg); };
  const escuchar = (fn) => { if (nativo) nativo.addEventListener('message', (e) => fn(typeof e.data === 'string' ? JSON.parse(e.data) : e.data)); else window.__alRecibir = fn; };

  // ---------- estado ----------
  const S = { pantalla: 'bienvenida', modo: 'instalar', version: '', detectadas: [], hayRespaldos: false, ruta: '', analisis: null, progreso: null, fin: null, ocupado: false, conflictos: [] };
  const PASOS = {
    instalar: [['bienvenida', 'Bienvenida'], ['carpeta', 'Carpeta del juego'], ['comprobacion', 'Comprobación'], ['instalacion', 'Instalación'], ['final', 'Listo']],
    restaurar: [['bienvenida', 'Bienvenida'], ['restaurar', 'Restauración'], ['final', 'Listo']],
  };
  const ESTADOS = {
    NotFound: ['error', 'No se ha encontrado el juego en esta ruta.'],
    InvalidFolder: ['error', 'Esta carpeta no parece la de FAIRY TAIL 2.'],
    Original: ['ok', 'Juego original detectado. Es compatible con la traducción.'],
    KnownPartial: ['ok', 'Se ha reconocido una versión anterior de la traducción. Se actualizará con seguridad.'],
    TranslationInstalled: ['aviso', 'La traducción ya está instalada. Puedes reinstalarla o restaurar los originales.'],
    Mixed: ['aviso', 'La traducción está instalada parcialmente. Reinstalarla la completará.'],
    Unknown: ['error', 'Esta versión del juego no es compatible con la traducción. Para proteger tu juego, no se modificará nada.'],
  };
  const ICO = {
    ok: '<svg class="ico ok" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9.5"/><path d="m7.5 12.5 3 3 6-6.5"/></svg>',
    aviso: '<svg class="ico aviso" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3.5 2.8 20h18.4z"/><path d="M12 10v4.5M12 17.6v.1"/></svg>',
    error: '<svg class="ico error" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9.5"/><path d="m8.8 8.8 6.4 6.4M15.2 8.8l-6.4 6.4"/></svg>',
  };
  const nivel = (l) => (/err/i.test(l) ? 'error' : /warn|avis/i.test(l) ? 'aviso' : 'ok');

  // ---------- render ----------
  function rail() {
    const pasos = PASOS[S.modo]; const idx = pasos.findIndex((p) => p[0] === S.pantalla);
    $('#rail').innerHTML = pasos.map((p, i) => `<div class="nodo ${i === idx ? 'activo' : i < idx ? 'hecho' : ''}" ${i === idx ? 'aria-current="step"' : ''}><div class="punto">${i < idx ? '✓' : i + 1}</div><span>${p[1]}</span></div>`).join('');
  }
  function botones(lista) {
    $('#acciones').innerHTML = lista.map((b) => b === 'esp' ? '<div class="espacio"></div>'
      : `<button class="btn ${b.cls || ''}" id="${b.id}" ${b.off ? 'disabled' : ''}>${esc(b.t)}</button>`).join('');
    lista.forEach((b) => { if (b !== 'esp' && b.fn) { const el = $('#' + b.id); if (el) el.onclick = b.fn; } });
  }
  function vista(html, bots) {
    const v = $('#view'); v.innerHTML = `<div class="panel-in">${html}</div>`; v.scrollTop = 0; botones(bots); rail();
  }
  function ir(p) { S.pantalla = p; render(); }
  function render() {
    ({ bienvenida, carpeta, comprobacion, instalacion, restaurar, final })[S.pantalla]();
  }

  function bienvenida() {
    S.modo = 'instalar';
    const ic = (d) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
    vista(`<div class="hero"><h2>Bienvenido, mago</h2>
      <p class="lead">Instala la traducción española de FAIRY TAIL 2 y vive su historia, menús y diálogos en tu idioma.</p>
      <p class="compat"><span>Compatible con las versiones <b>1.2.0.0</b> y <b>1.3.0.0</b> del juego</span></p></div>
      <div class="teselas">
        <div class="tesela">${ic('<path d="M12 3 4.5 6v5.5c0 4.4 3.1 8.1 7.5 9.5 4.4-1.4 7.5-5.1 7.5-9.5V6z"/><path d="m8.8 12.2 2.4 2.4 4.2-4.6"/>')}<b>Copia de seguridad</b><span>Antes de cambiar nada se guardan tus archivos y se verifican.</span></div>
        <div class="tesela">${ic('<path d="M4 9V4.5M4 9h4.5M4 9a8.5 8.5 0 1 1-1 4.6"/>')}<b>Reversible</b><span>Vuelve al juego original cuando quieras desde este instalador.</span></div>
        <div class="tesela">${ic('<path d="M3 3l18 18"/><path d="M8.5 8.7A12 12 0 0 0 3 12.5M16.5 8.7A12 12 0 0 1 21 12.5M12 20h.01M6.3 15a8 8 0 0 1 3.4-2M14.3 13a8 8 0 0 1 3.4 2"/>')}<b>Sin conexión</b><span>No necesita Internet ni ningún cargador de mods.</span></div>
      </div>`,
      [{ id: 'bComenzar', t: 'Comenzar instalación', cls: 'principal', fn: () => ir('carpeta') },
        { id: 'bInstr', t: 'Instrucciones', fn: () => abrirGuia(true) }, 'esp',
        { id: 'bRest', t: 'Restaurar originales', cls: 'peligro', fn: () => { S.modo = 'restaurar'; ir('restaurar'); } }]);
    setTimeout(() => $('#bComenzar') && $('#bComenzar').focus(), 60);
  }

  function carpeta() {
    const sug = S.detectadas.length ? `<p class="muted">Instalaciones detectadas en este equipo:</p><div class="sugerencias">${S.detectadas.map((d) => `<button class="chip" data-ruta="${esc(d)}">${esc(d)}</button>`).join('')}</div>` : '<p class="muted">No se ha detectado el juego automáticamente. Selecciona su carpeta con «Examinar».</p>';
    vista(`<h2>Carpeta del juego</h2>
      <p>Elige la carpeta principal de FAIRY TAIL 2, la que contiene <code>FAIRY_TAIL_2.exe</code>. Puede estar en cualquier unidad.</p>
      <div class="campo"><input id="ruta" type="text" spellcheck="false" autocomplete="off" aria-label="Ruta de la carpeta del juego" placeholder="Por ejemplo: D:\\Juegos\\FAIRY TAIL 2" value="${esc(S.ruta)}">
      <button class="btn" id="bExaminar">Examinar…</button></div>${sug}
      <div id="valida" aria-live="polite"></div>`,
      [{ id: 'bAtras', t: 'Atrás', fn: () => ir('bienvenida') }, 'esp', { id: 'bCont', t: 'Comprobar y continuar', cls: 'principal', off: !S.ruta, fn: continuar }]);
    const inp = $('#ruta');
    inp.oninput = () => { S.ruta = inp.value.trim(); $('#bCont').disabled = !S.ruta; };
    inp.onkeydown = (e) => { if (e.key === 'Enter' && S.ruta) continuar(); };
    $('#bExaminar').onclick = () => enviar({ cmd: 'browse', actual: S.ruta });
    document.querySelectorAll('.chip').forEach((c) => (c.onclick = () => { S.ruta = c.dataset.ruta; inp.value = S.ruta; $('#bCont').disabled = false; continuar(); }));
    if (!S.ruta) inp.focus();
  }
  function continuar() { S.analisis = null; S.ocupado = true; ir('comprobacion'); enviar({ cmd: 'analyze', path: S.ruta }); }

  function comprobacion() {
    const a = S.analisis;
    if (!a) { vista(`<h2>Comprobando el juego</h2><p class="muted">Verificando archivos, permisos y espacio disponible…</p><div class="carril" role="progressbar" aria-label="Comprobando"><div class="relleno" style="width:46%"></div></div>`, [{ id: 'bAtras', t: 'Atrás', fn: () => ir('carpeta') }]); return; }
    const [niv, txt] = ESTADOS[a.state] || ['error', 'Estado desconocido.'];
    const puede = a.canInstall;
    const reinst = a.state === 'TranslationInstalled' || a.state === 'Mixed';
    const chk = a.checks || [];
    const GRUPOS = [
      ['Juego', ['exe', 'master-eng', 'recursos', 'juego-version', 'version', 'estructura', 'estado'], () => { const m = (chk.find((c) => c.id === 'recursos') || {}).message || ''; const n = (m.match(/(\d+) archivos/) || [])[1]; const v = ((chk.find((c) => c.id === 'juego-version') || {}).message || '').match(/: (\d+(?:\.\d+)+)/); return `${v ? 'Versión ' + v[1] : 'Versión compatible'}${n ? ' · ' + n + ' archivos' : ''}`; }, '<path d="M4 7a2 2 0 0 1 2-2h4l2 2h6a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z"/>'],
      ['Seguridad', ['respaldo', 'herramienta', 'proceso'], () => 'Se hará una copia de seguridad', '<path d="M12 3 4.5 6v5.5c0 4.4 3.1 8.1 7.5 9.5 4.4-1.4 7.5-5.1 7.5-9.5V6z"/><path d="m8.8 12.2 2.4 2.4 4.2-4.6"/>'],
      ['Espacio y permisos', ['solo-lectura', 'escritura', 'espacio'], () => { const m = (chk.find((c) => c.id === 'espacio') || {}).message || ''; const n = (m.match(/unos ([\d.,]+ ?\w+)/) || [])[1]; return `Todo en orden${n ? ' · unos ' + n : ''}`; }, '<path d="M4 6h16M4 12h16M4 18h10"/>'],
    ];
    const peor = (ids) => { const l = chk.filter((c) => ids.includes(c.id)); return l.find((c) => nivel(c.level) === 'error') || l.find((c) => nivel(c.level) === 'aviso') || null; };
    const tarjetas = GRUPOS.map(([tit, ids, okTxt, ico]) => { const p = peor(ids); const n = p ? nivel(p.level) : 'ok';
      return `<div class="tarj ${n}"><svg class="tarj-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${ico}</svg><b>${tit}</b><span>${esc(p ? p.message : okTxt())}</span></div>`; }).join('');
    const titular = puede ? (reinst ? 'La traducción ya está instalada' : 'Todo listo para instalar') : txt;
    vista(`<h2>Comprobación</h2>
      <div class="estado ${niv}">${ICO[niv]}<div><b>${esc(titular)}</b><span class="muted ruta-corta" title="${esc(S.ruta)}">${esc(S.ruta)}</span></div></div>
      <div class="tarjetas">${tarjetas}</div>
      <details class="detalles"><summary>Ver detalles técnicos</summary><ul class="lista">${chk.map((c) => `<li>${ICO[nivel(c.level)]}<span>${esc(c.message)}</span></li>`).join('')}</ul></details>`,
      [{ id: 'bAtras', t: 'Atrás', fn: () => ir('carpeta') }, 'esp',
        ...(a.hasBackup && a.state !== 'Unknown' ? [{ id: 'bRestH', t: 'Restaurar originales', cls: 'peligro', fn: () => { S.modo = 'restaurar'; ir('restaurar'); } }] : []),
        { id: 'bInst', t: reinst ? 'Reinstalar traducción' : 'Instalar traducción', cls: 'principal', off: !puede, fn: instalar }]);
  }
  function instalar() { S.progreso = null; S.fin = null; ir('instalacion'); enviar({ cmd: 'install', path: S.ruta }); }

  function barra(p, fase, titulo, cancelable) {
    const pct = p ? Math.max(0, Math.min(100, p.percent)) : 0;
    const C = 2 * Math.PI * 82;
    vista(`<h2>${titulo}</h2>
      <div class="prog">
        <div class="anillo"><svg viewBox="0 0 188 188"><defs><linearGradient id="gradAnillo" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#E8365A"/><stop offset="1" stop-color="#D8B76A"/></linearGradient></defs>
          <circle class="pista" cx="94" cy="94" r="82"/><circle class="arco" id="arco" cx="94" cy="94" r="82" stroke-dasharray="${C}" stroke-dashoffset="${C * (1 - pct / 100)}"/></svg>
          <div class="pct" id="pctTxt">${Math.floor(pct)}<small>%</small></div></div>
        <div>
          <div class="fase" id="faseTxt">${esc(p ? p.message : 'Preparando…')}</div>
          <div class="carril" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.floor(pct)}" aria-label="${esc(titulo)}"><div class="relleno" id="rell" style="width:${pct}%"></div></div>
          <div class="progreso-det">
            <div class="dato"><span>Fase</span><b id="dFase">${esc(p ? p.phase : '—')}</b></div>
            <div class="dato"><span>Completados</span><b id="dHechos">${p ? p.done : 0}</b></div>
            <div class="dato"><span>Restantes</span><b id="dRest">${p && p.total ? Math.max(0, p.total - p.done) : '—'}</b></div>
          </div>
          <div class="archivo-act" id="archAct">${esc(p ? p.file || '' : '')}</div>
        </div>
      </div>`,
      [{ id: 'bCancel', t: 'Cancelar', cls: 'peligro', off: !cancelable, fn: () => { $('#bCancel').disabled = true; enviar({ cmd: 'cancel' }); } }]);
  }
  function instalacion() { barra(S.progreso, 0, 'Instalando la traducción española', true); }
  function pintaProgreso(p) {
    S.progreso = p; const pct = Math.max(0, Math.min(100, p.percent));
    const set = (id, v) => { const e = $('#' + id); if (e) e.textContent = v; };
    const r = $('#rell'); if (!r) return; r.style.width = pct + '%';
    const arco = $('#arco'); if (arco) { const C = 2 * Math.PI * 82; arco.style.strokeDashoffset = C * (1 - pct / 100); }
    set('pctTxt', ''); const pc = $('#pctTxt'); if (pc) pc.innerHTML = Math.floor(pct) + '<small>%</small>';
    set('faseTxt', p.message || ''); set('dFase', p.phase || '—'); set('dHechos', p.done); set('dRest', p.total ? Math.max(0, p.total - p.done) : '—'); set('archAct', p.file || '');
    const bar = document.querySelector('[role=progressbar]'); if (bar) bar.setAttribute('aria-valuenow', Math.floor(pct));
    const c = $('#bCancel'); if (c) c.disabled = !p.canCancel;
  }

  function restaurar() {
    S.modo = 'restaurar';
    if (S.progreso && S.ocupado) { barra(S.progreso, 0, 'Restaurando los archivos originales', true); return; }
    const conf = S.conflictos.length ? `<div class="estado aviso">${ICO.aviso}<div><b>Hay archivos modificados después de instalar la traducción</b><span class="muted">No se sobrescribirán sin tu permiso:</span></div></div>
      <ul class="lista">${S.conflictos.slice(0, 8).map((c) => `<li>${ICO.aviso}<span>${esc(c)}</span></li>`).join('')}${S.conflictos.length > 8 ? `<li><span class="muted">… y ${S.conflictos.length - 8} más</span></li>` : ''}</ul>` : '';
    vista(`<h2>Restaurar originales</h2>
      <p class="lead">Se restaurarán los archivos guardados antes de instalar la traducción.</p>
      <p class="muted">Se comprueba la integridad de la copia de seguridad, solo se tocan los archivos que cambió el parche y, al terminar, se verifica cada uno.</p>
      <div class="campo"><input id="ruta" type="text" spellcheck="false" aria-label="Ruta de la carpeta del juego" value="${esc(S.ruta)}" placeholder="Carpeta de FAIRY TAIL 2"><button class="btn" id="bExaminar">Examinar…</button></div>${conf}`,
      [{ id: 'bAtras', t: 'Atrás', fn: () => { S.conflictos = []; ir('bienvenida'); } }, 'esp',
        ...(S.conflictos.length ? [{ id: 'bForzar', t: 'Sobrescribir de todos modos', cls: 'peligro', fn: () => lanzarRestaurar(true) }] : []),
        { id: 'bRestaurar', t: 'Restaurar originales', cls: 'principal', fn: () => lanzarRestaurar(false) }]);
    const inp = $('#ruta'); inp.oninput = () => { S.ruta = inp.value.trim(); }; $('#bExaminar').onclick = () => enviar({ cmd: 'browse', actual: S.ruta });
  }
  function lanzarRestaurar(forzar) {
    if (!S.ruta) { $('#ruta').focus(); return; }
    S.progreso = { percent: 0, message: 'Preparando la restauración…', phase: 'Verificación', done: 0, total: 0, canCancel: true }; S.ocupado = true;
    barra(S.progreso, 0, 'Restaurando los archivos originales', true); enviar({ cmd: 'restore', path: S.ruta, overwrite: !!forzar });
  }

  function final() {
    const f = S.fin || {}; const ok = f.success; const rest = f.op === 'restore';
    const titulo = ok ? (rest ? '¡Archivos originales restaurados!' : '¡Traducción española instalada correctamente!') : (rest ? 'No se pudo completar la restauración' : 'La instalación no se completó');
    vista(`<div class="final-cab"><div class="sello ${ok ? '' : 'mal'}">${ok ? '<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>' : '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><path d="m6 6 12 12M18 6 6 18"/></svg>'}</div>
      <h2>${esc(titulo)}</h2></div><p class="lead">${esc(f.message || '')}</p>
      ${ok ? `<div class="resumen"><div class="dato"><span>${rest ? 'Archivos restaurados' : 'Archivos instalados'}</span><b>${f.files ?? '—'}</b></div>
        <div class="dato"><span>Estado final</span><b>${rest ? 'Juego original' : 'Verificado'}</b></div>
        <div class="dato" style="grid-column:1/-1"><span>Ruta del juego</span><b class="ruta">${esc(S.ruta)}</b></div>
        ${rest ? '' : `<div class="dato" style="grid-column:1/-1"><span>Copia de seguridad · guardada y verificada</span><b class="ruta">${esc(f.backupDir || '')}</b></div>`}</div>`
        : `<p class="muted">Tus archivos originales están a salvo: si se llegó a cambiar algo, se ha revertido automáticamente.</p>`}`,
      [...(ok && !rest ? [{ id: 'bAbrir', t: 'Abrir carpeta del juego', fn: () => enviar({ cmd: 'openFolder', path: S.ruta }) }, { id: 'bJugar', t: 'Iniciar el juego', cls: 'oro', fn: () => enviar({ cmd: 'launchGame', path: S.ruta }) }] : []),
        ...(!ok ? [{ id: 'bReint', t: 'Volver a la comprobación', fn: () => ir('carpeta') }] : []), 'esp',
        { id: 'bFin', t: 'Finalizar', cls: 'principal', fn: () => enviar({ cmd: 'exit' }) }]);
    setTimeout(() => $('#bFin') && $('#bFin').focus(), 80);
  }

  // ---------- guía ----------
  function abrirGuia(abrir) {
    const g = $('#guia'); g.classList.toggle('abierta', abrir); g.setAttribute('aria-hidden', String(!abrir)); $('#btnGuia').setAttribute('aria-expanded', String(abrir));
    if (abrir) $('#cerrarGuia').focus(); else $('#btnGuia').focus();
  }
  $('#btnGuia').onclick = () => abrirGuia(!$('#guia').classList.contains('abierta'));
  $('#cerrarGuia').onclick = () => abrirGuia(false);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && $('#guia').classList.contains('abierta')) abrirGuia(false); });

  // ---------- ventana propia y brillo de cristal ----------
  $('#bMin').onclick = () => enviar({ cmd: 'minimize' });
  $('#bCerrar').onclick = () => enviar({ cmd: 'close' });
  const cristal = $('.cristal');
  document.addEventListener('pointermove', (e) => { const r = cristal.getBoundingClientRect(); cristal.style.setProperty('--mx', (e.clientX - r.left) + 'px'); cristal.style.setProperty('--my', (e.clientY - r.top) + 'px'); });

  // ---------- mensajes del núcleo ----------
  escuchar((m) => {
    switch (m.type) {
      case 'init': S.version = m.version; S.detectadas = m.detected || []; S.hayRespaldos = !!m.hasBackups; if (!S.ruta && S.detectadas.length) S.ruta = S.detectadas[0]; render(); break;
      case 'browse': if (m.path) { S.ruta = m.path; const i = $('#ruta'); if (i) { i.value = m.path; const b = $('#bCont'); if (b) b.disabled = false; } if (S.pantalla === 'carpeta') continuar(); } break;
      case 'analysis': S.analisis = m; S.ocupado = false; if (S.pantalla === 'comprobacion') comprobacion(); break;
      case 'progress': S.ocupado = true; if (S.pantalla === 'instalacion' || S.pantalla === 'restaurar') { if (!$('#rell')) { barra(m, 0, S.pantalla === 'restaurar' ? 'Restaurando los archivos originales' : 'Instalando la traducción española', true); } pintaProgreso(m); } break;
      case 'done': S.ocupado = false; S.fin = m; S.conflictos = m.conflicts || []; if (m.op === 'restore' && !m.success && S.conflictos.length) { S.progreso = null; ir('restaurar'); } else { S.hayRespaldos = m.op === 'restore' ? false : true; S.modo = m.op === 'restore' ? 'restaurar' : 'instalar'; ir('final'); } break;
      case 'error': S.ocupado = false; S.fin = { success: false, op: S.modo === 'restaurar' ? 'restore' : 'install', message: m.message }; ir('final'); break;
    }
  });
  enviar({ cmd: 'init' });
  render();
})();
