"use client";

import dynamic from "next/dynamic";

const MapExplorer = dynamic(() => import("../components/MapExplorer"), {
  ssr: false,
  loading: () => (
    <main className="loading-shell">
      <div className="loading-mark">UK</div>
      <p>正在载入英国影视取景地图…</p>
    </main>
  )
});

export default function Home() {
  return <MapExplorer />;
}
