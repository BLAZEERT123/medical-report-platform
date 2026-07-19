"""
Index Reference Corpus (Store B) into ChromaDB.

Fetches public medical articles from MedlinePlus and includes inline
static content from WHO/CDC guidelines.

Run once from project root:
    python scripts/index_reference_corpus.py

The script is idempotent — running it again will upsert without duplicates.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.chroma_service import index_reference_article

# ── MedlinePlus articles to fetch ─────────────────────────────────────────────
MEDLINEPLUS_ARTICLES = [
    {
        "id": "anemia",
        "url": "https://medlineplus.gov/anemia.html",
        "title": "Anemia",
    },
    {
        "id": "hemoglobin",
        "url": "https://medlineplus.gov/lab-tests/hemoglobin-test/",
        "title": "Hemoglobin Test",
    },
    {
        "id": "iron_deficiency",
        "url": "https://medlineplus.gov/irondeficiencyanemia.html",
        "title": "Iron Deficiency Anemia",
    },
    {
        "id": "diabetes",
        "url": "https://medlineplus.gov/diabetes.html",
        "title": "Diabetes",
    },
    {
        "id": "hba1c",
        "url": "https://medlineplus.gov/lab-tests/hemoglobin-a1c-hba1c-test/",
        "title": "HbA1c Test",
    },
    {
        "id": "blood_glucose",
        "url": "https://medlineplus.gov/lab-tests/blood-glucose-test/",
        "title": "Blood Glucose Test",
    },
    {
        "id": "cholesterol",
        "url": "https://medlineplus.gov/cholesterol.html",
        "title": "Cholesterol",
    },
    {
        "id": "ldl",
        "url": "https://medlineplus.gov/lab-tests/ldl-bad-cholesterol/",
        "title": "LDL (Bad) Cholesterol",
    },
    {
        "id": "creatinine",
        "url": "https://medlineplus.gov/lab-tests/creatinine-test/",
        "title": "Creatinine Test",
    },
    {
        "id": "cbc",
        "url": "https://medlineplus.gov/lab-tests/complete-blood-count-cbc/",
        "title": "Complete Blood Count (CBC)",
    },
]

# ── Static WHO/CDC content (avoids scraping PDFs) ─────────────────────────────
STATIC_ARTICLES = [
    {
        "id": "who_diabetes_guidelines",
        "title": "WHO Diabetes Management Guidelines (Summary)",
        "source_url": "https://www.who.int/publications/i/item/9789240015104",
        "text": """
WHO Diabetes Management Guidelines — Key Points

Definition: Diabetes mellitus is a chronic metabolic disease characterized by elevated levels 
of blood glucose (blood sugar), which leads over time to serious damage to the heart, blood 
vessels, eyes, kidneys and nerves.

Diagnostic Criteria (WHO):
- Fasting plasma glucose ≥ 7.0 mmol/L (126 mg/dL)
- 2-hour plasma glucose ≥ 11.1 mmol/L (200 mg/dL) after 75g oral glucose tolerance test
- HbA1c ≥ 48 mmol/mol (6.5%)
- Random plasma glucose ≥ 11.1 mmol/L (200 mg/dL) with symptoms

Glycemic Targets:
- HbA1c target: < 7% (53 mmol/mol) for most adults with type 2 diabetes
- Stricter target (< 6.5%) may be appropriate for younger patients with short duration of diabetes
- Less strict target (< 8%) for elderly patients or those with severe hypoglycemia risk

Pre-diabetes:
- Impaired Fasting Glucose (IFG): Fasting glucose 6.1–6.9 mmol/L (110–125 mg/dL)
- Impaired Glucose Tolerance (IGT): 2-hour glucose 7.8–11.0 mmol/L (140–199 mg/dL)

Management Principles:
1. Lifestyle modification: Diet and physical activity are first-line treatments
2. Metformin: First-line pharmacological therapy for type 2 diabetes if not contraindicated
3. Blood pressure control: Target < 130/80 mmHg
4. Lipid management: Statins recommended for high cardiovascular risk patients
5. Regular monitoring: HbA1c every 3 months until stable, then every 6 months

Complications to monitor:
- Diabetic nephropathy: Annual urine albumin-to-creatinine ratio
- Diabetic retinopathy: Annual eye examination
- Diabetic neuropathy: Annual foot examination
- Cardiovascular disease: Regular blood pressure and lipid monitoring

Hypoglycemia: Blood glucose < 70 mg/dL (3.9 mmol/L) requires immediate treatment with 
fast-acting carbohydrates (15-20g glucose). Severe hypoglycemia (< 54 mg/dL / 3.0 mmol/L) 
may require glucagon.
""",
    },
    {
        "id": "cdc_anemia_guidelines",
        "title": "CDC Anemia and Iron Deficiency Fact Sheet",
        "source_url": "https://www.cdc.gov/nutrition/micronutrient-malnutrition/micronutrients/iron.html",
        "text": """
CDC Anemia & Iron Deficiency — Clinical Facts

Definition:
Anemia is defined as hemoglobin (Hb) levels below:
- Men: < 13 g/dL
- Women: < 12 g/dL
- Pregnant women: < 11 g/dL
- Children 6–59 months: < 11 g/dL

Severity Classification (WHO):
- Mild anemia: Hb 10.0–11.9 g/dL (women) / 10.0–12.9 g/dL (men)
- Moderate anemia: Hb 8.0–9.9 g/dL
- Severe anemia: Hb < 8.0 g/dL
- Life-threatening/Critical: Hb < 7.0 g/dL — requires urgent medical attention

Iron Deficiency Anemia (IDA):
- Most common cause of anemia worldwide
- Diagnosed by: low Hb + low serum ferritin (< 12 µg/L) + low transferrin saturation (< 16%)
- MCV (mean corpuscular volume) typically < 80 fL in iron deficiency
- MCH (mean corpuscular hemoglobin) typically < 27 pg

Common Causes:
- Inadequate dietary iron intake
- Poor iron absorption (celiac disease, gastric bypass)
- Increased iron demand (pregnancy, growth)
- Chronic blood loss (menstruation, GI bleeding)

Treatment:
- Oral iron supplementation: Ferrous sulfate 325mg (65mg elemental iron) 2-3x daily
- Dietary sources: Red meat, poultry, fish, legumes, fortified cereals, dark leafy greens
- Vitamin C enhances iron absorption; calcium inhibits it
- IV iron infusion for severe cases or poor oral absorption
- Duration: 3-6 months after normalization of Hb to replenish stores

Monitoring Response:
- Reticulocyte count rises within 7-10 days of treatment
- Hemoglobin should increase by 1-2 g/dL every 3-4 weeks
- Ferritin levels normalize last (may take 3-6 months)

When to refer urgently:
- Hb < 7 g/dL
- Symptomatic anemia (chest pain, dyspnea, altered consciousness)
- No response to iron therapy after 4 weeks
- Suspected GI blood loss
""",
    },
    {
        "id": "atp4_cholesterol_guidelines",
        "title": "Cholesterol and Cardiovascular Risk — Clinical Reference",
        "source_url": "https://www.acc.org/guidelines",
        "text": """
Cholesterol Management — Clinical Reference

Normal Lipid Values (Adult):
- Total Cholesterol: < 200 mg/dL (desirable), 200-239 (borderline high), ≥ 240 (high)
- LDL Cholesterol: 
  - Optimal: < 100 mg/dL
  - Near optimal: 100-129 mg/dL
  - Borderline high: 130-159 mg/dL
  - High: 160-189 mg/dL
  - Very high: ≥ 190 mg/dL
- HDL Cholesterol: < 40 mg/dL (low, risk factor); ≥ 60 mg/dL (protective)
- Triglycerides: < 150 mg/dL (normal), 150-199 (borderline), 200-499 (high), ≥ 500 (very high)

Cardiovascular Risk Assessment:
High-risk patients (LDL target < 70 mg/dL):
- Known cardiovascular disease (prior MI, stroke, angina)
- Diabetes mellitus
- Chronic kidney disease (eGFR < 60)

Primary Prevention (no known CVD):
- If 10-year ASCVD risk ≥ 7.5%: Consider moderate-intensity statin
- If risk ≥ 20%: High-intensity statin recommended

Statin Therapy Intensity:
- High intensity: Atorvastatin 40-80mg, Rosuvastatin 20-40mg (LDL reduction ≥ 50%)
- Moderate intensity: Atorvastatin 10-20mg, Rosuvastatin 5-10mg (LDL reduction 30-49%)

Lifestyle Modifications:
- Reduce saturated fat to < 7% of total calories
- Eliminate trans fats
- Increase dietary fiber (oats, legumes, fruits): 5-10g/day soluble fiber
- Regular aerobic exercise: 150 minutes moderate intensity per week
- Weight loss (if BMI > 25): 5-10% weight loss can reduce LDL by 5-8%
- Smoking cessation (raises HDL by 5-10%)

Secondary Causes of Hyperlipidemia:
- Hypothyroidism, diabetes, nephrotic syndrome, alcoholism
- Medications: beta-blockers, thiazide diuretics, corticosteroids
""",
    },
    {
        "id": "kidney_function_reference",
        "title": "Kidney Function Tests — Clinical Interpretation Guide",
        "source_url": "https://www.kidney.org/professionals/guidelines",
        "text": """
Kidney Function Tests — Clinical Reference

Creatinine:
- Normal ranges: Men: 0.7–1.3 mg/dL | Women: 0.6–1.1 mg/dL
- Elevated creatinine suggests reduced kidney filtering capacity
- Mild elevation (1.3–2.0 mg/dL): Monitor, identify cause
- Significant elevation (> 4.0 mg/dL): Possible severe kidney impairment

eGFR (estimated Glomerular Filtration Rate):
- Normal: ≥ 90 mL/min/1.73m²
- Mildly decreased: 60–89 (G2)
- Mildly to moderately decreased: 45–59 (G3a)
- Moderately to severely decreased: 30–44 (G3b)
- Severely decreased: 15–29 (G4)
- Kidney failure: < 15 (G5) — dialysis may be needed

BUN (Blood Urea Nitrogen):
- Normal: 7–25 mg/dL
- BUN/Creatinine ratio: Normal 10–20:1
  - > 20:1: Pre-renal causes (dehydration, heart failure, GI bleeding)
  - < 10:1: Post-renal causes or liver disease

Chronic Kidney Disease (CKD) Management:
- Control blood pressure: < 130/80 mmHg (ACE inhibitors/ARBs preferred in diabetics)
- Control blood glucose in diabetics
- Avoid nephrotoxic drugs (NSAIDs, contrast dye without precautions)
- Restrict dietary protein in advanced CKD
- Monitor: eGFR and urine albumin/creatinine every 3–6 months

When to refer to Nephrologist:
- eGFR < 30 mL/min/1.73m²
- Rapid decline in eGFR (> 5 mL/min/year)
- Persistent proteinuria (albumin/creatinine > 300 mg/g)
- Refractory hypertension or hyperkalemia
""",
    },
]


def scrape_medlineplus(url: str) -> str:
    """Scrape main content text from a MedlinePlus article."""
    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            resp = client.get(url, headers={"User-Agent": "Mozilla/5.0 (medical-app-indexer/1.0)"})
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")

        # MedlinePlus main content is in article tags or specific divs
        main = (
            soup.find("article")
            or soup.find("div", {"id": "ency_summary"})
            or soup.find("div", {"class": "page-content"})
            or soup.find("main")
        )

        if main:
            # Remove nav, footer, sidebar
            for tag in main.find_all(["nav", "footer", "aside", "script", "style"]):
                tag.decompose()
            text = main.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)

        # Clean up excessive whitespace
        import re
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text[:8000]  # Cap to prevent huge chunks

    except Exception as exc:
        print(f"  ⚠ Could not scrape {url}: {exc}")
        return ""


def main():
    print("🔵 Indexing Reference Corpus (Store B) into ChromaDB...\n")

    # ── MedlinePlus articles ──────────────────────────────────────────────────
    print("=== MedlinePlus Articles ===")
    for article in MEDLINEPLUS_ARTICLES:
        print(f"  Fetching: {article['title']}...")
        text = scrape_medlineplus(article["url"])
        if text:
            n = index_reference_article(
                text=text,
                title=article["title"],
                source_url=article["url"],
                article_id=article["id"],
            )
            print(f"  ✅ Indexed '{article['title']}' → {n} chunks")
        else:
            print(f"  ❌ Skipped (no content): {article['title']}")
        time.sleep(0.5)  # Be polite to the server

    # ── Static articles ───────────────────────────────────────────────────────
    print("\n=== Static Guidelines ===")
    for article in STATIC_ARTICLES:
        for attempt in range(3):
            try:
                n = index_reference_article(
                    text=article["text"].strip(),
                    title=article["title"],
                    source_url=article["source_url"],
                    article_id=article["id"],
                )
                print(f"  ✅ Indexed '{article['title']}' → {n} chunks")
                break
            except Exception as exc:
                if attempt < 2:
                    wait = 5 * (attempt + 1)
                    print(f"  ⚠ Attempt {attempt+1} failed: {exc} — retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"  ❌ Failed after 3 attempts: {article['title']} — {exc}")

    print("\n✅ Reference corpus indexing complete!")


if __name__ == "__main__":
    main()
