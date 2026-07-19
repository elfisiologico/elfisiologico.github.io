# FisioLógico

Web pública de FisioLógico y repositorio de lectura crítica aplicada a fisioterapia.

Cada ficha científica enlaza la fuente original y presenta de forma accesible los resultados, sus límites y su posible utilidad clínica. El contenido tiene finalidad informativa y no sustituye una valoración sanitaria individual.

FisioLógico utiliza un criterio editorial propio. El procedimiento detallado de evaluación y sus herramientas forman parte del trabajo interno de la marca y no se distribuyen en este repositorio público.

## Regeneración y control de calidad

```bash
python3 scripts/build_site.py
python3 scripts/build_instruments.py
python3 scripts/build_clinical_tests.py
python3 scripts/sync_navigation.py
python3 scripts/validate_clinical_tests.py
python3 scripts/seo_audit.py
python3 scripts/ai_search_audit.py
python3 scripts/ai_search_audit.py --live
python3 scripts/submit_indexnow.py --all --dry-run
```

La navegación pública se organiza por audiencias: `patients/` para pacientes y `profesionales/` como entrada a evidencia, instrumentos y pruebas clínicas.

La auditoría AEO/GEO comprueba rastreadores de búsqueda con IA, disponibilidad de snippets, contenido citable, entidades, fechas, fuentes y consistencia de JSON-LD. La opción `--live` valida además que producción no redirige fuera del dominio canónico y entrega los archivos y schemas esperados a los bots. Tras publicar cambios relevantes, `submit_indexnow.py --all` notifica el sitemap a los motores compatibles; el modo `--dry-run` valida la carga sin enviarla.
