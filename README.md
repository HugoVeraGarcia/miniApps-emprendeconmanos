# Emprende con Manos — emprendeconmanos.com

Sitio de afiliados de Hotmart (español): comparativas de cursos para emprender con oficios artesanales + calculadora de precios.

## Build
- Producción: `python3 tools/build.py` → `dist/` (publica solo los cursos que tienen hotlink).
- Vista previa: `python3 tools/build.py --draft` (todos los cursos, `noindex`, botón "Enlace pendiente" si falta el hotlink).

## Datos
- `data/links.json`: hotlink de Hotmart por ID de curso (`https://go.hotmart.com/XXXX`). Un curso sin hotlink no se publica.
- `data/courses.json`: fichas (calificación, evaluaciones, precio de referencia, temario, a favor/en contra, veredicto). Revisar precios y evaluaciones cada 1–2 meses.
- `data/site.json`: oficios (categorías), fecha de revisión `checked`, `pinterest_verify`.

## Deploy
GitHub → Netlify (build `python3 tools/build.py`, publish `dist`). Dominio en Namecheap:
- `A @ 75.2.60.5` y `CNAME www <sitio>.netlify.app`, o usar Netlify DNS.

## Validación del build
Falla si un enlace de afiliado no tiene `rel="sponsored nofollow noopener"`, si hay enlaces internos rotos o si un hotlink no tiene formato `go.hotmart.com`/`pay.hotmart.com`.
