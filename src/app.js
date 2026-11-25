/* The Guybile — reader behaviour. Plain JS, no dependencies. */
(function () {
  "use strict";
  var d = document, root = d.documentElement, $ = function (s) { return d.getElementById(s); };
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  };
  var main = d.querySelector("main"), page = main ? main.dataset.page : "";

  /* ---------- Panels ---------- */
  var scrim = $("scrim"), toc = $("toc"), sheet = $("settings"), openPanel = null, lastFocus = null;
  function open(el, btn) {
    close();
    lastFocus = btn;
    openPanel = el;
    el.classList.add("on"); el.setAttribute("aria-hidden", "false");
    scrim.classList.add("on");
    if (btn) btn.setAttribute("aria-expanded", "true");
    var cur = el.querySelector("[aria-current]");
    if (cur) cur.scrollIntoView({ block: "center" });
    var f = el.querySelector("[data-close]"); if (f) f.focus({ preventScroll: true });
  }
  function close() {
    if (!openPanel) return;
    openPanel.classList.remove("on"); openPanel.setAttribute("aria-hidden", "true");
    scrim.classList.remove("on");
    d.querySelectorAll("[aria-expanded=true]").forEach(function (b) { b.setAttribute("aria-expanded", "false"); });
    openPanel = null;
    if (lastFocus) lastFocus.focus({ preventScroll: true });
  }
  $("open-toc").addEventListener("click", function () { open(toc, this); });
  $("open-set").addEventListener("click", function () { open(sheet, this); });
  scrim.addEventListener("click", close);
  d.querySelectorAll("[data-close]").forEach(function (b) { b.addEventListener("click", close); });
  d.addEventListener("keydown", function (e) {
    if (e.key === "Escape") { close(); deselect(); }
    if (openPanel || /INPUT|TEXTAREA/.test((e.target || {}).tagName)) return;
    var pager = d.querySelector(".pager");
    if (pager && e.key === "ArrowLeft" && !e.metaKey && !e.altKey) { var p = pager.querySelector(".prev"); if (p) location.href = p.href; }
    if (pager && e.key === "ArrowRight" && !e.metaKey && !e.altKey) { var n = pager.querySelector(".next"); if (n) location.href = n.href; }
    if (e.key === "/" ) { e.preventDefault(); location.href = "search.html"; }
  });

  /* ---------- Settings ---------- */
  function syncSettings() {
    var t = root.dataset.theme || "paper", s = root.dataset.size || "m";
    d.querySelectorAll("[data-theme-set]").forEach(function (b) { b.setAttribute("aria-pressed", b.dataset.themeSet === t); });
    d.querySelectorAll("[data-size-set]").forEach(function (b) { b.setAttribute("aria-pressed", b.dataset.sizeSet === s); });
    var meta = d.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = t === "night" ? "#15120f" : (page === "index" ? "#3a1f17" : (t === "light" ? "#ffffff" : "#f5eedf"));
  }
  d.querySelectorAll("[data-theme-set]").forEach(function (b) {
    b.addEventListener("click", function () { root.dataset.theme = b.dataset.themeSet; store.set("g-theme", b.dataset.themeSet); syncSettings(); });
  });
  d.querySelectorAll("[data-size-set]").forEach(function (b) {
    b.addEventListener("click", function () {
      var anchor = topVerse();
      root.dataset.size = b.dataset.sizeSet; store.set("g-size", b.dataset.sizeSet); syncSettings();
      if (anchor) anchor.scrollIntoView({ block: "start" });
    });
  });
  syncSettings();

  /* ---------- Bar hide-on-scroll + progress + remember place ---------- */
  var bar = $("bar"), prog = $("progress"), lastY = window.scrollY, ticking = false;
  function topVerse() {
    var vs = d.querySelectorAll(".v"), barH = bar.offsetHeight;
    for (var i = 0; i < vs.length; i++) if (vs[i].getBoundingClientRect().bottom > barH + 8) return vs[i];
    return null;
  }
  var saveTimer;
  function onScroll() {
    var y = window.scrollY, max = d.documentElement.scrollHeight - innerHeight;
    if (prog) prog.style.transform = "scaleX(" + (max > 0 ? Math.min(1, y / max) : 0) + ")";
    if (!openPanel) bar.classList.toggle("hide", y > lastY && y > 160);
    lastY = y; ticking = false;
    if (main && main.dataset.label) {
      clearTimeout(saveTimer);
      saveTimer = setTimeout(function () {
        var v = topVerse();
        store.set("g-last", JSON.stringify({ p: page, l: main.dataset.label, t: main.dataset.title, v: v && y > 200 ? v.id : "" }));
      }, 400);
    }
  }
  addEventListener("scroll", function () { if (!ticking) { ticking = true; requestAnimationFrame(onScroll); } }, { passive: true });
  onScroll();

  /* ---------- Verse select / copy / share ---------- */
  var vact = $("vact"), toast = $("toast"), selected = null, toastT;
  function say(msg) { toast.textContent = msg; toast.classList.add("on"); clearTimeout(toastT); toastT = setTimeout(function () { toast.classList.remove("on"); }, 1800); }
  function deselect() { if (selected) selected.classList.remove("sel"); selected = null; vact.classList.remove("on"); }
  function verseText(v) {
    var c = v.cloneNode(true);
    c.querySelectorAll(".num, .by").forEach(function (n) { n.remove(); });
    var t = c.textContent.trim();
    return (/^["“]/.test(t) ? t : "“" + t + "”") + " — Guybile " + v.dataset.ref;
  }
  function verseUrl(v) { return new URL("v/" + v.dataset.ref.replace(":", "-") + ".html", location.href).href; }
  d.addEventListener("click", function (e) {
    var v = e.target.closest && e.target.closest(".v");
    if (e.target.closest && (e.target.closest("a.ref") || e.target.closest(".vact"))) return;
    if (v) {
      if (e.target.closest(".num")) e.preventDefault();
      if (String(getSelection()).length > 0) return;
      if (selected === v) { deselect(); return; }
      deselect(); selected = v; v.classList.add("sel"); vact.classList.add("on");
      vact.querySelector("[data-act=save] span").textContent = isSaved(v.dataset.ref) ? "Saved" : "Save";
      history.replaceState(null, "", "#" + v.id);
    } else if (selected) deselect();
  });
  vact.addEventListener("click", function (e) {
    var b = e.target.closest("button"); if (!b || !selected) return;
    var text = verseText(selected), url = verseUrl(selected), ref = selected.dataset.ref;
    if (b.dataset.act === "save") {
      var on = toggleSaved(ref);
      selected.classList.toggle("saved", on);
      say(on ? "Saved to thy verses" : "Removed from saved");
      deselect(); return;
    }
    if (b.dataset.act === "image" || (b.dataset.act === "share" && canShareFiles())) {
      var c = selected.cloneNode(true);
      c.querySelectorAll(".num, .by").forEach(function (n) { n.remove(); });
      shareImage(c.textContent.trim(), ref, main.dataset.title || "", url);
      deselect(); return;
    }
    if (b.dataset.act === "share" && navigator.share) {
      navigator.share({ title: "Guybile " + selected.dataset.ref, text: text, url: url }).catch(function () {});
    } else {
      var payload = text + "\n" + url;
      (navigator.clipboard ? navigator.clipboard.writeText(payload) : Promise.reject()).then(
        function () { say(b.dataset.act === "share" ? "Link copied" : "Verse copied"); },
        function () { prompt("Copy this verse:", payload); });
    }
    deselect();
  });

  /* ---------- Saved verses (this device only) ---------- */
  function savedList() { try { return JSON.parse(store.get("g-saved") || "[]"); } catch (e) { return []; } }
  function isSaved(ref) { return savedList().indexOf(ref) !== -1; }
  function toggleSaved(ref) {
    var l = savedList(), i = l.indexOf(ref);
    if (i === -1) l.unshift(ref); else l.splice(i, 1);
    store.set("g-saved", JSON.stringify(l));
    return i === -1;
  }
  savedList().forEach(function (ref) {
    var el = $("v" + ref.replace(":", "-")); if (el) el.classList.add("saved");
  });

  /* ---------- Verse image (drawn on the reader's device) ---------- */
  var SERIF = '"Iowan Old Style", Palatino, "Palatino Linotype", "Book Antiqua", Georgia, serif';
  var SANS = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';
  function wrap(ctx, text, maxW) {
    var words = text.split(/\s+/), lines = [], line = "";
    words.forEach(function (w) {
      var t = line ? line + " " + w : w;
      if (ctx.measureText(t).width > maxW && line) { lines.push(line); line = w; } else line = t;
    });
    if (line) lines.push(line);
    return lines;
  }
  function drawVerse(text, ref, chapter) {
    var W = 1080, H = 1350, c = d.createElement("canvas"); c.width = W; c.height = H;
    var x = c.getContext("2d");
    var g = x.createRadialGradient(W / 2, 0, 50, W / 2, H * 0.3, H);
    g.addColorStop(0, "#4d2b1f"); g.addColorStop(1, "#1c0e09");
    x.fillStyle = g; x.fillRect(0, 0, W, H);
    x.strokeStyle = "rgba(226,194,125,.5)"; x.lineWidth = 2.5; x.strokeRect(40, 40, W - 80, H - 80);
    x.strokeStyle = "rgba(226,194,125,.22)"; x.lineWidth = 2; x.strokeRect(58, 58, W - 116, H - 116);
    // seal
    x.strokeStyle = "#e2c27d"; x.lineWidth = 2.5;
    x.beginPath(); x.arc(W / 2, 170, 44, 0, Math.PI * 2); x.stroke();
    x.fillStyle = "#e2c27d"; x.textAlign = "center"; x.textBaseline = "middle";
    x.font = "600 50px " + SERIF; x.fillText("G", W / 2, 173);
    x.font = "700 24px " + SANS; x.fillStyle = "rgba(226,194,125,.8)";
    if ("letterSpacing" in x) x.letterSpacing = "8px";
    x.fillText("THE GUYBILE", W / 2, 258);
    if ("letterSpacing" in x) x.letterSpacing = "0px";
    // verse: largest size that fits
    var quote = /^["“]/.test(text) ? text : "“" + text + "”", size = 64, lines, lh, maxH = 640;
    do {
      x.font = "500 " + size + "px " + SERIF; lines = wrap(x, quote, W - 220); lh = size * 1.38; size -= 2;
    } while (lines.length * lh > maxH && size > 28);
    x.fillStyle = "#f3e6c8"; x.textBaseline = "alphabetic";
    var top = 330 + (maxH - lines.length * lh) / 2 + lh * 0.8;
    lines.forEach(function (l, i) { x.fillText(l, W / 2, top + i * lh); });
    // ref
    x.fillStyle = "#e2c27d"; x.font = "600 40px " + SERIF; x.fillText("Guybile " + ref, W / 2, 1080);
    if (chapter) { x.font = "italic 30px " + SERIF; x.fillStyle = "rgba(234,217,182,.8)"; x.fillText(chapter, W / 2, 1128); }
    x.font = "700 24px " + SANS; x.fillStyle = "rgba(226,194,125,.7)";
    if ("letterSpacing" in x) x.letterSpacing = "6px";
    x.fillText("THEGUYBILE.COM", W / 2, H - 110);
    return c;
  }
  function vlink(v) { return new URL("v/" + v[0].replace(":", "-") + ".html", location.href).href; }
  function canShareFiles() {
    try { return !!(navigator.canShare && typeof File === "function" &&
      navigator.canShare({ files: [new File([""], "t.png", { type: "image/png" })] })); } catch (e) { return false; }
  }
  function shareImage(text, ref, chapter, link) {
    link = link || location.origin;
    var c = drawVerse(text, ref, chapter), name = "guybile-" + ref.replace(":", "-") + ".png";
    c.toBlob(function (blob) {
      var file = typeof File === "function" ? new File([blob], name, { type: "image/png" }) : null;
      if (file && navigator.canShare && navigator.canShare({ files: [file] })) {
        navigator.share({ files: [file], title: "Guybile " + ref, text: "Guybile " + ref + " — " + link }).catch(function () {});
      } else {
        var a = d.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name;
        d.body.appendChild(a); a.click(); a.remove();
        setTimeout(function () { URL.revokeObjectURL(a.href); }, 4000);
        say("Image downloaded");
      }
    }, "image/png");
  }

  /* ---------- Chapter tools: share page, listen ---------- */
  var sharePage = $("share-page");
  if (sharePage) sharePage.addEventListener("click", function () {
    var url = location.href.split("#")[0], title = d.title;
    if (navigator.share) navigator.share({ title: title, url: url }).catch(function () {});
    else (navigator.clipboard ? navigator.clipboard.writeText(url) : Promise.reject()).then(
      function () { say("Link copied"); }, function () { prompt("Copy this link:", url); });
  });
  var listen = $("listen"), synth = window.speechSynthesis, reading = false;
  if (listen && synth && window.SpeechSynthesisUtterance) {
    listen.hidden = false;
    var label = listen.querySelector("span");
    var stop = function () { reading = false; synth.cancel(); label.textContent = "Listen"; d.querySelectorAll(".reading").forEach(function (n) { n.classList.remove("reading"); }); };
    var voice = function () {
      var vs = synth.getVoices().filter(function (v) { return /^en/i.test(v.lang); });
      return vs.find(function (v) { return /Daniel|Arthur|Aaron|Google UK English Male|Male/i.test(v.name); }) || vs[0] || null;
    };
    listen.addEventListener("click", function () {
      if (reading) { stop(); return; }
      var items = Array.prototype.slice.call(d.querySelectorAll(".content > p, .content > h3, .content .oath p, .content li"));
      var start = topVerse(); var i = start ? Math.max(0, items.indexOf(start)) : 0;
      reading = true; label.textContent = "Stop";
      var next = function () {
        if (!reading || i >= items.length) { stop(); return; }
        var el = items[i++], c = el.cloneNode(true);
        c.querySelectorAll(".num").forEach(function (n) { n.textContent = el.dataset.ref ? "Verse " + el.dataset.ref.split(":")[1] + ". " : ""; });
        var u = new SpeechSynthesisUtterance(c.textContent.trim());
        var vv = voice(); if (vv) u.voice = vv; u.rate = 0.98;
        d.querySelectorAll(".reading").forEach(function (n) { n.classList.remove("reading"); });
        el.classList.add("reading");
        var r = el.getBoundingClientRect(); if (r.top < 60 || r.bottom > innerHeight - 40) el.scrollIntoView({ block: "center", behavior: "smooth" });
        u.onend = next; u.onerror = next;
        synth.speak(u);
      };
      synth.cancel(); next();
    });
    addEventListener("pagehide", stop);
  }

  /* ---------- Verse data (lazy) ---------- */
  var versesP;
  function verses() { return versesP || (versesP = fetch("verses.json").then(function (r) { return r.json(); })); }
  function escH(s) { return s.replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  /* ---------- Home ---------- */
  if (page === "index") {
    try {
      var last = JSON.parse(store.get("g-last") || "null"), c = $("continue");
      if (last && last.p) {
        c.href = last.p + ".html" + (last.v ? "#" + last.v : "");
        c.textContent = "Continue: " + last.l;
        c.hidden = false; $("browse").hidden = true;
      }
    } catch (e) {}
    var shown = null;
    var show = function (v, lbl) {
      shown = v;
      $("daily-text").textContent = v[3];
      var a = $("daily-ref"); a.textContent = "Guybile " + v[0] + " · " + v[2] + " →";
      a.href = v[1] + ".html#v" + v[0].replace(":", "-");
      $("daily").querySelector(".lbl").textContent = lbl;
    };
    verses().then(function (all) {
      var day = Math.floor((Date.now() - new Date().getTimezoneOffset() * 6e4) / 864e5);
      show(all[(day * 7919) % all.length], "Verse of the day");
      $("daily-random").addEventListener("click", function () {
        var v; do { v = all[Math.floor(Math.random() * all.length)]; } while (v === shown && all.length > 1);
        show(v, "The Guybile has spoken");
      });
    }).catch(function () { $("daily").hidden = true; });
    $("daily-image").addEventListener("click", function () { if (shown) shareImage(shown[3], shown[0], shown[2], vlink(shown)); });
  }

  /* ---------- Saved page ---------- */
  if (page === "saved") {
    var renderSaved = function () {
      var refs = savedList(), ul = $("saved-list");
      $("saved-empty").hidden = refs.length > 0;
      $("saved-count").textContent = refs.length ? refs.length + (refs.length === 1 ? " verse" : " verses") + " saved on this device" : "";
      if (!refs.length) { ul.innerHTML = ""; return; }
      verses().then(function (all) {
        var by = {}; all.forEach(function (v) { by[v[0]] = v; });
        ul.innerHTML = refs.filter(function (r) { return by[r]; }).map(function (r) {
          var v = by[r];
          return '<li class="sv"><a href="' + v[1] + ".html#v" + r.replace(":", "-") + '"><span class="r">Guybile ' + r + " · " + escH(v[2]) +
            "</span>" + escH(v[3]) + '</a><div class="svb"><button class="chip" data-img="' + r + '">Image</button><button class="chip" data-rm="' + r + '">Remove</button></div></li>';
        }).join("");
        ul.onclick = function (e) {
          var rm = e.target.closest("[data-rm]"), im = e.target.closest("[data-img]");
          if (rm) { toggleSaved(rm.dataset.rm); renderSaved(); }
          if (im) { var v = by[im.dataset.img]; shareImage(v[3], v[0], v[2], vlink(v)); }
        };
      });
    };
    renderSaved();
  }

  /* ---------- Search ---------- */
  if (page === "search") {
    var q = $("q"), list = $("results"), count = $("count");
    var fold = function (s) { return s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[‘’]/g, "'"); };
    var run = function () {
      verses().then(function (all) {
        var raw = q.value.trim(), terms = fold(raw).split(/\s+/).filter(Boolean);
        history.replaceState(null, "", raw ? "?q=" + encodeURIComponent(raw) : location.pathname);
        if (!terms.length) { list.innerHTML = ""; count.textContent = all.length + " verses. Start typing."; return; }
        var refQ = raw.match(/^(\d+)(?::(\d+))?$/);
        var hits = all.filter(function (v) {
          if (refQ) return refQ[2] ? v[0] === refQ[1] + ":" + refQ[2] : v[0].split(":")[0] === refQ[1];
          var hay = fold(v[3] + " " + v[2]);
          return terms.every(function (t) { return hay.indexOf(t) !== -1; });
        });
        count.textContent = hits.length + (hits.length === 1 ? " verse" : " verses");
        var re = refQ ? null : new RegExp("(" + terms.map(function (t) { return t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }).join("|") + ")", "gi");
        list.innerHTML = hits.slice(0, 200).map(function (v) {
          var t = escH(v[3]); if (re) t = t.replace(re, "<mark>$1</mark>");
          return '<li><a href="' + v[1] + ".html#v" + v[0].replace(":", "-") + '"><span class="r">Guybile ' + v[0] + " · " + escH(v[2]) + "</span>" + t + "</a></li>";
        }).join("");
      });
    };
    var t; q.addEventListener("input", function () { clearTimeout(t); t = setTimeout(run, 80); });
    var pre = new URLSearchParams(location.search).get("q"); if (pre) q.value = pre;
    run(); q.focus();
  }


  /* ---------- Shared: send a canvas as a picture ---------- */
  function shareCanvas(c, name, text) {
    c.toBlob(function (blob) {
      var file = typeof File === "function" ? new File([blob], name, { type: "image/png" }) : null;
      if (file && navigator.canShare && navigator.canShare({ files: [file] })) {
        navigator.share({ files: [file], text: text }).catch(function () {});
      } else {
        var a = d.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name;
        d.body.appendChild(a); a.click(); a.remove();
        setTimeout(function () { URL.revokeObjectURL(a.href); }, 4000);
        say("Image downloaded");
      }
    }, "image/png");
  }
  function loadImg(src) {
    return new Promise(function (ok) { var i = new Image(); i.onload = function () { ok(i); }; i.onerror = function () { ok(null); }; i.src = src; });
  }
  function tinted(img, w, h, color) { // ink-only mask image -> coloured ornament
    var o = d.createElement("canvas"); o.width = w; o.height = h;
    var x = o.getContext("2d"); x.drawImage(img, 0, 0, w, h);
    x.globalCompositeOperation = "source-in"; x.fillStyle = color; x.fillRect(0, 0, w, h);
    return o;
  }

  /* ---------- Oath certificate ---------- */
  if (page === "oath") {
    var form = $("oath-form"), certC = null;
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var name = $("o-name").value.trim(), by = $("o-by").value.trim();
      if (!name) return;
      Promise.all([loadImg("art/paper.webp"), loadImg("art/corner.webp"), loadImg("art/fleuron.webp")]).then(function (im) {
        var W = 1080, H = 1350, c = d.createElement("canvas"); c.width = W; c.height = H;
        var x = c.getContext("2d"), GOLD = "#9a7431", INK = "#2b241d", RED = "#9a2a1c";
        x.fillStyle = "#f3ead6"; x.fillRect(0, 0, W, H);
        if (im[0]) { x.fillStyle = x.createPattern(im[0], "repeat"); x.fillRect(0, 0, W, H); }
        x.strokeStyle = GOLD; x.lineWidth = 3; x.strokeRect(46, 46, W - 92, H - 92);
        x.lineWidth = 1.5; x.strokeRect(62, 62, W - 124, H - 124);
        if (im[1]) {
          var k = tinted(im[1], 230, 230, GOLD);
          [[0, 0, 1, 1], [W, 0, -1, 1], [0, H, 1, -1], [W, H, -1, -1]].forEach(function (p) {
            x.save(); x.translate(p[0], p[1]); x.scale(p[2], p[3]); x.drawImage(k, 70, 70); x.restore();
          });
        }
        var fl = im[2] ? tinted(im[2], 420, 140, GOLD) : null;
        x.textAlign = "center"; x.textBaseline = "alphabetic";
        x.fillStyle = GOLD; x.font = "700 26px " + SANS;
        if ("letterSpacing" in x) x.letterSpacing = "9px";
        x.fillText("THE GUYBILE", W / 2, 230);
        if ("letterSpacing" in x) x.letterSpacing = "0px";
        x.fillStyle = "#5e5246"; x.font = "italic 40px " + SERIF; x.fillText("Be it known unto all brothers that", W / 2, 330);
        var size = 120; do { x.font = "600 " + size + "px " + SERIF; size -= 4; } while (x.measureText(name).width > 820 && size > 40);
        x.fillStyle = RED; x.fillText(name, W / 2, 470);
        if (fl) x.drawImage(fl, (W - 420) / 2, 500);
        x.fillStyle = INK; x.font = "42px " + SERIF; x.fillText("hath sworn the Brother’s Oath and is hereby", W / 2, 700);
        x.font = "600 64px " + SERIF; x.fillText("A Sworn Brother", W / 2, 790);
        x.font = "italic 44px " + SERIF; x.fillText("of the Guybile", W / 2, 850);
        x.fillStyle = "#5e5246"; x.font = "italic 32px " + SERIF;
        ["I will show up.", "I will tell the truth, even when it is awkward.", "I will listen more than I fix.", "I will ask for help, and give it back."]
          .forEach(function (l, i) { x.fillText(l, W / 2, 950 + i * 46); });
        var when = new Date().toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" });
        x.fillStyle = INK; x.font = "30px " + SERIF;
        x.fillText((by ? "Sworn in by " + by + " · " : "Sworn on ") + when, W / 2, 1190);
        x.fillStyle = GOLD; x.font = "600 24px " + SANS; x.fillText("theguybile.com", W / 2, 1250);
        certC = c;
        $("cert-img").src = c.toDataURL("image/png");
        $("cert").hidden = false;
        $("cert").scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });
    $("cert-share").addEventListener("click", function () {
      if (certC) shareCanvas(certC, "sworn-brother.png", "Thou art now a Sworn Brother of the Guybile. Swear in thine own: " + new URL("oath.html", location.href).href);
    });
  }

  /* ---------- Quiz ---------- */
  if (page === "quiz") {
    var Q = JSON.parse($("quiz-data").textContent), box = $("quiz"), score = {}, step = 0, last = 0;
    var esc_ = function (t) { var e = d.createElement("i"); e.textContent = t; return e.innerHTML; };
    var ask = function () {
      var q = Q[step];
      box.innerHTML = '<p class="qn">Question ' + (step + 1) + ' of ' + Q.length + '</p><h2>' + esc_(q[0]) + '</h2><div class="opts">' +
        q[1].map(function (o, i) { return '<button class="opt" data-i="' + i + '">' + esc_(o[0]) + '</button>'; }).join("") + '</div>';
    };
    box.addEventListener("click", function (e) {
      var b = e.target.closest("button"); if (!b) return;
      if (b.id === "q-again") { score = {}; step = 0; ask(); return; }
      if (b.id === "q-share") { var r = box._row; shareImage(r[3], r[0], r[2], vlink(r)); return; }
      if (!b.classList.contains("opt")) return;
      last = Q[step][1][+b.dataset.i][1]; score[last] = (score[last] || 0) + 1; step++;
      if (step < Q.length) { ask(); return; }
      var best = last; Object.keys(score).forEach(function (k) { if (score[k] > score[best]) best = +k; });
      fetch("verses.json").then(function (r) { return r.json(); }).then(function (rows) {
        var pool = rows.filter(function (r) { return r[0].indexOf(best + ":") === 0; });
        var row = pool[Math.floor(Math.random() * pool.length)] || rows[0];
        box._row = row;
        box.innerHTML = '<p class="qn">The Guybile hath spoken. Thou hast broken</p><h2 class="qres"><a href="' + row[1] + '.html#v' + row[0].replace(":", "-") + '">Guybile ' + row[0] + '</a></h2>' +
          '<blockquote>' + esc_(row[3]) + '</blockquote><p class="meta">' + esc_(row[2]) + '</p>' +
          '<div class="dact"><button class="chip" id="q-share">Share result</button><a class="chip" href="' + row[1] + '.html">Read the chapter</a><button class="chip" id="q-again">Take it again</button></div>';
      });
    });
    ask();
  }

  /* ---------- Offline ---------- */
  if ("serviceWorker" in navigator && location.protocol !== "file:") {
    addEventListener("load", function () { navigator.serviceWorker.register("sw.js").catch(function () {}); });
  }
})();
