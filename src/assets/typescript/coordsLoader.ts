import { promises as fs } from "node:fs";
import path from "node:path";

export type CoordinatePack = {
  manifest: any;
  zoneSpaces: any[];
  projectionBounds: any[];
  mapDefaults: any[];
  legacyBases: any[];
  instanceAnchors: any[];
  zoneSpaceByAreaId: Map<number, any>;
  projectionBoundsByKey: Map<string, any>;
  mapDefaultByMapId: Map<number, number>;
  legacyBasisByKey: Map<number, any>;
  instanceAnchorByMapId: Map<number, any>;
  instanceAnchorByZoneAreaId: Map<number, any>;
};

const FILES: Record<string, string> = {
  manifest: "manifest.json",
  zoneSpaces: "zone_spaces.json",
  projectionBounds: "projection_bounds.json",
  mapDefaults: "map_defaults.json",
  legacyBases: "legacy_bases.json",
  instanceAnchors: "instance_anchors.json",
};
const CURRENT_SCHEMA_VERSION = 2;

export async function loadCoordinatePack(packDir: string): Promise<CoordinatePack> {
  const pack: any = {};
  for (const [key, filename] of Object.entries(FILES)) {
    const filePath = path.join(packDir, filename);
    pack[key] = JSON.parse(await fs.readFile(filePath, "utf8"));
  }
  const schemaVersion = Number(pack.manifest.schemaVersion);
  if (schemaVersion !== CURRENT_SCHEMA_VERSION) {
    throw new Error(
      `Unsupported coordinate pack schemaVersion=${schemaVersion} in ${path.join(packDir, FILES.manifest)}; expected ${CURRENT_SCHEMA_VERSION}`,
    );
  }

  pack.zoneSpaceByAreaId = new Map<number, any>(
    pack.zoneSpaces.map((row: any) => [Number(row.zoneAreaId), row]),
  );
  pack.projectionBoundsByKey = new Map<string, any>(
    pack.projectionBounds.map((row: any) => [
      `${Number(row.mapId)}:${Number(row.uiMapId)}`,
      row,
    ]),
  );
  pack.mapDefaultByMapId = new Map<number, number>(
    pack.mapDefaults.map((row: any) => [Number(row.mapId), Number(row.coordUiMapId)]),
  );
  pack.legacyBasisByKey = new Map<number, any>(
    pack.legacyBases.map((row: any) => [Number(row.legacyKey), row]),
  );
  pack.instanceAnchorByMapId = new Map<number, any>(
    pack.instanceAnchors.map((row: any) => [Number(row.instanceMapId), row]),
  );
  pack.instanceAnchorByZoneAreaId = new Map<number, any>(
    pack.instanceAnchors
      .filter((row: any) => row.zoneAreaId !== null && row.zoneAreaId !== undefined)
      .map((row: any) => [Number(row.zoneAreaId), row]),
  );
  return pack as CoordinatePack;
}
