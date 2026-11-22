/* Tablica Spraw: instant view switch (Tablica etapów / Tabela rejestru) + drag-and-drop between columns. */
(function () {
  var dragCaseId = null;

  function setView(view) {
    var box = document.querySelector("#rejestr .rejestr-views");
    if (!box) return;
    box.setAttribute("data-view", view);
    document.querySelectorAll("#rejestr .seg-btn").forEach(function (btn) {
      var active = btn.getAttribute("data-switch") === view;
      btn.classList.toggle("on", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });
    var rokUklad = document.getElementById("rok-uklad");
    if (rokUklad) rokUklad.value = view;
    try {
      var url = new URL(window.location.href);
      if (view === "tabela") {
        url.searchParams.set("uklad", "tabela");
      } else {
        url.searchParams.delete("uklad");
      }
      window.history.replaceState({}, "", url.pathname + url.search);
    } catch (_) {}
  }

  document.addEventListener("click", function (e) {
    var btn = e.target.closest("#rejestr .seg-btn[data-switch]");
    if (!btn || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    setView(btn.getAttribute("data-switch"));
  });

  document.addEventListener("dragstart", function (e) {
    var card = e.target.closest(".kcard[data-case-id]");
    if (!card) return;
    dragCaseId = card.getAttribute("data-case-id");
    card.classList.add("dragging");
    if (e.dataTransfer) {
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", dragCaseId);
    }
  });

  document.addEventListener("dragend", function () {
    dragCaseId = null;
    document.querySelectorAll(".kcard.dragging").forEach(function (c) { c.classList.remove("dragging"); });
    document.querySelectorAll(".board-col.drag-over").forEach(function (c) { c.classList.remove("drag-over"); });
  });

  document.addEventListener("dragover", function (e) {
    var col = e.target.closest(".board-col[data-drop-status]");
    if (!col || !dragCaseId) return;
    e.preventDefault();
    if (e.dataTransfer) e.dataTransfer.dropEffect = "move";
    document.querySelectorAll(".board-col.drag-over").forEach(function (c) {
      if (c !== col) c.classList.remove("drag-over");
    });
    col.classList.add("drag-over");
  });

  document.addEventListener("dragleave", function (e) {
    var col = e.target.closest(".board-col[data-drop-status]");
    if (!col) return;
    if (!col.contains(e.relatedTarget)) col.classList.remove("drag-over");
  });

  document.addEventListener("drop", function (e) {
    var col = e.target.closest(".board-col[data-drop-status]");
    if (!col) return;
    e.preventDefault();
    col.classList.remove("drag-over");
    var cid = dragCaseId || (e.dataTransfer ? e.dataTransfer.getData("text/plain") : null);
    if (!cid) return;
    var targetStatus = col.getAttribute("data-drop-status");
    var card = document.querySelector('.kcard[data-case-id="' + cid + '"]');
    if (!card) return;
    var form = card.querySelector("form.k-status-form");
    var sel = form ? form.querySelector('select[name="status"]') : null;
    if (!sel || sel.value === targetStatus) return;
    sel.value = targetStatus;
    sel.dispatchEvent(new Event("change", { bubbles: true }));
  });
})();
