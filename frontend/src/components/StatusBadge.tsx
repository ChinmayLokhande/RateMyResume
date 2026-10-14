const STYLES: Record<string, string> = {
  queued: "bg-black/[0.05] text-muted",
  not_started: "bg-black/[0.05] text-muted",
  processing: "bg-blue-50 text-blue-700",
  completed: "bg-green-50 text-green-700",
  failed: "bg-red-50 text-red-700",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${STYLES[status] ?? STYLES.queued}`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full bg-current ${status === "processing" ? "animate-pulse" : ""}`}
      />
      {status.replace("_", " ")}
    </span>
  );
}