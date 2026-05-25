import { Suspense } from "react";
import { api } from "@/lib/api";
import { fmtRelative, eventLabel, sentimentColor } from "@/lib/utils";
import Card, { CardHeader, CardTitle } from "@/components/shared/Card";
import Badge, { sentimentVariant } from "@/components/shared/Badge";
import Spinner from "@/components/shared/Spinner";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

async function RecentArticles() {
  const data = await api.articles.list({ limit: 6 }).catch(() => null);
  if (!data) return <p className="text-xs text-muted">Failed to load</p>;
  return (
    <ul className="space-y-2">
      {data.items.map((a) => (
        <li key={a.id} className="group rounded-lg border border-line bg-raised p-3 transition-colors hover:border-subtle">
          <p className="line-clamp-2 text-xs font-medium text-primary leading-relaxed">{a.title}</p>
          <div className="mt-1.5 flex items-center gap-2">
            <span className="text-2xs text-muted">{a.source}</span>
            <span className="text-2xs text-muted">·</span>
            <span className="text-2xs text-muted">{fmtRelative(a.published_at)}</span>
          </div>
        </li>
      ))}
    </ul>
  );
}

async function RecentEvents() {
  const data = await api.analysis.events({ limit: 6 }).catch(() => null);
  if (!data) return <p className="text-xs text-muted">Failed to load</p>;
  return (
    <ul className="space-y-2">
      {data.items.map((e) => (
        <li key={e.article_id} className="rounded-lg border border-line bg-raised p-3">
          <div className="flex items-start justify-between gap-2">
            <p className="line-clamp-2 text-xs font-medium text-primary leading-relaxed">{e.title}</p>
            <Badge variant="accent" className="shrink-0">{eventLabel(e.event_type ?? "other")}</Badge>
          </div>
          <p className="mt-1 text-2xs text-muted">{fmtRelative(e.published_at)}</p>
        </li>
      ))}
    </ul>
  );
}

async function RecentSentiments() {
  const data = await api.analysis.events({ limit: 10 }).catch(() => null);
  if (!data) return <p className="text-xs text-muted">Failed to load</p>;

  const tickers = Array.from(new Set(data.items.flatMap((e) => e.companies))).slice(0, 5);
  if (!tickers.length) return <p className="text-xs text-muted">No data yet</p>;

  const summaries = await Promise.all(
    tickers.map((t) => api.analysis.companySentimentSummary(t, 30).catch(() => null))
  );

  return (
    <ul className="space-y-2">
      {summaries.filter(Boolean).map((s) => (
        <li key={s!.ticker} className="flex items-center justify-between rounded-lg border border-line bg-raised px-3 py-2">
          <div>
            <span className="text-xs font-semibold text-primary">{s!.ticker}</span>
            <span className="ml-2 text-2xs text-muted">{s!.total} articles</span>
          </div>
          <span className={`text-xs font-medium ${sentimentColor(s!.weighted_score > 0.1 ? "positive" : s!.weighted_score < -0.1 ? "negative" : "neutral")}`}>
            {s!.weighted_score > 0 ? "+" : ""}{s!.weighted_score.toFixed(2)}
          </span>
        </li>
      ))}
    </ul>
  );
}

export default function DashboardPage() {
  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-primary">Dashboard</h1>
        <p className="mt-0.5 text-sm text-muted">Real-time financial news intelligence</p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Recent Articles */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Recent Articles</CardTitle>
            <Link href="/articles" className="flex items-center gap-1 text-2xs text-accent hover:underline">
              View all <ArrowRight className="h-3 w-3" />
            </Link>
          </CardHeader>
          <Suspense fallback={<Spinner />}>
            <RecentArticles />
          </Suspense>
        </Card>

        {/* Recent Events */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Market Events</CardTitle>
            <Link href="/analysis" className="flex items-center gap-1 text-2xs text-accent hover:underline">
              View all <ArrowRight className="h-3 w-3" />
            </Link>
          </CardHeader>
          <Suspense fallback={<Spinner />}>
            <RecentEvents />
          </Suspense>
        </Card>

        {/* Sentiment Snapshot */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Sentiment Snapshot</CardTitle>
            <Link href="/analysis" className="flex items-center gap-1 text-2xs text-accent hover:underline">
              Details <ArrowRight className="h-3 w-3" />
            </Link>
          </CardHeader>
          <Suspense fallback={<Spinner />}>
            <RecentSentiments />
          </Suspense>
        </Card>
      </div>
    </div>
  );
}
