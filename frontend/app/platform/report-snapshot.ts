import type { Frozen, RecordItem } from "./contracts";

export function reportSnapshot(
  selected: Frozen | null | undefined,
  assessment: RecordItem | null,
): Frozen | null {
  if (!assessment) return selected || null;
  const original = assessment.payload.input_snapshot as Frozen | undefined;
  if (
    !original?.sha256 ||
    original.version !==
      (assessment.payload.report as { graph_version?: number })?.graph_version
  )
    throw new Error("The assessment is missing its original graph snapshot.");
  return original;
}
