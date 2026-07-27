"use client";

import { useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import "leaflet/dist/leaflet.css";

const TYPE_NAMES = {
  film: "电影",
  "short film": "短片",
  "silent short film": "无声短片",
  "animated film": "动画电影",
  "television film": "电视电影",
  "two-part television film": "两集电视电影",
  "television series": "电视剧",
  miniseries: "迷你剧",
  "web series": "网络剧",
  "television program": "电视节目",
  "television season": "季度",
  "television episode": "电视剧单集",
  "television series episode": "电视剧单集",
  "television special": "电视特别节目",
  "Doctor Who serial": "Doctor Who 单元剧",
  "Christmas episode": "圣诞特别集"
};

const TYPE_GROUPS = {
  all: { label: "全部", test: () => true },
  film: {
    label: "电影",
    test: (type) =>
      ["film", "short film", "silent short film", "animated film"].includes(type)
  },
  tv: {
    label: "电视",
    test: (type) => !["film", "short film", "silent short film", "animated film"].includes(type)
  }
};

const SOURCE_GROUPS = {
  all: { label: "全部来源" },
  structured: { label: "结构化坐标" },
  community: { label: "民间分类" }
};

const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || "";

function yearOf(feature) {
  const year = Number(feature.properties.release_or_first_broadcast_date?.slice(0, 4));
  return Number.isFinite(year) && year > 1800 ? year : null;
}

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function popupHtml(group) {
  const shown = group.items.slice(0, 8);
  const rows = shown
    .map(({ properties: p }) => {
      const year = p.release_or_first_broadcast_date?.slice(0, 4) || "年份未知";
      const imdb = p.imdb_id
        ? `<a href="https://www.imdb.com/title/${encodeURIComponent(p.imdb_id)}/" target="_blank" rel="noreferrer">IMDb</a>`
        : "";
      const source = p.record_source === "community" ? "民间分类" : "结构化坐标";
      return `<li><strong>${escapeHtml(p.work_name)}</strong><span>${escapeHtml(year)} · ${escapeHtml(TYPE_NAMES[p.work_type] || p.work_type)} · ${source} ${imdb}</span></li>`;
    })
    .join("");
  const more =
    group.items.length > shown.length
      ? `<p class="popup-more">另有 ${group.items.length - shown.length} 条作品记录</p>`
      : "";
  const sourceUrl =
    group.items.find(({ properties: p }) => p.wikidata_location_url || p.wikipedia_url)
      ?.properties;
  const href = sourceUrl?.wikidata_location_url || sourceUrl?.wikipedia_url;
  const precision = group.items.some(({ properties: p }) => p.record_source === "community")
    ? "含城市、地区或制片厂代表点"
    : "Wikidata 结构化坐标";
  const sourceLink = href
    ? `<a class="popup-source" href="${escapeHtml(href)}" target="_blank" rel="noreferrer">查看数据来源 ↗</a>`
    : "";
  return `<div class="map-popup"><p class="popup-kicker">取景地点 · ${precision}</p><h3>${escapeHtml(group.location)}</h3><p class="popup-address">${escapeHtml(group.address || "暂无详细地址")}</p><ul>${rows}</ul>${more}${sourceLink}</div>`;
}

export default function MapExplorer() {
  const mapNode = useRef(null);
  const mapRef = useRef(null);
  const layerRef = useRef(null);
  const rendererRef = useRef(null);
  const markerRefs = useRef(new Map());
  const [features, setFeatures] = useState([]);
  const [query, setQuery] = useState("");
  const [typeGroup, setTypeGroup] = useState("all");
  const [sourceGroup, setSourceGroup] = useState("all");
  const [yearRange, setYearRange] = useState([1900, 2026]);
  const [onlyPrecise, setOnlyPrecise] = useState(false);
  const [loading, setLoading] = useState(true);
  const [dataError, setDataError] = useState("");
  const [mapReady, setMapReady] = useState(false);
  const deferredQuery = useDeferredValue(query);

  useEffect(() => {
    const load = (path) =>
      fetch(`${BASE_PATH}${path}`).then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      });
    Promise.all([
      load("/data/uk_filming_locations.geojson"),
      load("/data/wikipedia_uk_filming_categories_geocoded.geojson")
    ])
      .then(([structured, community]) => {
        const structuredFeatures = (structured.features || []).map((feature) => ({
          ...feature,
          properties: {
            ...feature.properties,
            record_source: "structured",
            coordinate_precision: feature.properties.coordinate_precision || "structured"
          }
        }));
        setFeatures([...structuredFeatures, ...(community.features || [])]);
      })
      .catch(() => setDataError("地图数据加载失败，请稍后刷新。"))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    const needle = deferredQuery.trim().toLocaleLowerCase();
    return features.filter((feature) => {
      const p = feature.properties;
      const year = yearOf(feature);
      const matchesQuery =
        !needle ||
        [p.work_name, p.location_name, p.address, p.imdb_id]
          .filter(Boolean)
          .some((value) => value.toLocaleLowerCase().includes(needle));
      const matchesType = TYPE_GROUPS[typeGroup].test(p.work_type);
      const matchesSource = sourceGroup === "all" || p.record_source === sourceGroup;
      const matchesYear = !year || (year >= yearRange[0] && year <= yearRange[1]);
      const matchesPrecision =
        !onlyPrecise ||
        (p.record_source !== "community" &&
          !["英格兰", "蘇格蘭", "威爾斯", "北爱尔兰", "倫敦", "London", "England", "Scotland", "Wales", "Northern Ireland"].includes(
            p.location_name
          ));
      return matchesQuery && matchesType && matchesSource && matchesYear && matchesPrecision;
    });
  }, [features, deferredQuery, typeGroup, sourceGroup, yearRange, onlyPrecise]);

  const groups = useMemo(() => {
    const grouped = new Map();
    filtered.forEach((feature) => {
      const [lng, lat] = feature.geometry.coordinates;
      const key = `${lat.toFixed(6)},${lng.toFixed(6)}`;
      if (!grouped.has(key)) {
        grouped.set(key, {
          key,
          lat,
          lng,
          location: feature.properties.location_name,
          address: feature.properties.address,
          items: []
        });
      }
      grouped.get(key).items.push(feature);
    });
    return [...grouped.values()].sort((a, b) => b.items.length - a.items.length);
  }, [filtered]);

  useEffect(() => {
    if (!mapNode.current || mapRef.current) return;
    let cancelled = false;
    import("leaflet").then(({ default: L }) => {
      if (cancelled || mapRef.current) return;
      const map = L.map(mapNode.current, {
        zoomControl: false,
        minZoom: 4,
        maxZoom: 18,
        preferCanvas: true
      }).setView([54.4, -3.2], 6);
      L.control.zoom({ position: "bottomright" }).addTo(map);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
      }).addTo(map);
      mapRef.current = map;
      layerRef.current = L.layerGroup().addTo(map);
      rendererRef.current = L.canvas({ padding: 0.35 });
      setMapReady(true);
    });
    return () => {
      cancelled = true;
      mapRef.current?.remove();
      mapRef.current = null;
      layerRef.current = null;
      rendererRef.current = null;
      setMapReady(false);
    };
  }, []);

  useEffect(() => {
    if (!mapRef.current || !layerRef.current || !rendererRef.current) return;
    let active = true;
    import("leaflet").then(({ default: L }) => {
      if (!active || !layerRef.current) return;
      layerRef.current.clearLayers();
      markerRefs.current.clear();
      groups.forEach((group) => {
        const count = group.items.length;
        const communityOnly = group.items.every(
          ({ properties: p }) => p.record_source === "community"
        );
        const radius = Math.max(6, Math.min(18, 5 + Math.log2(count + 1) * 2.1));
        const marker = L.circleMarker([group.lat, group.lng], {
          renderer: rendererRef.current,
          radius,
          color: "#fff8e7",
          weight: 1.5,
          fillColor: communityOnly
            ? "#3f9b84"
            : count > 20
              ? "#ff5b35"
              : count > 5
                ? "#ff8b45"
                : "#ffc857",
          fillOpacity: 0.88
        });
        marker.bindTooltip(
          `<strong>${escapeHtml(group.location)}</strong><br>${count} 条作品记录${communityOnly ? " · 民间分类" : ""}`,
          { direction: "top", offset: [0, -radius], opacity: 0.94 }
        );
        marker.bindPopup(() => popupHtml(group), { maxWidth: 360, minWidth: 260 });
        marker.addTo(layerRef.current);
        markerRefs.current.set(group.key, marker);
      });
    });
    return () => {
      active = false;
    };
  }, [groups, mapReady]);

  function focusGroup(group) {
    mapRef.current?.flyTo([group.lat, group.lng], Math.max(mapRef.current.getZoom(), 12), {
      duration: 0.8
    });
    window.setTimeout(() => markerRefs.current.get(group.key)?.openPopup(), 850);
  }

  function resetFilters() {
    setQuery("");
    setTypeGroup("all");
    setSourceGroup("all");
    setYearRange([1900, 2026]);
    setOnlyPrecise(false);
    mapRef.current?.flyTo([54.4, -3.2], 6);
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">UK</span>
          <div>
            <p>OPEN FILMING DATA</p>
            <h1>英国影视取景地图</h1>
          </div>
        </div>
        <nav>
          <a href="https://github.com/CeHouGIS/UKMovie" target="_blank" rel="noreferrer">
            GitHub ↗
          </a>
          <a href={`${BASE_PATH}/data/wikipedia_uk_filming_categories_geocoded.csv`} download>
            下载新增数据 ↓
          </a>
        </nav>
      </header>

      <section className="workspace">
        <aside className="sidebar">
          <section className="intro">
            <p className="eyebrow">UNITED KINGDOM · 影视地理档案</p>
            <h2>在地图上，找到银幕背后的英国。</h2>
            <p>
              浏览结构化坐标与民间分类记录。绿色点是城市、地区或制片厂代表点，橙色点来自结构化取景坐标。
            </p>
          </section>

          <section className="metrics">
            <div><strong>{filtered.length.toLocaleString()}</strong><span>筛选后记录</span></div>
            <div><strong>{groups.length.toLocaleString()}</strong><span>地图坐标</span></div>
            <div><strong>{new Set(filtered.map((x) => x.properties.work_wikidata_id || x.properties.wikipedia_url || x.properties.work_name)).size.toLocaleString()}</strong><span>不同作品</span></div>
          </section>

          <section className="filters">
            <label className="search-label">
              <span>搜索作品、地点或 IMDb ID</span>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="例如：哈利·波特、Oxford、tt…"
              />
            </label>

            <div className="filter-block">
              <span className="filter-title">作品类型</span>
              <div className="segmented">
                {Object.entries(TYPE_GROUPS).map(([key, group]) => (
                  <button
                    key={key}
                    className={typeGroup === key ? "active" : ""}
                    onClick={() => setTypeGroup(key)}
                  >
                    {group.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="filter-block">
              <span className="filter-title">数据来源</span>
              <div className="segmented source-segmented">
                {Object.entries(SOURCE_GROUPS).map(([key, group]) => (
                  <button
                    key={key}
                    className={sourceGroup === key ? "active" : ""}
                    onClick={() => setSourceGroup(key)}
                  >
                    {group.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="filter-block year-filter">
              <span className="filter-title">上映 / 首播年份</span>
              <div className="year-inputs">
                <input
                  type="number"
                  min="1880"
                  max="2026"
                  value={yearRange[0]}
                  onChange={(event) => setYearRange([Number(event.target.value), yearRange[1]])}
                />
                <span>—</span>
                <input
                  type="number"
                  min="1880"
                  max="2026"
                  value={yearRange[1]}
                  onChange={(event) => setYearRange([yearRange[0], Number(event.target.value)])}
                />
              </div>
            </div>

            <label className="toggle-row">
              <input
                type="checkbox"
                checked={onlyPrecise}
                onChange={(event) => setOnlyPrecise(event.target.checked)}
              />
              <span className="toggle-ui" />
              <span>隐藏国家 / 城市中心点</span>
            </label>

            <button className="reset-button" onClick={resetFilters}>重置筛选</button>
          </section>

          <section className="location-list">
            <div className="list-heading">
              <h3>高频取景坐标</h3>
              <span>TOP {Math.min(groups.length, 40)}</span>
            </div>
            <div className="list-scroll">
              {loading && <p className="status-text">正在读取开放数据…</p>}
              {dataError && <p className="status-text error">{dataError}</p>}
              {!loading && !dataError && groups.length === 0 && (
                <p className="status-text">没有符合条件的地点。</p>
              )}
              {groups.slice(0, 40).map((group, index) => (
                <button className="location-row" key={group.key} onClick={() => focusGroup(group)}>
                  <span className="rank">{String(index + 1).padStart(2, "0")}</span>
                  <span className="location-copy">
                    <strong>{group.location}</strong>
                    <small>{group.items[0].properties.work_name}</small>
                  </span>
                  <span className="count">{group.items.length}</span>
                </button>
              ))}
            </div>
          </section>
        </aside>

        <section className="map-panel">
          <div ref={mapNode} className="map" aria-label="英国影视取景地交互地图" />
          <div className="map-legend">
            <span><i className="dot low" />1–5</span>
            <span><i className="dot mid" />6–20</span>
            <span><i className="dot high" />20+</span>
            <span><i className="dot community" />民间分类</span>
          </div>
          <div className="map-note">
            <strong>数据说明</strong>
            <span>部分坐标是城市或地区中心，并非摄影机精确机位。</span>
          </div>
        </section>
      </section>
    </main>
  );
}
