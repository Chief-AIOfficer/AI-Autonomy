/* Выравнивание краёв деки: встраивается в HTML-деку последним скриптом (правило стиля v3).
   Соседние блоки одного ряда доводятся до общего низа, если разница не больше max от высоты ряда.
   Блок с фоном растягивается, текст в нём по центру. У таблицы раздвигаются строки. Схема или картинка без фона
   опускается к середине, заголовок колонки остаётся на месте. Текстовый список остаётся от верха. Большую разницу не трогаем.
   Настройка до подключения: window.DECK_ALIGN = {slide: '.slide', rows: '.g2,.g2w,.g3,.g4', fig: '.ex', max: 0.22}.
   Сухой прогон: window.DECK_ALIGN_DRY = 1, журнал в window.DECK_ALIGN_LOG. Готовность: window.DECK_ALIGN_DONE (Promise). */
(function () {
  const C = Object.assign({slide: '.slide', rows: '.g2,.g2w,.g3,.g4', fig: '.ex', max: 0.22}, window.DECK_ALIGN || {});
  const slides = [...document.querySelectorAll(C.slide)];
  const isBox = e => { const b = getComputedStyle(e).backgroundColor; return b && b !== 'rgba(0, 0, 0, 0)' && b !== 'rgb(255, 255, 255)'; };
  const vis = e => e.offsetHeight > 0 && getComputedStyle(e).position !== 'absolute';
  const bottom = e => { const ch = [...e.children].filter(vis); if (isBox(e) || !ch.length) return e.getBoundingClientRect().bottom; return Math.max(...ch.map(c => c.getBoundingClientRect().bottom)); };
  const grow = (e, d) => { const cs = getComputedStyle(e); e.style.paddingTop = (parseFloat(cs.paddingTop) + d / 2) + 'px'; e.style.paddingBottom = (parseFloat(cs.paddingBottom) + d / 2) + 'px'; };
  function fill(e, d) {
    if (isBox(e)) return grow(e, d);
    const ch = [...e.children].filter(vis), boxes = ch.filter(isBox), tb = e.querySelector('table');
    if (boxes.length) return grow(boxes[boxes.length - 1], d);
    if (tb) { tb.style.height = (tb.offsetHeight + d) + 'px'; return; }
    if (e.matches(C.fig)) { e.style.paddingTop = (d / 2) + 'px'; return; }
    const fig = ch.find(c => c.matches(C.fig + ',svg,img') || c.querySelector('svg,img'));
    if (fig) fig.style.marginTop = (parseFloat(getComputedStyle(fig).marginTop) + d / 2) + 'px';
  }
  function alignSlide(s, k) {
    s.querySelectorAll(C.rows).forEach(g => {
      const kids = [...g.children].filter(vis); if (kids.length < 2) return;
      const sc = (g.getBoundingClientRect().height / g.offsetHeight) || 1, rows = {};
      kids.forEach(c => { const t = Math.round(c.getBoundingClientRect().top / (6 * sc)); (rows[t] = rows[t] || []).push(c); });
      Object.values(rows).forEach(row => {
        if (row.length < 2) return;
        const top = Math.min(...row.map(c => c.getBoundingClientRect().top)), b = row.map(bottom), mb = Math.max(...b), H = mb - top;
        row.forEach((c, i) => {
          const d = mb - b[i]; if (d / H <= 0.01 || d / H > C.max) return;
          if (window.DECK_ALIGN_LOG) window.DECK_ALIGN_LOG.push((k + 1) + ': ' + (c.className || c.tagName) + ' +' + Math.round(d / sc) + 'px, ' + Math.round(100 * d / H) + '%');
          if (!window.DECK_ALIGN_DRY) { fill(c, d / sc); c.dataset.deckAligned = '1'; }
        });
      });
    });
  }
  function run() {   // каждый слайд временно показывается, чтобы у блоков были размеры
    slides.forEach((s, k) => {
      const was = s.style.display, hidden = getComputedStyle(s).display === 'none';
      if (hidden) s.style.display = 'flex';
      alignSlide(s, k);
      if (hidden) s.style.display = was;
    });
  }
  window.deckAlignRun = run;
  window.DECK_ALIGN_DONE = (document.fonts ? document.fonts.ready : Promise.resolve()).then(run);   // мерить после шрифтов
})();
