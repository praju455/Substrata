import type { RecordItem } from "./contracts";

export function eventForAlert(record: RecordItem, records: RecordItem[]) {
  return record.kind === "alert"
    ? records.find(
        (item) => item.kind === "event" && item.id === record.payload.event_id,
      )
    : undefined;
}

export function recordTitle(record: RecordItem, records: RecordItem[]): string {
  const value =
    record.payload.title ||
    eventForAlert(record, records)?.payload.title ||
    record.payload.type;
  return typeof value === "string" && value ? value : "Event alert";
}
