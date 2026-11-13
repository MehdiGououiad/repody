import { NotFoundScreen } from "@/components/error/not-found-screen";

/** Unknown URLs, outside the app shell. */
export default function NotFound() {
  return (
    <main className="min-h-dvh bg-canvas">
      <NotFoundScreen />
    </main>
  );
}
