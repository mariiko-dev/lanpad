/* Remote touchpad — React (UMD) + htm, no build step. */
(function () {
  "use strict";
  var React = window.React;
  var ReactDOM = window.ReactDOM;
  var html = window.htm.bind(React.createElement);
  var useState = React.useState;
  var useRef = React.useRef;
  var useEffect = React.useEffect;
  var useCallback = React.useCallback;

  var TOKEN = new URLSearchParams(location.search).get("t") || "";
  var Q = "t=" + encodeURIComponent(TOKEN);

  function postFallback(payload) {
    fetch("/e?" + Q, { method: "POST", body: payload, keepalive: true }).catch(function () {});
  }

  /* ---------------- transport: WebSocket, POST fallback ------------- */
  function useTransport() {
    var _s = useState(false), connected = _s[0], setConnected = _s[1];
    var wsRef = useRef(null);
    var queueRef = useRef([]);

    useEffect(function () {
      var stopped = false, hb, raf;
      function connect() {
        if (stopped) return;
        var proto = location.protocol === "https:" ? "wss" : "ws";
        var ws = new WebSocket(proto + "://" + location.host + "/ws?" + Q);
        wsRef.current = ws;
        ws.onopen = function () { setConnected(true); };
        ws.onclose = function () {
          setConnected(false);
          wsRef.current = null;
          if (!stopped) setTimeout(connect, 1000);
        };
        ws.onerror = function () { try { ws.close(); } catch (e) {} };
      }
      connect();
      hb = setInterval(function () {
        var ws = wsRef.current;
        if (ws && ws.readyState === 1) { try { ws.send("[]"); } catch (e) {} }
      }, 25000);

      function flush() {
        var q = queueRef.current;
        if (q.length) {
          var payload = JSON.stringify(q);
          queueRef.current = [];
          var ws = wsRef.current;
          if (ws && ws.readyState === 1) {
            try { ws.send(payload); } catch (e) { postFallback(payload); }
          } else {
            postFallback(payload);
          }
        }
        raf = requestAnimationFrame(flush);
      }
      raf = requestAnimationFrame(flush);

      return function () {
        stopped = true;
        clearInterval(hb);
        cancelAnimationFrame(raf);
        var ws = wsRef.current;
        if (ws) { try { ws.close(); } catch (e) {} }
      };
    }, []);

    var send = useCallback(function (ev) {
      var q = queueRef.current;
      q.push(ev);
      if (q.length > 600) q.splice(0, q.length - 600);
    }, []);

    return { send: send, connected: connected };
  }

  /* ---------------- press-and-hold button ------------------------- */
  function HoldButton(props) {
    var onFire = props.onFire, repeat = props.repeat;
    var timer = useRef(null);
    useEffect(function () {
      return function () { if (timer.current) clearInterval(timer.current); };
    }, []);
    function start(e) {
      e.preventDefault();
      onFire();
      if (repeat) timer.current = setInterval(onFire, 110);
    }
    function stop() {
      if (timer.current) { clearInterval(timer.current); timer.current = null; }
    }
    return html`<button
      class=${props.class || ""}
      aria-label=${props["aria-label"]}
      onPointerDown=${start}
      onPointerUp=${stop}
      onPointerCancel=${stop}
      onPointerLeave=${stop}
    >${props.children}</button>`;
  }

  /* ---------------- trackpad ------------------------------------- */
  function Trackpad(props) {
    var send = props.send;
    var elRef = useRef(null);
    var glowRef = useRef(null);

    useEffect(function () {
      var el = elRef.current, glow = glowRef.current;
      var pts = new Map();
      var startT = 0, moved = 0, twoFinger = false, scrollAcc = 0;
      var dragArmed = false, dragging = false, lastTapT = 0;

      function opts() {
        return {
          accel: parseFloat(localStorage.getItem("rt_accel") || "1.1"),
          natural: localStorage.getItem("rt_natural") === "1",
        };
      }
      function setGlow(x, y, on) {
        var r = el.getBoundingClientRect();
        glow.style.transform = "translate(" + (x - r.left) + "px," + (y - r.top) + "px)";
        glow.style.opacity = on ? "1" : "0";
      }
      function bloom() {
        try {
          glow.animate(
            [{ filter: "blur(6px) brightness(1.9)" }, { filter: "blur(6px) brightness(1)" }],
            { duration: 300, easing: "ease-out" }
          );
        } catch (e) {}
      }

      function onStart(e) {
        e.preventDefault();
        el.classList.add("touched");
        for (var i = 0; i < e.changedTouches.length; i++) {
          var t = e.changedTouches[i];
          pts.set(t.identifier, { x: t.clientX, y: t.clientY });
        }
        var t0 = e.changedTouches[0];
        if (t0) setGlow(t0.clientX, t0.clientY, true);
        if (pts.size === 1) {
          startT = performance.now();
          moved = 0;
          twoFinger = false;
          if (performance.now() - lastTapT < 300) dragArmed = true;
        }
      }
      function onMove(e) {
        e.preventDefault();
        var arr = Array.prototype.slice.call(e.touches);
        var o = opts();
        var lead = arr[0];
        if (lead) setGlow(lead.clientX, lead.clientY, true);

        if (pts.size === 1 && arr.length === 1) {
          var t = arr[0], p = pts.get(t.identifier);
          if (!p) return;
          var dx = t.clientX - p.x, dy = t.clientY - p.y;
          p.x = t.clientX; p.y = t.clientY;
          var dist = Math.hypot(dx, dy);
          moved += dist;
          var f = o.accel * (1 + Math.min(dist * 0.06, 4));
          if (dragArmed && !dragging) { send(["bd", "l"]); dragging = true; el.classList.add("dragging"); }
          send(["m", Math.round(dx * f), Math.round(dy * f)]);
        } else if (arr.length >= 2) {
          twoFinger = true;
          var sy = 0, c = 0;
          for (var i = 0; i < arr.length; i++) {
            var tt = arr[i], pp = pts.get(tt.identifier);
            if (pp) { sy += tt.clientY - pp.y; pp.x = tt.clientX; pp.y = tt.clientY; c++; }
          }
          if (c) {
            var dir = o.natural ? 1 : -1;
            scrollAcc += (sy / c) * 0.09 * dir;
            var n = Math.trunc(scrollAcc);
            if (n) { scrollAcc -= n; send(["w", n]); }
            moved += Math.abs(sy);
          }
        }
      }
      function onEnd(e) {
        e.preventDefault();
        var p0 = e.changedTouches[0];
        for (var i = 0; i < e.changedTouches.length; i++) {
          pts.delete(e.changedTouches[i].identifier);
        }
        var dt = performance.now() - startT;
        if (dragging && pts.size === 0) {
          send(["bu", "l"]); dragging = false; el.classList.remove("dragging"); dragArmed = false;
        } else if (pts.size === 0) {
          if (twoFinger) {
            if (dt < 260 && moved < 16) send(["click", "r"]);
          } else if (dt < 240 && moved < 12) {
            send(["click", "l"]);
            lastTapT = performance.now();
            bloom();
          }
          dragArmed = false; twoFinger = false; moved = 0;
        }
        if (pts.size === 0 && p0) setGlow(p0.clientX, p0.clientY, false);
      }

      el.addEventListener("touchstart", onStart, { passive: false });
      el.addEventListener("touchmove", onMove, { passive: false });
      el.addEventListener("touchend", onEnd, { passive: false });
      el.addEventListener("touchcancel", onEnd, { passive: false });
      return function () {
        el.removeEventListener("touchstart", onStart);
        el.removeEventListener("touchmove", onMove);
        el.removeEventListener("touchend", onEnd);
        el.removeEventListener("touchcancel", onEnd);
      };
    }, [send]);

    return html`
      <div class="pad rise" style=${{ "--i": 2 }} ref=${elRef}>
        <div class="pad-breath"></div>
        <div class="pad-glow" ref=${glowRef}></div>
        <span class="pad-hint">коснись и веди</span>
      </div>`;
  }

  /* ---------------- click row ---------------------------------- */
  function ClickRow(props) {
    var send = props.send;
    return html`
      <div class="clicks rise" style=${{ "--i": 3 }}>
        <${HoldButton} class="wide" onFire=${function () { send(["click", "l"]); }}>Клик<//>
        <${HoldButton} onFire=${function () { send(["click", "r"]); }}>Правый<//>
        <${HoldButton} onFire=${function () { send(["click", "m"]); }} aria-label="Средняя кнопка">···<//>
      </div>`;
  }

  /* ---------------- volume ------------------------------------ */
  function VolumeRow(props) {
    var send = props.send;
    var _s = useState(null), st = _s[0], setSt = _s[1];

    var poll = useCallback(function () {
      fetch("/vol?" + Q).then(function (r) { return r.ok ? r.json() : null; })
        .then(function (j) { if (j) setSt(j); }).catch(function () {});
    }, []);

    useEffect(function () {
      poll();
      var i = setInterval(poll, 4000);
      return function () { clearInterval(i); };
    }, [poll]);

    function after() { setTimeout(poll, 130); }
    var pct = st && st.vol != null ? st.vol : null;
    var muted = !!(st && st.muted);

    return html`
      <div class=${"vol rise" + (muted ? " muted" : "")} style=${{ "--i": 4 }}>
        <${HoldButton} class="vol-btn" aria-label="Без звука"
          onFire=${function () { send(["volmute"]); after(); }}>${muted ? "🔇" : "🔊"}<//>
        <${HoldButton} class="vol-btn" repeat aria-label="Тише"
          onFire=${function () { send(["vol", -4]); after(); }}>−<//>
        <div class="vol-track" role="progressbar" aria-valuenow=${pct == null ? 0 : pct}>
          <div class="vol-fill" style=${{ width: (pct == null ? 0 : pct) + "%" }}></div>
          <span class="vol-pct">${pct == null ? "" : pct + "%"}</span>
        </div>
        <${HoldButton} class="vol-btn" repeat aria-label="Громче"
          onFire=${function () { send(["vol", 4]); after(); }}>+<//>
      </div>`;
  }

  /* ---------------- quick keys ------------------------------- */
  var KEYS = [
    { l: "Esc", tap: "escape" },
    { l: "Tab", tap: "tab" },
    { l: "↵", tap: "enter" },
    { l: "⌫", tap: "backspace" },
    { l: "↑", tap: "up", rep: true },
    { l: "↓", tap: "down", rep: true },
    { l: "←", tap: "left", rep: true },
    { l: "→", tap: "right", rep: true },
    { l: "⌘", tap: "super", label: "Активности" },
    { l: "Alt+Tab", combo: ["alt", "tab"] },
    { l: "Ctrl+C", combo: ["ctrl", "c"] },
    { l: "Ctrl+V", combo: ["ctrl", "v"] },
  ];
  function QuickKeys(props) {
    var send = props.send;
    return html`
      <div class="keys rise" style=${{ "--i": 5 }}>
        ${KEYS.map(function (k, idx) {
          return html`<${HoldButton} key=${idx} repeat=${!!k.rep} aria-label=${k.label || k.l}
            onFire=${function () {
              if (k.combo) send(["combo", k.combo]);
              else send(["tap", k.tap]);
            }}>${k.l}<//>`;
        })}
        <button class="kbkey" aria-label="Клавиатура"
          onClick=${props.onKeyboard}>⌨</button>
      </div>`;
  }

  /* ---------------- keyboard sheet --------------------------- */
  function padField(el) {
    if (el.value.length < 2) el.value = "  ";
    try { el.setSelectionRange(el.value.length, el.value.length); } catch (e) {}
  }

  function KeyboardSheet(props) {
    var open = props.open, onClose = props.onClose, send = props.send;
    var inputRef = useRef(null);
    var sheetRef = useRef(null);
    var _m = useState({ ctrl: false, alt: false, shift: false, super: false });
    var mods = _m[0], setMods = _m[1];
    var modsRef = useRef(mods);
    modsRef.current = mods;
    var _p = useState(""), paste = _p[0], setPaste = _p[1];

    var activeMods = function () {
      var m = modsRef.current;
      return Object.keys(m).filter(function (k) { return m[k]; });
    };
    var clearMods = function () { setMods({ ctrl: false, alt: false, shift: false, super: false }); };

    /* native listeners on the hidden input (reliable on iOS) */
    useEffect(function () {
      var el = inputRef.current;
      if (!el) return;
      function onBeforeInput(e) {
        var it = e.inputType, data = e.data;
        if (it === "insertText" && data) {
          var am = activeMods();
          if (am.length && data.length === 1) { send(["combo", am.concat([data])]); clearMods(); }
          else send(["type", data]);
        } else if (it === "insertLineBreak" || it === "insertParagraph") {
          send(["tap", "enter"]);
        } else if (it === "deleteContentBackward") {
          send(["tap", "backspace"]);
        } else if (it === "deleteWordBackward") {
          send(["combo", ["ctrl", "backspace"]]);
        } else if (it === "insertFromPaste" && data) {
          send(["paste", data]);
        }
        e.preventDefault();
      }
      function onKeyDown(e) {
        var map = {
          Escape: "escape", Tab: "tab", ArrowUp: "up", ArrowDown: "down",
          ArrowLeft: "left", ArrowRight: "right", Backspace: "backspace",
          Enter: "enter", Delete: "delete", Home: "home", End: "end",
          PageUp: "pageup", PageDown: "pagedown",
        };
        if (map[e.key]) { send(["tap", map[e.key]]); e.preventDefault(); return; }
        if (e.key.length === 1 && (e.ctrlKey || e.metaKey || e.altKey)) {
          var am = [];
          if (e.ctrlKey) am.push("ctrl");
          if (e.altKey) am.push("alt");
          if (e.metaKey) am.push("super");
          if (e.shiftKey) am.push("shift");
          send(["combo", am.concat([e.key.toLowerCase()])]);
          e.preventDefault();
        }
      }
      function onInput() { padField(el); }
      el.addEventListener("beforeinput", onBeforeInput);
      el.addEventListener("keydown", onKeyDown);
      el.addEventListener("input", onInput);
      return function () {
        el.removeEventListener("beforeinput", onBeforeInput);
        el.removeEventListener("keydown", onKeyDown);
        el.removeEventListener("input", onInput);
      };
    }, [send]);

    /* focus + lift sheet above the on-screen keyboard */
    useEffect(function () {
      var sheet = sheetRef.current;
      if (open) {
        padField(inputRef.current);
        inputRef.current.focus();
      } else {
        sheet.style.setProperty("--kb-h", "0px");
        clearMods();
        return;
      }
      var vv = window.visualViewport;
      if (!vv) return;
      function onResize() {
        var h = Math.max(0, window.innerHeight - vv.height - vv.offsetTop);
        sheet.style.setProperty("--kb-h", h + "px");
      }
      vv.addEventListener("resize", onResize);
      vv.addEventListener("scroll", onResize);
      onResize();
      return function () {
        vv.removeEventListener("resize", onResize);
        vv.removeEventListener("scroll", onResize);
      };
    }, [open]);

    function toggleMod(name) {
      setMods(function (m) {
        var next = Object.assign({}, m);
        next[name] = !m[name];
        return next;
      });
      inputRef.current.focus();
    }

    var MODS = [["ctrl", "Ctrl"], ["alt", "Alt"], ["shift", "Shift"], ["super", "⌘"]];

    return html`
      <div class=${"kb" + (open ? " open" : "")} ref=${sheetRef}>
        <div class="kb-grip"></div>
        <div class="kb-mods">
          ${MODS.map(function (pair) {
            return html`<button key=${pair[0]}
              class=${"kb-mod" + (mods[pair[0]] ? " on" : "")}
              onPointerDown=${function (e) { e.preventDefault(); toggleMod(pair[0]); }}
            >${pair[1]}</button>`;
          })}
        </div>
        <div class="kb-hint">
          Печатай — буквы идут на ноут. Модификатор + клавиша — сочетание.
          Для кириллицы и длинного текста — поле ниже.
        </div>
        <input class="kb-input" ref=${inputRef}
          autocapitalize="none" autocomplete="off" autocorrect="off"
          spellcheck="false" inputmode="text" aria-label="Ввод с клавиатуры" />
        <textarea class="kb-paste" value=${paste}
          onInput=${function (e) { setPaste(e.target.value); }}
          placeholder="Текст для вставки — кириллицу тоже"></textarea>
        <div class="kb-send">
          <button class="primary" onClick=${function () { if (paste) send(["paste", paste]); }}>
            Вставить
          </button>
          <button onClick=${function () { if (paste) send(["tpaste", paste]); }}>
            В терминал
          </button>
        </div>
        <button class="kb-done" onClick=${onClose}>Готово</button>
      </div>`;
  }

  /* ---------------- settings ------------------------------- */
  function Settings(props) {
    var _a = useState(parseFloat(localStorage.getItem("rt_accel") || "1.1"));
    var accel = _a[0], setAccel = _a[1];
    var _n = useState(localStorage.getItem("rt_natural") === "1");
    var natural = _n[0], setNatural = _n[1];

    function changeAccel(e) {
      var v = parseFloat(e.target.value);
      setAccel(v);
      localStorage.setItem("rt_accel", String(v));
    }
    function toggleNatural() {
      var v = !natural;
      setNatural(v);
      localStorage.setItem("rt_natural", v ? "1" : "0");
    }

    return html`
      <div class="settings">
        <label class="field">
          Чувствительность
          <input type="range" min="0.5" max="2.4" step="0.1"
            value=${accel} onInput=${changeAccel} />
        </label>
        <div class="field">
          Естественная прокрутка
          <button class=${"toggle" + (natural ? " on" : "")}
            role="switch" aria-checked=${natural}
            onClick=${toggleNatural} aria-label="Естественная прокрутка"></button>
        </div>
      </div>`;
  }

  /* ---------------- app ---------------------------------- */
  function App() {
    var t = useTransport();
    var _k = useState(false), kb = _k[0], setKb = _k[1];
    var _s = useState(false), settings = _s[0], setSettings = _s[1];

    useEffect(function () {
      var h = location.hash;
      if (h === "#kb") setKb(true);
      else if (h === "#settings") setSettings(true);
    }, []);

    return html`
      <div class="shell">
        <div class="statusbar rise" style=${{ "--i": 0 }}>
          <span class=${"dot" + (t.connected ? " ok" : "")}></span>
          <span class="status-label" aria-live="polite">
            ${t.connected ? "на связи" : "ищу ноут…"}
          </span>
          <span class="spacer"></span>
          <button class=${"icon-btn" + (settings ? " on" : "")}
            aria-label="Настройки"
            onClick=${function () { setSettings(function (s) { return !s; }); }}>⚙</button>
        </div>

        ${settings && html`<div class="rise" style=${{ "--i": 1 }}><${Settings} /></div>`}

        <${Trackpad} send=${t.send} />
        <${ClickRow} send=${t.send} />
        <${VolumeRow} send=${t.send} />
        <${QuickKeys} send=${t.send} onKeyboard=${function () { setKb(true); }} />

        <${KeyboardSheet} open=${kb} onClose=${function () { setKb(false); }} send=${t.send} />
      </div>`;
  }

  ReactDOM.createRoot(document.getElementById("root")).render(html`<${App} />`);

  /* prevent pinch / double-tap zoom bleeding through */
  document.addEventListener("gesturestart", function (e) { e.preventDefault(); });
  document.addEventListener("dblclick", function (e) { e.preventDefault(); });

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js").catch(function () {});
    });
  }
})();
