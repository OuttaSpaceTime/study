// Instant skeleton while the article server-renders — this is what makes
// click-to-page feel immediate: Next can swap to this boundary synchronously
// and stream the real page in.
export default function ArticleLoading() {
  return (
    <div className="mx-auto w-full max-w-3xl animate-pulse px-8 py-12">
      <div className="h-3 w-44 rounded bg-panel-2" />
      <div className="mt-5 h-9 w-3/4 rounded-md bg-panel-2" />
      <div className="mt-4 flex gap-2">
        <div className="h-5 w-16 rounded-full bg-panel-2" />
        <div className="h-5 w-20 rounded-full bg-panel-2" />
        <div className="h-5 w-24 rounded-full bg-panel-2" />
      </div>
      <div className="mt-10 space-y-3">
        <div className="h-4 w-full rounded bg-panel-2" />
        <div className="h-4 w-11/12 rounded bg-panel-2" />
        <div className="h-4 w-4/5 rounded bg-panel-2" />
      </div>
      <div className="mt-8 h-40 rounded-lg border border-border bg-panel" />
      <div className="mt-8 space-y-3">
        <div className="h-4 w-full rounded bg-panel-2" />
        <div className="h-4 w-10/12 rounded bg-panel-2" />
        <div className="h-4 w-2/3 rounded bg-panel-2" />
      </div>
    </div>
  );
}
