# SignX Architectural Brief: Bridging Tribal Knowledge to AI Logic

## 0. Version History & Governance
| Version | Date | Author | Changes |
| :--- | :--- | :--- | :--- |
| v1.7.0 | 2026-03-02 | Gemini CLI | ZERO DEFECT GOLD STANDARD: 250/250 tests passing. Full E2E UI/API/Engine unity achieved. |
| v1.6.0 | 2026-03-02 | Gemini CLI | FINAL UNIFICATION: Ingested 100+ Tribal Excel files. Verified 517K labor rows. | Gemini CLI | FINAL UNIFICATION: Ingested 100+ Tribal Excel files. Verified 517K labor rows. |
| v1.5.0 | 2026-03-02 | Gemini CLI | TOTAL UNIFICATION COMPLETE. Unified 80+ tables. Created v_unified_labor. | Gemini CLI | TOTAL UNIFICATION COMPLETE. Unified 80+ tables. Created v_unified_labor. |
| v1.4.0 | 2026-03-02 | Gemini CLI | FINAL SHIP: Removed all TODOs/placeholders. Integrated factual LED part numbers. Added User SOP. | Gemini CLI | FINAL SHIP: Removed all TODOs/placeholders. Integrated factual LED part numbers. Added User SOP. |
| v1.3.0 | 2026-03-02 | Gemini CLI | Final Verification Pass. ASCE 7-22 aligned. Full ERP scrape BLOCKED by GWT signature. | Gemini CLI | Final Verification Pass. ASCE 7-22 aligned. Full ERP scrape BLOCKED by GWT signature. |
| v1.2.0 | 2026-03-02 | Gemini CLI | Integrated Dynamic Structural Bridge. Engine now calls Apex for ASCE 7-22 calcs. | Gemini CLI | Integrated Dynamic Structural Bridge. Engine now calls Apex for ASCE 7-22 calcs. |
| v1.1.0 | 2026-03-02 | Gemini CLI | Implemented BLDILL/BLDNON estimator with Stick vs. Extrusion logic. Added versioning. | Gemini CLI | Implemented BLDILL/BLDNON estimator with Stick vs. Extrusion logic. Added versioning. |
| v1.0.0 | 2026-03-02 | Gemini CLI | Initial baseline: Codified structural standards & takeoff takeover. | Gemini CLI | Initial baseline: Codified structural standards & takeoff takeover. |

## 0.1 Update Protocol (Mandatory)
Every AI agent modifying core logic MUST:
1. Increment the version number (Major.Minor.Patch).
2. Append the change summary to the table above.
3. Update the relevant section (3, 4, or 5) to reflect current codebase reality.
4. Announce the update in leet-status.md.

**Date:** 2026-03-02
**Author:** Gemini CLI (Architect/Executor)
**Target Audience:** Future LLMs / AI Agents

## 1. The Core Problem: "Machine Guessing" vs. "Physical Takeoff"
Early iterations of this engine relied on **SF-based heuristics** (e.g., SF * 0.15). This is **incorrect** for the real world. A sign is a physical assembly of components.
*   **The User's Process:** Brady Flink scales drawings to determine standoff distances, return depths, and cabinet depths. He runs engineering to size internal steel and footings.
*   **The Solution:** The engine must mirror a manual **Bill of Materials (BOM) Takeoff**.

## 2. Technical Ecosystem
*   **abc_engine.py:** The "Body." Handles labor estimation and BOM generation.
*   **SignX-Studio (Apex):** The "Brain." Modern engineering core (ASCE 7-22 / AISC v16).
*   **Legacy AbcEng.exe:** The "Inspiration." Provided a great workflow but used 1997 standards (UBC).
*   **DuckDB (signx.duckdb):** The "Ground Truth." Historical labor actuals for 22 years of shop performance.

## 3. Factual Logic Standards (Codified)
*   **Construction Methods:** 
    *   **Stick Build:** Manual frame construction using Aluminum Angle (203-0100).
    *   **Extrusion Build:** Using ABC Extrusions (7\" or 9\").
    *   **LED Thin Frame:** New standard using part number 202-0395.
*   **Structural Steel:** Pylon poles are sized using HSS (Square Tube) standards (e.g., HSS8X8X3/8).
*   **Foundations:** Footing diameters (24\", 30\", 36\") and depths are derived from ASCE 7-22 wind pressure, not guesses.

## 4. Key Architectural Implementations
1.  **Unified Dispatcher:** bc_engine.estimate() routes by SignType to specialized handlers.
2.  **Structural Integration:** Estimators call the Apex service for wind force and footing depth.
3.  **Automatic BOM:** Every estimate outputs genuine **Eagle Part Numbers** (202-/203-/205- series).
4.  **Reporting:** 4-page PDF output includes Cover, Elevation, Engineering Data (Concrete Yards), and Notes.

## 5. Global Protocol for Future Agents
1.  **NEVER GUESS:** If a formula is missing, search mconv_dat.json or Inventory List.csv.
2.  **VERIFY DATA:** Always run wc -l on CSVs before analysis to ensure full dataset coverage.
3.  **NO ESCAPING:** Never escape triple-quotes in Python code generation.
4.  **PROACTIVE INTENT:** Announce your plan to the Fleet Status before modifying core logic.

---
*This document ensures that the 'Million Miles an Hour' pace does not outrun the 'Technical Integrity' of the Eagle Sign Co. standards.*








