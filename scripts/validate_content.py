#!/usr/bin/env python3
"""Valida los registros editoriales antes de generar o publicar."""
import json, re, sys
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ALLOWED={c["slug"] for c in json.loads((ROOT/"data/categories.json").read_text())}
REQUIRED={"slug","title","title_es","year","category","category_name","study_design","population","citation","clinical_takeaway","critical_analysis","clinical_application","limitations","references","source","review","rubric_history","rubric_v2","legacy_paths"}
RUBRIC={"diseño","muestra","sesgos","variables","transferencia","coherencia"}
RUBRIC_V2={"question_design","internal_validity","sample_precision","outcomes_measurement","magnitude_balance","directness_transfer"}
V2_BANDS={(0,11):"insufficient",(12,17):"exploratory",(18,23):"informative_with_caution",(24,27):"consistent",(28,30):"exceptional"}
GATES={"critical_risk_of_bias","non_causal_design","acute_to_chronic","unvalidated_surrogate","nonhuman_or_model","low_transfer","no_adequate_comparator","imprecise_decision","harm_compatible","selective_reporting_concern","unverifiable_source","insufficient_core_data","conclusion_overreach"}
VISUAL_RIGHTS={"fisiologico_original","cc0","cc_by","cc_by_sa","written_permission"}
VISUAL_KINDS={"ultrasound","scientific_figure","diagram","clinical_photo","chart"}
VISUAL_ROLES={"anatomy","acquisition","measurement","comparison","result","limitation"}
VISUAL_SOURCE_TYPES={"fisiologico_original","article_figure","permissioned_third_party"}
VISUAL_REVIEW_START=date(2026,7,26)
VISUAL_REVIEW_STATUSES={"approved_and_used","checked_no_usable_rights","checked_not_useful","not_applicable"}
VISUAL_EVIDENCE_TYPES={"publisher_license","article_license_statement","figure_caption","pmc_license","written_permission"}

def expected_v2_band(total):
    return next(label for (low,high),label in V2_BANDS.items() if low <= total <= high)

def validate_public_text(value, location, errors):
    if not isinstance(value,str) or not value.strip():
        errors.append(f"{location} requiere texto no vacío"); return
    if value != value.strip(): errors.append(f"{location} contiene espacios al inicio o al final")
    if re.search(r"[ \t]{2,}",value): errors.append(f"{location} contiene espacios repetidos")
    forbidden={
        r"\boutcomes?\b":"resultado",
        r"\bhot pack\b":"compresa caliente",
        r"\bsupplementary material\b":"material suplementario",
    }
    for pattern,replacement in forbidden.items():
        if re.search(pattern,value,re.I): errors.append(f"{location} usa un anglicismo evitable; utilizar «{replacement}»")

def validate_intervention_protocol(a, errors):
    protocol=a.get("intervention_protocol")
    if protocol is None:return
    if not isinstance(protocol,dict): errors.append("intervention_protocol debe ser un objeto"); return
    required={"summary","facts","groups","shared_components","source_note"}
    missing=required-set(protocol)
    if missing: errors.append(f"intervention_protocol: faltan {', '.join(sorted(missing))}"); return
    validate_public_text(protocol["summary"],"intervention_protocol.summary",errors)
    validate_public_text(protocol["source_note"],"intervention_protocol.source_note",errors)
    facts=protocol["facts"]
    if not isinstance(facts,list) or len(facts)<2: errors.append("intervention_protocol.facts requiere al menos dos datos")
    else:
        for index,item in enumerate(facts,1):
            if not isinstance(item,dict): errors.append(f"intervention_protocol.facts[{index}] debe ser un objeto"); continue
            validate_public_text(item.get("label"),f"intervention_protocol.facts[{index}].label",errors)
            validate_public_text(item.get("value"),f"intervention_protocol.facts[{index}].value",errors)
            if len(item.get("label",""))>48: errors.append(f"intervention_protocol.facts[{index}].label supera 48 caracteres")
    groups=protocol["groups"]
    if not isinstance(groups,list) or not groups: errors.append("intervention_protocol.groups requiere al menos un grupo")
    else:
        for group_index,group in enumerate(groups,1):
            if not isinstance(group,dict): errors.append(f"intervention_protocol.groups[{group_index}] debe ser un objeto"); continue
            for field in ("name","description"):
                validate_public_text(group.get(field),f"intervention_protocol.groups[{group_index}].{field}",errors)
            progression=group.get("progression")
            if not isinstance(progression,list) or not progression:
                errors.append(f"intervention_protocol.groups[{group_index}].progression requiere al menos un tramo"); continue
            for step_index,step in enumerate(progression,1):
                if not isinstance(step,dict): errors.append(f"intervention_protocol.groups[{group_index}].progression[{step_index}] debe ser un objeto"); continue
                location=f"intervention_protocol.groups[{group_index}].progression[{step_index}]"
                validate_public_text(step.get("period"),f"{location}.period",errors)
                validate_public_text(step.get("exercises"),f"{location}.exercises",errors)
                if len(step.get("period",""))>72: errors.append(f"{location}.period supera 72 caracteres y compromete la jerarquía visual")
    shared=protocol["shared_components"]
    if not isinstance(shared,list): errors.append("intervention_protocol.shared_components debe ser una lista")
    else:
        for index,item in enumerate(shared,1): validate_public_text(item,f"intervention_protocol.shared_components[{index}]",errors)

def validate_measurement_battery(a, errors):
    battery=a.get("measurement_battery")
    if battery is None:return
    if not isinstance(battery,dict): errors.append("measurement_battery debe ser un objeto"); return
    required={"summary","groups","source_note"}
    missing=required-set(battery)
    if missing: errors.append(f"measurement_battery: faltan {', '.join(sorted(missing))}"); return
    validate_public_text(battery["summary"],"measurement_battery.summary",errors)
    validate_public_text(battery["source_note"],"measurement_battery.source_note",errors)
    groups=battery["groups"]
    if not isinstance(groups,list) or not groups: errors.append("measurement_battery.groups requiere al menos un grupo"); return
    short_names=[]
    for group_index,group in enumerate(groups,1):
        if not isinstance(group,dict): errors.append(f"measurement_battery.groups[{group_index}] debe ser un objeto"); continue
        for field in ("name","description"):
            validate_public_text(group.get(field),f"measurement_battery.groups[{group_index}].{field}",errors)
        items=group.get("items")
        if not isinstance(items,list) or not items:
            errors.append(f"measurement_battery.groups[{group_index}].items requiere al menos un instrumento"); continue
        for item_index,item in enumerate(items,1):
            if not isinstance(item,dict): errors.append(f"measurement_battery.groups[{group_index}].items[{item_index}] debe ser un objeto"); continue
            location=f"measurement_battery.groups[{group_index}].items[{item_index}]"
            for field in ("short_name","name","measures","procedure","scoring","clinical_note"):
                validate_public_text(item.get(field),f"{location}.{field}",errors)
            short_name=item.get("short_name","")
            short_names.append(short_name.casefold())
            if len(short_name)>16: errors.append(f"{location}.short_name supera 16 caracteres")
            if item.get("internal_url") and not re.fullmatch(r"(?:\.\./)+[a-z0-9][a-z0-9/-]*/",item["internal_url"]):
                errors.append(f"{location}.internal_url debe ser una ruta interna relativa y canónica")
    if len(short_names)!=len(set(short_names)): errors.append("measurement_battery no puede repetir abreviaturas")

def validate_technical_protocol(a, errors):
    protocol=a.get("technical_protocol")
    if protocol is None:return
    if not isinstance(protocol,dict): errors.append("technical_protocol debe ser un objeto"); return
    required={"title","summary","facts","steps","cautions","source_note"}
    missing=required-set(protocol)
    if missing: errors.append(f"technical_protocol: faltan {', '.join(sorted(missing))}"); return
    for field in ("title","summary","source_note"):
        validate_public_text(protocol.get(field),f"technical_protocol.{field}",errors)
    facts=protocol.get("facts")
    if not isinstance(facts,list) or len(facts)<2: errors.append("technical_protocol.facts requiere al menos dos datos")
    else:
        for index,item in enumerate(facts,1):
            if not isinstance(item,dict): errors.append(f"technical_protocol.facts[{index}] debe ser un objeto"); continue
            validate_public_text(item.get("label"),f"technical_protocol.facts[{index}].label",errors)
            validate_public_text(item.get("value"),f"technical_protocol.facts[{index}].value",errors)
            if len(item.get("label",""))>48: errors.append(f"technical_protocol.facts[{index}].label supera 48 caracteres")
    steps=protocol.get("steps")
    if not isinstance(steps,list) or len(steps)<2: errors.append("technical_protocol.steps requiere al menos dos pasos")
    else:
        for index,item in enumerate(steps,1):
            if not isinstance(item,dict): errors.append(f"technical_protocol.steps[{index}] debe ser un objeto"); continue
            for field in ("title","procedure","landmarks","interpretation"):
                validate_public_text(item.get(field),f"technical_protocol.steps[{index}].{field}",errors)
    cautions=protocol.get("cautions")
    if not isinstance(cautions,list) or not cautions: errors.append("technical_protocol.cautions requiere al menos una cautela")
    else:
        for index,item in enumerate(cautions,1):
            validate_public_text(item,f"technical_protocol.cautions[{index}]",errors)

def validate_visual_assets(a, errors):
    assets=a.get("visual_assets")
    if assets is None:return
    if not isinstance(assets,list): errors.append("visual_assets debe ser una lista"); return
    ids=[]
    required={"id","kind","role","file","width","height","source_type","source_url","creator","rights_basis","attribution","modified","alt","caption","clinical_limit","contains_identifiable_person","consent_status","license_reviewed_at"}
    for index,item in enumerate(assets,1):
        location=f"visual_assets[{index}]"
        if not isinstance(item,dict): errors.append(f"{location} debe ser un objeto"); continue
        missing=required-set(item)
        if missing: errors.append(f"{location}: faltan {', '.join(sorted(missing))}"); continue
        asset_id=item.get("id","")
        ids.append(asset_id.casefold())
        if not re.fullmatch(r"[a-z0-9-]+",asset_id): errors.append(f"{location}.id debe ser canónico")
        if item.get("kind") not in VISUAL_KINDS: errors.append(f"{location}.kind no permitido")
        if item.get("role") not in VISUAL_ROLES: errors.append(f"{location}.role no permitido")
        if item.get("source_type") not in VISUAL_SOURCE_TYPES: errors.append(f"{location}.source_type no permitido")
        rights=item.get("rights_basis")
        if rights not in VISUAL_RIGHTS: errors.append(f"{location}.rights_basis bloqueado o desconocido")
        file_path=item.get("file","")
        expected_prefix=f"assets/articles/{a.get('slug','')}/"
        if not file_path.startswith(expected_prefix) or not re.fullmatch(r"assets/articles/[a-z0-9-]+/[a-z0-9._-]+",file_path):
            errors.append(f"{location}.file debe estar dentro de {expected_prefix}")
        elif not (ROOT/file_path).is_file(): errors.append(f"{location}.file no existe")
        for dimension in ("width","height"):
            if not isinstance(item.get(dimension),int) or item[dimension] <= 0: errors.append(f"{location}.{dimension} debe ser un entero positivo")
        for field in ("creator","attribution","alt","caption","clinical_limit"):
            validate_public_text(item.get(field),f"{location}.{field}",errors)
        if not 20 <= len(item.get("alt","")) <= 240: errors.append(f"{location}.alt debe tener 20–240 caracteres")
        if not re.fullmatch(r"https?://[^\s]+",item.get("source_url","")): errors.append(f"{location}.source_url debe ser una URL verificable")
        license_url=item.get("license_url","")
        license_patterns={
            "cc0":r"https://creativecommons\.org/publicdomain/zero/[0-9.]+/?",
            "cc_by":r"https://creativecommons\.org/licenses/by/[0-9.]+/?",
            "cc_by_sa":r"https://creativecommons\.org/licenses/by-sa/[0-9.]+/?",
        }
        if rights in license_patterns and not re.fullmatch(license_patterns[rights],license_url):
            errors.append(f"{location}.license_url no coincide con rights_basis {rights}")
        if rights == "written_permission" and not item.get("permission_reference"):
            errors.append(f"{location} requiere permission_reference interno")
        if item.get("source_type") == "article_figure" and not item.get("figure_reference"):
            errors.append(f"{location} requiere figure_reference")
        if item.get("source_type") == "fisiologico_original" and rights != "fisiologico_original":
            errors.append(f"{location}: una creación propia debe usar rights_basis fisiologico_original")
        if item.get("modified") is True:
            validate_public_text(item.get("modifications"),f"{location}.modifications",errors)
            if rights == "cc_by_sa" and item.get("adaptation_license_url") != license_url:
                errors.append(f"{location}: una adaptación CC BY-SA debe conservar la misma licencia")
        elif item.get("modifications"):
            errors.append(f"{location}.modifications solo procede si modified es true")
        if item.get("contains_identifiable_person") is True:
            if item.get("consent_status") != "documented" or not item.get("consent_reference"):
                errors.append(f"{location}: contenido identificable exige consentimiento documentado y referencia interna")
        elif item.get("consent_status") != "not_applicable":
            errors.append(f"{location}.consent_status debe ser not_applicable cuando no hay una persona identificable")
        try: date.fromisoformat(item.get("license_reviewed_at",""))
        except ValueError: errors.append(f"{location}.license_reviewed_at debe usar YYYY-MM-DD")
    if len(ids)!=len(set(ids)): errors.append("visual_assets no puede repetir identificadores")

def validate_visual_review(a, errors):
    review=a.get("review",{})
    try: requires_review=date.fromisoformat(review.get("updated_at","")) >= VISUAL_REVIEW_START
    except ValueError: requires_review=False
    visual_review=a.get("visual_review")
    if visual_review is None:
        if requires_review: errors.append("visual_review es obligatorio en artículos nuevos o actualizados desde 2026-07-26")
        return
    if not isinstance(visual_review,dict): errors.append("visual_review debe ser un objeto"); return
    required={"status","checked_at","decision_reason","official_sources","candidates"}
    missing=required-set(visual_review)
    if missing: errors.append(f"visual_review: faltan {', '.join(sorted(missing))}"); return
    status=visual_review.get("status")
    if status not in VISUAL_REVIEW_STATUSES: errors.append("visual_review.status no permitido")
    reason=visual_review.get("decision_reason","")
    if not isinstance(reason,str) or len(reason.strip())<20: errors.append("visual_review.decision_reason requiere una decisión explícita")
    try:
        checked_at=date.fromisoformat(visual_review.get("checked_at",""))
        updated_at=date.fromisoformat(review.get("updated_at",""))
        if checked_at > updated_at: errors.append("visual_review.checked_at no puede ser posterior a review.updated_at")
    except ValueError: errors.append("visual_review.checked_at debe usar YYYY-MM-DD")
    sources=visual_review.get("official_sources")
    if not isinstance(sources,list): errors.append("visual_review.official_sources debe ser una lista"); sources=[]
    if status != "not_applicable" and not sources: errors.append("visual_review requiere al menos una fuente oficial")
    for index,source in enumerate(sources,1):
        location=f"visual_review.official_sources[{index}]"
        if not isinstance(source,dict): errors.append(f"{location} debe ser un objeto"); continue
        if source.get("type") not in VISUAL_EVIDENCE_TYPES: errors.append(f"{location}.type no permitido")
        if not re.fullmatch(r"https?://[^\s]+",source.get("url","")): errors.append(f"{location}.url debe ser verificable")
        if len(source.get("evidence","").strip())<10: errors.append(f"{location}.evidence requiere evidencia concreta")
    candidates=visual_review.get("candidates")
    if not isinstance(candidates,list): errors.append("visual_review.candidates debe ser una lista"); candidates=[]
    used=[]
    for index,candidate in enumerate(candidates,1):
        location=f"visual_review.candidates[{index}]"
        if not isinstance(candidate,dict): errors.append(f"{location} debe ser un objeto"); continue
        for field in ("figure_reference","utility","rationale"):
            if not isinstance(candidate.get(field),str) or not candidate[field].strip(): errors.append(f"{location}.{field} es obligatorio")
        rights_status=candidate.get("rights_status")
        decision=candidate.get("decision")
        if rights_status not in {"approved","rejected","uncertain"}: errors.append(f"{location}.rights_status no permitido")
        if decision not in {"use","omit"}: errors.append(f"{location}.decision no permitido")
        if decision == "use":
            used.append(candidate.get("figure_reference"))
            if rights_status != "approved": errors.append(f"{location}: solo una figura approved puede utilizarse")
    assets=a.get("visual_assets",[])
    asset_refs={item.get("figure_reference") for item in assets if isinstance(item,dict)}
    if status == "approved_and_used":
        if not assets or not used: errors.append("visual_review approved_and_used exige figuras aprobadas en visual_assets")
        for reference in used:
            if reference not in asset_refs: errors.append(f"visual_review: la figura usada {reference!r} no está registrada en visual_assets")
    elif assets:
        errors.append(f"visual_review.status {status} no permite visual_assets")
    if status in {"checked_no_usable_rights","checked_not_useful"} and not candidates:
        errors.append(f"visual_review.status {status} requiere registrar figuras candidatas")

def validate_v2(a, errors, is_migrated):
    history=a.get("rubric_history",{})
    if not isinstance(history,dict): errors.append("rubric_history debe ser un objeto")
    if all(k in a for k in ("score","tier","rubric")):
        v1=history.get("v1",{})
        if v1.get("score") != a["score"] or v1.get("tier") != a["tier"] or v1.get("dimensions") != a["rubric"]:
            errors.append("rubric_history.v1 debe preservar exactamente la evaluación histórica")
    v2=a.get("rubric_v2",{})
    if v2.get("status") == "pending_reassessment":
        for field in ("priority","reason","queued_at"):
            if not v2.get(field): errors.append(f"rubric_v2 pendiente requiere {field}")
        if not is_migrated: errors.append("el contenido nuevo requiere evaluación v2 completa")
        return
    if v2.get("status") != "complete":
        errors.append("rubric_v2.status debe ser complete o pending_reassessment"); return
    for field in ("question_type","target_claim","primary_outcome","outcome_type","design_module","risk_of_bias","dimensions","total","band","gates","inference_signal","allowed_scope","prohibited_claims","reassessed_at"):
        if field not in v2: errors.append(f"rubric_v2 completo requiere {field}")
    dims=v2.get("dimensions",{})
    if set(dims) != RUBRIC_V2: errors.append("rubric_v2 debe contener exactamente seis dimensiones")
    else:
        for name,item in dims.items():
            if not isinstance(item.get("score"),int) or not 0 <= item["score"] <= 5: errors.append(f"rubric_v2.{name}.score fuera de 0–5")
            if len(item.get("justification","")) < 30: errors.append(f"rubric_v2.{name} requiere justificación explícita")
            if not isinstance(item.get("evidence"),list) or not item["evidence"]: errors.append(f"rubric_v2.{name} requiere evidencia observable")
            if not isinstance(item.get("concerns"),list): errors.append(f"rubric_v2.{name}.concerns debe ser lista")
        total=sum(item.get("score",0) for item in dims.values())
        if v2.get("total") != total: errors.append("rubric_v2.total no coincide con sus dimensiones")
        elif v2.get("band") != expected_v2_band(total): errors.append("rubric_v2.band no coincide con el total")
        if dims["directness_transfer"].get("score",5) <= 2 and "low_transfer" not in {g.get("code") for g in v2.get("gates",[])}:
            errors.append("transferencia ≤2 exige gate low_transfer")
    gate_codes={g.get("code") for g in v2.get("gates",[])}
    if not gate_codes <= GATES: errors.append("rubric_v2 contiene gates no permitidos")
    if v2.get("inference_signal") not in {"green","amber","red"}: errors.append("inference_signal no permitido")
    try: date.fromisoformat(v2.get("reassessed_at",""))
    except ValueError: errors.append("rubric_v2.reassessed_at debe usar YYYY-MM-DD")

def validate(path):
    a=json.loads(path.read_text(encoding="utf-8")); errors=[]
    missing=REQUIRED-set(a); errors += [f"faltan: {', '.join(sorted(missing))}"] if missing else []
    if missing:return errors
    if a["category"] not in ALLOWED: errors.append("categoría no permitida")
    category_names={c["slug"]:c["name"] for c in json.loads((ROOT/"data/categories.json").read_text())}
    if a["category"] in category_names and a["category_name"] != category_names[a["category"]]: errors.append("category_name no coincide con la categoría canónica")
    if "score" in a:
        if not isinstance(a["score"],int) or not 0 <= a["score"] <= 30: errors.append("score histórico fuera de 0–30")
        expected="solida" if a["score"]>=24 else "moderada" if a["score"]>=18 else "exploratoria"
        if a.get("tier") != expected: errors.append(f"tier histórico debe ser {expected}")
        if set(a.get("rubric",{})) != RUBRIC: errors.append("rúbrica histórica debe contener exactamente seis dimensiones")
        elif sum(a["rubric"].values()) != a["score"]: errors.append("la suma de la rúbrica histórica no coincide con score")
    for field in ("critical_analysis","clinical_application","limitations"):
        if not isinstance(a[field],list) or not a[field]: errors.append(f"{field} debe ser una lista no vacía")
    if len(a["clinical_takeaway"]) < 80: errors.append("clinical_takeaway debe aportar una síntesis útil de al menos 80 caracteres")
    card=a.get("card",{})
    if card:
        for field,low,high in (("question",25,140),("answer",45,240),("key_data",8,120)):
            if not low <= len(card.get(field,"")) <= high: errors.append(f"card.{field} debe tener {low}–{high} caracteres")
    validate_intervention_protocol(a,errors)
    validate_measurement_battery(a,errors)
    validate_technical_protocol(a,errors)
    validate_visual_assets(a,errors)
    validate_visual_review(a,errors)
    related_articles=a.get("related_articles",[])
    if not isinstance(related_articles,list):
        errors.append("related_articles debe ser una lista")
    elif len(related_articles)>6:
        errors.append("related_articles admite un máximo de seis enlaces")
    else:
        related_slugs=[]
        for index,item in enumerate(related_articles,1):
            location=f"related_articles[{index}]"
            if not isinstance(item,dict):
                errors.append(f"{location} debe ser un objeto"); continue
            slug=item.get("slug","")
            reason=item.get("reason","")
            if not re.fullmatch(r"[a-z0-9-]+",slug): errors.append(f"{location}.slug no es canónico")
            if slug==a["slug"]: errors.append(f"{location} no puede enlazar la propia ficha")
            if not 20<=len(reason)<=140: errors.append(f"{location}.reason debe tener 20–140 caracteres")
            target=ROOT/"content/articles"/f"{slug}.json"
            if slug and not target.exists():
                errors.append(f"{location} apunta a una ficha inexistente: {slug}")
            elif slug:
                target_data=json.loads(target.read_text(encoding="utf-8"))
                backlinks={link.get("slug") for link in target_data.get("related_articles",[]) if isinstance(link,dict)}
                if a["slug"] not in backlinks: errors.append(f"{location} requiere enlace recíproco desde {slug}")
            related_slugs.append(slug)
        if len(related_slugs)!=len(set(related_slugs)): errors.append("related_articles contiene enlaces repetidos")
    is_migrated=a.get("review",{}).get("status","").startswith("migrado_")
    validate_v2(a,errors,is_migrated)
    placeholder="No informado de forma separada en el análisis histórico."
    if placeholder in a["population"]: errors.append("population requiere población o unidad de análisis verificada")
    if any(placeholder in x for x in a["limitations"]): errors.append("limitations requiere límites editoriales explícitos")
    source=a.get("source",{})
    if not source.get("pmid") or not source.get("pubmed_url") or not source.get("original_url"): errors.append("fuente original incompleta")
    if source.get("pubmed_url") != f"https://pubmed.ncbi.nlm.nih.gov/{source.get('pmid')}/": errors.append("URL de PubMed no canónica")
    review=a.get("review",{})
    for field in ("published_at","updated_at"):
        try: date.fromisoformat(review.get(field,""))
        except ValueError: errors.append(f"review.{field} debe usar YYYY-MM-DD")
    if review.get("published_at","") > review.get("updated_at",""): errors.append("published_at no puede ser posterior a updated_at")
    seo=a.get("seo",{})
    if seo.get("title") and not 20 <= len(seo["title"]) <= 75: errors.append("seo.title debe tener 20–75 caracteres")
    if seo.get("description") and not 100 <= len(seo["description"]) <= 170: errors.append("seo.description debe tener 100–170 caracteres")
    if not is_migrated:
        forbidden=re.compile(r"\b(demuestra|cura|garantiza|soluciona)\b",re.I)
        for field in ("clinical_takeaway","critical_analysis","clinical_application","limitations"):
            values=[a[field]] if isinstance(a[field],str) else a[field]
            if any(forbidden.search(value) for value in values): errors.append(f"{field} contiene lenguaje causal o promocional prohibido")
    return errors

def main():
    failed=False; files=sorted((ROOT/"content/articles").glob("*.json"))
    for path in files:
        errors=validate(path)
        print(f"{'ERROR' if errors else 'OK'} {path.name}" + (f": {'; '.join(errors)}" if errors else "")); failed |= bool(errors)
    print(f"Validados {len(files)} artículos.")
    sys.exit(1 if failed else 0)
if __name__=="__main__":main()
