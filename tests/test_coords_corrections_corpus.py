from __future__ import annotations

import pytest

from tests._coords import (
    COORD_FIELDS,
    EXPANSION_TO_VERSION,
    ZoneBucketCase,
    classify_zone_bucket_case,
    validate_map_buckets,
)


def test_corrections_corpus_contains_coordinate_cases(corrections_cases: list[ZoneBucketCase]) -> None:
    assert corrections_cases


def test_all_coordinate_points_in_corrections_corpus_are_numeric_pairs(
    corrections_cases: list[ZoneBucketCase],
) -> None:
    errors: list[str] = []

    for case in corrections_cases:
        if not case.points:
            errors.append(f"{case.file}:{case.entity_id}:{case.source_label} contains no points")
            continue
        for point in case.points:
            if len(point) != 2:
                errors.append(
                    f"{case.file}:{case.entity_id}:{case.source_label} "
                    f"has a point with unexpected length {len(point)}"
                )
            for value in point:
                if not isinstance(value, float):
                    errors.append(
                        f"{case.file}:{case.entity_id}:{case.source_label} "
                        f"contains a non-float point value {value!r}"
                    )

    assert not errors, _format_errors(errors)


@pytest.mark.parametrize("expansion", sorted(EXPANSION_TO_VERSION))
@pytest.mark.parametrize("field", COORD_FIELDS)
def test_corpus_zone_buckets_convert_or_fail_by_design(
    expansion: str,
    field: str,
    corrections_cases: list[ZoneBucketCase],
    coordinate_runtimes: dict[str, dict],
) -> None:
    cases = [case for case in corrections_cases if case.expansion == expansion and case.field == field]
    if not cases:
        pytest.skip(f"No {field} cases for {expansion}")

    version = EXPANSION_TO_VERSION[expansion]
    runtime = coordinate_runtimes[version]
    converter = runtime["converter"]
    pack = runtime["pack"]

    errors: list[str] = []
    for case in cases:
        expectation = classify_zone_bucket_case(pack, converter, case)
        zone_buckets = {case.zone_area_id: [list(point) for point in case.points]}

        try:
            converted = converter.convert_zone_buckets(pack, zone_buckets)
        except Exception as exc:  # pragma: no cover - asserted via expectation
            if expectation == "missing_mapping":
                if not isinstance(exc, KeyError):
                    errors.append(
                        f"{_case_label(case)} expected KeyError for missing mapping, got {type(exc).__name__}: {exc}"
                    )
            elif expectation == "unresolved_instance_non_sentinel":
                if not isinstance(exc, ValueError) or "unresolved instance space" not in str(exc):
                    errors.append(
                        f"{_case_label(case)} expected unresolved instance ValueError, "
                        f"got {type(exc).__name__}: {exc}"
                    )
            else:
                errors.append(
                    f"{_case_label(case)} should convert successfully but raised {type(exc).__name__}: {exc}"
                )
            continue

        if expectation != "convertible":
            errors.append(f"{_case_label(case)} unexpectedly converted despite expectation={expectation}")
            continue

        replaced = converter.replace_unknown_instance_buckets(pack, converted)
        bucket_errors = validate_map_buckets(replaced)
        if bucket_errors:
            errors.extend(f"{_case_label(case)} {message}" for message in bucket_errors)

    assert not errors, _format_errors(errors)


def _case_label(case: ZoneBucketCase) -> str:
    return (
        f"[{case.expansion}/{case.entity_type} {case.entity_id} in {case.file} "
        f"{case.source_label}]"
    )


def _format_errors(errors: list[str], limit: int = 50) -> str:
    if not errors:
        return ""
    head = errors[:limit]
    suffix = "" if len(errors) <= limit else f"\n... {len(errors) - limit} more"
    return "\n".join(head) + suffix
