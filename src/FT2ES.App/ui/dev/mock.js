/* SOLO DESARROLLO: simula el núcleo nativo para poder revisar la interfaz en un navegador. No se incluye en el EXE. */
window.__mock = (() => {
  let cancelado = false;
  const resp = (m) => setTimeout(() => window.__alRecibir && window.__alRecibir(m), 0);
  const checks = [
    { level: 'Ok', message: 'Se ha encontrado FAIRY_TAIL_2.exe y la estructura MASTER\\ENG.' },
    { level: 'Ok', message: 'Versión compatible con la traducción (SHA-256 de 24 archivos comprobado).' },
    { level: 'Ok', message: 'Permisos de escritura correctos en las carpetas que se van a modificar.' },
    { level: 'Ok', message: 'Espacio disponible: 118,4 GB. Se necesitan unos 410 MB.' },
    { level: 'Ok', message: 'FAIRY TAIL 2 no está en ejecución.' },
    { level: 'Warning', message: 'No hay copia de seguridad previa: se creará una nueva.' },
  ];
  function simular(op) {
    cancelado = false; const fases = ['Verificación', 'Copia de seguridad', 'Parcheo', 'Reconstrucción', 'Validación final']; let p = 0; const total = 520;
    const t = setInterval(() => {
      if (cancelado) { clearInterval(t); resp({ type: 'done', op, success: false, message: 'Instalación cancelada. Se han restaurado los archivos originales.' }); return; }
      p += 1.4 + Math.random() * 2.2; const pct = Math.min(p, 99.4); const f = Math.min(4, Math.floor(pct / 20));
      resp({ type: 'progress', percent: pct, phase: fases[f], message: ['Comprobando los archivos originales…', 'Guardando la copia de seguridad…', 'Aplicando texturas y fuente…', 'Aplicando textos de los diálogos…', 'Verificando la instalación…'][f],
        file: 'Motor\\enUS\\0xb766cb46.fdata', done: Math.floor(pct / 100 * total), total, canCancel: f < 4 });
      if (p >= 100) { clearInterval(t); resp({ type: 'done', op, success: true, message: op === 'restore' ? 'Se han restaurado los archivos originales y se ha verificado cada uno.' : 'Todos los archivos se han verificado correctamente.', files: total, backupDir: '%LOCALAPPDATA%\\Donelys\\FairyTail2ES\\3f9a1c' }); }
    }, 90);
  }
  return {
    recibir(m) {
      if (m.cmd === 'init') resp({ type: 'init', version: '1.0.0', detected: ['H:\\FAIRY TAIL 2'], hasBackups: true });
      else if (m.cmd === 'browse') resp({ type: 'browse', path: 'D:\\Juegos\\FAIRY TAIL 2' });
      else if (m.cmd === 'analyze') setTimeout(() => resp({ type: 'analysis', path: m.path, state: 'Original', checks, hasBackup: true, canInstall: true }), 700);
      else if (m.cmd === 'install') simular('install');
      else if (m.cmd === 'restore') simular('restore');
      else if (m.cmd === 'cancel') cancelado = true;
    },
  };
})();
