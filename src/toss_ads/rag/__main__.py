"""CLI entry point for the Product RAG HTTP service."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys

import psycopg

from .config import Settings
from .review_followup import (
    ASPECT_TAXONOMY_VERSION,
    SUPPORTED_REVIEW_ASPECTS,
    SUPPORTED_REVIEW_POLARITIES,
)
from .review_classifier import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    LocalReviewAspectClassifier,
    PROMPT_VERSION,
    ReviewClassificationError,
)
from .store import RagStore


def _annotation_rows(path: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    try:
        with open(path, encoding="utf-8") as source:
            for line_number, line in enumerate(source, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except (json.JSONDecodeError, UnicodeError):
                    raise ValueError(f"invalid_jsonl_line:{line_number}") from None
                if not isinstance(row, dict):
                    raise ValueError(f"invalid_annotation_line:{line_number}")
                product_id = row.get("product_id")
                review_key = row.get("review_key")
                aspect = row.get("aspect")
                polarity = row.get("polarity")
                confidence = row.get("confidence")
                classifier_version = row.get("classifier_version")
                profile = row.get("profile")
                dataset_version = row.get("dataset_version")
                category = row.get("category")
                taxonomy_version = row.get("taxonomy_version")
                if (
                    not isinstance(product_id, str) or not product_id.strip()
                    or not isinstance(review_key, str) or not review_key.strip()
                    or aspect not in SUPPORTED_REVIEW_ASPECTS
                    or polarity not in SUPPORTED_REVIEW_POLARITIES
                    or classifier_version is not None
                    and (
                        not isinstance(classifier_version, str)
                        or not classifier_version.strip()
                        or len(classifier_version) > 128
                    )
                    or profile is not None
                    and (not isinstance(profile, str) or not profile.strip() or len(profile) > 128)
                    or dataset_version is not None
                    and (
                        not isinstance(dataset_version, str)
                        or not dataset_version.strip()
                        or len(dataset_version) > 256
                    )
                    or category is not None
                    and (not isinstance(category, str) or not category.strip() or len(category) > 128)
                    or taxonomy_version is not None
                    and (
                        not isinstance(taxonomy_version, str)
                        or not taxonomy_version.strip()
                        or len(taxonomy_version) > 128
                    )
                ):
                    raise ValueError(f"invalid_annotation_line:{line_number}")
                if confidence is not None and (
                    isinstance(confidence, bool)
                    or not isinstance(confidence, (int, float))
                    or not math.isfinite(float(confidence))
                    or not 0 <= float(confidence) <= 1
                ):
                    raise ValueError(f"invalid_annotation_line:{line_number}")
                rows.append({
                    "product_id": product_id,
                    "review_key": review_key,
                    "aspect": aspect,
                    "polarity": polarity,
                    "confidence": None if confidence is None else float(confidence),
                    "classifier_version": classifier_version,
                    "profile": profile,
                    "dataset_version": dataset_version,
                    "category": category,
                    "taxonomy_version": taxonomy_version,
                })
    except (OSError, UnicodeError):
        raise ValueError("annotation_file_unavailable") from None
    if not rows:
        raise ValueError("empty_annotation_file")
    return rows

def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m toss_ads.rag")
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="serve POST /v1/rag/search")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8001)
    load = commands.add_parser(
        "load-review-aspect-labels",
        help="atomically load a complete, versioned review aspect label JSONL file",
    )
    load.add_argument("--file", required=True)
    load.add_argument("--profile", default=None)
    load.add_argument("--dataset-version", required=True)
    load.add_argument("--category", required=True)
    load.add_argument("--taxonomy-version", default=ASPECT_TAXONOMY_VERSION)
    load.add_argument("--classifier-version", default=None)
    classify = commands.add_parser(
        "classify-review-aspects",
        help="classify the full review population through a loopback-only local model",
    )
    classify.add_argument("--output", required=True)
    classify.add_argument("--profile", default=None)
    classify.add_argument("--dataset-version", default=None)
    classify.add_argument("--category", default="beauty")
    classify.add_argument("--aspect", default="moisturizing", choices=SUPPORTED_REVIEW_ASPECTS)
    classify.add_argument("--model", default=os.getenv("RAG_REVIEW_CLASSIFIER_MODEL", DEFAULT_MODEL))
    classify.add_argument(
        "--base-url",
        default=os.getenv("RAG_REVIEW_CLASSIFIER_BASE_URL", DEFAULT_BASE_URL),
    )
    classify.add_argument("--batch-size", type=int, default=8, choices=range(1, 17))
    classify.add_argument("--max-review-chars", type=int, default=4000, choices=range(1, 32001))
    classify.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.command == "serve":
        import uvicorn

        uvicorn.run("toss_ads.rag.api:app", host=args.host, port=args.port)
        return 0

    annotation_database_url = os.getenv("RAG_ANNOTATION_DATABASE_URL", "").strip()
    if not annotation_database_url:
        error_prefix = "classification_failed" if args.command == "classify-review-aspects" else "annotation_import_failed"
        print(f"{error_prefix}:missing_RAG_ANNOTATION_DATABASE_URL", file=sys.stderr)
        return 2

    if args.command == "classify-review-aspects":
        profile = (
            args.profile
            or os.getenv("RAG_DEFAULT_PROFILE", "test_items2").strip()
            or "test_items2"
        )
        output_path = os.path.abspath(args.output)
        if os.path.exists(output_path) and not args.resume:
            print("classification_failed:output_exists_use_resume", file=sys.stderr)
            return 2
        if args.resume and not os.path.isfile(output_path) and os.path.exists(output_path):
            print("classification_failed:output_not_a_file", file=sys.stderr)
            return 2
        try:
            Settings(rag_database_url=annotation_database_url)
            existing_rows = _annotation_rows(output_path) if args.resume and os.path.isfile(output_path) else []
            existing_by_key: dict[tuple[str, str], dict[str, object]] = {}
            for row in existing_rows:
                key = (str(row["product_id"]), str(row["review_key"]))
                if key in existing_by_key or row["aspect"] != args.aspect:
                    raise ValueError("resume_file_has_duplicate_or_mismatched_rows")
                if row.get("classifier_version") != (
                    f"{args.model};prompt={PROMPT_VERSION};thinking=off"
                ):
                    raise ValueError("resume_file_classifier_version_mismatch")
                existing_by_key[key] = row

            with LocalReviewAspectClassifier(base_url=args.base_url, model=args.model) as classifier:
                classifier.check_model_available()
                with RagStore(annotation_database_url) as store:
                    active = store.active_run(profile)
                    if active is None:
                        raise ValueError("active_profile_not_found")
                    if (
                        args.dataset_version is not None
                        and args.dataset_version != active["dataset_version"]
                    ):
                        raise ValueError("active_dataset_version_mismatch")
                    for row in existing_rows:
                        if (
                            row.get("profile") != profile
                            or row.get("dataset_version") != active["dataset_version"]
                            or row.get("category") != args.category
                            or row.get("taxonomy_version") != ASPECT_TAXONOMY_VERSION
                        ):
                            raise ValueError("resume_file_dataset_scope_mismatch")
                    if args.category not in store.supported_categories(active["run_id"]):
                        raise ValueError("unsupported_category")
                    reviews = store.list_review_texts(
                        active["run_id"], active["dataset_version"], args.category
                    )
                    if not reviews:
                        raise ValueError("empty_review_population")

                    population_keys = {
                        (str(row["product_id"]), str(row["source_id"]))
                        for row in reviews
                    }
                    if not set(existing_by_key).issubset(population_keys):
                        raise ValueError("resume_file_has_unknown_reviews")

                    mode = "a" if args.resume and os.path.isfile(output_path) else "w"
                    with open(output_path, mode, encoding="utf-8") as output:
                        pending: list[dict[str, object]] = []

                        def write_rows(rows: list[dict[str, object]]) -> None:
                            for row in rows:
                                output.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                            output.flush()

                        def classify_pending() -> None:
                            if not pending:
                                return
                            labels = classifier.classify_batch([
                                str(row["review_text"]) for row in pending
                            ])
                            version = classifier.classifier_version
                            if existing_rows and version != existing_rows[0].get("classifier_version"):
                                raise ValueError("resume_file_classifier_version_mismatch")
                            write_rows([
                                {
                                    "product_id": row["product_id"],
                                    "review_key": row["source_id"],
                                    "aspect": args.aspect,
                                    "polarity": polarity,
                                    "confidence": None,
                                    "classifier_version": version,
                                    "profile": profile,
                                    "dataset_version": active["dataset_version"],
                                    "category": args.category,
                                    "taxonomy_version": ASPECT_TAXONOMY_VERSION,
                                }
                                for row, polarity in zip(pending, labels, strict=True)
                            ])
                            pending.clear()

                        for index, row in enumerate(reviews, 1):
                            key = (str(row["product_id"]), str(row["source_id"]))
                            if key in existing_by_key:
                                continue
                            text_value = row.get("review_text")
                            valid_text = (
                                row.get("text_valid") is True
                                and isinstance(text_value, str)
                                and bool(text_value.strip())
                            )
                            if not valid_text or len(str(text_value)) > args.max_review_chars:
                                write_rows([{
                                    "product_id": row["product_id"],
                                    "review_key": row["source_id"],
                                    "aspect": args.aspect,
                                    "polarity": "unclassified",
                                    "confidence": None,
                                    "classifier_version": classifier.classifier_version,
                                    "profile": profile,
                                    "dataset_version": active["dataset_version"],
                                    "category": args.category,
                                    "taxonomy_version": ASPECT_TAXONOMY_VERSION,
                                }])
                            else:
                                pending.append(row)
                                if len(pending) >= args.batch_size:
                                    classify_pending()
                            if index % 1000 == 0:
                                print(
                                    f"classification_progress={index}/{len(reviews)}",
                                    file=sys.stderr,
                                )
                        classify_pending()

            completed_rows = _annotation_rows(output_path)
            completed_keys = [(str(row["product_id"]), str(row["review_key"])) for row in completed_rows]
            if (
                len(completed_keys) != len(population_keys)
                or set(completed_keys) != population_keys
                or any(row["aspect"] != args.aspect for row in completed_rows)
                or len({row.get("classifier_version") for row in completed_rows}) != 1
                or any(
                    row.get("profile") != profile
                    or row.get("dataset_version") != active["dataset_version"]
                    or row.get("category") != args.category
                    or row.get("taxonomy_version") != ASPECT_TAXONOMY_VERSION
                    for row in completed_rows
                )
            ):
                raise ValueError("classification_output_population_mismatch")
            counts = {polarity: 0 for polarity in SUPPORTED_REVIEW_POLARITIES}
            for row in completed_rows:
                counts[str(row["polarity"])] += 1
            print(json.dumps({
                "profile": profile,
                "dataset_version": active["dataset_version"],
                "category": args.category,
                "aspect": args.aspect,
                "review_population_count": len(reviews),
                "label_counts": counts,
                "classifier_version": completed_rows[0]["classifier_version"],
                "confidence": "not_calibrated; stored as null",
                "output_file": output_path,
            }, ensure_ascii=False, sort_keys=True))
            return 0
        except (ValueError, OSError, ReviewClassificationError) as error:
            code = error.code if isinstance(error, ReviewClassificationError) else str(error)
            print(f"classification_failed:{code}", file=sys.stderr)
            return 2
        except psycopg.Error:
            print("classification_failed:database_error", file=sys.stderr)
            return 2

    if args.taxonomy_version != ASPECT_TAXONOMY_VERSION:
        print("annotation_import_failed:unsupported_taxonomy_version", file=sys.stderr)
        return 2
    try:
        # Reuse the endpoint guard so the loader cannot target a non-RAG database.
        Settings(rag_database_url=annotation_database_url)
        labels = _annotation_rows(args.file)
        file_versions = {row.get("classifier_version") for row in labels}
        classifier_version = args.classifier_version
        if classifier_version is None and len(file_versions) == 1:
            classifier_version = next(iter(file_versions))
        if (
            not isinstance(classifier_version, str)
            or not classifier_version.strip()
            or len(classifier_version) > 128
        ):
            raise ValueError("invalid_classifier_version")
        if any(
            row.get("classifier_version") is not None
            and row["classifier_version"] != classifier_version
            for row in labels
        ):
            raise ValueError("annotation_classifier_version_mismatch")
        profile = args.profile or os.getenv("RAG_DEFAULT_PROFILE", "all_products").strip()
        if any(
            (row.get("profile") is not None and row["profile"] != profile)
            or (
                row.get("dataset_version") is not None
                and row["dataset_version"] != args.dataset_version
            )
            or (row.get("category") is not None and row["category"] != args.category)
            or (
                row.get("taxonomy_version") is not None
                and row["taxonomy_version"] != args.taxonomy_version
            )
            for row in labels
        ):
            raise ValueError("annotation_dataset_scope_mismatch")
        with RagStore(annotation_database_url) as store:
            result = store.import_review_aspect_annotations(
                profile_name=profile,
                dataset_version=args.dataset_version,
                category=args.category,
                taxonomy_version=args.taxonomy_version,
                classifier_version=classifier_version,
                aspects=SUPPORTED_REVIEW_ASPECTS,
                labels=labels,
            )
    except (ValueError, OSError) as error:
        print(f"annotation_import_failed:{error}", file=sys.stderr)
        return 2
    except psycopg.Error:
        print("annotation_import_failed:database_error", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
