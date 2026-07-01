import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-24">
      <h1 className="text-3xl font-semibold">Naval Architecture Suite</h1>
      <p className="text-muted-foreground">
        Modular calculation tools for hull form analysis.
      </p>
      <Link
        href="/hydrostatics"
        className="rounded-md bg-primary px-4 py-2 text-primary-foreground hover:opacity-90"
      >
        Open Hydrostatic Curve Calculator →
      </Link>
    </main>
  );
}
