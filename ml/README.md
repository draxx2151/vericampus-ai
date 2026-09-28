# VeriCampus AI — Synthetic ML Dataset Generator

Generates synthetic scholarship document datasets for training and evaluating machine learning models within the VeriCampus AI platform.

> **⚠️ All generated documents are clearly marked as "SYNTHETIC DEMO DOCUMENT — NOT REAL".
> No real student PII is used. All names, addresses, and ID numbers are fictional.**

## Quick Start

```bash
# Install dependencies (from project root)
pip install -r ml/requirements.txt

# Generate a small dataset (10 students, 40 documents)
python ml/data_generator/generate_dataset.py --samples-per-class 10

# Generate a larger dataset
python ml/data_generator/generate_dataset.py --samples-per-class 100 --seed 123
```

> **Note (Windows):** If you see Unicode encoding errors, set the encoding first:
> ```powershell
> $env:PYTHONIOENCODING='utf-8'
> python ml/data_generator/generate_dataset.py --samples-per-class 10
> ```

## What It Generates

For each synthetic student, the pipeline creates **4 document images** (PNG) corresponding to the VeriCampus AI document types:

| Document Type | Backend Enum | Extraction Schema |
|---|---|---|
| Government ID (Aadhaar/PAN/Voter ID) | `GOVERNMENT_ID` | `GovernmentIdExtraction` |
| Academic Marksheet | `MARKSHEET` | `MarksheetExtraction` |
| Income Certificate | `INCOME_CERTIFICATE` | `IncomeCertificateExtraction` |
| Domicile Certificate | `DOMICILE_CERTIFICATE` | `DomicileCertificateExtraction` |

### Pipeline Steps

1. **Student Profiles** — Synthetic Indian student data (Faker `en_IN` locale, Maharashtra-focused)
2. **Document Rendering** — Pillow-based PNG image generation with formal document layouts
3. **Annotations** — OCR ground truth + field-level annotations with bounding boxes `[x1, y1, x2, y2]`
4. **Verification Cases** — VALID (70%) and NEEDS_REVIEW (30%) labels with controlled inconsistencies
5. **Visual Augmentations** — 7 distortion types simulating real-world scanning conditions
6. **Dataset Split** — 70/15/15 train/val/test split by student identity (prevents data leakage)
7. **Validation** — 10 automated checks confirming dataset integrity
8. **Statistics** — JSON + human-readable report

## Output Directory Structure

```
ml/datasets/run_n10_seed42/
├── students.json                          # Student profiles
├── images/
│   ├── GOVERNMENT_ID/                     # Clean document PNGs
│   ├── MARKSHEET/
│   ├── INCOME_CERTIFICATE/
│   └── DOMICILE_CERTIFICATE/
├── annotations/
│   ├── ocr_ground_truth/                  # OCR text ground truth JSONs
│   └── field_annotations/                 # Field-level + bounding box JSONs
├── augmented/                             # Augmented image variants
│   ├── GOVERNMENT_ID/
│   ├── MARKSHEET/
│   ├── INCOME_CERTIFICATE/
│   └── DOMICILE_CERTIFICATE/
├── split/
│   ├── train/                             # 70% of students
│   │   ├── images/{doc_type}/
│   │   └── annotations/{ocr,field}/
│   ├── val/                               # 15% of students
│   └── test/                              # 15% of students
├── verification_labels.json               # VALID / NEEDS_REVIEW labels
├── split_manifest.json                    # Student IDs per split
├── augmentation_metadata.json             # Augmentation details
├── validation_report.json                 # Validation check results
├── dataset_statistics.json                # Full statistics
└── dataset_statistics_report.txt          # Human-readable report
```

## Visual Augmentations

Each clean document image gets 3 random augmentations from:

| Augmentation | Description |
|---|---|
| `blur` | Gaussian blur (simulates unfocused photo) |
| `rotation` | ±5° rotation (simulates tilted scan) |
| `brightness_up` | Increased brightness (overexposed) |
| `brightness_down` | Decreased brightness (underexposed) |
| `noise` | Gaussian noise (simulates sensor noise) |
| `jpeg_compression` | JPEG artifacts (quality=30) |
| `perspective_distortion` | Slight perspective warp (simulates angled photo) |

## Verification Cases

30% of students are labeled `NEEDS_REVIEW` with controlled inconsistencies:

- **Name mismatch** — Slight spelling change across documents
- **Date of birth mismatch** — Different DOB across documents
- **Income above threshold** — Income exceeds scholarship scheme limit
- **Percentage below minimum** — Marks below scholarship requirement
- **Missing fields** — Some fields set to null
- **Wrong state** — Domicile state ≠ Maharashtra

These align with the real backend `RulesEngine` and `DEFAULT_SCHOLARSHIP_RULES`.

## Backend Schema Alignment

All field names match the real VeriCampus AI backend extraction schemas:

- `GovernmentIdExtraction`: `id_type`, `id_number`, `full_name`, `date_of_birth`, `gender`, `address`
- `MarksheetExtraction`: `candidate_name`, `roll_number`, `exam_name`, `passing_year`, `total_marks`, `max_marks`, `percentage`, `result_status`
- `IncomeCertificateExtraction`: `applicant_name`, `father_guardian_name`, `annual_income_inr`, `certificate_number`, `issuing_authority`, `issue_date`, `financial_year`
- `DomicileCertificateExtraction`: `candidate_name`, `state`, `is_maharashtra_domicile`, `certificate_number`, `issue_date`

Scholarship schemes and eligibility rules match `DEFAULT_SCHOLARSHIP_RULES` from the backend.

## CLI Options

```
python ml/data_generator/generate_dataset.py [OPTIONS]

--samples-per-class N    Number of students (default: 10)
--seed N                 Random seed for reproducibility (default: 42)
--output-dir PATH        Custom output directory
--skip-augmentation      Skip augmentation step (faster)
```

## Dependencies

Listed in `ml/requirements.txt`:

- Pillow ≥ 10.0.0
- Faker ≥ 20.0.0
- numpy ≥ 1.26.0
- opencv-python ≥ 4.8.0
- pandas ≥ 2.1.0

## Module Architecture

```
ml/data_generator/
├── __init__.py
├── config.py                    # Central configuration
├── generate_students.py         # Synthetic student data (Faker)
├── generate_documents.py        # Pillow document image rendering
├── generate_annotations.py      # OCR ground truth + field annotations
├── generate_verification_cases.py   # VALID / NEEDS_REVIEW labeling
├── augment_images.py            # Visual augmentations (OpenCV)
├── split_dataset.py             # Train/val/test split by student
├── validate_dataset.py          # Dataset validation checks
├── generate_statistics.py       # Statistics report
└── generate_dataset.py          # CLI entry point (orchestrator)
```

## Stage 1: AI Document Quality Gate

The **Stage 1 AI Document Quality Gate** evaluates the physical and optical readability of uploaded scholarship documents before downstream AI verification and OCR extraction.

> **CRITICAL ARCHITECTURAL SAFEGUARD:**  
> The quality gate **evaluates visual and optical readability only**. It **NEVER** judges document authenticity, student scholarship eligibility, or commits automated fraud rejections.  
> If quality is insufficient (`< 70.0`), the system sets application status to `NEEDS_REVIEW` and prompts the student to re-upload clear documents via the existing correction workflow.

### Quality Tiers & Thresholds

| Quality Tier | Score Range | Gate Status | Downstream Action |
|---|---|---|---|
| **HIGH** | `85.0 – 100.0` | `PASS` | Proceed to OCR, Field Extraction & Rules Engine |
| **ACCEPTABLE** | `70.0 – 84.9` | `WARNING` | Proceed with caution (soft flag for human review) |
| **LOW** | `40.0 – 69.9` | `REUPLOAD_REQUIRED` | Application marked `NEEDS_REVIEW`; student correction request created |
| **UNREADABLE** | `0.0 – 39.9` | `REUPLOAD_REQUIRED` | Application marked `NEEDS_REVIEW`; immediate re-upload required |

### Extracted Optical & Physical Features (10 Dimensions)

1. `resolution_megapixels`: Document image pixel count (checks if $\ge 150\text{ DPI}$).
2. `blur_laplacian_variance`: Standard variance of the Laplacian filter (unfocused / motion blur).
3. `normalized_sharpness`: Tenengrad gradient energy density ($0.0 – 100.0$).
4. `brightness_mean`: Mean luminance channel intensity ($0.0 – 255.0$).
5. `brightness_std`: Luminance spread across document.
6. `contrast_rms`: Root-mean-square contrast of grayscale document.
7. `noise_estimate_sigma`: High-frequency sensor noise standard deviation.
8. `skew_angle_degrees`: Hough line transform tilt / orientation deviation.
9. `crop_margin_completeness`: Edge contour proximity ratio (detects cut-off text/borders while ignoring watermarks).
10. `ocr_confidence`: Baseline OCR character confidence ($0.0 – 1.0$) when text is extracted.

### Quality Model Architecture

- **Classifier:** `RandomForestClassifier` (100 estimators, max depth 6) with `StandardScaler`.
- **Hybrid Fusion:** Combines classical explainable rule heuristics (60%) with trained ML model probabilities (40%).
- **Explainability:** Generates deterministic, human-readable reason strings (e.g., *"Noticeable image blur detected; text clarity is reduced"*).
- **Graceful Fallback:** If the model artifact is missing or corrupted, the system automatically falls back to heuristic rule scoring without failing runtime requests.
- **Zero Leakage:** Split strictly by `student_id` (all 4 documents of a student reside in the same split).

### Quality Gate CLI Commands

```powershell
# Set encoding on Windows
$env:PYTHONIOENCODING='utf-8'

# 1. Train the Document Quality Gate Model
python -m ml.document_quality.train

# 2. Evaluate Trained Model on Test Split
python -m ml.document_quality.evaluate

# 3. Run Inference on a Single Document
python -m ml.document_quality.inference --image-path "path/to/document.png"
```

## Stage 5: Pluggable Authority Verification Architecture

Located at `backend/app/services/verification/authority/`:
- **Contract:** `BaseAuthorityProvider` abstract base class.
- **Implementations:**
  - `DigiLockerProvider`: Pluggable stub returning `NOT_AVAILABLE`.
  - `NADProvider`: Pluggable stub returning `NOT_AVAILABLE`.
  - `DirectIssuerProvider`: Pluggable stub returning `NOT_AVAILABLE`.
  - `UnavailableProvider`: Default production provider returning `NOT_AVAILABLE` with `is_available: false`.
- **Strict Compliance:** No fake API calls or synthetic verification responses against real government portals.

## Dependencies

Listed in `ml/requirements.txt`:
- Pillow ≥ 10.0.0
- Faker ≥ 20.0.0
- numpy ≥ 1.26.0
- opencv-python ≥ 4.8.0
- pandas ≥ 2.1.0
- scikit-learn ≥ 1.3.0
- joblib ≥ 1.3.0

## Directory Structure

```
ml/
├── data_generator/                    # Synthetic dataset generation pipeline
│   ├── quality_degradations.py        # Physical & optical degradation generator
│   ├── generate_documents.py          # Document renderer with quality labels
│   ├── generate_annotations.py        # Quality labels & metrics generator
│   └── ...
├── document_quality/                  # Stage 1 Quality Gate Module
│   ├── config.py                      # Thresholds & model paths (single source of truth)
│   ├── schemas.py                     # Pydantic schemas (QualityAssessment, etc.)
│   ├── features.py                    # 10 physical & optical feature extractors
│   ├── scorer.py                      # Deterministic rule scorer & reason generator
│   ├── model.py                       # RandomForest classifier pipeline
│   ├── dataset.py                     # Non-leaking student-split dataset loader
│   ├── train.py                       # Training script
│   ├── evaluate.py                    # Boundary confusion & evaluation metrics
│   └── inference.py                   # Runtime inference engine with caching & fallback
├── models/
│   └── quality_gate_model.joblib      # Trained model artifact (gitignored)
└── requirements.txt
```
