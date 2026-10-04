(function () {
  "use strict";
  var DATA = JSON.parse(document.getElementById("calc-data").textContent);
  var KEY = "ecm-calc-v1";
  var $ = function (id) { return document.getElementById(id); };
  var mats = $("mats");
  var fields = ["cur", "pname", "pack", "mins", "hour", "over", "waste", "fee", "markup", "invest", "perm"];
  var DEFAULTS = { cur: "S/", pname: "", pack: "", mins: "", hour: "", over: "10", waste: "5", fee: "0", markup: "100", invest: "", perm: "40" };
  var preset = "";

  function num(v) { var n = parseFloat(String(v).replace(",", ".")); return isFinite(n) ? n : 0; }
  function fmt(v) {
    var c = $("cur").value.trim();
    var s = v.toLocaleString("es", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return (c ? c + " " : "") + s;
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (m) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[m]; }); }

  function addRow(r) {
    r = r || { n: "", u: "", price: "", qty: "", use: "" };
    var d = document.createElement("div");
    d.className = "mat";
    d.innerHTML =
      '<input class="n" data-l="Material" aria-label="Material" placeholder="Ej. cera de soya" value="' + esc(r.n) + '">' +
      '<span data-l="Precio del paquete"><input class="p" type="number" min="0" step="0.01" inputmode="decimal" aria-label="Precio del paquete" placeholder="0" value="' + esc(r.price) + '"></span>' +
      '<span class="u" data-l="Cantidad que trae"><input class="q" type="number" min="0" step="any" inputmode="decimal" aria-label="Cantidad que trae el paquete" value="' + esc(r.qty) + '"><small>' + esc(r.u) + '</small></span>' +
      '<span class="u" data-l="Cantidad que usas"><input class="s" type="number" min="0" step="any" inputmode="decimal" aria-label="Cantidad que usas por pieza" value="' + esc(r.use) + '"><small>' + esc(r.u) + '</small></span>' +
      '<span class="c" aria-label="Costo por pieza">–</span>' +
      '<button type="button" class="x" aria-label="Quitar material">×</button>';
    d.dataset.u = r.u || "";
    d.querySelector(".x").addEventListener("click", function () { d.remove(); calc(); });
    mats.appendChild(d);
    return d;
  }

  function readRows() {
    return Array.prototype.map.call(mats.querySelectorAll(".mat"), function (d) {
      return { n: d.querySelector(".n").value, u: d.dataset.u, price: d.querySelector(".p").value, qty: d.querySelector(".q").value, use: d.querySelector(".s").value, el: d };
    });
  }

  function save() {
    try {
      var st = { preset: preset, rows: readRows().map(function (r) { return { n: r.n, u: r.u, price: r.price, qty: r.qty, use: r.use }; }) };
      fields.forEach(function (f) { st[f] = $(f).value; });
      localStorage.setItem(KEY, JSON.stringify(st));
    } catch (e) { /* almacenamiento no disponible */ }
  }

  function load(st) {
    mats.innerHTML = "";
    fields.forEach(function (f) { $(f).value = st[f] != null ? st[f] : DEFAULTS[f]; });
    (st.rows && st.rows.length ? st.rows : [null, null]).forEach(addRow);
    preset = st.preset || "";
    $("preset").value = preset;
  }

  function applyPreset(k, quiet) {
    var p = DATA.presets[k];
    preset = k;
    if (!p) { load({}); calc(); return; }
    var keep = { cur: $("cur").value, hour: $("hour").value, over: $("over").value, waste: $("waste").value, fee: $("fee").value, markup: $("markup").value, perm: $("perm").value };
    load({
      preset: k, pname: p.label, mins: String(p.minutes), cur: keep.cur, hour: keep.hour, over: keep.over, waste: keep.waste,
      fee: keep.fee, markup: keep.markup, perm: keep.perm,
      rows: p.items.map(function (i) { return { n: i[0], u: i[1], qty: String(i[2]), use: String(i[3]), price: "" }; })
    });
    calc();
    var first = mats.querySelector(".p");
    if (first && !quiet) first.focus();
  }

  function set(id, v) { $(id).textContent = v; }

  function calc() {
    var rows = readRows(), mat = 0, priced = 0;
    rows.forEach(function (r) {
      var q = num(r.qty), u = num(r.use), p = num(r.price);
      var c = q > 0 ? p / q * u : 0;
      if (p > 0 && q > 0 && u > 0) priced++;
      r.el.querySelector(".c").textContent = c > 0 ? fmt(c) : "–";
      mat += c;
    });
    var waste = mat * num($("waste").value) / 100;
    var over = mat * num($("over").value) / 100;
    var pack = num($("pack").value);
    var labor = num($("mins").value) / 60 * num($("hour").value);
    var cost = mat + waste + over + pack + labor;
    var fee = Math.min(num($("fee").value), 90) / 100;
    var mk = num($("markup").value) / 100;
    var price = cost * (1 + mk) / (1 - fee);
    var whole = cost * (1 + mk / 2) / (1 - fee);
    var profit = price * (1 - fee) - cost;
    var perm = num($("perm").value), invest = num($("invest").value);

    set("outname", $("pname").value ? "· " + $("pname").value : "");
    var has = cost > 0;
    set("r-mat", has ? fmt(mat) : "–");
    set("r-waste", has ? fmt(waste) : "–");
    set("r-over", has ? fmt(over) : "–");
    set("r-pack", has ? fmt(pack) : "–");
    set("r-labor", has ? fmt(labor) : "–");
    set("r-cost", has ? fmt(cost) : "–");
    set("r-price", has ? fmt(price) : "–");
    set("r-whole", has ? "Precio mayorista sugerido: " + fmt(whole) : "");
    set("r-profit", has ? fmt(profit) : "–");
    set("r-month", has && perm > 0 ? fmt(profit * perm) + " (" + perm + " piezas)" : "–");
    if (has && invest > 0 && profit > 0) {
      var units = Math.ceil(invest / profit);
      var months = perm > 0 ? units / perm : 0;
      set("r-be", units + " piezas" + (months ? " (≈ " + (months < 1 ? "menos de 1 mes" : months.toLocaleString("es", { maximumFractionDigits: 1 }) + " meses") + ")" : ""));
    } else set("r-be", "–");
    var hint = "";
    if (!has) hint = "Completa los precios de tus materiales para ver el resultado.";
    else if (priced < rows.length) hint = "Hay materiales sin precio: complétalos para un costo exacto.";
    else if (!num($("hour").value)) hint = "Consejo: agrega lo que quieres ganar por hora para que tu tiempo también se pague.";
    set("r-hint", hint);
    $("r-hint").hidden = !hint;

    var rec = DATA.rec[preset], box = $("rec");
    if (rec) {
      box.innerHTML = "<p><b>¿Aún no sabes hacerlo?</b></p><p>El curso mejor valorado de " + esc(rec.cat.toLowerCase()) +
        ': <a href="' + rec.curl + '">' + esc(rec.course) + '</a>.</p><p><a class="more" href="' + rec.url + '">Ver la comparativa de cursos</a></p>';
      box.hidden = false;
    } else box.hidden = true;
    save();
  }

  $("addmat").addEventListener("click", function () { addRow().querySelector(".n").focus(); });
  $("preset").addEventListener("change", function () { applyPreset(this.value); });
  $("reset").addEventListener("click", function () {
    try { localStorage.removeItem(KEY); } catch (e) { /* nada */ }
    load({}); calc();
  });
  document.getElementById("calc").addEventListener("input", calc);

  var q = new URLSearchParams(location.search).get("oficio");
  var st = null;
  try { st = JSON.parse(localStorage.getItem(KEY) || "null"); } catch (e) { st = null; }
  if (q && DATA.presets[q] && (!st || st.preset !== q)) applyPreset(q, true);
  else { load(st || {}); calc(); }
})();
