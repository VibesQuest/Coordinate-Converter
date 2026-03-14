from __future__ import annotations

from dataclasses import dataclass

from tests._coords import EXPANSION_TO_VERSION, ZoneBucketCase, validate_map_buckets


SUPPORTED_EXPANSIONS = {"classic", "sod", "tbc", "wotlk"}
KNOWN_UNMAPPED_LEGACY_KEYS = {
    "classic": set(),
    "sod": set(),
    "wotlk": {
        10002,  # BLACKROCK_DEPTHS_SHADOWFORGE_CITY
        10047,  # BAND_OF_ACCELERATION
        10048,  # BAND_OF_TRANSMUTATION
        10049,  # BAND_OF_ALIGNMENT
        10050,  # THE_DESCENT_OF_MADNESS
        10051,  # THE_SPARK_OF_IMAGINATION
        10052,  # THE_INNER_SANCTUM_OF_ULDUAR
        10053,  # UTGARDE_PINNACLE_LOWER_LEVEL
        10054,  # THE_TERRESTRIAL_WATCHTOWER
        10055,  # THE_BROOD_PIT
        10056,  # HADRONOXS_LAIR
        10057,  # UTGARDE_KEEP_MIDDLE_LEVEL
        10058,  # UTGARDE_KEEP_UPPER_LEVEL
        10059,  # THE_CULLING_OF_STRATHOLME_CITY
        10060,  # DRAKTHARON_KEEP_UPPER_LEVEL
        10061,  # GUNDRAK_LOWER_LEVEL
        10062,  # NAXXRAMAS_CONSTRUCT_QUARTER
        10063,  # NAXXRAMAS_ARACHNID_QUARTER
        10064,  # NAXXRAMAS_MILITARY_QUARTER
        10065,  # NAXXRAMAS_PLAGUE_QUARTER
        10066,  # NAXXRAMAS_FROSTWYRM_LAIR
        10067,  # ICECROWN_CITADEL_UPPER_SPIRE
        10068,  # ICECROWN_CITADEL_QUEEN_LANA_THEL
        10069,  # ICECROWN_CITADEL_SINDRAGOSA
        10070,  # ICECROWN_CITADEL_RAMPART_OF_SKULLS
        10071,  # ICECROWN_CITADEL_DEATHBRINGERS_RISE
        10072,  # ICECROWN_CITADEL_THE_FROZEN_THRONE
    },
}


@dataclass(frozen=True)
class ConversionFailure:
    case: ZoneBucketCase
    point_index: int
    error_type: str
    message: str


def test_every_coordinate_in_corrections_corpus_converts_or_hits_known_fake_ids(
    corrections_cases: list[ZoneBucketCase],
    coordinate_runtimes: dict[str, dict],
) -> None:
    failures = _collect_failures(corrections_cases, coordinate_runtimes)
    unexpected_errors: list[str] = []
    seen_known_fake_ids: set[tuple[str, int]] = set()

    for failure in failures:
        expected_ids = KNOWN_UNMAPPED_LEGACY_KEYS.get(failure.case.expansion, set())
        if (
            failure.error_type == "KeyError"
            and failure.case.zone_area_id in expected_ids
            and f"No coordinate mapping for legacy key={failure.case.zone_area_id}" in failure.message
        ):
            seen_known_fake_ids.add((failure.case.expansion, failure.case.zone_area_id))
            continue
        unexpected_errors.append(_format_failure(failure))

    expected_known_fake_ids = {
        (expansion, legacy_key)
        for expansion, legacy_keys in KNOWN_UNMAPPED_LEGACY_KEYS.items()
        for legacy_key in legacy_keys
    }

    assert not unexpected_errors, _format_errors(unexpected_errors)
    assert seen_known_fake_ids == expected_known_fake_ids


def _collect_failures(
    corrections_cases: list[ZoneBucketCase],
    coordinate_runtimes: dict[str, dict],
) -> list[ConversionFailure]:
    failures: list[ConversionFailure] = []

    for case in corrections_cases:
        if case.expansion not in SUPPORTED_EXPANSIONS:
            continue
        version = EXPANSION_TO_VERSION[case.expansion]
        runtime = coordinate_runtimes[version]
        converter = runtime["converter"]
        pack = runtime["pack"]

        for point_index, point in enumerate(case.points, start=1):
            zone_buckets = {case.zone_area_id: [[float(point[0]), float(point[1])]]}

            try:
                converted = converter.convert_zone_buckets(pack, zone_buckets)
                replaced = converter.replace_unknown_instance_buckets(pack, converted)
            except Exception as exc:
                failures.append(
                    ConversionFailure(
                        case=case,
                        point_index=point_index,
                        error_type=type(exc).__name__,
                        message=str(exc),
                    )
                )
                continue

            bucket_errors = validate_map_buckets(replaced)
            if bucket_errors:
                failures.extend(
                    ConversionFailure(
                        case=case,
                        point_index=point_index,
                        error_type="bucket",
                        message=message,
                    )
                    for message in bucket_errors
                )

    return failures


def _case_label(case: ZoneBucketCase, point_index: int) -> str:
    return (
        f"[{case.expansion}/{case.entity_type} {case.entity_id} in {case.file} "
        f"{case.source_label} point#{point_index}]"
    )


def _format_failure(failure: ConversionFailure) -> str:
    prefix = _case_label(failure.case, failure.point_index)
    if failure.error_type == "bucket":
        return f"{prefix} {failure.message}"
    return f"{prefix} raised {failure.error_type}: {failure.message}"


def _format_errors(errors: list[str], limit: int = 100) -> str:
    if not errors:
        return ""
    head = errors[:limit]
    suffix = "" if len(errors) <= limit else f"\n... {len(errors) - limit} more"
    return "\n".join(head) + suffix
