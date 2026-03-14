from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from tests._coords import (
    EXPANSION_TO_VERSION,
    ZoneBucketCase,
    iter_zone_bucket_cases,
    load_runtime_modules,
    validate_map_buckets,
)


SUPPORTED_EXPANSIONS = tuple(EXPANSION_TO_VERSION)


@dataclass(frozen=True)
class ConversionFailure:
    case: ZoneBucketCase
    point_index: int
    error_type: str
    message: str


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Report which legacy zone keys in corrections.json still fail conversion."
    )
    parser.add_argument(
        "--expansion",
        action="append",
        choices=SUPPORTED_EXPANSIONS,
        dest="expansions",
        help="Restrict the report to one or more expansions.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="How many example failures to print per legacy key. Default: 10.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of a text report.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    corrections_data = _load_corrections_data(repo_root)
    corrections_cases = list(iter_zone_bucket_cases(corrections_data))
    runtimes = _load_runtimes(repo_root)
    expansions = tuple(args.expansions or SUPPORTED_EXPANSIONS)
    failures = _collect_failures(corrections_cases, runtimes, expansions)

    if args.json:
        print(json.dumps(_to_json_payload(failures, limit=args.limit), indent=2))
        return

    _print_report(failures, expansions=expansions, limit=args.limit)


def _load_corrections_data(repo_root: Path) -> dict:
    candidates = (
        repo_root / "ui" / "public" / "corrections.json",
        repo_root / "tests" / "data" / "corrections.json",
    )
    for path in candidates:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    raise FileNotFoundError(
        "No corrections.json found; checked: " + ", ".join(str(path) for path in candidates)
    )


def _load_runtimes(repo_root: Path) -> dict[str, dict]:
    runtimes: dict[str, dict] = {}
    for version in sorted(set(EXPANSION_TO_VERSION.values())):
        loader_module, converter_module = load_runtime_modules(repo_root, version)
        pack_dir = repo_root / "output" / version
        runtimes[version] = {
            "loader": loader_module,
            "converter": converter_module,
            "pack": loader_module.load_coordinate_pack(pack_dir),
        }
    return runtimes


def _collect_failures(
    corrections_cases: list[ZoneBucketCase],
    runtimes: dict[str, dict],
    expansions: tuple[str, ...],
) -> list[ConversionFailure]:
    failures: list[ConversionFailure] = []
    allowed = set(expansions)

    for case in corrections_cases:
        if case.expansion not in allowed:
            continue
        version = EXPANSION_TO_VERSION[case.expansion]
        runtime = runtimes[version]
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

            for message in validate_map_buckets(replaced):
                failures.append(
                    ConversionFailure(
                        case=case,
                        point_index=point_index,
                        error_type="bucket",
                        message=message,
                    )
                )

    return failures


def _group_failures(
    failures: list[ConversionFailure],
) -> dict[str, dict[int, list[ConversionFailure]]]:
    grouped: dict[str, dict[int, list[ConversionFailure]]] = defaultdict(lambda: defaultdict(list))
    for failure in failures:
        grouped[failure.case.expansion][failure.case.zone_area_id].append(failure)
    return grouped


def _print_report(
    failures: list[ConversionFailure],
    *,
    expansions: tuple[str, ...],
    limit: int,
) -> None:
    print(f"expansions={list(expansions)} total_failures={len(failures)}")
    grouped = _group_failures(failures)

    for expansion in expansions:
        expansion_group = grouped.get(expansion, {})
        expansion_failure_count = sum(len(items) for items in expansion_group.values())
        print(f"\n[{expansion}] failing_legacy_keys={len(expansion_group)} failures={expansion_failure_count}")
        for zone_area_id, items in sorted(
            expansion_group.items(),
            key=lambda item: (-len(item[1]), item[0]),
        ):
            sample = items[0]
            print(
                f"  legacyKey={zone_area_id} count={len(items)} "
                f"first_error={sample.error_type}: {sample.message}"
            )
            for failure in items[:limit]:
                print(
                    "    "
                    f"{failure.case.entity_type} {failure.case.entity_id} "
                    f"{failure.case.source_label} point#{failure.point_index} "
                    f"in {failure.case.file}"
                )


def _to_json_payload(
    failures: list[ConversionFailure],
    *,
    limit: int,
) -> dict[str, object]:
    grouped = _group_failures(failures)
    payload: dict[str, object] = {
        "totalFailures": len(failures),
        "expansions": {},
    }
    expansions_payload: dict[str, object] = {}
    for expansion, expansion_group in grouped.items():
        legacy_keys_payload: dict[str, object] = {}
        for zone_area_id, items in sorted(
            expansion_group.items(),
            key=lambda item: (-len(item[1]), item[0]),
        ):
            first = items[0]
            legacy_keys_payload[str(zone_area_id)] = {
                "count": len(items),
                "firstErrorType": first.error_type,
                "firstErrorMessage": first.message,
                "examples": [
                    {
                        "entityType": failure.case.entity_type,
                        "entityId": failure.case.entity_id,
                        "file": failure.case.file,
                        "sourceLabel": failure.case.source_label,
                        "pointIndex": failure.point_index,
                        "errorType": failure.error_type,
                        "message": failure.message,
                    }
                    for failure in items[:limit]
                ],
            }
        expansions_payload[expansion] = {
            "failureCount": sum(len(items) for items in expansion_group.values()),
            "failingLegacyKeyCount": len(expansion_group),
            "legacyKeys": legacy_keys_payload,
        }
    payload["expansions"] = expansions_payload
    return payload


if __name__ == "__main__":
    main()
