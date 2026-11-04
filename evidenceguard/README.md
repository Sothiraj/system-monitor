# EvidenceGuard-SOC — Chapter 4 / 5 figures

Original, report-ready replacement figures built from the shared-chat spec
(Figure 4.2, 4.4, 4.5, 5.2). They are **newly drawn** for this repository —
the copyrighted web images referenced in the chat (forensic-lab photo,
ESET screenshot, pneumonia calibration plot, TechPrescient ABAC diagram)
are **not** copied here.

## What this folder contains

| File | Purpose |
|---|---|
| `generate_figures.py` | Generates all four figures (PNG + PDF) with matplotlib |
| `figures/fig4_2_digital_evidence_preservation_workflow.{png,pdf}` | Figure 4.2 |
| `figures/fig4_4_reliability_diagram_ccva.{png,pdf}` | Figure 4.4 |
| `figures/fig4_5_response_authorization_rcra.{png,pdf}` | Figure 4.5 |
| `figures/fig5_2_endpoint_process_graph.{png,pdf}` | Figure 5.2 |
| `ccva_calibration_template.csv` | Replace the synthetic calibration numbers with real CCVA results |
| `latex_snippets.tex` | Copy-paste `\begin{figure}` blocks with correct captions/labels |
| `requirements-figures.txt` | Python deps for figure generation |

## Regenerate

```bash
pip install -r evidenceguard/requirements-figures.txt
python evidenceguard/generate_figures.py --outdir evidenceguard/figures --dpi 300
```

To use **real** CCVA evaluation numbers in Figure 4.4 instead of the clearly
labelled synthetic placeholder:

```bash
# 1. Edit ccva_calibration_template.csv with your 10-bin results
# 2. Re-run with:
python evidenceguard/generate_figures.py --calibration evidenceguard/ccva_calibration_template.csv
```

## Exact placement (from the shared-chat mapping)

### Figure 4.2 — Digital evidence preservation workflow  ✅ include
- **Location:** Chapter 4, Section 4.2 (PCEM), PDF p.15
- **Place:** immediately after the paragraph explaining SHA-256 hashing,
  before the next section.
- **Caption:** `Figure 4.2: Digital Evidence Preservation and Integrity Verification Workflow.`
- **In-text lead-in (suggested):** *"Figure 4.2 summarises the preservation
  path: the raw exhibit is write-blocked and hashed (Hash A); analysts only
  ever touch a working copy whose re-hash (Hash B) must match before any
  processing. A mismatch quarantines the copy and forces re-acquisition,
  so every downstream claim stays traceable to an integrity-verified source."*

### Figure 4.4 — Calibrated claim verification  ⚠️ replace, do not use supplied image
- **Location:** Chapter 4, Section 4.4 (CCVA), PDF p.17
- **Why replace:** the supplied graph is about pneumonia prediction, not
  cybersecurity, and would confuse examiners.
- **Place:** after the calibration / ECE explanation.
- **Caption:** `Figure 4.4: Reliability Diagram for Calibrated Cybersecurity Claim Verification.`
- **In-text lead-in (suggested):** *"Figure 4.4 plots mean predicted
  confidence against observed claim accuracy on the held-out CCVA evaluation
  split, with Expected Calibration Error (ECE) reported. Bars on the diagonal
  indicate calibrated confidence; the shaded gaps show residual
  miscalibration per bin. Replace the placeholder counts with the final
  evaluation split before submission."*

### Figure 4.5 — Response authorization architecture  ✅ include after adaptation
- **Location:** Chapter 4, Section 4.5 (RCRA), PDF p.18
- **Place:** after the policy-outcome table.
- **Caption:** `Figure 4.5: Risk-Constrained Response Authorization Architecture.`
- **Adaptations applied:** labels changed to Case Scope, Analyst Role, Target
  Asset, Evidence Verdict, Action Allow-list, Human Approval; outputs are
  ALLOW FOR SIMULATION, REQUIRE REVIEW, DENY; every decision writes to an
  audit log.
- **In-text lead-in (suggested):** *"Figure 4.5 shows how RCRA gates every
  response: the six case/analyst/evidence attributes are evaluated against
  risk constraints, and only low-risk, evidence-backed actions are allowed
  for simulation — anything uncertain requires review and unsafe actions are
  denied with a logged rationale."*

### Figure 5.2 — Endpoint process relationship graph  ✅ include with explanation
- **Location:** Chapter 5, Section 5.2 (Temporal Evidence Graph), PDF p.19
- **Place:** after the explanation of graph nodes, edges and entity relationships.
- **Caption:** `Figure 5.2: Example of an Endpoint Process Relationship Graph.`
- **Mandatory note (examiners will check):** state explicitly that this is an
  *illustrative* security-event subgraph, **not** the complete
  EvidenceGuard-SOC graph schema.
- **In-text lead-in (suggested):** *"Figure 5.2 is a simplified illustration
  of the node and edge types (endpoint, process, file, network, registry,
  user). The production Temporal Evidence Graph carries additional node
  properties, timestamps and provenance links described in the surrounding text."*

## Updated figure numbering

| Figure | Description | Status |
|---|---|---|
| 4.1 | Overall investigation workflow | existing, unchanged |
| **4.2** | Digital evidence preservation workflow | **new (this folder)** |
| 4.3 | Evidence provenance pipeline | existing, renumbered from old 4.2 |
| **4.4** | Calibrated claim verification (cybersecurity reliability diagram) | **replaced (this folder)** |
| **4.5** | Response authorization architecture (adapted) | **new (this folder)** |
| 5.1 | Seven-layer architecture | existing, unchanged |
| **5.2** | Endpoint process relationship graph | **new (this folder)** |
| 5.3+ | Existing Chapter 5 diagrams | renumber old 5.2 → 5.3, etc. |

Checklist before re-exporting the 34-page PDF:
- [ ] Insert the four figures at the positions above (not decorative appendices)
- [ ] Paste captions exactly as listed
- [ ] Renumber old Figure 4.2 → 4.3 and old 5.2 → 5.3 (+ following figures)
- [ ] Update the List of Figures and every `\ref{fig:...}` / cross-reference
- [ ] Replace synthetic Figure 4.4 counts with the real CCVA evaluation split
- [ ] Add the "illustrative, not complete schema" disclaimer under Figure 5.2

## How each figure supports the methodology

- **4.2** explains how evidence is *preserved* (integrity before analysis).
- **5.2** explains how security relationships are *investigated* (graph reasoning).
- **4.4** explains how the system *measures confidence* (calibration, not raw scores).
- **4.5** explains how unsafe response actions are *prevented* (deny-by-default gating).
