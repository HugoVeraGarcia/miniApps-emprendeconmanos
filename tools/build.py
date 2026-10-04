#!/usr/bin/env python3
"""Emprende con Manos: generador del sitio estático (solo stdlib).

python3 tools/build.py           -> dist/ (producción: publica solo cursos con hotlink)
python3 tools/build.py --draft   -> dist/ (vista previa: todos los cursos, botón deshabilitado si falta el hotlink)

Datos: data/site.json, data/courses.json, data/links.json
"""
import datetime as dt
import hashlib
import html
import json
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
SRC = ROOT / "src"
DRAFT = "--draft" in sys.argv
SITE = json.load(open(ROOT / "data" / "site.json", encoding="utf-8"))
ALL = json.load(open(ROOT / "data" / "courses.json", encoding="utf-8"))["courses"]
LINKS = {k: v.strip() for k, v in json.load(open(ROOT / "data" / "links.json", encoding="utf-8")).items() if not k.startswith("_")}
DOMAIN = SITE["domain"].rstrip("/")
NAME = SITE["name"]
E = html.escape
IMG = "https://hotmart.s3.amazonaws.com/product_pictures/"
HOTLINK_RE = re.compile(r"^https://(go|pay)\.hotmart\.com/[A-Za-z0-9?=&_\-]+$")
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
CHECKED = dt.date.fromisoformat(SITE["checked"])
CHECKED_TXT = f"{CHECKED.day} de {MESES[CHECKED.month - 1]} de {CHECKED.year}"
PAGES = []

# ---------- datos ----------
for c in ALL:
    link = LINKS.get(str(c["id"]), "")
    if link and not HOTLINK_RE.match(link):
        raise SystemExit(f"hotlink inválido para {c['id']} ({c['name']}): {link}")
    c["link"] = link
    c["score"] = round((c["rating"] * c["reviews"] + 4.5 * 50) / (c["reviews"] + 50), 4)

missing = [c for c in ALL if not c["link"]]
COURSES = ALL if DRAFT else [c for c in ALL if c["link"]]
if not COURSES:
    raise SystemExit("No hay cursos con hotlink en data/links.json. Usa --draft para la vista previa.")
CATS = [k for k in SITE["categories"] if any(k["slug"] in c["cats"] for c in COURSES)]
CAT = {k["slug"]: k for k in SITE["categories"]}


def in_cat(slug):
    return sorted([c for c in COURSES if slug in c["cats"]], key=lambda c: (not c["star"], -c["score"]))


def best_of(slug):
    lst = in_cat(slug)
    return lst[0] if lst else None


def _ver(rel):
    return hashlib.md5((SRC / rel).read_bytes()).hexdigest()[:8]


ASSET = {r: f"/{r}?v={_ver(r)}" for r in ("assets/css/site.css", "assets/js/calc.js")}


# ---------- piezas ----------
def money(v):
    return f"US${v:,.0f}" if float(v).is_integer() else f"US${v:,.2f}"


def stars(r):
    full = int(round(r * 2) / 2)
    half = (round(r * 2) / 2) - full >= 0.5
    return "★" * full + ("½" if half else "") + "☆" * (5 - full - (1 if half else 0))


def rating(c, small=False):
    return (f'<span class="rating{" sm" if small else ""}" aria-label="{c["rating"]:.1f} de 5">'
            f'<b>{c["rating"]:.1f}</b> <span class="st" aria-hidden="true">{stars(c["rating"])}</span> '
            f'<span class="muted">({c["reviews"]} evaluaciones)</span></span>')


def cta(c, label="Ver el curso en Hotmart", cls="btn"):
    if c["link"]:
        return (f'<a class="{cls}" href="{E(c["link"])}" target="_blank" rel="sponsored nofollow noopener">'
                f'{E(label)} <span aria-hidden="true">→</span></a>')
    return f'<span class="{cls} disabled" title="Falta el hotlink en data/links.json">Enlace pendiente</span>'


def img(c, cls="", eager=False):
    lazy = "" if eager else 'loading="lazy" '
    return (f'<img class="{cls}" src="{IMG}{E(c["img"])}" alt="{E(c["name"])}" width="600" height="600" '
            f'{lazy}decoding="async" referrerpolicy="no-referrer">')


def card(c, rank=None):
    badge = '<span class="badge">Mejor valorado</span>' if c["star"] else ""
    rk = f'<span class="rank">#{rank}</span>' if rank else ""
    return f'''<article class="card">
  <a class="card-img" href="/cursos/{c["slug"]}/">{img(c)}{rk}{badge}</a>
  <div class="card-body">
    <h3><a href="/cursos/{c["slug"]}/">{E(c["name"])}</a></h3>
    {rating(c, True)}
    <p>{E(c["summary"])}</p>
    <div class="card-foot"><span class="price">{money(c["price"])}</span>
      <a class="more" href="/cursos/{c["slug"]}/">Ver análisis</a></div>
  </div>
</article>'''


def ul(items, cls=""):
    return f'<ul class="{cls}">' + "".join(f"<li>{E(i)}</li>" for i in items) + "</ul>"


def crumbs(items):
    lis = "".join(f'<li><a href="{u}">{E(t)}</a></li>' if u else f'<li aria-current="page">{E(t)}</li>' for t, u in items)
    ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": t, **({"item": DOMAIN + u} if u else {})} for i, (t, u) in enumerate(items)]}
    return f'<nav class="crumbs" aria-label="Ruta"><ol>{lis}</ol></nav>' + jsonld(ld)


def jsonld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False).replace("</", "<\\/") + "</script>"


DISCLOSURE = ('<p class="disclosure">Algunos enlaces son de afiliado: si compras un curso a través de ellos, '
              'recibimos una comisión de Hotmart sin costo extra para ti. <a href="/aviso-de-afiliados/">Más información</a>.</p>')


def nav():
    cats = "".join(f'<li><a href="/mejores-cursos/{k["slug"]}/">{k["emoji"]} {E(k["name"])}</a></li>' for k in CATS)
    return f'''<header class="top">
  <div class="wrap top-in">
    <a class="logo" href="/" aria-label="{E(NAME)}, inicio"><span class="logo-mark" aria-hidden="true">✋</span>{E(NAME)}</a>
    <button class="menu-btn" aria-expanded="false" aria-controls="menu">Menú</button>
    <nav id="menu" class="menu" aria-label="Principal">
      <details class="dd"><summary>Cursos</summary><ul>{cats}</ul></details>
      <a href="/que-oficio-elegir/">¿Qué oficio elegir?</a>
      <a class="nav-cta" href="/calculadora-de-precios/">Calculadora de precios</a>
    </nav>
  </div>
</header>'''


def footer():
    cats = "".join(f'<li><a href="/mejores-cursos/{k["slug"]}/">{E(k["name"])}</a></li>' for k in CATS)
    return f'''<footer class="foot">
  <div class="wrap foot-grid">
    <div><a class="logo" href="/"><span class="logo-mark" aria-hidden="true">✋</span>{E(NAME)}</a>
      <p class="muted">{E(SITE["tagline"])} Comparamos cursos online de oficios artesanales con datos de Hotmart revisados el {CHECKED_TXT}.</p></div>
    <div><h4>Cursos</h4><ul>{cats}</ul></div>
    <div><h4>Herramientas</h4><ul><li><a href="/calculadora-de-precios/">Calculadora de precios</a></li><li><a href="/que-oficio-elegir/">¿Qué oficio elegir?</a></li></ul>
      <h4>Sitio</h4><ul><li><a href="/sobre-nosotros/">Sobre nosotros</a></li><li><a href="/aviso-de-afiliados/">Aviso de afiliados</a></li><li><a href="/privacidad/">Privacidad</a></li></ul></div>
  </div>
  <div class="wrap legal">{DISCLOSURE}<p class="muted">© {dt.date.today().year} {E(NAME)}. Hotmart es una marca de sus respectivos dueños; no estamos afiliados a los productores más allá del programa de afiliados.</p></div>
</footer>'''


def page(path, title, desc, body, *, scripts=(), ld=None, og_img=None, noindex=False):
    canon = DOMAIN + path
    meta_extra = ""
    if SITE.get("pinterest_verify"):
        meta_extra += f'\n<meta name="p:domain_verify" content="{E(SITE["pinterest_verify"])}">'
    if noindex or DRAFT:
        meta_extra += '\n<meta name="robots" content="noindex">'
    if og_img:
        meta_extra += f'\n<meta property="og:image" content="{E(og_img)}">'
    js = "".join(f'<script src="{ASSET[s]}" defer></script>' for s in scripts)
    full_title = title if NAME in title else f"{title} | {NAME}"
    doc = f'''<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(full_title)}</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{canon}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{E(NAME)}">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="{canon}">
<meta property="og:locale" content="es_LA">{meta_extra}
<meta name="theme-color" content="#FBF7F1">
<link rel="icon" href="/assets/img/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{ASSET["assets/css/site.css"]}">
{jsonld(ld) if ld else ""}
</head>
<body>
<a class="skip" href="#main">Saltar al contenido</a>
{nav()}
<main id="main">
{body}
</main>
{footer()}
<script>
(function(){{var b=document.querySelector('.menu-btn'),m=document.getElementById('menu');if(!b)return;
b.addEventListener('click',function(){{var o=m.classList.toggle('open');b.setAttribute('aria-expanded',o)}});}})();
</script>
{js}
</body>
</html>'''
    out = DIST / path.lstrip("/") / "index.html" if path.endswith("/") else DIST / path.lstrip("/")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    if not noindex:
        PAGES.append(path)


# ---------- páginas ----------
def build_home():
    stars_ = sorted([c for c in COURSES if c["star"]], key=lambda c: -c["score"])[:4]
    if len(stars_) < 4:
        stars_ += sorted([c for c in COURSES if not c["star"]], key=lambda c: -c["score"])[:4 - len(stars_)]
    cats = "".join(f'''<a class="cat" href="/mejores-cursos/{k["slug"]}/"><span class="cat-emo" aria-hidden="true">{k["emoji"]}</span>
<span class="cat-name">{E(k["name"])}</span><span class="cat-meta">Inversión {E(k["invest"].lower())} · {len(in_cat(k["slug"]))} curso{"s" if len(in_cat(k["slug"])) != 1 else ""}</span></a>''' for k in CATS)
    faq = [
        ("¿Qué es Hotmart?", "Es la plataforma donde se venden la mayoría de cursos online en español. Pagas en Hotmart, recibes acceso inmediato al área de alumnos y puedes ver las clases cuando quieras."),
        ("¿Puedo pedir un reembolso si el curso no me gusta?", "Sí. Todos los productos de Hotmart tienen un periodo de garantía, de al menos 7 días, en el que puedes pedir la devolución desde tu cuenta sin dar explicaciones. Revisa el plazo exacto en la página de cada curso."),
        ("¿Necesito experiencia previa?", "No. Todos los cursos de esta comparativa empiezan desde cero. Lo que sí necesitas es comprar los materiales del oficio que elijas; en cada página te decimos cuáles."),
        ("¿Cuánto cuesta empezar?", "Depende del oficio: velas, jabones y postres se empiezan con muy poco; sublimación o DTF requieren equipo. Usa nuestra calculadora para saber tu costo por pieza y en cuántas ventas recuperas la inversión."),
        ("¿Cómo eligen los cursos?", "Revisamos el mercado de Hotmart en español y nos quedamos con los cursos con mejor calificación y más evaluaciones de compradores, buen temario y productores con trayectoria. Descartamos productos con promesas exageradas o que exigen pagar membresías extra."),
    ]
    faq_html = "".join(f"<details class='faq'><summary>{E(q)}</summary><p>{E(a)}</p></details>" for q, a in faq)
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebSite", "name": NAME, "url": DOMAIN + "/", "inLanguage": "es"},
        {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}]}
    body = f'''<section class="hero">
  <div class="wrap hero-in">
    <div>
      <p class="eyebrow">Oficios artesanales para emprender</p>
      <h1>Aprende un oficio con tus manos y véndelo desde casa</h1>
      <p class="lead">Comparamos los cursos online mejor valorados de velas, jabones, resina, sublimación, globos y más. Calificaciones reales de compradores, precios y lo que necesitas para empezar.</p>
      <div class="hero-cta"><a class="btn" href="#oficios">Ver los mejores cursos</a><a class="btn ghost" href="/calculadora-de-precios/">Calcula tu precio de venta</a></div>
      <p class="muted small">Datos de Hotmart revisados el {CHECKED_TXT}.</p>
    </div>
    <div class="hero-art" aria-hidden="true">{"".join(img(c, "hero-img", eager=True) for c in stars_[:3])}</div>
  </div>
</section>
<section class="wrap sec" id="oficios">
  <h2>Elige tu oficio</h2>
  <p class="sec-lead">Cada oficio tiene su comparativa de cursos, lo que necesitas comprar y qué puedes vender.</p>
  <div class="cats">{cats}</div>
</section>
<section class="wrap sec">
  <h2>Los cursos mejor valorados</h2>
  <p class="sec-lead">Los que combinan mejor calificación, más evaluaciones y un temario pensado para vender.</p>
  <div class="grid">{"".join(card(c) for c in stars_)}</div>
</section>
<section class="band">
  <div class="wrap band-in">
    <div><h2>¿Cuánto deberías cobrar por cada pieza?</h2>
    <p>Suma materiales, empaque, tu tiempo y gastos, y obtén tu precio de venta, el precio mayorista y en cuántas ventas recuperas lo invertido.</p></div>
    <a class="btn light" href="/calculadora-de-precios/">Abrir la calculadora</a>
  </div>
</section>
<section class="wrap sec">
  <h2>Cómo elegimos los cursos</h2>
  <ol class="steps">
    <li><b>Revisamos todo el mercado.</b> Más de 1.400 cursos en español de Hotmart en categorías de oficios y manualidades.</li>
    <li><b>Filtramos por compradores reales.</b> Calificación y número de evaluaciones de quienes ya compraron el curso.</li>
    <li><b>Leemos el temario.</b> Que enseñe desde cero y que incluya cómo vender lo que haces.</li>
    <li><b>Descartamos lo dudoso.</b> Promesas de ingresos exageradas, manuales caros en PDF o cursos que exigen pagar membresías extra.</li>
  </ol>
</section>
<section class="wrap sec narrow">
  <h2>Preguntas frecuentes</h2>
  {faq_html}
  {DISCLOSURE}
</section>'''
    page("/", f"{NAME}: los mejores cursos para emprender con manualidades", SITE["description"], body, ld=ld,
         og_img=IMG + stars_[0]["img"])


def build_course(c):
    cats = [CAT[s] for s in c["cats"]]
    main_cat = cats[0]
    others = [o for o in in_cat(main_cat["slug"]) if o["id"] != c["id"]]
    since = f" · En Hotmart desde {c['since']}" if c.get("since") else ""
    badge = '<span class="badge inline">Mejor valorado</span>' if c["star"] else ""
    compare = ""
    if others:
        compare = f'''<section class="sec-sm"><h2>Compáralo con</h2><div class="grid">{"".join(card(o) for o in others[:3])}</div>
<p><a class="more" href="/mejores-cursos/{main_cat["slug"]}/">Ver la comparativa completa de {E(main_cat["name"].lower())}</a></p></section>'''
    start = ""
    for k in cats:
        start += f'<h3>Para {E(k["name"].lower())}</h3>' + ul(k["start"], "check") if len(cats) > 1 else ul(k["start"], "check")
    notes = "".join(f'<p class="note">{E(k["note"])}</p>' for k in cats if k.get("note"))
    ld = {"@context": "https://schema.org", "@type": "Course", "name": c["name"], "description": c["summary"],
          "inLanguage": "es", "provider": {"@type": "Organization", "name": c["producer"]},
          "image": IMG + c["img"], "offers": {"@type": "Offer", "category": "Paid", "price": c["price"], "priceCurrency": "USD"},
          "hasCourseInstance": {"@type": "CourseInstance", "courseMode": "online"}}
    body = f'''<div class="wrap">{crumbs([("Inicio", "/"), (main_cat["name"], f"/mejores-cursos/{main_cat['slug']}/"), (c["name"], None)])}</div>
<article class="wrap course">
  <div class="course-head">
    <div class="course-media">{img(c, "course-img", eager=True)}</div>
    <div class="course-info">
      {badge}
      <h1>{E(c["name"])}</h1>
      <p class="muted">Por {E(c["producer"])}{since}</p>
      {rating(c)}
      <p class="lead">{E(c["summary"])}</p>
      <div class="buybox">
        <div><span class="price big">{money(c["price"])}</span><span class="muted small">Precio de referencia en Hotmart. Puede variar según tu país y promociones.</span></div>
        {cta(c)}
        <p class="muted small">Acceso online inmediato · Garantía de reembolso de Hotmart</p>
      </div>
    </div>
  </div>
  <div class="course-body">
    <section class="sec-sm"><h2>Qué aprenderás</h2>{ul(c["learn"], "check")}</section>
    <section class="sec-sm"><h2>Para quién es</h2><p>{E(c["for"])}</p></section>
    <section class="sec-sm procon">
      <div class="pro"><h2>A favor</h2>{ul(c["pros"], "plus")}</div>
      <div class="con"><h2>A considerar</h2>{ul(c["cons"], "minus")}</div>
    </section>
    <section class="sec-sm verdict"><h2>Nuestro veredicto</h2><p>{E(c["verdict"])}</p>{cta(c)}</section>
    <section class="sec-sm"><h2>Qué necesitas para empezar</h2>{start}{notes}
      <p>¿Cuánto te costará cada pieza? <a href="/calculadora-de-precios/?oficio={main_cat["slug"]}">Calcúlalo con nuestra calculadora de precios</a>.</p></section>
    {compare}
    <p class="muted small">Calificación y número de evaluaciones de compradores en Hotmart, revisados el {CHECKED_TXT}.</p>
    {DISCLOSURE}
  </div>
</article>'''
    title = f"{c['name']}: opiniones, precio y temario"
    desc = f"{c['summary']} {c['rating']:.1f}/5 con {c['reviews']} evaluaciones en Hotmart. Qué aprenderás, a favor, en contra y nuestro veredicto."
    page(f"/cursos/{c['slug']}/", title, desc[:300], body, ld=ld, og_img=IMG + c["img"])


def build_category(k):
    lst = in_cat(k["slug"])
    rows = "".join(f'''<tr><td><a href="/cursos/{c["slug"]}/">{E(c["name"])}</a>{' <span class="badge inline">Mejor valorado</span>' if c["star"] else ""}</td>
<td>{c["rating"]:.1f} ★</td><td>{c["reviews"]}</td><td>{money(c["price"])}</td><td>{cta(c, "Ver curso", "btn sm")}</td></tr>''' for c in lst)
    ranked = "".join(f'''<article class="pick" id="{c["slug"]}">
  <a class="pick-img" href="/cursos/{c["slug"]}/">{img(c)}</a>
  <div class="pick-body">
    <p class="eyebrow">#{i} {"· Mejor valorado" if c["star"] else ""}</p>
    <h3><a href="/cursos/{c["slug"]}/">{E(c["name"])}</a></h3>
    {rating(c, True)}
    <p>{E(c["summary"])}</p>
    <p><b>Ideal para:</b> {E(c["for"])}</p>
    <p class="verdict-line"><b>Veredicto:</b> {E(c["verdict"])}</p>
    <div class="pick-foot"><span class="price">{money(c["price"])}</span>{cta(c, "Ver curso en Hotmart", "btn sm")}<a class="more" href="/cursos/{c["slug"]}/">Análisis completo</a></div>
  </div>
</article>''' for i, c in enumerate(lst, 1))
    note = f'<p class="note">{E(k["note"])}</p>' if k.get("note") else ""
    others = "".join(f'<a class="chip" href="/mejores-cursos/{o["slug"]}/">{o["emoji"]} {E(o["name"])}</a>' for o in CATS if o["slug"] != k["slug"])
    ld = {"@context": "https://schema.org", "@type": "ItemList", "name": k["title"], "itemListElement": [
        {"@type": "ListItem", "position": i, "url": f"{DOMAIN}/cursos/{c['slug']}/", "name": c["name"]} for i, c in enumerate(lst, 1)]}
    n = len(lst)
    body = f'''<div class="wrap">{crumbs([("Inicio", "/"), (k["name"], None)])}</div>
<section class="wrap sec-top">
  <p class="eyebrow">{k["emoji"]} {E(k["name"])}</p>
  <h1>{E(k["title"])} ({CHECKED.year})</h1>
  <p class="lead">{E(k["intro"])}</p>
  <dl class="facts"><div><dt>Inversión inicial</dt><dd>{E(k["invest"])}</dd></div><div><dt>Espacio</dt><dd>{E(k["space"])}</dd></div><div><dt>Tiempo para aprender</dt><dd>{E(k["learn"])}</dd></div></dl>
</section>
<section class="wrap sec-sm">
  <h2>Comparativa rápida</h2>
  <div class="table-wrap"><table class="cmp"><thead><tr><th>Curso</th><th>Calificación</th><th>Evaluaciones</th><th>Precio</th><th></th></tr></thead><tbody>{rows}</tbody></table></div>
  <p class="muted small">Datos de compradores en Hotmart revisados el {CHECKED_TXT}. Precios de referencia en dólares.</p>
</section>
<section class="wrap sec-sm"><h2>{"Los " + str(n) + " cursos, uno por uno" if n > 1 else "El curso recomendado"}</h2>{ranked}</section>
<section class="wrap sec-sm two">
  <div><h2>Qué necesitas para empezar</h2>{ul(k["start"], "check")}{note}</div>
  <div><h2>Qué puedes vender</h2>{ul(k["sell"], "check")}
    <div class="mini-cta"><p><b>¿A qué precio vender?</b> Calcula tu costo por pieza, el precio de venta y en cuántas ventas recuperas la inversión.</p><a class="btn sm" href="/calculadora-de-precios/?oficio={k["slug"]}">Usar la calculadora</a></div></div>
</section>
<section class="wrap sec-sm"><h2>Otros oficios</h2><div class="chips">{others}</div>{DISCLOSURE}</section>'''
    desc = f"Comparamos {n} curso{'s' if n > 1 else ''} de {k['name'].lower()} con calificaciones reales de Hotmart, precios y qué necesitas para empezar a vender."
    page(f"/mejores-cursos/{k['slug']}/", f"{k['title']} ({CHECKED.year})", desc, body, ld=ld, og_img=IMG + lst[0]["img"])


def build_chooser():
    rows = ""
    for k in CATS:
        b = best_of(k["slug"])
        rows += f'''<tr><td><a href="/mejores-cursos/{k["slug"]}/">{k["emoji"]} {E(k["name"])}</a></td><td>{E(k["invest"])}</td><td>{E(k["space"])}</td><td>{E(k["learn"])}</td>
<td><a href="/cursos/{b["slug"]}/">{E(b["name"])}</a></td></tr>'''
    profiles = [
        ("Tengo poco presupuesto", ["velas", "jabones", "reposteria"], "Empieza con algo que puedas hacer en tu cocina y vender rápido. Los materiales iniciales son baratos y aprendes en pocas semanas."),
        ("Quiero vender por Instagram y TikTok", ["resina", "velas", "decoracion-concreto"], "Productos muy visuales y personalizables, que se ven increíbles en fotos y videos cortos."),
        ("Quiero pedidos grandes y de empresas", ["sublimacion", "globos-eventos"], "Personalización y decoración de eventos permiten cobrar más por pedido y trabajar con empresas."),
        ("Quiero aprender un oficio para toda la vida", ["costura-tejido"], "Costura y tejido llevan más tiempo de aprendizaje, pero te permiten crear casi cualquier producto."),
    ]
    prof_html = ""
    for t, slugs, txt in profiles:
        links = " · ".join(f'<a href="/mejores-cursos/{s}/">{E(CAT[s]["name"])}</a>' for s in slugs if s in [k["slug"] for k in CATS])
        if links:
            prof_html += f'<div class="profile"><h3>{E(t)}</h3><p>{E(txt)}</p><p>{links}</p></div>'
    body = f'''<div class="wrap">{crumbs([("Inicio", "/"), ("¿Qué oficio elegir?", None)])}</div>
<section class="wrap sec-top"><h1>¿Qué oficio artesanal elegir para emprender?</h1>
<p class="lead">Compara los oficios por inversión inicial, espacio que necesitas y tiempo para aprender. Después elige el curso mejor valorado de cada uno.</p></section>
<section class="wrap sec-sm"><div class="table-wrap"><table class="cmp"><thead><tr><th>Oficio</th><th>Inversión inicial</th><th>Espacio</th><th>Para aprender</th><th>Curso mejor valorado</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="muted small">La inversión es orientativa y depende de los precios de tu país. Calcula tu caso con la <a href="/calculadora-de-precios/">calculadora de precios</a>.</p></section>
<section class="wrap sec-sm"><h2>Según lo que buscas</h2><div class="profiles">{prof_html}</div>{DISCLOSURE}</section>'''
    page("/que-oficio-elegir/", "¿Qué oficio artesanal elegir para emprender desde casa?",
         "Compara velas, jabones, resina, sublimación, globos, costura y más por inversión inicial, espacio y tiempo de aprendizaje.", body)


CALC_PRESETS = {
    "velas": {"label": "Vela de soya en envase (200 g)", "unit": "vela", "minutes": 15, "items": [
        ["Cera de soya", "kg", 1, 0.18], ["Fragancia para velas", "ml", 500, 16], ["Mecha con base", "unid.", 100, 1], ["Envase de vidrio", "unid.", 12, 1], ["Colorante", "g", 50, 0.5]]},
    "jabones": {"label": "Jabón de glicerina (100 g)", "unit": "jabón", "minutes": 8, "items": [
        ["Base de glicerina", "kg", 1, 0.1], ["Fragancia cosmética", "ml", 100, 1.5], ["Colorante cosmético", "ml", 30, 0.3], ["Molde de silicona", "usos", 200, 1]]},
    "resina": {"label": "Llavero de resina", "unit": "llavero", "minutes": 10, "items": [
        ["Kit de resina epóxica (A+B)", "g", 1000, 15], ["Pigmento o mica", "g", 50, 0.3], ["Argolla de llavero", "unid.", 100, 1], ["Molde de silicona", "usos", 100, 1]]},
    "sublimacion": {"label": "Taza sublimada", "unit": "taza", "minutes": 10, "items": [
        ["Taza blanca para sublimar", "unid.", 36, 1], ["Papel de sublimación", "hojas", 100, 1], ["Tinta de sublimación", "ml", 400, 1.5], ["Cinta térmica", "cm", 3300, 15]]},
    "reposteria": {"label": "Postre en vaso", "unit": "postre", "minutes": 6, "items": [
        ["Vaso con tapa", "unid.", 50, 1], ["Crema de leche", "ml", 1000, 80], ["Galletas", "g", 400, 40], ["Chocolate", "g", 500, 20], ["Cucharita", "unid.", 100, 1]]},
    "globos-eventos": {"label": "Arco de globos (100 globos)", "unit": "arco", "minutes": 120, "items": [
        ["Globos de látex", "unid.", 100, 100], ["Cinta para arco", "m", 5, 3], ["Hilo de pescar", "m", 100, 5], ["Cinta doble faz", "unid.", 1, 0.5]]},
    "decoracion-concreto": {"label": "Maceta de concreto pequeña", "unit": "maceta", "minutes": 15, "items": [
        ["Cemento blanco", "kg", 25, 0.4], ["Arena fina", "kg", 25, 0.3], ["Pigmento", "g", 500, 5], ["Sellador", "ml", 1000, 15]]},
    "costura-tejido": {"label": "Bolso de trapillo", "unit": "bolso", "minutes": 240, "items": [
        ["Trapillo", "m", 120, 70], ["Base o asas", "unid.", 1, 1], ["Forro (opcional)", "m", 1, 0.4]]},
}


def build_calc():
    presets = {k: v for k, v in CALC_PRESETS.items() if k in CAT}
    rec = {}
    for k in presets:
        b = best_of(k) if k in [c["slug"] for c in CATS] else None
        if b:
            rec[k] = {"cat": CAT[k]["name"], "url": f"/mejores-cursos/{k}/", "course": b["name"], "curl": f"/cursos/{b['slug']}/"}
    data = json.dumps({"presets": presets, "rec": rec}, ensure_ascii=False).replace("</", "<\\/")
    opts = "".join(f'<option value="{k}">{CAT[k]["emoji"]} {E(v["label"])}</option>' for k, v in presets.items())
    faq = [
        ("¿Cómo calculo el costo de un material por pieza?", "Divide lo que pagaste por el paquete entre la cantidad que trae, y multiplícalo por lo que usas en cada pieza. Por ejemplo, si 1 kg de cera cuesta 40 y usas 0,18 kg por vela, el costo de cera por vela es 7,20."),
        ("¿Cuánto debo cobrar por mi tiempo?", "Pon lo que te gustaría ganar por hora trabajando. Si no cobras tu tiempo, cuando vendas más no podrás pagar a alguien que te ayude."),
        ("¿Qué margen de ganancia uso?", "En productos artesanales es común multiplicar el costo total entre 2 y 3 para el precio al público (100 % a 200 % de ganancia). El precio mayorista suele ser la mitad de esa ganancia."),
        ("¿Qué son los gastos generales?", "Luz, gas, agua, internet, desgaste de herramientas y moldes. Si no los conoces, un 10 % sobre los materiales es un buen punto de partida."),
    ]
    faq_html = "".join(f"<details class='faq'><summary>{E(q)}</summary><p>{E(a)}</p></details>" for q, a in faq)
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebApplication", "name": "Calculadora de precios para productos artesanales", "applicationCategory": "BusinessApplication",
         "operatingSystem": "Any", "offers": {"@type": "Offer", "price": 0, "priceCurrency": "USD"}, "url": DOMAIN + "/calculadora-de-precios/", "inLanguage": "es"},
        {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}]}
    body = f'''<div class="wrap">{crumbs([("Inicio", "/"), ("Calculadora de precios", None)])}</div>
<section class="wrap sec-top"><h1>Calculadora de precios para productos artesanales</h1>
<p class="lead">Calcula cuánto te cuesta cada pieza y a qué precio venderla: materiales, empaque, tu tiempo y gastos. Funciona con cualquier moneda.</p></section>
<section class="wrap calc" id="calc">
  <div class="calc-form">
    <div class="row2">
      <label>Producto de ejemplo<select id="preset"><option value="">Empezar en blanco</option>{opts}</select></label>
      <label>Moneda<input id="cur" value="S/" maxlength="5" autocomplete="off"></label>
    </div>
    <label>Nombre del producto<input id="pname" placeholder="Ej. vela aromática 200 g"></label>
    <h2 class="h3">1. Materiales por pieza</h2>
    <p class="muted small">Precio del paquete que compras, cuánto trae y cuánto usas en una pieza.</p>
    <div class="mat-head" aria-hidden="true"><span>Material</span><span>Precio paquete</span><span>Trae</span><span>Usas</span><span>Costo</span><span></span></div>
    <div id="mats"></div>
    <button type="button" class="btn ghost sm" id="addmat">+ Agregar material</button>
    <h2 class="h3">2. Empaque, tiempo y gastos</h2>
    <div class="row3">
      <label>Empaque y etiqueta por pieza<input id="pack" type="number" min="0" step="0.01" inputmode="decimal" placeholder="0"></label>
      <label>Minutos por pieza<input id="mins" type="number" min="0" step="1" inputmode="numeric"></label>
      <label>Lo que quieres ganar por hora<input id="hour" type="number" min="0" step="0.01" inputmode="decimal" placeholder="0"></label>
    </div>
    <div class="row3">
      <label>Gastos generales (% de materiales)<input id="over" type="number" min="0" step="1" value="10"></label>
      <label>Merma o pérdidas (%)<input id="waste" type="number" min="0" step="1" value="5"></label>
      <label>Comisión de cobro (%)<input id="fee" type="number" min="0" step="0.1" value="0"></label>
    </div>
    <h2 class="h3">3. Ganancia y metas</h2>
    <div class="row3">
      <label>Ganancia sobre el costo (%)<input id="markup" type="number" min="0" step="5" value="100"></label>
      <label>Inversión inicial (equipo, curso)<input id="invest" type="number" min="0" step="1" inputmode="decimal" placeholder="0"></label>
      <label>Piezas que venderás al mes<input id="perm" type="number" min="0" step="1" value="40"></label>
    </div>
  </div>
  <aside class="calc-out" aria-live="polite">
    <h2 class="h3">Resultado <span id="outname" class="muted"></span></h2>
    <dl class="res">
      <div><dt>Materiales</dt><dd id="r-mat">–</dd></div>
      <div><dt>Merma</dt><dd id="r-waste">–</dd></div>
      <div><dt>Gastos generales</dt><dd id="r-over">–</dd></div>
      <div><dt>Empaque</dt><dd id="r-pack">–</dd></div>
      <div><dt>Tu tiempo</dt><dd id="r-labor">–</dd></div>
      <div class="tot"><dt>Costo por pieza</dt><dd id="r-cost">–</dd></div>
    </dl>
    <div class="price-box"><span>Precio de venta sugerido</span><strong id="r-price">–</strong><small id="r-whole"></small></div>
    <dl class="res">
      <div><dt>Ganancia por pieza</dt><dd id="r-profit">–</dd></div>
      <div><dt>Ganancia al mes</dt><dd id="r-month">–</dd></div>
      <div><dt>Recuperas la inversión en</dt><dd id="r-be">–</dd></div>
    </dl>
    <p class="muted small" id="r-hint">Completa los precios de tus materiales para ver el resultado.</p>
    <div id="rec" class="rec" hidden></div>
    <button type="button" class="btn ghost sm" id="reset">Borrar todo</button>
  </aside>
</section>
<section class="wrap sec-sm narrow"><h2>Preguntas frecuentes</h2>{faq_html}{DISCLOSURE}</section>
<script type="application/json" id="calc-data">{data}</script>'''
    page("/calculadora-de-precios/", "Calculadora de precios para productos artesanales (gratis)",
         "Calcula el costo por pieza y el precio de venta de tus velas, jabones, resina, tazas sublimadas y más. Incluye precio mayorista y punto de equilibrio.",
         body, scripts=("assets/js/calc.js",), ld=ld)


def build_static():
    about = f'''<div class="wrap">{crumbs([("Inicio", "/"), ("Sobre nosotros", None)])}</div>
<section class="wrap sec-top narrow prose"><h1>Sobre {E(NAME)}</h1>
<p>{E(NAME)} ayuda a personas que quieren emprender desde casa a elegir un oficio artesanal y el curso adecuado para aprenderlo.</p>
<p>Hay cientos de cursos de manualidades en internet y es difícil saber cuáles valen la pena. Por eso revisamos el mercado de Hotmart en español, comparamos calificaciones y número de evaluaciones de compradores reales, leemos los temarios y descartamos los cursos con promesas exageradas.</p>
<p>También creamos herramientas gratuitas, como la <a href="/calculadora-de-precios/">calculadora de precios</a>, para que sepas cuánto cobrar por lo que haces.</p>
<p>Nos financiamos con comisiones de afiliado: si compras un curso desde nuestros enlaces, Hotmart nos paga una comisión sin costo extra para ti. Eso no cambia el orden de los cursos, que depende de sus calificaciones y su contenido. <a href="/aviso-de-afiliados/">Lee nuestro aviso de afiliados</a>.</p></section>'''
    page("/sobre-nosotros/", "Sobre nosotros", f"Quiénes somos y cómo elegimos los cursos que recomendamos en {NAME}.", about)
    aff = f'''<div class="wrap">{crumbs([("Inicio", "/"), ("Aviso de afiliados", None)])}</div>
<section class="wrap sec-top narrow prose"><h1>Aviso de afiliados</h1>
<p>{E(NAME)} participa en el programa de afiliados de Hotmart. Cuando haces clic en un botón como «Ver el curso en Hotmart» y compras, recibimos una comisión pagada por el productor del curso.</p>
<p><b>No pagas más por comprar desde nuestros enlaces.</b> El precio es el mismo que si entraras directamente.</p>
<p>Los cursos se ordenan según su calificación, el número de evaluaciones de compradores y la calidad del temario, no según la comisión. Recomendamos cursos con comisiones distintas y descartamos cursos con buenas comisiones que no cumplen nuestros criterios.</p>
<p>Las calificaciones, evaluaciones y precios provienen de Hotmart y se revisaron el {CHECKED_TXT}. Los precios pueden variar según tu país, la moneda y las promociones del productor. Confirma siempre el precio final y el plazo de garantía en la página de pago.</p>
<p>Los resultados de un emprendimiento dependen de cada persona. Ningún curso garantiza ingresos.</p></section>'''
    page("/aviso-de-afiliados/", "Aviso de afiliados", f"Cómo se financia {NAME} y cómo funcionan nuestros enlaces de afiliado de Hotmart.", aff)
    priv = f'''<div class="wrap">{crumbs([("Inicio", "/"), ("Privacidad", None)])}</div>
<section class="wrap sec-top narrow prose"><h1>Política de privacidad</h1>
<p>{E(NAME)} no tiene registro de usuarios ni formularios, y no usa cookies de publicidad.</p>
<p><b>Calculadora de precios.</b> Los datos que escribes se guardan solo en tu navegador (almacenamiento local) para que no los pierdas al volver. No se envían a ningún servidor. Puedes borrarlos con el botón «Borrar todo».</p>
<p><b>Enlaces a Hotmart.</b> Al hacer clic en un enlace de curso sales de este sitio. Hotmart usa sus propias cookies para registrar la compra y asignar la comisión de afiliado. Consulta la política de privacidad de Hotmart.</p>
<p><b>Servidor e imágenes.</b> El sitio se aloja en Netlify, que puede registrar datos técnicos como la dirección IP para seguridad. Las imágenes de los cursos se cargan desde los servidores de Hotmart. Las fuentes tipográficas se cargan desde Google Fonts.</p>
<p>Actualizado el {CHECKED_TXT}.</p></section>'''
    page("/privacidad/", "Política de privacidad", f"Qué datos trata {NAME} y cómo.", priv)
    nf = f'''<section class="wrap sec-top narrow"><h1>Página no encontrada</h1><p class="lead">La página que buscas no existe o cambió de dirección.</p>
<p><a class="btn" href="/">Ir al inicio</a> <a class="btn ghost" href="/calculadora-de-precios/">Calculadora de precios</a></p></section>'''
    page("/404.html", "Página no encontrada", "Página no encontrada.", nf, noindex=True)


def build_meta():
    today = dt.date.today().isoformat()
    urls = "".join(f"<url><loc>{DOMAIN}{p}</loc><lastmod>{today}</lastmod></url>" for p in PAGES)
    (DIST / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n', encoding="utf-8")
    robots = "User-agent: *\nDisallow: /\n" if DRAFT else f"User-agent: *\nAllow: /\n\nSitemap: {DOMAIN}/sitemap.xml\n"
    (DIST / "robots.txt").write_text(robots, encoding="utf-8")


def validate():
    errs = []
    for f in DIST.rglob("*.html"):
        t = f.read_text(encoding="utf-8")
        for a in re.findall(r"<a [^>]*hotmart\.com[^>]*>", t):
            if 'rel="sponsored nofollow noopener"' not in a:
                errs.append(f"{f}: enlace de afiliado sin rel sponsored: {a[:120]}")
        for href in re.findall(r'href="(/[^"#?]*)', t):
            target = DIST / href.lstrip("/")
            if not (target.exists() or (target / "index.html").exists()):
                errs.append(f"{f.relative_to(DIST)}: enlace interno roto {href}")
    if errs:
        raise SystemExit("\n".join(sorted(set(errs))[:40]))


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(SRC, DIST)
    build_home()
    for c in COURSES:
        build_course(c)
    for k in CATS:
        build_category(k)
    build_chooser()
    build_calc()
    build_static()
    build_meta()
    validate()
    mode = "BORRADOR (noindex)" if DRAFT else "PRODUCCIÓN"
    print(f"{mode}: {len(PAGES)} páginas · {len(COURSES)} cursos · {len(CATS)} oficios -> {DIST}")
    if missing:
        print(f"Faltan hotlinks ({len(missing)}): " + ", ".join(f"{c['id']} {c['name']}" for c in missing))


if __name__ == "__main__":
    main()
