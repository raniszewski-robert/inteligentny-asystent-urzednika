// Anonimizacja (T08): click a fragment to black it out or leave it visible; select text to add a manual fragment.
// Every decision lives in the form's selects (st_<id>), so the page also works without JavaScript.
(function () {
  "use strict";
  var form = document.getElementById("anon-form");
  var docEl = document.getElementById("doc");
  if (!form || !docEl) return;
  var count = document.getElementById("undecided-count");
  var markBtn = document.getElementById("mark-selection");
  var manual = document.getElementById("manual");
  var saveBtn = form.querySelector('button[value="zapisz"]');
  var STATES = ["suggested", "review", "accepted", "rejected"];

  function sel(id) { return document.getElementById("st_" + id); }

  function paint(id, status) {
    docEl.querySelectorAll('mark.sp[data-id="' + id + '"]').forEach(function (m) {
      STATES.forEach(function (s) { m.classList.remove("sp-" + s); });
      m.classList.add("sp-" + status);
      m.setAttribute("aria-pressed", status === "accepted" ? "true" : "false");
    });
  }

  function recount() {
    if (!count) return;
    var n = 0;
    form.querySelectorAll("select[data-id]").forEach(function (s) {
      if (s.value === "suggested" || s.value === "review") n++;
    });
    count.textContent = String(n);
  }

  function toggle(mark) {
    var id = mark.getAttribute("data-id");
    var s = sel(id);
    if (!s) return;
    s.value = s.value === "accepted" ? "rejected" : "accepted";
    paint(id, s.value);
    recount();
  }

  docEl.addEventListener("click", function (e) {
    var m = e.target.closest("mark.sp");
    if (m && !window.getSelection().toString()) toggle(m);
  });
  docEl.addEventListener("keydown", function (e) {
    var m = e.target.closest("mark.sp");
    if (m && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); toggle(m); }
  });
  form.querySelectorAll("select[data-id]").forEach(function (s) {
    s.addEventListener("change", function () { paint(s.getAttribute("data-id"), s.value); recount(); });
  });

  // Manual fragment: the selected text goes to the "Dodatkowe fragmenty" list and the form is saved.
  if (markBtn && manual) {
    markBtn.hidden = false;
    var picked = "";
    document.addEventListener("selectionchange", function () {
      var s = window.getSelection();
      var inside = s.rangeCount && docEl.contains(s.getRangeAt(0).commonAncestorContainer);
      picked = inside ? s.toString().replace(/\s+/g, " ").trim() : "";
      markBtn.disabled = picked.length < 2;
    });
    markBtn.addEventListener("click", function () {
      if (picked.length < 2) return;
      manual.value = (manual.value.trim() ? manual.value.trim() + "\n" : "") + picked;
      if (form.requestSubmit && saveBtn) form.requestSubmit(saveBtn); else form.submit();
    });
  }
})();
