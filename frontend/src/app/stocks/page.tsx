"use client";

import { useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { fmtMarketCap, fmtPrice, fmtNumber } from "@/lib/utils";
import Card, { CardHeader, CardTitle } from "@/components/shared/Card";
import Badge from "@/components/shared/Badge";
import Spinner from "@/components/shared/Spinner";
import EmptyState from "@/components/shared/EmptyState";
import { Search, TrendingUp, SlidersHorizontal } from "lucide-react";
import type { ScreenerParams } from "@/lib/types";

const SECTORS = [
  "Technology", "Healthcare", "Financials", "Consumer Discretionary",
  "Industrials", "Communication Services", "Consumer Staples",
  "Energy", "Utilities", "Real Estate", "Materials",
];

export default function StocksPage() {
  const [tab, setTab] = useState<"search" | "screen">("search");

  // NL Search
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const { data: searchData, isLoading: searchLoading } = useSWR(
    submittedQuery ? ["nl-search", submittedQuery] : null,
    () => api.stocks.search(submittedQuery)
  );

  // Screener
  const [screenerParams, setScreenerParams] = useState<ScreenerParams>({
    sort_by: "market_cap",
    sort_dir: "desc",
    limit: 20,
  });
  const [runScreener, setRunScreener] = useState(false);
  const { data: screenerData, isLoading: screenerLoading } = useSWR(
    runScreener ? ["screener", JSON.stringify(screenerParams)] : null,
    () => api.stocks.screen(screenerParams)
  );

  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-primary">Stocks</h1>
        <p className="mt-0.5 text-sm text-muted">Natural language search and metric screener</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg border border-line bg-raised p-1 w-fit">
        {(["search", "screen"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex items-center gap-1.5 rounded px-3 py-1.5 text-xs font-medium transition-colors ${
              tab === t ? "bg-surface text-primary shadow-sm" : "text-muted hover:text-secondary"
            }`}
          >
            {t === "search" ? <><Search className="h-3 w-3" /> NL Search</> : <><SlidersHorizontal className="h-3 w-3" /> Screener</>}
          </button>
        ))}
      </div>

      {/* NL Search */}
      {tab === "search" && (
        <div className="space-y-4">
          <form
            onSubmit={(e) => { e.preventDefault(); setSubmittedQuery(query); }}
            className="flex gap-2"
          >
            <div className="relative flex-1 max-w-xl">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted" />
              <input
                type="text"
                placeholder='e.g. "companies that build AI chips" or "dividend-paying utilities"'
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="h-9 w-full rounded-lg border border-line bg-raised pl-9 pr-3 text-xs text-primary placeholder:text-muted focus:border-accent focus:outline-none"
              />
            </div>
            <button type="submit" className="h-9 rounded-lg bg-accent px-4 text-xs font-medium text-white hover:bg-accent-hover transition-colors">
              Search
            </button>
          </form>

          {searchLoading && <div className="flex justify-center py-20"><Spinner /></div>}

          {searchData && (
            <div className="space-y-4">
              {searchData.reasoning && (
                <Card className="border-accent/20 bg-accent-soft/10">
                  <p className="text-xs text-secondary leading-relaxed">{searchData.reasoning}</p>
                </Card>
              )}
              <StockTable stocks={searchData.stocks} />
            </div>
          )}

          {!submittedQuery && (
            <EmptyState
              icon={<Search className="h-8 w-8" />}
              title="Search NYSE stocks with natural language"
              description='Try "data center companies" or "EV manufacturers with high volume"'
            />
          )}
        </div>
      )}

      {/* Screener */}
      {tab === "screen" && (
        <div className="space-y-4">
          <Card>
            <CardHeader><CardTitle>Filters</CardTitle></CardHeader>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
              <div className="space-y-1">
                <label className="text-2xs text-muted">Sector</label>
                <select
                  value={screenerParams.sector ?? ""}
                  onChange={(e) => setScreenerParams((p) => ({ ...p, sector: e.target.value || undefined }))}
                  className="h-7 w-full rounded border border-line bg-raised px-2 text-xs text-primary focus:border-accent focus:outline-none"
                >
                  <option value="">Any</option>
                  {SECTORS.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>

              {[
                { label: "Min Market Cap ($B)", key: "min_market_cap", scale: 1e9 },
                { label: "Max Market Cap ($B)", key: "max_market_cap", scale: 1e9 },
                { label: "Min Price ($)",        key: "min_price",      scale: 1 },
                { label: "Max Price ($)",        key: "max_price",      scale: 1 },
                { label: "Min Volume",           key: "min_volume",     scale: 1 },
              ].map(({ label, key, scale }) => (
                <div key={key} className="space-y-1">
                  <label className="text-2xs text-muted">{label}</label>
                  <input
                    type="number"
                    min={0}
                    step={scale >= 1e9 ? 0.1 : 1}
                    value={screenerParams[key as keyof ScreenerParams] ? Number(screenerParams[key as keyof ScreenerParams]) / scale : ""}
                    onChange={(e) => {
                      const v = e.target.value ? Number(e.target.value) * scale : undefined;
                      setScreenerParams((p) => ({ ...p, [key]: v }));
                    }}
                    className="h-7 w-full rounded border border-line bg-raised px-2 text-xs text-primary focus:border-accent focus:outline-none"
                  />
                </div>
              ))}

              <div className="space-y-1">
                <label className="text-2xs text-muted">Sort by</label>
                <select
                  value={screenerParams.sort_by ?? "market_cap"}
                  onChange={(e) => setScreenerParams((p) => ({ ...p, sort_by: e.target.value }))}
                  className="h-7 w-full rounded border border-line bg-raised px-2 text-xs text-primary focus:border-accent focus:outline-none"
                >
                  {["market_cap", "price", "volume", "pe_ratio", "dividend_yield", "ticker", "name"].map((s) => (
                    <option key={s} value={s}>{s.replace(/_/g, " ")}</option>
                  ))}
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-2xs text-muted">Order</label>
                <select
                  value={screenerParams.sort_dir ?? "desc"}
                  onChange={(e) => setScreenerParams((p) => ({ ...p, sort_dir: e.target.value as "asc" | "desc" }))}
                  className="h-7 w-full rounded border border-line bg-raised px-2 text-xs text-primary focus:border-accent focus:outline-none"
                >
                  <option value="desc">Descending</option>
                  <option value="asc">Ascending</option>
                </select>
              </div>
            </div>

            <div className="mt-4 flex justify-end">
              <button
                onClick={() => { setRunScreener(true); }}
                className="h-8 rounded-lg bg-accent px-4 text-xs font-medium text-white hover:bg-accent-hover transition-colors"
              >
                Run Screener
              </button>
            </div>
          </Card>

          {screenerLoading && <div className="flex justify-center py-10"><Spinner /></div>}

          {screenerData && (
            <div>
              <p className="mb-2 text-xs text-muted">{screenerData.total} results</p>
              <StockTable stocks={screenerData.stocks} />
            </div>
          )}

          {!runScreener && (
            <EmptyState icon={<TrendingUp className="h-8 w-8" />} title="Configure filters and run screener" />
          )}
        </div>
      )}
    </div>
  );
}

function StockTable({ stocks }: { stocks: import("@/lib/types").Stock[] }) {
  if (!stocks.length) return <EmptyState title="No stocks found" />;

  return (
    <div className="overflow-x-auto rounded-xl border border-line">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-line bg-raised">
            {["Ticker", "Name", "Sector", "Market Cap", "Price", "Volume", "P/E"].map((h) => (
              <th key={h} className="px-3 py-2.5 text-left font-medium text-muted">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {stocks.map((s) => (
            <tr key={s.ticker} className="hover:bg-raised/50 transition-colors">
              <td className="px-3 py-2.5 font-semibold text-accent">{s.ticker}</td>
              <td className="px-3 py-2.5 max-w-[180px] truncate text-primary">{s.name}</td>
              <td className="px-3 py-2.5">
                {s.sector ? <Badge variant="muted">{s.sector}</Badge> : <span className="text-muted">—</span>}
              </td>
              <td className="px-3 py-2.5 font-mono text-secondary">{fmtMarketCap(s.metrics?.market_cap)}</td>
              <td className="px-3 py-2.5 font-mono text-secondary">{fmtPrice(s.metrics?.price)}</td>
              <td className="px-3 py-2.5 font-mono text-secondary">{fmtNumber(s.metrics?.volume, { notation: "compact" })}</td>
              <td className="px-3 py-2.5 font-mono text-secondary">{s.metrics?.pe_ratio ? s.metrics.pe_ratio.toFixed(1) : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
