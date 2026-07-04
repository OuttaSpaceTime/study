export default function HomeLoading() {
  return (
    <div className="mx-auto w-full max-w-3xl animate-pulse px-8 py-12">
      <div className="h-8 w-48 rounded-md bg-panel-2" />
      <div className="mt-3 h-4 w-64 rounded bg-panel-2" />
      <div className="mt-10 space-y-3">
        <div className="h-12 rounded-lg bg-panel-2" />
        <div className="h-12 rounded-lg bg-panel-2" />
        <div className="h-12 rounded-lg bg-panel-2" />
      </div>
    </div>
  );
}
