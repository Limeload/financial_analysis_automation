"use client";

import useSWR from "swr";
import { useState } from "react";
import { api } from "@/lib/api";
import { fmtRelative, eventLabel, sentimentColor } from "@/lib/utils";
import { EVENT_TYPES, type EventType } from "@/lib/types";
import Card from "@/components/shared/Card";
import Badge, { sentimentVariant } from "@/components/shared/Badge";
import Spinner from "@/components/shared/Spinner";
import EmptyState from "@/components/shared/EmptyState";
import { BarChart3, ChevronLeft, ChevronRight } from "lucide-react";

const PAGE_SIZE = 20;

type Tab = "events" | "sentiment";

export default function AnalysisPage() {
  const [tab, setTab] = useState<Tab>("events");
  const [eventType, setEventType] = useState<EventType | "">("");
  const [ticker, setTicker] = useState("");
  const [submittedTicker, setSubmittedTicker] = useState("");
  const [offset, setOffset] = useState(0);

  const { data: eventsData, isLoading: eventsLoading } = useSWR(
    tab === "events" ? ["events", eventType, offset] : null,
    () => api.analysis.events({ event_type: eventType || undefined, limit: PAGE_SIZE, offset })
  );

  const { data: sentimentData, isLoading: sentimentLoading } = useSWR(
    tab === "sentiment" && submittedTicker ? ["sentiment", submittedTicker, offset] : null,
    () => api.analysis.companySentimentFeed(submittedTicker, { limit: PAGE_SIZE, offset })
  );

  const { data: summaryData } = useSWR(
    tab === "sentiment" && submittedTicker ? ["summary", submittedTicker] : null,
    () => api.analysis.companySentimentSummary(submittedTicker)
  );

  const total = tab === "events" ? (eventsData?.total ?? 0) : (sentimentData?.total ?? 0);
  const pages = Math.ceil(total / PAGE_SIZE);
  const page = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-primary">Analysis</h1>
        <p className="mt-0.5 text-sm text-muted">Event classification and company sentiment</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg border border-line bg-raised p-1 w-fit">
        {(["events", "sentiment"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => { setTab(t); setOffset(0); }}
            className={`rounded px-3 py-1.5 text-xs font-medium transition-colors ${
              tab === t ? "bg-surface text-primary shadow-sm" : "text-muted hover:text-secondary"
            }`}
          >
            {t === "events" ? "Market Events" : "Company Sentiment"}
          </button>
        ))}
      </div>

      {/* Filters */}
      {tab === "events" && (
        <select
          value={eventType}
          onChange={(e) => { setEventType(e.target.value as EventType | ""); setOffset(0); }}
          className="h-8 rounded-lg border border-line bg-raised px-2 text-xs text-primary focus:border-accent focus:outline-none"
        >
          <option value="">All event types</option>
          {EVENT_TYPES.map((t) => (
            <option key={t} value={t}>{eventLabel(t)}</option>
          ))}
        </select>
      )}

      {tab === "sentiment" && (
        <form
          onSubmit={(e) => { e.preventDefault(); setSubmittedTicker(ticker.toUpperCase()); setOffset(0); }}
          className="flex gap-2"
        >
          <input
            type="text"
            placeholder="Ticker symbol (e.g. AAPL)"
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            className="h-8 w-48 rounded-lg border border-line bg-raised px-3 text-xs text-primary placeholder:text-muted focus:border-accent focus:outline-none uppercase"
          />
          <button type="submit" className="h-8 rounded-lg bg-accent px-3 text-xs font-medium text-white hover:bg-accent-hover transition-colors">
            Search
          </button>
        </form>
      )}

      {/* Summary card for sentiment */}
      {tab === "sentiment" && summaryData && (
        <div className="grid grid-cols-5 gap-3">
          {[
            { label: "Total", value: summaryData.total },
            { label: "Positive", value: summaryData.positive, className: "text-pos" },
            { label: "Negative", value: summaryData.negative, className: "text-neg" },
            { label: "Neutral",  value: summaryData.neutral },
            { label: "Score",    value: summaryData.weighted_score.toFixed(2),
              className: sentimentColor(summaryData.weighted_score > 0.1 ? "positive" : summaryData.weighted_score < -0.1 ? "negative" : "neutral") },
          ].map(({ label, value, className }) => (
            <Card key={label} className="text-center py-3">
              <p className={`text-lg font-bold ${className ?? "text-primary"}`}>{value}</p>
              <p className="text-2xs text-muted">{label}</p>
            </Card>
          ))}
        </div>
      )}

      {/* Content */}
      {(tab === "events" ? eventsLoading : sentimentLoading) && (
        <div className="flex justify-center py-20"><Spinner /></div>
      )}

      {tab === "events" && !eventsLoading && (
        <div className="space-y-2">
          {eventsData?.items.length === 0 && (
            <EmptyState icon={<BarChart3 className="h-8 w-8" />} title="No events found" />
          )}
          {eventsData?.items.map((e) => (
            <Card key={e.article_id} className="hover:border-subtle transition-colors">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-primary leading-snug">{e.title}</p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {e.companies.map((c) => (
                      <Badge key={c} variant="muted">{c}</Badge>
                    ))}
                  </div>
                  <p className="mt-1.5 text-2xs text-muted">{fmtRelative(e.published_at)} · {e.source}</p>
                </div>
                <div className="flex flex-col items-end gap-1.5">
                  <Badge variant="accent">{eventLabel(e.event_type ?? "other")}</Badge>
                  <span className="text-2xs text-muted">{(e.event_confidence * 100).toFixed(0)}% conf.</span>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {tab === "sentiment" && !sentimentLoading && submittedTicker && (
        <div className="space-y-2">
          {sentimentData?.items.length === 0 && (
            <EmptyState title={`No sentiment data for ${submittedTicker}`} />
          )}
          {sentimentData?.items.map((s) => (
            <Card key={s.article_id} className="hover:border-subtle transition-colors">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-primary leading-snug">{s.title}</p>
                  {s.reason && <p className="mt-1 text-xs text-secondary leading-relaxed">{s.reason}</p>}
                  <p className="mt-1.5 text-2xs text-muted">{fmtRelative(s.published_at)}</p>
                </div>
                <div className="flex flex-col items-end gap-1.5 shrink-0">
                  <Badge variant={sentimentVariant(s.sentiment)}>{s.sentiment}</Badge>
                  <span className={`text-xs font-semibold ${sentimentColor(s.sentiment)}`}>
                    {s.sentiment_score > 0 ? "+" : ""}{s.sentiment_score.toFixed(2)}
                  </span>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {tab === "sentiment" && !submittedTicker && (
        <EmptyState title="Enter a ticker to view sentiment" description="e.g. AAPL, MSFT, NVDA" />
      )}

      {/* Pagination */}
      {pages > 1 && (
        <div className="flex items-center justify-center gap-4 pt-2">
          <button onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))} disabled={offset === 0}
            className="flex items-center gap-1 rounded px-2 py-1 text-xs text-secondary hover:text-primary disabled:opacity-30">
            <ChevronLeft className="h-3.5 w-3.5" /> Prev
          </button>
          <span className="text-xs text-muted">{page} / {pages}</span>
          <button onClick={() => setOffset(offset + PAGE_SIZE)} disabled={offset + PAGE_SIZE >= total}
            className="flex items-center gap-1 rounded px-2 py-1 text-xs text-secondary hover:text-primary disabled:opacity-30">
            Next <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}
