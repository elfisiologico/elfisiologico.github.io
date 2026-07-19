# Inventario de fuentes científicas

Actualizado: 2026-07-14

## Resumen

| Estado | Cantidad |
|---|---:|
| Artículos inventariados | 46 |
| Evaluaciones v2 completas/publicables | 37 |
| PDF principales archivados | 35 |
| Textos completos JATS de PMC archivados | 23 |
| Artículos pendientes de original | 9 |

Los PDF y JATS permanecen en iCloud y fuera del despliegue web. Las fichas públicas enlazan al DOI, editor y PubMed; nunca distribuyen copias locales.

## Estructura

- `pdfs-originales/<PMID>.pdf`: PDF principal entregado por Fran o recuperado legalmente de una fuente abierta.
- `texto-completo-pmc/<PMID>.nxml`: texto completo JATS obtenido del paquete oficial OA de PubMed Central.
- `material-suplementario/`: protocolos, apéndices y suplementos cuando sean relevantes para riesgo de sesgo.

## Pendientes

La relación canónica y los enlaces están en [`../docs/solicitud-pdfs-repositorio.md`](../docs/solicitud-pdfs-repositorio.md). Son seis originales no disponibles y tres depósitos PMC bajo embargo.

## Control de integridad

- El nombre canónico siempre es el PMID.
- Un PMCID asignado no equivale a acceso inmediato: se comprueba el paquete OA.
- Un suplemento nunca se archiva como si fuera el PDF principal.
- Una ficha solo entra en producción con `rubric_v2.status = complete`.
- La puntuación histórica se conserva, pero nunca sustituye la reevaluación por outcome.
