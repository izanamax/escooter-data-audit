"""Validate a documented detection-only subset of COCO without modifying data."""

from collections import Counter
import math
from pathlib import PurePosixPath


def _integer(value):
    return type(value) is int and value >= 0


def _number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _filename(value):
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.replace("\\", "/")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or ":" in value or str(path) == ".":
        return None
    return str(path)


def audit_splits(splits, *, require_sequences=False):
    """Return a deterministic, JSON-serializable report for named COCO objects.

    IDs are local to each split. Leakage uses normalized, case-sensitive file
    names and optional image.source_sequence values, never local image IDs.
    This is a metadata audit: no image pixels or segmentation masks are read.
    """
    findings = []
    summaries = {}
    file_owners = {}
    sequence_owners = {}
    category_maps = {}

    def add(severity, code, split, location, message):
        findings.append(dict(severity=severity, code=code, split=split,
                             location=location, message=message))

    if not isinstance(splits, dict) or not splits:
        raise ValueError("Provide at least one named dataset split.")
    if any(not isinstance(name, str) or not name.strip() for name in splits):
        raise ValueError("Split names must be non-empty strings.")

    for name, data in sorted(splits.items()):
        summary = dict(images=0, annotations=0, categories=0,
                       images_without_annotations=0, sequences=0,
                       images_missing_sequence=0, annotations_per_category={})
        summaries[name] = summary
        if not isinstance(data, dict):
            add("error", "schema", name, "$", "Dataset must be a JSON object.")
            continue
        records = {}
        for key in ("images", "annotations", "categories"):
            value = data.get(key)
            if not isinstance(value, list):
                add("error", "schema", name, key, "Required field must be a list.")
                records[key] = []
            else:
                records[key] = value
                summary[key] = len(value)

        indexes = {}
        for key, rows in records.items():
            index = {}
            indexes[key] = index
            for i, row in enumerate(rows):
                location = f"{key}[{i}]"
                if not isinstance(row, dict):
                    add("error", "record_type", name, location, "Record must be an object.")
                    continue
                identifier = row.get("id")
                if not _integer(identifier):
                    add("error", "invalid_id", name, location, "id must be a non-negative integer.")
                elif identifier in index:
                    add("error", "duplicate_id", name, location, f"Duplicate {key} id {identifier}.")
                else:
                    index[identifier] = row

        categories = {}
        for i, row in enumerate(records["categories"]):
            if not isinstance(row, dict):
                continue
            label = row.get("name")
            if not isinstance(label, str) or not label.strip():
                add("error", "category_name", name, f"categories[{i}]", "Category name must be non-empty.")
            elif _integer(row.get("id")):
                categories[row["id"]] = label
        category_maps[name] = categories

        files = set()
        sequences = set()
        dimensions = {}
        for i, row in enumerate(records["images"]):
            if not isinstance(row, dict):
                summary["images_missing_sequence"] += 1
                continue
            location = f"images[{i}]"
            filename = _filename(row.get("file_name"))
            if filename is None:
                add("error", "file_name", name, location, "file_name must be a safe relative path.")
            elif filename in files:
                add("error", "duplicate_file", name, location, f"Repeated filename: {filename}.")
            else:
                files.add(filename)
                file_owners.setdefault(filename, set()).add(name)
            width, height = row.get("width"), row.get("height")
            if not (_integer(width) and width > 0 and _integer(height) and height > 0):
                add("error", "image_size", name, location, "Image dimensions must be positive integers.")
            elif _integer(row.get("id")):
                dimensions[row["id"]] = (width, height)
            sequence = row.get("source_sequence")
            if not isinstance(sequence, str) or not sequence.strip():
                summary["images_missing_sequence"] += 1
            else:
                sequence = sequence.strip()
                sequences.add(sequence)
                sequence_owners.setdefault(sequence, set()).add(name)
        summary["sequences"] = len(sequences)
        if not records["images"]:
            add("error", "empty_split", name, "images", "A split must contain at least one image.")
        if summary["images_missing_sequence"]:
            add("error" if require_sequences else "warning", "missing_sequence", name, "images",
                f"{summary['images_missing_sequence']} image(s) lack source_sequence; sequence leakage cannot be fully checked.")

        annotated = set()
        counts = Counter()
        for i, row in enumerate(records["annotations"]):
            if not isinstance(row, dict):
                continue
            location = f"annotations[{i}]"
            image_id, category_id = row.get("image_id"), row.get("category_id")
            image_valid = _integer(image_id) and image_id in indexes["images"]
            category_valid = _integer(category_id) and category_id in indexes["categories"]
            if not image_valid:
                add("error", "image_reference", name, location, "image_id does not reference a declared image.")
            else:
                annotated.add(image_id)
            if not category_valid:
                add("error", "category_reference", name, location, "category_id does not reference a declared category.")
            else:
                counts[str(category_id)] += 1
            box = row.get("bbox")
            if not isinstance(box, list) or len(box) != 4 or not all(_number(v) for v in box):
                add("error", "bbox_format", name, location, "bbox must contain four finite numbers [x,y,width,height].")
                continue
            x, y, width, height = box
            if x < 0 or y < 0 or width <= 0 or height <= 0:
                add("error", "bbox_geometry", name, location, "Box origin must be non-negative and size positive.")
            elif image_valid and image_id in dimensions:
                iw, ih = dimensions[image_id]
                if x + width > iw or y + height > ih:
                    add("error", "bbox_bounds", name, location, "Box extends beyond declared image dimensions.")
        summary["images_without_annotations"] = len(set(indexes["images"]) - annotated)
        summary["annotations_per_category"] = dict(sorted(counts.items()))

    if category_maps:
        first = next(iter(category_maps))
        for name, mapping in category_maps.items():
            if mapping != category_maps[first]:
                add("error", "category_map_mismatch", name, "categories",
                    f"Category id/name mapping differs from split {first}.")
    for code, owners in (("file_overlap", file_owners), ("sequence_overlap", sequence_owners)):
        for identifier, names in sorted(owners.items()):
            if len(names) > 1:
                add("error", code, ", ".join(sorted(names)), identifier,
                    "Identifier occurs in multiple splits.")

    errors = sum(item["severity"] == "error" for item in findings)
    warnings = sum(item["severity"] == "warning" for item in findings)
    return dict(schema_version=1, status="fail" if errors else "pass",
                error_count=errors, warning_count=warnings,
                sequence_check_complete=all(s["images"] > 0 and s["images_missing_sequence"] == 0 for s in summaries.values()),
                splits=summaries, findings=findings)
