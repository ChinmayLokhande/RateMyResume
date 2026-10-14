const STYLES: Record<string, string> = {
  queued: "bg-gray-100 text-gray-700",
  not_started: "bg-gray-100 text-gray-600",
  processing: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
};

export function StatusBadge({ status }: { status: string }) {
  const label = status.replace("_", " ");
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${STYLES[status] ?? STYLES.queued}`}
    >
      {label}
    </span>
  );
}