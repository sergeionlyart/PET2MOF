#!/usr/bin/env python3
"""Reproduce a region-assisted glyph-survival audit, not a blind table parser.

Reference annotations are entered from the inspected 200 dpi source renders.
No numerical tolerance, superscript folding or guessed relationships is used.
"""
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from collections import Counter, defaultdict
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from pet2mof.ocr.cache import RawCache, cache_key
from pet2mof.ocr.local import extract_local
from pet2mof.provenance.extraction import validate_extraction
import yaml

FIELDS = []


def add(page, region, locator, category, values, alternatives=None):
    for i, value in enumerate(values):
        FIELDS.append(dict(field_id=f"{page}-{len(FIELDS)+1:03d}", extraction_id="T006-"+page,
                           region_norm=region, locator=locator, category=category,
                           expected=value, lossy_alternative=(alternatives or {}).get(value),
                           reference_basis="visual inspection of the source page PNG at 200 dpi",
                           reference_status="provisional; T007 independent check pending"))


def reference():
    # Coordinates are relative to the entire source PDF page; top-left origin.
    add("S100-p02",[.17,.57,.83,.88],"§S1 synthesis, lower paragraph", "numbers",["50","2.5","36.5","353","423","8"])
    add("S100-p02",[.17,.57,.83,.88],"§S1 synthesis", "units",["353 K","423 K","8 h"])
    add("S100-p02",[.17,.57,.83,.88],"§S1 precursor", "symbols",["ZrCl₄"],{"ZrCl₄":"ZrCl4"})
    add("S100-p03",[.17,.10,.83,.35],"§S2 first paragraph: apparatus precision", "numbers",["0.5","3"])
    add("S100-p03",[.17,.10,.83,.35],"§S2 precision", "symbols",["±0.5","±3%"])
    add("S100-p03",[.17,.35,.83,.76],"§S2 second paragraph: conditions", "units",["100 mg","1 bar"])
    add("S100-p03",[.17,.35,.83,.76],"§S2 gas names", "symbols",["CO₂","CH₄","H₂O"],{"CO₂":"CO2","CH₄":"CH4","H₂O":"H2O"})
    add("S100-p04",[.2,.32,.84,.47],"Fig. S1 caption, instrument list", "numbers",["10","11","12","13"])
    add("S100-p04",[.2,.70,.70,.77],"Eq. (1), free-volume correction, minus sign", "symbols",["−"])
    add("S100-p04",[.2,.70,.70,.77],"Eq. (1): qi=Ci p/(mads RT) × (Vt−Vcol+mads/rhoads)", "relationships",["qᵢ = Cᵢp/(m_ads RT) × (Vt − V_col + m_ads/ρ_ads)"])
    add("S100-p05",[.2,.13,.69,.23],"Eq. (2), integration and subtraction", "symbols",["∫","−"])
    add("S100-p05",[.2,.13,.69,.23],"Eq. (2), integration of concentration ratio", "relationships",["t = ∫(1 − Cₜ/Cᵢ)dt"])
    add("S100-p05",[.2,.48,.69,.55],"Eq. (3), ratio of ratios", "relationships",["Sᵢⱼ = (qᵢ/qⱼ)/(Xᵢ/Xⱼ)"])
    add("S100-p07",[.3,.1,.75,.36],"Fig. S4 y axis and legend", "units",["mmol/m²"],{"mmol/m²":"mmol/m2"})
    add("S100-p07",[.25,.53,.75,.83],"Fig. S5 axes", "units",["mmol/g","kPa"])
    add("S100-p07",[.25,.53,.75,.83],"Fig. S5 y major ticks", "numbers",["0.5","3.5"])
    add("S100-p07",[.25,.53,.75,.83],"Fig. S5 axes", "symbols",["CO₂","P/P₀"])
    add("S100-p07",[.25,.53,.75,.83],"Fig. S5 symbols: marker shape/colour and material; temperature unknown in this caption", "relationships",["black square → UiO-66", "red circle → 10PEI@UiO-66", "blue up-triangle → 20PEI@UiO-66", "magenta down-triangle → 30PEI@UiO-66", "green diamond → 40PEI@UiO-66"])
    table = [
        ("UiO-66",["1.463","0.0126","72.940","1.7583E-4","0.99994"]),
        ("10PEI@UiO-66",["0.698","0.653","7.621","0.00299","0.99999"]),
        ("20PEI@UiO-66",["0.833","0.477","8.124","0.00307","0.99986"]),
        ("30PEI@UiO-66",["1.056","0.395","5.558","0.00307","0.99945"]),
        ("40PEI@UiO-66",["1.253","2.345","1.578","0.0115","0.99991"])]
    for i,(material, values) in enumerate(table):
        box=[.17,.698+i*.0278,.82,.726+i*.0278]
        add("S100-p09",box,f"Table S1 row {material}, columns q1/b1/q2/d2/R² (author fit)","numbers",values)
        add("S100-p09",box,f"Table S1 row {material}","relationships",[material+" | q1,b1,q2,d2,R² | "+",".join(values)])
    add("S100-p09",[.17,.665,.82,.697],"Table S1 headers (d2 preserved verbatim)","symbols",["q₁","d₂","R²"],{"q₁":"q1","d₂":"d2","R²":"R2"})
    add("S100-p09",[.2,.46,.83,.53],"Fig. S8 caption, parent material and conditions", "numbers",["308"])
    add("S100-p09",[.27,.13,.75,.42],"Fig. S8 legend", "relationships",["UiO-66 | CO₂/CH₄ | 308 K | 80% RH"])
    add("S106-p03",[.51,.32,.95,.49],"§2 Experimental, synthesis/activation paragraph (right column)","numbers",["621","2.66","0.634","65.8"])
    add("S106-p03",[.51,.69,.95,.76],"§2 Experimental, isotherm temperatures (right column bottom)","units",["77 K","293 K"])
    add("S106-p03",[.51,.5,.95,.55],"FTIR wavenumber unit", "symbols",["cm⁻¹"],{"cm⁻¹":"cm−1"})
    add("S106-p04",[.05,.19,.49,.24],"QE-TPDA sample masses/He flow (left column)","numbers",["1.2","1.1","1.4","6.5"])
    add("S106-p04",[.51,.06,.95,.1],"§3 Monte Carlo cycles (right column top)","symbols",["5⋅10⁴","5⋅10⁵"],{"5⋅10⁴":"5⋅104","5⋅10⁵":"5⋅105"})
    add("S106-p04",[.05,.84,.49,.88],"§3 equation absolute/excess adsorption", "relationships",["θ_excess = θ_absolute − PV/(zRT)"])
    for i,(property_, vals) in enumerate([("PV",["0.353","0.376","0.460"]),("BET",["1115","1197","1646"])]):
        box=[.06,.433+i*.012,.49,.448+i*.012]
        add("S106-p05",box,f"Table 1 {property_}, columns UiO-66_220/_160/_100", "numbers",vals)
        for material,v in zip(["UiO-66_220","UiO-66_160","UiO-66_100"],vals):
            add("S106-p05",box,f"Table 1 {property_}, {material}","relationships",[f"{material} | {property_} | {v}"])
    add("S106-p05",[.06,.433,.49,.46],"Table 1 row labels/units", "units",["cm³/g","m²/g"],{"cm³/g":"cm3/g","m²/g":"m2/g"})
    add("S106-p05",[.51,.31,.95,.35],"Fig. 4 caption", "units",["293 K"])
    add("S106-p05",[.51,.06,.95,.31],"Fig. 4 legend, water, measured at 293 K in caption", "relationships",["purple square → UiO-66_220 | H₂O | 293 K"])
    add("S106-p06",[.05,.88,.49,.94],"Fig. 5 caption", "numbers",["1.4","2.6","1.1","1.2","2.7"])
    add("S106-p06",[.06,.06,.49,.88],"Fig. 5 axis minimum", "numbers",["−1.0"])
    add("S106-p06",[.51,.90,.95,.94],"Fig. 6 caption", "units",["293 K","2.6 kPa"])
    add("S106-p06",[.51,.33,.95,.87],"Fig. 6a/b experimental versus calculated curves", "relationships",["open squares → UiO-66_220 desorption", "dashed circle curve → Tuned EQeq charges (simulation)"])
    add("S106-p07",[.05,.45,.49,.52],"Fig. 7 discussion, occupation profiles", "numbers",["300","700","1700","100","800","1000"])
    add("S106-p07",[.05,.91,.95,.94],"Fig. 7 caption temperature", "units",["293.15 K"])
    add("S106-p07",[.51,.18,.95,.23],"Framework charge, right column", "symbols",["¹²⁺"],{"¹²⁺":"12+"})
    add("S105-p08",[.12,.23,.88,.32],"§3.4 activation and temperature range", "numbers",["393","273","298","318"])
    add("S105-p08",[.12,.23,.88,.32],"§3.4 pretreatment", "units",["12 h","393 K"])
    add("S105-p08",[.29,.33,.70,.79],"Fig. 8 A/B axes", "units",["mmol/g","bar"])
    add("S105-p08",[.29,.33,.70,.79],"Fig. 8B legend, temperature from caption on p.9", "relationships",["teal down-triangle → UiO-66-NH₂/GO | 298 K"])
    add("S105-p09",[.2,.35,.8,.38],"Fig. 8 caption A/B/C temperature association", "numbers",["273","298","318"])
    add("S105-p09",[.12,.5,.88,.62],"§3.4 uptake discussion", "numbers",["3.93","3.66","6.41","6.10","2.26"])
    add("S105-p09",[.12,.5,.88,.62],"§3.4 uptake units", "units",["mmol/g"])
    add("S105-p09",[.2,.35,.8,.38],"Fig. 8C caption", "relationships",["panel C → 318 K"])
    add("S113-p06",[.12,.09,.88,.2],"Methods, outgassing", "numbers",["120","1"])
    add("S113-p06",[.12,.09,.88,.2],"Methods, outgassing", "units",["120 °C","1 day"])
    add("S113-p06",[.12,.3,.88,.41],"§2.4.5 enhancement coefficient", "numbers",["2.888"])
    add("S113-p06",[.12,.42,.88,.47],"Eq. (7) subscript/ratio structure", "relationships",["F_index = ln(P_filled/P_unfilled) + η ln(α_filled/α_unfilled)"])
    for i,(material,values) in enumerate([
        ("UiO-66",["1733","2266","1662","0.809","0.938"]),
        ("UiO-66-NH₂",["1218","1599","1160","0.569","0.682"]),
        ("UiO-66-Br",["851","1117","818","0.380","0.440"]),
        ("UiO-66-(OH)₂",["318","418","293","0.136","0.178"]) ]):
        box=[.15,.68+i*.016,.85,.698+i*.016]
        add("S113-p07",box,f"Table 1 row {material}, SBET/SLANG/Smicro/Vmicro/Vtotal", "numbers",values)
        add("S113-p07",box,f"Table 1 row {material}","relationships",[material+" | SBET,SLANG,Smicro,Vmicro,Vtotal | "+",".join(values)])
    add("S113-p07",[.15,.66,.85,.68],"Table 1 headers", "units",["m²/g","cc/g"],{"m²/g":"m2/g"})
    add("S113-p07",[.15,.74,.85,.81],"Table 1 footnote BET pressure range", "numbers",["0.05","0.2","0.99"])
    add("S113-p09",[.14,.09,.88,.28],"Fig. 5 a/b axes", "numbers",["1.6","0.16"])
    add("S113-p09",[.14,.09,.88,.28],"Fig. 5 a/b axes", "units",["mmol/g","bar"])
    add("S113-p09",[.14,.29,.88,.33],"Fig. 5 caption", "units",["35 °C"])
    add("S113-p09",[.14,.09,.88,.28],"Fig. 5a/b series and gas", "relationships",["blue square → UiO-66-Br | panel a CO₂ | 35 °C", "blue square → UiO-66-Br | panel b N₂ | 35 °C"])
    add("S103-p02",[.51,.86,.93,.9],"Table 1 DFT+D adsorption energies, CO2 / methanol, metal cluster / linker", "numbers",["1.89","−7.86","−7.70","−3.27"])
    add("S103-p02",[.51,.9,.93,.93],"Table 1 footnote", "units",["kcal·mol⁻¹"],{"kcal·mol⁻¹":"kcal·mol−1"})
    add("S103-p02",[.51,.86,.93,.9],"Table 1 computed energy, not measured capacity", "relationships",["carbon dioxide | organic linker | −7.86 kcal·mol⁻¹"])
    add("S103-p03",[.08,.614,.49,.627],"Table 2 PV row, columns _220/_160/_100", "numbers",["0.315","0.410","0.444"])
    add("S103-p03",[.08,.627,.49,.641],"Table 2 BET row, columns _220/_160/_100", "numbers",["980","1260","1438"])
    add("S103-p03",[.08,.614,.49,.641],"Table 2 units", "units",["cm³·g⁻¹","m²·g⁻¹"],{"cm³·g⁻¹":"cm3·g−1","m²·g⁻¹":"m2·g−1"})
    add("S103-p03",[.2,.7,.8,.9],"Fig. 2a/b axes", "units",["cm³ STP·g⁻¹","bar"])
    add("S103-p03",[.07,.91,.94,.95],"Fig. 2 caption", "units",["27 °C"])
    add("S103-p03",[.2,.7,.8,.95],"Fig. 2 caption distinguishes experiment from computation", "relationships",["panel a → experiment; panel b → calculations | 27 °C"])
    add("S102-p05",[.27,.815,.74,.875],"Fig. S6 caption, water loadings a/b/c", "numbers",["2.05","3.03","4.10"])
    add("S102-p05",[.27,.815,.74,.875],"Fig. S6 caption, water loading unit", "units",["mol/kg"])
    add("S102-p05",[.27,.13,.74,.80],"Fig. S6 axes", "units",["kPa"])
    add("S102-p05",[.27,.815,.74,.875],"Fig. S6 caption chemical indices", "symbols",["CO₂/H₂O"],{"CO₂/H₂O":"CO2/H2O"})
    add("S102-p05",[.27,.13,.74,.86],"Fig. S6 panels a/b/c; temperature unknown in caption", "relationships",["a → 2.05 mol/kg H₂O; b → 3.03; c → 4.10 | UiO-66-NH₂", "green open diamond → experimental binary; triangle → IAST"])


def main():
    reference()
    output = ROOT / "data/extraction/benchmark"
    pages = {p["extraction_id"]:p for p in json.loads((output / "pages.json").read_text())}
    # Serialize reference separately BEFORE evaluating candidates.
    (output / "reference_fields.json").write_text(json.dumps(FIELDS,ensure_ascii=False,indent=2)+"\n")
    results=[]
    for field in FIELDS:
        meta=pages[field["extraction_id"]]
        with pymupdf.open(ROOT/meta["input"]) as doc:
            page=doc[meta["pdf_page"]-1]
            a,b,c,d=field["region_norm"]
            rect=pymupdf.Rect(a*page.rect.width,b*page.rect.height,c*page.rect.width,d*page.rect.height)
            text=page.get_text("text",clip=rect,sort=True)
        expected=field["expected"]
        category=field["category"]
        # The engines return plain text; they have no cell/curve relationship
        # representation. Never infer semantic success from token co-occurrence.
        candidate=None
        if category != "relationships":
            pattern=re.escape(expected)
            if category=="numbers":
                pattern=r"(?<![\d.])"+pattern+r"(?!\d)(?!\.\d)"
            match=re.search(pattern,text)
            if match:
                candidate=match.group()
            elif field["lossy_alternative"] and field["lossy_alternative"] in text:
                candidate=field["lossy_alternative"]
        status="correct" if candidate==expected else ("omission" if candidate is None else "mismatch")
        results.append(dict(**field,candidate=candidate,result=status,engine="pymupdf",
                            region_text=text,render=meta["render"],render_sha256=meta["render_sha256"]))
    (output / "field_results.json").write_text(json.dumps(results,ensure_ascii=False,indent=2)+"\n")
    summary={}
    for category in ["numbers","units","symbols","relationships"]:
        counts=Counter(r["result"] for r in results if r["category"]==category)
        total=sum(counts.values())
        summary[category]=dict(total=total,correct=counts["correct"],omissions=counts["omission"],
                               mismatches=counts["mismatch"],fraction=counts["correct"]/total)
    (output/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    # Per-page passports hash the actual derived page field results, not a mutable report.
    record_dir=ROOT/"data/extraction/records"
    record_dir.mkdir(parents=True,exist_ok=True)
    for eid,meta in pages.items():
        page_results=[r for r in results if r["extraction_id"]==eid]
        derived=output/(eid+".json")
        derived.write_text(json.dumps(page_results,ensure_ascii=False,indent=2)+"\n")
        failed=[r for r in page_results if r["result"]!="correct"]
        record=dict(extraction_id=eid,source_id=meta["source_id"],doi=meta["doi"],url=None,
                    input_sha256=meta["input_sha256"],pdf_page=meta["pdf_page"],
                    api_page_map={"1":meta["pdf_page"]},figure_or_table="; ".join(sorted(set(r["locator"] for r in page_results))),
                    region={"units":"normalized page coordinates; origin top-left", "field_regions":str(derived.relative_to(ROOT)),
                            "render":meta["render"],"render_sha256":meta["render_sha256"]},
                    tool="PyMuPDF region-assisted glyph audit; manual visual reference",
                    tool_version=pymupdf.VersionBind,params={"dpi":200,"sort":True,"printed_page":meta["printed_page"],
                    "script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    "benchmark_only":True,"not_a_measurement_dataset":True},
                    date=datetime.now(timezone.utc).isoformat(),raw_response_ref=meta["raw_response_ref"],unit_conversions=[],
                    derived_sha256=hashlib.sha256(derived.read_bytes()).hexdigest(),status="provisional",reviewer=None,
                    corrections=[{"field_id":r["field_id"],"kind":r["result"],"reference":r["expected"],
                                  "applied_to_raw":False,"action":"manual transcription/structure; pending T007"} for r in failed],
                    error_estimate={"scope":"selected fields only; region-assisted presence, not blind extraction",
                                    "correct":len(page_results)-len(failed),"total":len(page_results)},
                    data_kind="text_value",sensitivity_only=True)
        validate_extraction(record)
        (record_dir/(eid+".yaml")).write_text(yaml.safe_dump(record,sort_keys=False,allow_unicode=True))
    print(json.dumps(summary,indent=2))


if __name__=="__main__":
    main()
