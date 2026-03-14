export const UNKNOWN_COORD_UI_MAP_ID = 0;

type Pack = {
  zoneSpaceByAreaId: Map<number, any>;
  projectionBoundsByKey: Map<string, any>;
  mapDefaultByMapId: Map<number, number>;
  legacyBasisByKey: Map<number, any>;
  instanceAnchorByMapId: Map<number, any>;
  instanceAnchorByZoneAreaId: Map<number, any>;
};

export function convertZoneBuckets(
  pack: Pack,
  zoneBuckets: Record<number, Array<[number, number]>>,
  coordDecimals = 2,
): Record<number, Record<number, Array<Array<number>>>> {
  const result: Record<number, Record<number, Array<Array<number>>>> = {};

  for (const [zoneAreaIdText, points] of Object.entries(zoneBuckets)) {
    const zoneAreaId = Number(zoneAreaIdText);
    const legacyBasis = pack.legacyBasisByKey.get(zoneAreaId);
    const zoneSpace = pack.zoneSpaceByAreaId.get(zoneAreaId);
    if (!legacyBasis && !zoneSpace) {
      throw new Error(`No coordinate mapping for legacy key=${zoneAreaId}`);
    }

    const mapId = legacyBasis ? Number(legacyBasis.mapId) : Number(zoneSpace.mapId);
    const targetUiMapId = legacyBasis
      ? Number(legacyBasis.targetCoordUiMapId)
      : targetCoordUiMapId(pack, zoneSpace);
    const bounds = targetUiMapId === UNKNOWN_COORD_UI_MAP_ID
      ? undefined
      : getProjectionBounds(pack, mapId, targetUiMapId);

    for (const point of points) {
      if (shouldEmitUnknownInstanceBucket(pack, zoneAreaId, mapId, [Number(point[0]), Number(point[1])])) {
        result[mapId] ??= {};
        result[mapId][UNKNOWN_COORD_UI_MAP_ID] ??= [];
        result[mapId][UNKNOWN_COORD_UI_MAP_ID].push([
          UNKNOWN_COORD_POINT[0],
          UNKNOWN_COORD_POINT[1],
        ]);
        continue;
      }
      const [x, y] = convertLegacyPoint(
        pack,
        legacyBasis,
        zoneSpace,
        bounds,
        [Number(point[0]), Number(point[1])],
      );
      result[mapId] ??= {};
      result[mapId][targetUiMapId] ??= [];
      const coordPair: Array<number> = [
        roundTo(x, coordDecimals),
        roundTo(y, coordDecimals),
      ];
      if (legacyBasis?.defaultUiMapHintId !== null && legacyBasis?.defaultUiMapHintId !== undefined) {
        coordPair.push(Number(legacyBasis.defaultUiMapHintId));
      }
      result[mapId][targetUiMapId].push(coordPair);
    }
  }

  return result;
}

export function replaceUnknownInstanceBuckets(
  pack: Pack,
  mapBuckets: Record<number, Record<number, Array<[number, number]>>>,
): Record<number, Record<number, Array<Array<number>>>> {
  const result: Record<number, Record<number, Array<Array<number>>>> = {};

  for (const [mapIdText, coordBuckets] of Object.entries(mapBuckets)) {
    const mapId = Number(mapIdText);
    const anchorRecord = pack.instanceAnchorByMapId.get(mapId);

    if (
      anchorRecord &&
      Object.keys(coordBuckets).length === 1 &&
      isUnknownBucket(coordBuckets[UNKNOWN_COORD_UI_MAP_ID])
    ) {
      for (const bucket of anchorRecord.entrances as any[]) {
        const bucketMapId = Number(bucket.mapId);
        const coordUiMapId = Number(bucket.coordUiMapId);
        result[bucketMapId] ??= {};
        result[bucketMapId][coordUiMapId] ??= [];
        result[bucketMapId][coordUiMapId].push(
          ...bucket.points.map((point: [number, number]) => [Number(point[0]), Number(point[1])]),
        );
      }
      continue;
    }

    result[mapId] = {};
    for (const [coordUiMapIdText, points] of Object.entries(coordBuckets)) {
      result[mapId][Number(coordUiMapIdText)] = points.map((point) => normalizePoint(point));
    }
  }

  return result;
}

export function invertZonePercentToWorld(
  zoneSpace: any,
  zoneX: number,
  zoneY: number,
): [number, number] {
  const dx = Number(zoneSpace.worldXMax) - Number(zoneSpace.worldXMin);
  const dy = Number(zoneSpace.worldYMax) - Number(zoneSpace.worldYMin);
  if (dx === 0 || dy === 0) {
    const sourceLabel = zoneSpace.zoneAreaId !== undefined
      ? `zoneAreaId=${zoneSpace.zoneAreaId}`
      : `mapId=${zoneSpace.mapId}, uiMapId=${zoneSpace.uiMapId}`;
    throw new Error(`Degenerate source bounds for ${sourceLabel}`);
  }

  const worldY = Number(zoneSpace.worldYMax) - (zoneX / 100) * dy;
  const worldX = Number(zoneSpace.worldXMax) - (zoneY / 100) * dx;
  return [worldX, worldY];
}

function convertLegacyPoint(
  pack: Pack,
  legacyBasis: any | undefined,
  zoneSpace: any | undefined,
  targetBounds: any | undefined,
  point: [number, number],
): [number, number] {
  if (legacyBasis) {
    if (Number(legacyBasis.targetCoordUiMapId) === UNKNOWN_COORD_UI_MAP_ID) {
      if (
        legacyBasis.transform === "identity"
        && Number(point[0]) === UNKNOWN_COORD_POINT[0]
        && Number(point[1]) === UNKNOWN_COORD_POINT[1]
      ) {
        return [UNKNOWN_COORD_POINT[0], UNKNOWN_COORD_POINT[1]];
      }
      throw new Error(
        `Legacy key=${Number(legacyBasis.legacyKey)} maps to unresolved instance space; only {-1,-1} sentinel points are supported`,
      );
    }
    if (legacyBasis.transform === "identity") {
      return [Number(point[0]), Number(point[1])];
    }

    const sourceBounds = getProjectionBounds(
      pack,
      Number(legacyBasis.mapId),
      Number(legacyBasis.sourceCoordUiMapId),
    );
    const [worldX, worldY] = invertZonePercentToWorld(
      sourceBounds,
      Number(point[0]),
      Number(point[1]),
    );
    if (!targetBounds) {
      throw new Error("Missing target bounds for legacy reprojection");
    }
    return projectWorldToPercent(targetBounds, worldX, worldY);
  }

  if (!zoneSpace) {
    throw new Error("Missing zone-space record for legacy conversion");
  }
  if (!targetBounds) {
    throw new Error("Missing target bounds for legacy reprojection");
  }
  const [worldX, worldY] = invertZonePercentToWorld(
    zoneSpace,
    Number(point[0]),
    Number(point[1]),
  );
  return projectWorldToPercent(targetBounds, worldX, worldY);
}

function shouldEmitUnknownInstanceBucket(
  pack: Pack,
  zoneAreaId: number,
  mapId: number,
  point: [number, number],
): boolean {
  return (
    Number(point[0]) === UNKNOWN_COORD_POINT[0]
    && Number(point[1]) === UNKNOWN_COORD_POINT[1]
  );
}

export function projectWorldToPercent(
  bounds: any,
  worldX: number,
  worldY: number,
): [number, number] {
  const dx = Number(bounds.worldXMax) - Number(bounds.worldXMin);
  const dy = Number(bounds.worldYMax) - Number(bounds.worldYMin);
  if (dx === 0 || dy === 0) {
    throw new Error(`Degenerate target bounds for mapId=${bounds.mapId}, uiMapId=${bounds.uiMapId}`);
  }

  const x = (Number(bounds.worldYMax) - worldY) / dy * 100;
  const y = (Number(bounds.worldXMax) - worldX) / dx * 100;
  return [x, y];
}

function targetCoordUiMapId(pack: Pack, zoneSpace: any): number {
  const mapId = Number(zoneSpace.mapId);
  const coordUiMapId = pack.mapDefaultByMapId.get(mapId);
  if (coordUiMapId !== undefined) {
    return Number(coordUiMapId);
  }
  if (zoneSpace.parentUiMapId !== null && zoneSpace.parentUiMapId !== undefined) {
    return Number(zoneSpace.parentUiMapId);
  }
  return Number(zoneSpace.zoneUiMapId);
}

function getProjectionBounds(pack: Pack, mapId: number, uiMapId: number): any {
  const bounds = pack.projectionBoundsByKey.get(`${mapId}:${uiMapId}`);
  if (!bounds) {
    throw new Error(`No projection bounds for mapId=${mapId}, uiMapId=${uiMapId}`);
  }
  return bounds;
}

function isUnknownBucket(points?: Array<[number, number]>): boolean {
  if (!points || points.length === 0) {
    return false;
  }
  return points.every((point) => Number(point[0]) === -1 && Number(point[1]) === -1);
}

function roundTo(value: number, decimals: number): number {
  return Number(value.toFixed(decimals));
}

function normalizePoint(point: Array<number>): Array<number> {
  return [Number(point[0]), Number(point[1]), ...point.slice(2)];
}
