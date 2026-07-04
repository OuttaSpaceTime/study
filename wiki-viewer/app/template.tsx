// Remounts on every navigation, giving each page a brief fade/rise-in while
// the persistent chrome (sidebar, graph rail) stays put.
export default function Template({ children }: { children: React.ReactNode }) {
  return <div className="page-enter">{children}</div>;
}
