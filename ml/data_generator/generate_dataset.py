#!/usr/bin/env python3
"""
VeriCampus AI — Synthetic ML Dataset Generator

Single command entry point that orchestrates the full pipeline:
  1. Generate synthetic student profiles
  2. Render document images (Pillow)
  3. Generate OCR ground truth + field annotations
  4. Generate verification cases (VALID / NEEDS_REVIEW)
  5. Apply visual augmentations
  6. Split dataset (70/15/15 by student identity)
  7. Validate dataset
  8. Generate statistics report

Usage:
  python ml/data_generator/generate_dataset.py --samples-per-class 10
  python ml/data_generator/generate_dataset.py --samples-per-class 100 --seed 123
"""
import argparse
import json
import sys
import time
from pathlib import Path

# Ensure ml/ is on sys.path so relative imports work
_this_dir = Path(__file__).resolve().parent          # ml/data_generator/
_ml_root = _this_dir.parent                          # ml/
if str(_ml_root) not in sys.path:
    sys.path.insert(0, str(_ml_root))

from data_generator import config
from data_generator.generate_students import generate_students
from data_generator.generate_documents import generate_all_documents
from data_generator.generate_annotations import generate_all_annotations
from data_generator.generate_verification_cases import generate_verification_cases
from data_generator.augment_images import augment_all_images
from data_generator.split_dataset import split_dataset
from data_generator.validate_dataset import validate_dataset
from data_generator.generate_statistics import generate_statistics


def main():
    parser = argparse.ArgumentParser(
        description="VeriCampus AI — Synthetic ML Dataset Generator",
    )
    parser.add_argument(
        "--samples-per-class",
        type=int,
        default=10,
        help="Number of student samples per document class (default: 10). "
             "Total images = samples_per_class × 4 doc types.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=config.DEFAULT_SEED,
        help=f"Random seed for reproducibility (default: {config.DEFAULT_SEED}).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory (default: ml/datasets/<run_name>).",
    )
    parser.add_argument(
        "--skip-augmentation",
        action="store_true",
        help="Skip image augmentation step (faster for testing).",
    )
    args = parser.parse_args()

    n = args.samples_per_class
    seed = args.seed

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = config.DEFAULT_OUTPUT_DIR / f"run_n{n}_seed{seed}"

    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  VERICAMPUS AI — SYNTHETIC ML DATASET GENERATOR")
    print("=" * 60)
    print(f"  Samples per class : {n}")
    print(f"  Total students    : {n}")
    print(f"  Total documents   : {n * len(config.DOCUMENT_TYPES)}")
    print(f"  Seed              : {seed}")
    print(f"  Output            : {output_dir}")
    print("=" * 60)
    print()

    t0 = time.time()

    # ── Step 1: Generate synthetic student profiles ─────────
    print("[1/8] Generating synthetic student profiles...")
    students = generate_students(count=n, seed=seed, output_dir=output_dir)

    # ── Step 2: Render document images ──────────────────────
    print(f"[2/8] Rendering {n * len(config.DOCUMENT_TYPES)} document images...")
    doc_metadata = generate_all_documents(students, output_dir)
    print(f"  ✓ Rendered {len(doc_metadata)} document images")

    # ── Step 3: Generate annotations ────────────────────────
    print("[3/8] Generating annotations (OCR ground truth + field-level)...")
    generate_all_annotations(students, doc_metadata, output_dir)

    # ── Step 4: Generate verification cases ─────────────────
    print("[4/8] Generating verification cases (VALID / NEEDS_REVIEW)...")
    verif_cases = generate_verification_cases(
        students, output_dir, seed=seed
    )
    valid_count = sum(1 for c in verif_cases if c["label"] == "VALID")
    review_count = sum(1 for c in verif_cases if c["label"] == "NEEDS_REVIEW")
    print(f"  ✓ VALID={valid_count}, NEEDS_REVIEW={review_count}")

    # ── Step 5: Visual augmentations ────────────────────────
    if not args.skip_augmentation:
        print("[5/8] Applying visual augmentations...")
        aug_metadata = augment_all_images(
            source_dir=output_dir / "images",
            output_dir=output_dir / "augmented",
            seed=seed,
        )
        print(f"  ✓ Created {len(aug_metadata)} augmented images")

        # Save augmentation metadata
        with open(
            output_dir / "augmentation_metadata.json", "w", encoding="utf-8"
        ) as f:
            json.dump(aug_metadata, f, indent=2)
    else:
        print("[5/8] Skipping augmentation (--skip-augmentation)")

    # ── Step 6: Split dataset ───────────────────────────────
    print("[6/8] Splitting dataset (70/15/15 by student identity)...")
    split_result = split_dataset(output_dir, seed=seed)

    # ── Step 7: Validate dataset ────────────────────────────
    print("[7/8] Validating dataset...")
    validation = validate_dataset(output_dir)
    for check in validation["checks"]:
        status_icon = "✓" if check["status"] == "PASS" else "✗"
        print(f"  {status_icon} {check['check_name']}: {check['details']}")
    print(f"  → Overall: {validation['summary']}")

    # ── Step 8: Generate statistics ─────────────────────────
    print("[8/8] Generating dataset statistics...")
    stats = generate_statistics(output_dir)

    elapsed = time.time() - t0

    # ── Final Summary ───────────────────────────────────────
    print()
    print("=" * 60)
    print("  DATASET GENERATION COMPLETE")
    print("=" * 60)
    print(f"  Total students         : {stats['total_students']}")
    print(f"  Total images           : {stats['total_images']}")
    print(f"  Total OCR annotations  : {stats['total_ocr_annotations']}")
    print(f"  Total field annotations: {stats['total_field_annotations']}")
    print(f"  Augmented images       : {stats['augmented_images_total']}")
    print(f"  Dataset size           : {stats['dataset_size_mb']} MB")
    print(f"  Validation             : {validation['status']}")
    print(f"  Elapsed time           : {elapsed:.1f}s")
    print(f"  Output directory       : {output_dir}")
    print("=" * 60)

    return 0 if validation["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
