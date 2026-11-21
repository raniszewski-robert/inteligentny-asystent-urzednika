// Projekt pisma (T07): move sentences between "Ad N" sections; the textarea stays the source of truth.
// Without JavaScript the clerk edits the textarea directly; the form posts the same field either way.
(function () {
  "use strict";
  var ta = document.getElementById("letter-text");
  var box = document.getElementById("ad-editor");
  var typeSel = document.getElementById("ltype");

  // Type-specific fields: show only those the chosen letter type uses.
  function syncFields() {
    if (!typeSel) return;
    document.querySelectorAll("[data-types]").forEach(function (el) {
      el.hidden = el.getAttribute("data-types").split(" ").indexOf(typeSel.value) < 0;
    });
  }
  if (typeSel) { typeSel.addEventListener("change", syncFields); syncFields(); }
  if (!ta || !box) return;

  var AD = /^Ad\s+(\d+)\s*$/;
  var GAP = "[LUKA: brak odpowiedzi wydziału – uzupełnij przed wysyłką]";
  // Same rule as draft.py _sentences(): no split after abbreviations ("2025 r. 839 psom", "ul. Jezuicka").
  var ABBR = /(?:^|[^\wąćęłńóśźż])(?:r|ul|nr|tj|np|ok|tys|mln|zł|art|ust|pkt|poz|al|os|pl|św|ks|dr|inż|mgr)\.$/i;

  function sentences(body) {
    var parts = body.replace(/\s+/g, " ").trim().split(/(?<=[.!?])\s+(?=[A-ZĄĆĘŁŃÓŚŹŻ])/);
    var out = [];
    parts.forEach(function (p) {
      if (out.length && ABBR.test(out[out.length - 1])) out[out.length - 1] += " " + p;
      else if (p) out.push(p);
    });
    return out.filter(function (s) { return s && s !== GAP; });
  }

  // Letter = lines before the first "Ad", sections (heading + body lines), lines after the last body.
  function parse(text) {
    var lines = text.replace(/\r\n/g, "\n").split("\n");
    var head = [], secs = [], tail = [], cur = null, i;
    for (i = 0; i < lines.length; i++) {
      var m = AD.exec(lines[i]);
      if (m && !tail.length) { cur = { no: m[1], body: [] }; secs.push(cur); continue; }
      if (cur && lines[i].trim() && !tail.length) { cur.body.push(lines[i]); continue; }
      if (cur) tail.push(lines[i]); else head.push(lines[i]);
    }
    secs.forEach(function (s) { s.sent = sentences(s.body.join(" ")); });
    return { head: head, secs: secs, tail: tail };
  }

  function serialize(doc) {
    var out = doc.head.slice();
    doc.secs.forEach(function (s) { out.push("Ad " + s.no, s.sent.length ? s.sent.join(" ") : GAP); });
    return out.concat(doc.tail).join("\n");
  }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function render() {
    var doc = parse(ta.value);
    box.textContent = "";
    if (doc.secs.length < 2) { box.hidden = true; return; }
    box.hidden = false;
    doc.secs.forEach(function (s, si) {
      var sec = el("div", "ad-sec");
      sec.appendChild(el("h3", null, "Ad " + s.no));
      if (!s.sent.length) sec.appendChild(el("p", "ad-gap", "Brak treści. Przenieś tu zdanie albo uzupełnij tekst."));
      var ol = el("ol", "ad-list");
      s.sent.forEach(function (t, ti) {
        var li = el("li", "ad-sentence");
        li.appendChild(el("span", "ad-text", t));
        var lab = el("label", "ad-move", "Przenieś do ");
        var sel = el("select");
        doc.secs.forEach(function (o, oi) {
          var opt = el("option", null, "Ad " + o.no);
          opt.value = String(oi);
          if (oi === si) opt.selected = true;
          sel.appendChild(opt);
        });
        sel.addEventListener("change", function () {
          var to = parseInt(sel.value, 10);
          if (to === si) return;
          s.sent.splice(ti, 1);
          doc.secs[to].sent.push(t);
          ta.value = serialize(doc);
          render();
          var moved = box.querySelectorAll(".ad-sec")[to];
          if (moved) moved.classList.add("ad-changed");
        });
        lab.appendChild(sel);
        li.appendChild(lab);
        ol.appendChild(li);
      });
      sec.appendChild(ol);
      box.appendChild(sec);
    });
  }

  var timer = null;
  ta.addEventListener("input", function () { clearTimeout(timer); timer = setTimeout(render, 300); });
  render();
})();
