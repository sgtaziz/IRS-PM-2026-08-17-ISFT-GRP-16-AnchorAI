/* AnchorAI presentation engine. Dependency-free; works from file://.
   Usage: <div class="deck" data-id="demo" data-speaker="Name"> <section class="slide dark">...</section> </div> + this script. */
(function () {
  'use strict';

  var DW = 1920, DH = 1080;
  var EASE = 'cubic-bezier(.2,.8,.2,1)';
  var REACT = '.react,[data-count],[data-split],.lower-third,.logo-reveal,.bar,.chart,.check-item';
  var RM = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : { matches: false };

  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function pad2(n) { return (n < 10 ? '0' : '') + n; }
  function fmtTime(ms) { var s = Math.max(0, Math.round(ms / 1000)); return Math.floor(s / 60) + ':' + pad2(s % 60); }
  function parseTime(v) {
    if (v == null || v === '') return 0;
    v = String(v);
    if (v.indexOf(':') > -1) { var p = v.split(':'); return (+p[0]) * 60 + (+p[1]); }
    return +v || 0;
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  var uid = 0;

  /* ---------- Cross-window link: BroadcastChannel + postMessage fallback, de-duplicated ---------- */
  function Link(id, onmsg) {
    var self = this, seen = {};
    this.wins = [];
    this.bc = null;
    function receive(m) {
      if (!m || !m.__anchorai || m.id !== id || seen[m.mid]) return;
      seen[m.mid] = 1;
      onmsg(m);
    }
    try {
      if (window.BroadcastChannel) {
        this.bc = new BroadcastChannel('anchorai-deck-' + id);
        this.bc.onmessage = function (e) { receive(e.data); };
      }
    } catch (e) { this.bc = null; }
    window.addEventListener('message', function (e) { receive(e.data); });
    this.send = function (m) {
      m.__anchorai = 1; m.id = id; m.mid = Date.now() + '-' + Math.random().toString(36).slice(2);
      try { if (self.bc) self.bc.postMessage(m); } catch (e) {}
      self.wins.forEach(function (w) { try { if (w && !w.closed) w.postMessage(m, '*'); } catch (e) {} });
    };
  }
  window.AnchorLink = Link;

  /* Direct children the engine may animate without fighting the deck: no own CSS animation or
     transition, not step-gated, and not hidden by their base style. */
  function safeKids(slide) {
    return $$(':scope > :not(.slide-bg):not(aside)', slide).filter(function (k) {
      if (k.hasAttribute('data-step') || k.hasAttribute('data-step-out')) return false;
      var cs = getComputedStyle(k);
      return cs.display !== 'none' && cs.opacity === '1' && k.getAnimations().length === 0;
    });
  }
  function restartAnimations(e) {
    e.style.display = 'none';
    void e.offsetHeight;
    e.style.display = '';
  }

  /* ---------- Deck ---------- */
  function Deck(root) {
    this.root = root;
    this.id = root.dataset.id || (location.pathname.split('/').pop() || 'deck').replace(/\.html?$/, '');
    this.title = root.dataset.title || document.title;
    this.speaker = root.dataset.speaker || '';
    this.role = root.dataset.speakerRole || '';
    this.cur = -1; this.step = 0; this.scale = 1;
    this.anims = []; this.finishers = [];
    this.keyBuf = '';
    this.build();
    this.parse();
    this.bind();
    this.restoreTimer();
    var h = this.readHash();
    this.goto(h.slide, h.step, { instant: true, noTimer: true });
    this.fit();
    this.publish();
  }

  Deck.prototype.build = function () {
    var root = this.root;
    document.body.classList.toggle('rm', RM.matches);
    this.dv = el('div', 'dv');
    this.stage = el('div', 'stage');
    root.parentNode.insertBefore(this.dv, root);
    this.dv.appendChild(this.stage);
    this.stage.appendChild(root);
    var c = this.chrome = el('div', 'chrome');
    c.innerHTML = '<div class="pg"><i></i></div><div class="chip"><b></b><span class="nm"></span><span class="n"></span></div>' +
      '<div class="toast"></div><div class="camzone">Camera safe zone 480 x 300</div><div class="rehearsal"></div>';
    this.stage.appendChild(c);
    this.pgFill = $('.pg i', c); this.chipAv = $('.chip b', c); this.chipNm = $('.chip .nm', c); this.chipN = $('.chip .n', c);
    this.toastEl = $('.toast', c); this.rehEl = $('.rehearsal', c);
  };

  Deck.prototype.parse = function () {
    var self = this, sections = [];
    this.slides = $$(':scope > .slide', this.root).map(function (se, i) {
      var s = { el: se, index: i, inited: false, live: false, stepped: [], react: [], frames: [] };
      if (!$('.slide-bg', se)) se.insertBefore(el('div', 'slide-bg', '<i class="glow a"></i><i class="glow b"></i><i class="glow c"></i><div class="grain"></div><div class="vignette"></div>'), se.firstChild);
      var maxStep = 0;
      $$('[data-step]', se).forEach(function (e) { maxStep = Math.max(maxStep, +e.dataset.step || 0); });
      $$('[data-step-out]', se).forEach(function (e) { maxStep = Math.max(maxStep, +e.dataset.stepOut || 0); });
      s.notes = [];
      var k = 0;
      $$(':scope > aside.notes', se).forEach(function (a) {
        var beats = $$(':scope > [data-beat]', a);
        var units = beats.length ? beats : [a];
        units.forEach(function (u) {
          var st = u.dataset.step != null && u.dataset.step !== '' ? +u.dataset.step : k;
          s.notes.push({ step: st, beat: u.dataset.beat || a.dataset.beat || '', text: u.textContent.replace(/\s+/g, ' ').trim() });
          k = st + 1;
          maxStep = Math.max(maxStep, st);
        });
      });
      s.steps = maxStep;
      var h = $('h1,h2,.display,.h1,.h2,.qtext,.cap', se);
      s.title = se.dataset.title || (h ? h.textContent.replace(/\s+/g, ' ').trim().slice(0, 70) : 'Slide ' + (i + 1));
      if (se.dataset.section != null || i === 0) {
        sections.push({ name: se.dataset.section || 'Opening', target: parseTime(se.dataset.sectionTarget), start: i });
      }
      s.section = sections.length - 1;
      return s;
    });
    this.sections = sections;
    var tot = parseTime(this.root.dataset.totalTarget);
    this.totalTarget = tot || sections.reduce(function (a, s) { return a + s.target; }, 0);
  };

  Deck.prototype.readHash = function () {
    var m = /^#(\d+)(?:\/(\d+))?/.exec(location.hash || '');
    var n = this.slides.length;
    return m ? { slide: clamp((+m[1] || 1) - 1, 0, n - 1), step: +m[2] || 0 } : { slide: 0, step: 0 };
  };
  Deck.prototype.writeHash = function () {
    try { history.replaceState(null, '', '#' + (this.cur + 1) + '/' + this.step); } catch (e) { location.hash = (this.cur + 1) + '/' + this.step; }
  };

  Deck.prototype.fit = function () {
    var k = Math.min(window.innerWidth / DW, window.innerHeight / DH);
    this.scale = k;
    this.stage.style.transform = 'translate(-50%,-50%) scale(' + k + ')';
  };

  /* ---------- Slide initialisation (lazy, after the slide is displayed so layout is measurable) ---------- */
  Deck.prototype.initSlide = function (s) {
    if (s.inited) return;
    s.inited = true;
    var se = s.el, self = this;
    $$('[data-split]', se).forEach(splitWords);
    $$('.logo-reveal', se).forEach(buildLogo);
    $$('.bar', se).forEach(buildBar);
    $$('.chart', se).forEach(buildChart);
    $$('.check-item', se).forEach(buildCheck);
    $$('.lower-third', se).forEach(buildLower);
    $$('.flow', se).forEach(buildFlow);
    $$('.frame', se).forEach(function (f) { s.frames.push(buildFrame(f)); });
    $$('[data-count]', se).forEach(hookCount);
    s.stepped = $$('[data-step],[data-step-out]', se);
    s.react = $$(REACT, se);
    s.timelines = $$('.timeline', se);
  };

  Deck.prototype.applySteps = function (s, step) {
    s.stepped.forEach(function (e) {
      var st = e.dataset.step, out = e.dataset.stepOut;
      e.classList.toggle('is-in', st == null || st === '' || step >= +st);
      e.classList.toggle('is-out', out != null && out !== '' && step >= +out);
    });
    s.timelines.forEach(function (tl) {
      var items = $$('.tl-item', tl), k = -1;
      items.forEach(function (it, i) { if (it.classList.contains('is-in')) k = i; });
      tl.style.setProperty('--p', k < 0 ? '0px' : 'calc(' + (k / items.length * 100) + '% + 24px)');
    });
    s.frames.forEach(function (f) { f.update(); });
    this.syncReact(s);
  };

  Deck.prototype.syncReact = function (s) {
    var live = s.live;
    s.react.forEach(function (e) {
      var shown = live && !e.closest('[data-step]:not(.is-in)');
      if (shown === !!e._shown) return;
      e._shown = shown;
      e.classList.toggle('is-shown', shown);
      if (e._hook) e._hook(shown);
    });
  };

  /* ---------- Navigation ---------- */
  Deck.prototype.goto = function (i, step, opts) {
    opts = opts || {};
    i = clamp(i, 0, this.slides.length - 1);
    var s = this.slides[i];
    step = clamp(step || 0, 0, s.steps);
    if (i === this.cur) {
      this.step = step;
      this.applySteps(s, step);
      this.after(opts);
      return;
    }
    var reshown = s.el.classList.contains('is-leaving');
    this.finishTransition();
    var from = this.cur >= 0 ? this.slides[this.cur] : null;
    var dir = opts.dir || (from && i < from.index ? -1 : 1);
    s.live = true;
    this.cur = i; this.step = step;
    if (reshown) restartAnimations(s.el);
    s.el.classList.add('is-active');
    this.initSlide(s);
    // Style flush: the slide must be rendered once in its unrevealed state, otherwise CSS
    // transitions have no start value and the final state paints first.
    void s.el.offsetHeight;
    this.applySteps(s, step);
    if (from) {
      from.el.classList.add('is-leaving');
      var type = opts.instant ? 'cut' : (s.el.dataset.transition || this.root.dataset.transition || 'fade');
      if (RM.matches && type !== 'cut') type = 'fade';
      this.runTransition(type, from, s, dir);
    }
    this.after(opts);
  };

  Deck.prototype.after = function (opts) {
    var s = this.slides[this.cur];
    this.writeHash();
    var theme = s.el.classList.contains('light') ? 'light' : 'dark';
    this.stage.dataset.theme = theme;
    this.stage.dataset.chrome = s.el.dataset.chrome === 'off' ? 'off' : 'on';
    var sp = s.el.dataset.speaker || this.speaker;
    this.chipAv.textContent = sp ? sp.trim().charAt(0).toUpperCase() : '';
    this.chipNm.textContent = sp;
    this.chrome.querySelector('.chip').style.display = sp ? '' : 'none';
    this.chipN.textContent = pad2(this.cur + 1) + ' / ' + pad2(this.slides.length);
    var total = 0, done = 0;
    this.slides.forEach(function (x, j) { total += 1; });
    done = this.cur + (s.steps ? this.step / (s.steps + 1) : 0);
    this.pgFill.style.transform = 'scaleX(' + clamp((done + (this.cur === this.slides.length - 1 && this.step === s.steps ? 1 : 0.0001)) / total, 0, 1) + ')';
    if (!opts.noTimer && this.timer && !this.timer.running && !this.timer.started && (this.cur > 0 || this.step > 0)) this.startTimer();
    this.publish();
  };

  Deck.prototype.next = function () {
    var s = this.slides[this.cur];
    if (this.step < s.steps) this.goto(this.cur, this.step + 1);
    else if (this.cur < this.slides.length - 1) this.goto(this.cur + 1, 0, { dir: 1 });
  };
  Deck.prototype.prev = function () {
    if (this.step > 0) this.goto(this.cur, this.step - 1);
    else if (this.cur > 0) this.goto(this.cur - 1, this.slides[this.cur - 1].steps, { dir: -1 });
  };

  /* ---------- Transitions ---------- */
  Deck.prototype.finishTransition = function () {
    var f = this.finishers; this.finishers = [];
    f.forEach(function (fn) { fn(); });
  };

  Deck.prototype.runTransition = function (type, from, to, dir) {
    var self = this, anims = [], cleanups = [];
    var fe = from.el, te = to.el;
    var kids = function (e) { return safeKids(e); };
    function A(node, kf, o) {
      var a = node.animate(kf, Object.assign({ easing: EASE, fill: 'both' }, o));
      anims.push(a); return a;
    }
    var D = type === 'cut' ? 0 : 1;
    var d = dir;
    if (type === 'fade') {
      A(fe, [{ opacity: 1, scale: 1 }, { opacity: 0, scale: .985 }], { duration: 420, easing: 'ease-in' });
      A(te, [{ opacity: 0, scale: 1.02 }, { opacity: 1, scale: 1 }], { duration: 820, delay: 260 });
    } else if (type === 'slide') {
      A(fe, [{ translate: '0 0', opacity: 1, filter: 'brightness(1)' }, { translate: (-d * 24) + '% 0', opacity: .35, filter: 'brightness(.6)' }], { duration: 1000 });
      te.style.boxShadow = '0 0 160px rgba(0,0,0,.55)';
      cleanups.push(function () { te.style.boxShadow = ''; });
      A(te, [{ translate: (d * 100) + '% 0' }, { translate: '0 0' }], { duration: 1000 });
      A($('.slide-bg', te), [{ translate: (-d * 240) + 'px 0' }, { translate: '0 0' }], { duration: 1000 });
      kids(te).forEach(function (k, i) { A(k, [{ translate: (d * 200) + 'px 0', opacity: 0 }, { translate: '0 0', opacity: 1 }], { duration: 1000, delay: 80 + i * 45 }); });
    } else if (type === 'up') {
      A(fe, [{ translate: '0 0', opacity: 1 }, { translate: '0 ' + (-d * 16) + '%', opacity: .3 }], { duration: 1000 });
      te.style.boxShadow = '0 0 160px rgba(0,0,0,.55)';
      cleanups.push(function () { te.style.boxShadow = ''; });
      A(te, [{ translate: '0 ' + (d * 100) + '%' }, { translate: '0 0' }], { duration: 1000 });
      kids(te).forEach(function (k, i) { A(k, [{ translate: '0 ' + (d * 120) + 'px', opacity: 0 }, { translate: '0 0', opacity: 1 }], { duration: 1000, delay: 80 + i * 45 }); });
    } else if (type === 'zoom') {
      A(fe, [{ scale: 1, opacity: 1, filter: 'blur(0px)' }, { scale: 1.22, opacity: 0, filter: 'blur(22px)' }], { duration: 760, easing: 'cubic-bezier(.5,0,.8,.4)' });
      A(te, [{ scale: .84, opacity: 0, filter: 'blur(26px)' }, { scale: 1, opacity: 1, filter: 'blur(0px)' }], { duration: 1000, delay: 160 });
    } else if (type === 'wipe') {
      A(fe, [{ translate: '0 0', scale: 1, filter: 'brightness(1)' }, { translate: (-d * 3) + '% 0', scale: .97, filter: 'brightness(.55)' }], { duration: 1100 });
      var p0 = d > 0 ? 'polygon(0% 0%, 0% 0%, -26% 100%, 0% 100%)' : 'polygon(100% 0%, 100% 0%, 126% 100%, 100% 100%)';
      var p1 = d > 0 ? 'polygon(0% 0%, 126% 0%, 100% 100%, 0% 100%)' : 'polygon(100% 0%, -26% 0%, 0% 100%, 100% 100%)';
      A(te, [{ clipPath: p0 }, { clipPath: p1 }], { duration: 1100, easing: 'cubic-bezier(.7,0,.2,1)' });
      kids(te).forEach(function (k, i) { A(k, [{ translate: '0 40px', opacity: 0 }, { translate: '0 0', opacity: 1 }], { duration: 900, delay: 520 + i * 50 }); });
    } else if (type === 'morph') {
      this.morph(from, to, A, cleanups);
    }
    if (!anims.length) { this.endTransition(from, to, cleanups); return; }
    var done = false;
    var finish = function () {
      if (done) return; done = true;
      anims.forEach(function (a) { try { a.cancel(); } catch (e) {} });
      self.endTransition(from, to, cleanups);
    };
    this.finishers.push(finish);
    Promise.all(anims.map(function (a) { return a.finished; })).then(function () {
      var i = self.finishers.indexOf(finish);
      if (i > -1) self.finishers.splice(i, 1);
      finish();
    }, function () {});
  };

  Deck.prototype.endTransition = function (from, to, cleanups) {
    cleanups.forEach(function (c) { c(); });
    from.el.classList.remove('is-leaving', 'is-active');
    from.live = false;
    this.syncReact(from);
    from.el.style.cssText = '';
  };

  Deck.prototype.morph = function (from, to, A, cleanups) {
    var k = this.scale, fe = from.el, te = to.el;
    var pairs = [];
    $$('[data-morph]', te).forEach(function (m) {
      var o = fe.querySelector('[data-morph="' + m.dataset.morph + '"]');
      if (o) pairs.push([o, m]);
    });
    var holds = pairs.map(function (p) { return p[1]; });
    var isMorphy = function (n) { return n.matches('[data-morph]') || n.querySelector('[data-morph]'); };
    A($('.slide-bg', te), [{ opacity: 0 }, { opacity: 1 }], { duration: 900, easing: 'ease-out' });
    $$(':scope > :not(.slide-bg):not(aside)', fe).forEach(function (n) {
      if (!isMorphy(n)) A(n, [{ opacity: 1 }, { opacity: 0 }], { duration: 380, easing: 'ease-in' });
    });
    safeKids(te).forEach(function (n, i) {
      if (!isMorphy(n)) A(n, [{ opacity: 0, translate: '0 36px' }, { opacity: 1, translate: '0 0' }], { duration: 900, delay: 480 + i * 60 });
    });
    pairs.forEach(function (p) {
      var o = p[0], m = p[1];
      var ro = o.getBoundingClientRect(), ri = m.getBoundingClientRect();
      if (!ri.width || !ri.height) return;
      var dx = (ro.left - ri.left) / k, dy = (ro.top - ri.top) / k;
      var prevO = o.style.visibility;
      o.style.visibility = 'hidden';
      m.style.transformOrigin = '0 0';
      cleanups.push(function () { m.style.transformOrigin = ''; o.style.visibility = prevO; });
      A(m, [{ translate: dx + 'px ' + dy + 'px', scale: (ro.width / ri.width) + ' ' + (ro.height / ri.height) },
            { translate: '0px 0px', scale: '1 1' }], { duration: 1200, easing: 'cubic-bezier(.65,0,.2,1)' });
    });
  };

  /* ---------- Input ---------- */
  Deck.prototype.bind = function () {
    var self = this;
    window.addEventListener('resize', function () { self.fit(); });
    window.addEventListener('hashchange', function () {
      var h = self.readHash();
      if (h.slide !== self.cur || h.step !== self.step) self.goto(h.slide, h.step, { instant: true, noTimer: true });
    });
    document.addEventListener('keydown', function (e) {
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      var k = e.key, used = true;
      if (k === 'ArrowRight' || k === ' ' || k === 'PageDown' || k === 'ArrowDown') self.next();
      else if (k === 'ArrowLeft' || k === 'PageUp' || k === 'ArrowUp') self.prev();
      else if (k === 'Home') self.goto(0, 0);
      else if (k === 'End') { var l = self.slides[self.slides.length - 1]; self.goto(self.slides.length - 1, l.steps); }
      else if (k === 'f' || k === 'F') self.fullscreen();
      else if (k === 'c' || k === 'C') document.body.classList.toggle('show-cam');
      else if (k === 't' || k === 'T') { document.body.classList.toggle('show-reh'); self.renderReh(); }
      else if (k === 'p' || k === 'P') self.openPresenter();
      else if (k === 'R' && e.shiftKey) self.resetTimer();
      else if (/^[0-9]$/.test(k)) { self.keyBuf = (self.keyBuf + k).slice(-3); self.toast('Go to ' + self.keyBuf); }
      else if (k === 'Enter' && self.keyBuf) { self.goto(+self.keyBuf - 1, 0); self.toast(''); self.keyBuf = ''; }
      else if (k === 'Escape') { self.keyBuf = ''; self.toast(''); }
      else used = false;
      if (used) e.preventDefault();
    });
    this.dv.addEventListener('click', function (e) { if (e.button === 0) self.next(); });
    var idleT;
    document.addEventListener('mousemove', function () {
      self.dv.classList.remove('idle'); clearTimeout(idleT);
      idleT = setTimeout(function () { self.dv.classList.add('idle'); }, 1800);
    });
    idleT = setTimeout(function () { self.dv.classList.add('idle'); }, 1800);
    this.link = new Link(this.id, function (m) { self.onMessage(m); });
    setInterval(function () { self.tick(); }, 250);
  };

  Deck.prototype.fullscreen = function () {
    try {
      if (document.fullscreenElement) document.exitFullscreen();
      else document.documentElement.requestFullscreen();
    } catch (e) {}
  };
  Deck.prototype.toast = function (t) {
    var tt = this.toastEl;
    tt.textContent = t; tt.classList.toggle('on', !!t);
    clearTimeout(this._toastT);
    if (t) this._toastT = setTimeout(function () { tt.classList.remove('on'); }, 2200);
  };

  /* ---------- Timers (shared by rehearsal overlay and presenter) ---------- */
  Deck.prototype.restoreTimer = function () {
    this.timer = { running: false, started: false, last: 0, el: this.sections.map(function () { return 0; }) };
    try {
      var j = JSON.parse(sessionStorage.getItem('anchorai-timer-' + this.id) || 'null');
      if (j && j.el && j.el.length === this.sections.length) { this.timer.el = j.el; this.timer.started = !!j.started; this.timer.running = !!j.running; this.timer.last = performance.now(); }
    } catch (e) {}
  };
  Deck.prototype.saveTimer = function () {
    try { sessionStorage.setItem('anchorai-timer-' + this.id, JSON.stringify({ el: this.timer.el, started: this.timer.started, running: this.timer.running })); } catch (e) {}
  };
  Deck.prototype.startTimer = function () { this.timer.running = true; this.timer.started = true; this.timer.last = performance.now(); this.saveTimer(); };
  Deck.prototype.toggleTimer = function () { if (this.timer.running) { this.tick(); this.timer.running = false; } else this.startTimer(); this.saveTimer(); this.publish(); };
  Deck.prototype.resetTimer = function () { this.timer.el = this.sections.map(function () { return 0; }); this.timer.running = false; this.timer.started = false; this.saveTimer(); this.renderReh(); this.publish(); this.toast('Timers reset'); };
  Deck.prototype.tick = function () {
    var t = this.timer, now = performance.now();
    if (t.running) {
      var sec = this.slides[this.cur] ? this.slides[this.cur].section : 0;
      t.el[sec] += now - t.last; t.last = now;
      if (!this._lastSave || now - this._lastSave > 2000) { this._lastSave = now; this.saveTimer(); }
      if (!this._lastPub || now - this._lastPub > 900) { this._lastPub = now; this.publish(); }
    }
    this.renderReh();
  };
  Deck.prototype.timers = function () {
    var t = this.timer;
    return { running: t.running, el: t.el.slice(), total: t.el.reduce(function (a, b) { return a + b; }, 0) };
  };
  Deck.prototype.renderReh = function () {
    if (!document.body.classList.contains('show-reh')) return;
    var self = this, T = this.timers(), cur = this.slides[this.cur].section;
    var h = '<h4><span>Rehearsal</span><span>' + (T.running ? 'running' : 'paused') + ' &middot; Shift+R reset</span></h4>';
    this.sections.forEach(function (s, i) {
      var e = T.el[i], tg = s.target * 1000, r = tg ? e / tg : 0;
      var cls = 'rr' + (i === cur ? ' cur' : '') + (tg && r > 1 ? ' over' : tg && r > .85 ? ' warn' : '');
      h += '<div class="' + cls + '"><span>' + esc(s.name) + '</span><span>' + fmtTime(e) + (tg ? ' / ' + fmtTime(tg) : '') + '</span><div class="rb"><i style="width:' + clamp(r * 100, 0, 100) + '%"></i></div></div>';
    });
    var tt = this.totalTarget * 1000;
    h += '<div class="rr tot"><span>Total</span><span>' + fmtTime(T.total) + (tt ? ' / ' + fmtTime(tt) : '') + '</span></div>';
    this.rehEl.innerHTML = h;
  };

  /* ---------- Presenter sync ---------- */
  Deck.prototype.outline = function () {
    return this.slides.map(function (s) {
      return { title: s.title, section: s.section, steps: s.steps, notes: s.notes };
    });
  };
  Deck.prototype.publish = function () {
    if (!this.link) return;
    var s = this.slides[this.cur];
    this.link.send({
      t: 'state', title: this.title, speaker: s.el.dataset.speaker || this.speaker, role: this.role,
      cur: this.cur, step: this.step, outline: this.outline(),
      sections: this.sections, totalTarget: this.totalTarget, timers: this.timers()
    });
  };
  Deck.prototype.onMessage = function (m) {
    if (m.t === 'hello') { this.publish(); return; }
    if (m.t !== 'cmd') return;
    if (m.cmd === 'next') this.next();
    else if (m.cmd === 'prev') this.prev();
    else if (m.cmd === 'goto') this.goto(m.slide, m.step || 0);
    else if (m.cmd === 'timer-toggle') this.toggleTimer();
    else if (m.cmd === 'timer-reset') this.resetTimer();
  };
  Deck.prototype.openPresenter = function () {
    var url = (this.root.dataset.presenter || 'presenter.html') + '#' + encodeURIComponent(this.id);
    var w = window.open(url, 'anchorai-presenter', 'popup,width=1280,height=760');
    if (!w) { this.toast('Popup blocked: allow popups for this page'); return; }
    if (this.link.wins.indexOf(w) < 0) this.link.wins.push(w);
    try { w.focus(); } catch (e) {}
    var self = this;
    setTimeout(function () { self.publish(); }, 600);
  };

  /* ---------- Component builders ---------- */
  function splitWords(e) {
    var i = 0;
    (function walk(n) {
      Array.prototype.slice.call(n.childNodes).forEach(function (c) {
        if (c.nodeType === 3) {
          var frag = document.createDocumentFragment();
          c.textContent.split(/(\s+)/).forEach(function (t) {
            if (!t) return;
            if (/^\s+$/.test(t)) { frag.appendChild(document.createTextNode(' ')); return; }
            var w = el('span', 'w'); w.textContent = t; w.style.setProperty('--i', i++); frag.appendChild(w);
          });
          n.replaceChild(frag, c);
        } else if (c.nodeType === 1) walk(c);
      });
    })(e);
    e.style.setProperty('--n', i);
  }

  function buildLogo(e) {
    if (e.firstChild) return;
    var id = 'lg' + (++uid);
    if (e.dataset.size) e.style.setProperty('--ls', e.dataset.size + 'px');
    var parts = [
      '<circle cx="16" cy="8.4" r="2.5"/>', '<path d="M16 10.9v14.6"/>', '<path d="M11.6 14.6h8.8"/>',
      '<path d="M7.6 18.4c.3 4.3 3.9 7.1 8.4 7.1s8.1-2.8 8.4-7.1"/>', '<path d="M5.9 20.3l1.7-1.9 2.1 1.4"/>', '<path d="M26.1 20.3l-1.7-1.9-2.1 1.4"/>'
    ].map(function (p, k) { return p.replace('/>', ' pathLength="1" style="--k:' + k + '"/>'); }).join('');
    e.innerHTML = '<svg class="mk" viewBox="0 0 32 32" fill="none"><defs><linearGradient id="' + id + '" x1="4" y1="2" x2="28" y2="30" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#4c93ff"/><stop offset="1" stop-color="#1a3fac"/></linearGradient></defs>' +
      '<rect class="bgr" width="32" height="32" rx="9" fill="url(#' + id + ')"/><g class="st" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">' + parts + '</g>' +
      '<circle class="ping" cx="24.6" cy="7.6" r="1.7" fill="#7fe3c4"/><circle class="dot" cx="24.6" cy="7.6" r="1.7" fill="#7fe3c4"/></svg>' +
      (e.dataset.mark === 'only' ? '' : '<span class="wm"><span class="in">Anchor<span class="ai">AI</span></span></span>');
  }

  function buildBar(e) {
    if (e.dataset.built) return; e.dataset.built = 1;
    var max = +e.dataset.max || 100, v = +e.dataset.value || 0;
    e.style.setProperty('--p', clamp(v / max, 0, 1));
    e.innerHTML = '<div class="lbl">' + esc(e.dataset.label || '') + (e.dataset.sub ? '<small>' + esc(e.dataset.sub) + '</small>' : '') + '</div>' +
      '<div class="track"><div class="fill"></div></div>' +
      '<div class="val" data-count="' + v + '" data-prefix="' + esc(e.dataset.prefix || '') + '" data-suffix="' + esc(e.dataset.suffix || '') + '" data-decimals="' + (e.dataset.decimals || 0) + '" data-duration="1600"></div>';
    if (e.dataset.tone) e.dataset.tone = e.dataset.tone;
  }

  function buildCheck(e) {
    if ($('.tick', e)) return;
    var body = el('div', null, e.innerHTML);
    e.innerHTML = '<svg class="tick" viewBox="0 0 64 64"><circle cx="32" cy="32" r="30"/><path pathLength="1" d="' + (e.classList.contains('fail') ? 'M23 23l18 18M41 23L23 41' : 'M19 33l9 9 17-20') + '"/></svg>';
    e.appendChild(body);
  }

  function buildLower(e) {
    if (!e.firstElementChild) {
      e.innerHTML = '<span class="lt-bar"></span><div><div class="lt-name">' + esc(e.dataset.name || '') + '</div><div class="lt-role">' + esc(e.dataset.role || '') + '</div></div>';
    }
    var hold = +e.dataset.hold || 5000, t1, t2;
    e._hook = function (shown) {
      clearTimeout(t1); clearTimeout(t2);
      if (shown) {
        e.classList.remove('lt-off');
        t1 = setTimeout(function () { e.classList.add('lt-on'); }, +e.dataset.delay || 700);
        t2 = setTimeout(function () { e.classList.remove('lt-on'); e.classList.add('lt-off'); }, (+e.dataset.delay || 700) + hold);
      } else e.classList.remove('lt-on', 'lt-off');
    };
  }

  /* count-up numbers: any element with data-count */
  function fmtNum(v, dec) { return v.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec }); }
  function hookCount(e) {
    if (e._hooked) return; e._hooked = 1;
    var to = +e.dataset.count || 0, from = +e.dataset.from || 0, dec = +e.dataset.decimals || 0;
    var pre = e.dataset.prefix || '', suf = e.dataset.suffix || '', dur = +e.dataset.duration || 1900, delay = +e.dataset.delay || 0;
    var raf = 0, t0;
    function render(v) {
      e.innerHTML = (pre ? '<span class="pre">' + esc(pre) + '</span>' : '') + fmtNum(v, dec) + (suf ? '<span class="suf">' + esc(suf) + '</span>' : '');
    }
    render(from);
    var prev = e._hook;
    e._hook = function (shown) {
      if (prev) prev(shown);
      cancelAnimationFrame(raf);
      if (!shown) { render(from); return; }
      if (RM.matches) { render(to); return; }
      t0 = performance.now() + delay;
      (function step(now) {
        var t = clamp((now - t0) / dur, 0, 1);
        var k = t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
        render(from + (to - from) * k);
        if (t < 1) raf = requestAnimationFrame(step);
      })(performance.now());
    };
  }

  function niceMax(v) {
    var p = Math.pow(10, Math.floor(Math.log10(v || 1))), n = v / p;
    var c = n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10;
    return c * p;
  }
  function smooth(pts) {
    var d = 'M' + pts[0][0] + ' ' + pts[0][1];
    for (var i = 0; i < pts.length - 1; i++) {
      var p0 = pts[i - 1] || pts[i], p1 = pts[i], p2 = pts[i + 1], p3 = pts[i + 2] || p2;
      var lo = Math.min(p1[1], p2[1]), hi = Math.max(p1[1], p2[1]);
      var c1y = clamp(p1[1] + (p2[1] - p0[1]) / 6, lo, hi), c2y = clamp(p2[1] - (p3[1] - p1[1]) / 6, lo, hi);
      d += ' C' + (p1[0] + (p2[0] - p0[0]) / 6).toFixed(1) + ' ' + c1y.toFixed(1) + ' ' + (p2[0] - (p3[0] - p1[0]) / 6).toFixed(1) + ' ' + c2y.toFixed(1) + ' ' + p2[0].toFixed(1) + ' ' + p2[1].toFixed(1);
    }
    return d;
  }
  function buildChart(e) {
    if (e.dataset.built) return; e.dataset.built = 1;
    var W = +e.dataset.w || 1280, H = +e.dataset.h || 520;
    if (!e.style.width) e.style.width = W + 'px';
    var series = JSON.parse(e.dataset.series || '[]'), labels = (e.dataset.labels || '').split(',').map(function (x) { return x.trim(); });
    var unit = e.dataset.unit || '';
    var P = { l: 96, r: 120, t: 24, b: 64 }, n = Math.max.apply(null, series.map(function (s) { return s.data.length; }));
    var all = [].concat.apply([], series.map(function (s) { return s.data; }));
    var ymin = e.dataset.ymin != null ? +e.dataset.ymin : Math.min(0, Math.min.apply(null, all));
    var ymax = e.dataset.ymax != null ? +e.dataset.ymax : niceMax(Math.max.apply(null, all));
    var X = function (i) { return P.l + i * (W - P.l - P.r) / (n - 1); };
    var Y = function (v) { return P.t + (1 - (v - ymin) / (ymax - ymin)) * (H - P.t - P.b); };
    var svg = '<svg viewBox="0 0 ' + W + ' ' + H + '"><defs>';
    var gid = 'cg' + (++uid);
    series.forEach(function (s, i) {
      svg += '<linearGradient id="' + gid + i + '" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:var(--c-' + (s.tone || 'brand') + ');stop-opacity:.38"/><stop offset="1" style="stop-color:var(--c-' + (s.tone || 'brand') + ');stop-opacity:0"/></linearGradient>';
    });
    svg += '</defs>';
    for (var k = 0; k <= 4; k++) {
      var v = ymin + (ymax - ymin) * k / 4, y = Y(v);
      svg += '<line class="gridl" x1="' + P.l + '" x2="' + (W - P.r + 24) + '" y1="' + y + '" y2="' + y + '"/><text class="axl" x="' + (P.l - 20) + '" y="' + (y + 8) + '" text-anchor="end">' + fmtNum(v, 0) + unit + '</text>';
    }
    labels.forEach(function (l, i) { if (l) svg += '<text class="axl" x="' + X(i) + '" y="' + (H - 16) + '" text-anchor="middle">' + esc(l) + '</text>'; });
    series.forEach(function (s, i) {
      var pts = s.data.map(function (v, j) { return [X(j), Y(v)]; });
      var line = smooth(pts), last = pts[pts.length - 1];
      var area = line + ' L' + last[0] + ' ' + Y(ymin) + ' L' + pts[0][0] + ' ' + Y(ymin) + ' Z';
      svg += '<g data-tone="' + (s.tone || 'brand') + '" style="--i:' + i + '"><path class="area" d="' + area + '" fill="url(#' + gid + i + ')"/><path class="line" pathLength="1" d="' + line + '"/>' +
        '<circle class="endp" cx="' + last[0] + '" cy="' + last[1] + '" r="10" fill="var(--t)" stroke="var(--card-solid)" stroke-width="4"/>' +
        '<text class="endt" x="' + (last[0] + 24) + '" y="' + (last[1] + 10) + '">' + fmtNum(s.data[s.data.length - 1], 0) + unit + '</text></g>';
    });
    svg += '</svg>';
    var legend = series.length > 1 || series[0].name ? '<div class="legend">' + series.map(function (s) { return '<span data-tone="' + (s.tone || 'brand') + '"><i></i>' + esc(s.name || '') + '</span>'; }).join('') + '</div>' : '';
    e.innerHTML = legend + svg;
  }

  /* Flow diagram: .flow > .node[data-id] + .edge-cfg[data-from][data-to][data-step] */
  function buildFlow(f) {
    var nodes = {};
    $$('.node[data-id]', f).forEach(function (n) { nodes[n.dataset.id] = n; });
    var R = function (n) { return { x: n.offsetLeft, y: n.offsetTop, w: n.offsetWidth, h: n.offsetHeight }; };
    var anchor = function (r, side) { return side === 'r' ? [r.x + r.w, r.y + r.h / 2] : side === 'l' ? [r.x, r.y + r.h / 2] : side === 't' ? [r.x + r.w / 2, r.y] : [r.x + r.w / 2, r.y + r.h]; };
    var NORM = { r: [1, 0], l: [-1, 0], t: [0, -1], b: [0, 1] };
    var OPP = { r: 'l', l: 'r', t: 'b', b: 't' };
    $$('.edge-cfg', f).forEach(function (c) {
      var A = nodes[c.dataset.from], B = nodes[c.dataset.to];
      if (!A || !B) return;
      var a = R(A), b = R(B);
      var dx = b.x + b.w / 2 - (a.x + a.w / 2), dy = b.y + b.h / 2 - (a.y + a.h / 2);
      var horiz = Math.abs(dx) >= Math.abs(dy);
      var fs = c.dataset.fromSide || (horiz ? (dx > 0 ? 'r' : 'l') : (dy > 0 ? 'b' : 't'));
      var ts = c.dataset.toSide || OPP[fs];
      var s = anchor(a, fs), e = anchor(b, ts);
      var dist = Math.hypot(e[0] - s[0], e[1] - s[1]), kk = Math.max(48, dist * .42);
      var c1 = [s[0] + NORM[fs][0] * kk, s[1] + NORM[fs][1] * kk], c2 = [e[0] + NORM[ts][0] * kk, e[1] + NORM[ts][1] * kk];
      var d = 'M' + s[0] + ' ' + s[1] + ' C' + c1[0] + ' ' + c1[1] + ' ' + c2[0] + ' ' + c2[1] + ' ' + e[0] + ' ' + e[1];
      var ang = Math.atan2(-NORM[ts][1], -NORM[ts][0]) * 180 / Math.PI;
      var ns = 'http://www.w3.org/2000/svg', sv = document.createElementNS(ns, 'svg');
      sv.setAttribute('class', 'edge' + (c.dataset.dash != null ? ' dash' : '')); sv.setAttribute('width', f.offsetWidth); sv.setAttribute('height', f.offsetHeight);
      sv.innerHTML = '<path class="ln"' + (c.dataset.dash != null ? '' : ' pathLength="1"') + ' d="' + d + '"/><path class="ah" d="M-14 -11 L0 0 L-14 11" transform="translate(' + e[0] + ',' + e[1] + ') rotate(' + ang + ')"/>';
      if (c.dataset.step != null) sv.setAttribute('data-step', c.dataset.step);
      sv.classList.add('raw');
      if (c.dataset.tone) sv.setAttribute('data-tone', c.dataset.tone);
      f.insertBefore(sv, f.firstChild);
      var mid = [(s[0] + 3 * c1[0] + 3 * c2[0] + e[0]) / 8, (s[1] + 3 * c1[1] + 3 * c2[1] + e[1]) / 8];
      if (c.dataset.label) {
        var lb = el('div', 'elabel raw', esc(c.dataset.label));
        lb.style.left = mid[0] + 'px'; lb.style.top = mid[1] + 'px';
        if (c.dataset.step != null) lb.setAttribute('data-step', c.dataset.step);
        f.appendChild(lb);
      }
      var np = +c.dataset.packets || 0, dur = +c.dataset.packetDur || 2.6;
      for (var i = 0; i < np; i++) {
        var pk = el('div', 'packet raw');
        pk.style.offsetPath = "path('" + d + "')";
        pk.style.setProperty('--dur', dur + 's'); pk.style.setProperty('--pd', (1 + i * dur / np) + 's');
        if (c.dataset.tone) pk.setAttribute('data-tone', c.dataset.tone);
        if (c.dataset.step != null) pk.setAttribute('data-step', c.dataset.step);
        f.appendChild(pk);
      }
      c.parentNode.removeChild(c);
    });
  }

  /* Frame: .frame[data-src][data-url] > .focus[data-step][data-focus="x,y,w,h"][data-label] */
  function buildFrame(f) {
    var focuses = $$(':scope > .focus', f);
    var bar = f.classList.contains('device') ? '' : '<div class="frame-bar"><i></i><i></i><i></i>' + (f.dataset.url ? '<span class="url">' + esc(f.dataset.url) + '</span>' : '') + '</div>';
    var wrap = el('div', null, bar + '<div class="frame-view"><div class="frame-layer"><img alt="" src="' + esc(f.dataset.src || '') + '"></div><div class="ring"><div class="rl"></div></div></div>');
    while (wrap.firstChild) f.appendChild(wrap.firstChild);
    var view = $('.frame-view', f), layer = $('.frame-layer', f), img = $('img', f), ring = $('.ring', f), rl = $('.rl', ring);
    if (f.dataset.ar) view.style.aspectRatio = f.dataset.ar;
    function size() { if (!f.dataset.ar && img.naturalWidth) view.style.aspectRatio = img.naturalWidth / img.naturalHeight; update(); }
    img.addEventListener('load', size);
    function update() {
      var cur = null;
      focuses.forEach(function (fo) { if (fo.classList.contains('is-in')) cur = fo; });
      var r = cur && cur.dataset.focus ? cur.dataset.focus.split(',').map(Number) : [0, 0, 1, 1];
      var W = view.offsetWidth, H = view.offsetHeight;
      if (!W) return;
      var rg = cur && (cur.dataset.ring != null || cur.dataset.label);
      var m = rg ? 1.2 : 1.04;
      var s = Math.max(1, Math.min(1 / (r[2] * m), 1 / (r[3] * m), +f.dataset.maxZoom || 3.2));
      if (r[2] >= 1 && r[3] >= 1) s = 1;
      var tx = clamp(W / 2 - s * (r[0] + r[2] / 2) * W, W - s * W, 0), ty = clamp(H / 2 - s * (r[1] + r[3] / 2) * H, H - s * H, 0);
      layer.style.transform = 'translate3d(' + tx + 'px,' + ty + 'px,0) scale(' + s + ')';
      if (rg) {
        var pd = 12, rx = tx + s * r[0] * W - pd, ry = ty + s * r[1] * H - pd, rw = s * r[2] * W + pd * 2, rh = s * r[3] * H + pd * 2;
        ring.style.left = rx + 'px'; ring.style.top = ry + 'px'; ring.style.width = rw + 'px'; ring.style.height = rh + 'px';
        rl.textContent = cur.dataset.label || '';
        rl.style.display = cur.dataset.label ? '' : 'none';
        var below = H - (ry + rh) >= 100, above = ry >= 100;
        rl.classList.toggle('up', !below && above);
        rl.classList.toggle('in', !below && !above);
        rl.classList.toggle('right', rx + rw / 2 > W / 2 && rw < W * .8);
        ring.classList.add('on');
      } else ring.classList.remove('on');
    }
    if (img.complete && img.naturalWidth) size();
    return { update: update };
  }

  /* ---------- Boot ---------- */
  function boot() {
    var root = $('.deck');
    if (!root) return;
    var d = window.deck = new Deck(root);
    var errs = [];
    window.addEventListener('error', function (e) { errs.push(e.message); document.documentElement.setAttribute('data-errors', errs.join(' | ')); });
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { d.slides[d.cur] && d.applySteps(d.slides[d.cur], d.step); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
