import path from "node:path";

import { convertZoneBuckets, replaceUnknownInstanceBuckets } from "./coordsConverter";
import { loadCoordinatePack } from "./coordsLoader";

async function main(): Promise<void> {
  const packRoot = path.resolve(__dirname, "..", "..");
  const pack = await loadCoordinatePack(packRoot);

  const zoneResult = convertZoneBuckets(pack, {
    12: [[42.1, 65.3]],
  });
  const instanceResult = replaceUnknownInstanceBuckets(pack, {
    36: {
      0: [[-1, -1]],
    },
  });

  console.log("zone conversion:", zoneResult);
  console.log("instance fallback:", instanceResult);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
