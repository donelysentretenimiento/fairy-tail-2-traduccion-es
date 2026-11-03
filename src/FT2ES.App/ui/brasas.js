/* Brasas flotantes de fondo: ~70 partículas doradas y carmesí que suben despacio. Ligero (≈30 fps), se detiene si la ventana no se ve
   y no se dibuja con «reducir movimiento». Es solo decoración: la interfaz no depende de ello. */
(() => {
  'use strict';
  const cv = document.getElementById('brasas');
  if (!cv || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const cx = cv.getContext('2d'); let W = 0, H = 0, dpr = 1, ps = [], ultimo = 0;
  const colores = [[255, 214, 120], [255, 170, 90], [240, 80, 110], [255, 236, 190]];
  const nueva = (abajo) => ({ x: Math.random() * W, y: abajo ? H + 10 : Math.random() * H, r: 0.6 + Math.random() * 2.1, v: 8 + Math.random() * 26, d: (Math.random() - 0.5) * 12,
    f: Math.random() * Math.PI * 2, c: colores[(Math.random() * colores.length) | 0], a: 0.25 + Math.random() * 0.6 });
  function medir() { dpr = Math.min(2, window.devicePixelRatio || 1); W = cv.clientWidth; H = cv.clientHeight; cv.width = W * dpr; cv.height = H * dpr; cx.setTransform(dpr, 0, 0, dpr, 0, 0); ps = Array.from({ length: Math.round(W * H / 14000) }, () => nueva(false)); }
  function paso(t) {
    requestAnimationFrame(paso); if (document.hidden || t - ultimo < 33) return; const dt = Math.min(0.1, (t - ultimo) / 1000); ultimo = t;
    cx.clearRect(0, 0, W, H);
    for (const p of ps) {
      p.y -= p.v * dt; p.x += (p.d + Math.sin(t / 1400 + p.f) * 9) * dt; if (p.y < -12 || p.x < -12 || p.x > W + 12) Object.assign(p, nueva(true));
      const al = p.a * (0.55 + 0.45 * Math.sin(t / 700 + p.f)) * Math.min(1, (H - p.y) / 120, p.y / 90 + 0.2);
      const g = cx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 5);
      g.addColorStop(0, `rgba(${p.c[0]},${p.c[1]},${p.c[2]},${Math.max(0, al)})`); g.addColorStop(1, `rgba(${p.c[0]},${p.c[1]},${p.c[2]},0)`);
      cx.fillStyle = g; cx.beginPath(); cx.arc(p.x, p.y, p.r * 5, 0, 6.2832); cx.fill();
    }
  }
  window.addEventListener('resize', medir); medir(); requestAnimationFrame(paso);
})();
