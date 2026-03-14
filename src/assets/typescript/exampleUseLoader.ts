import path from "node:path";

import { loadCoordinatePack } from "./coordsLoader";

async function main(): Promise<void> {
  const packRoot = path.resolve(__dirname, "..", "..");
  const pack = await loadCoordinatePack(packRoot);

  console.log("flavor:", pack.manifest.flavor);
  console.log("zone 12 source:", pack.zoneSpaceByAreaId.get(12));
  console.log("map 0 default coordUiMapId:", pack.mapDefaultByMapId.get(0));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
