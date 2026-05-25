"use client";

import useSWR from "swr";
import { api } from "@/lib/api";
import { fmtRelative } from "@/lib/utils";
import Card from "@/components/shared/Card";
import Spinner from "@/components/shared/Spinner";
import EmptyState from "@/components/shared/EmptyState";
import { Newspaper, ChevronLeft, ChevronRight } from "lucide-react";
import { useState } from "react";
import type { Paginated, Article } from "@/lib/types";

const PAGE_SIZE = 20;

export default function ArticlesPage() {
  const [offset, setOffset] = useState(0);
  const [source, setSource] = useState("");

  const { data, isLoading } = useSWR<Paginated<Article>>(
    ["articles", offset, source],
    () => api.articles.list({ limit: PAGE_SIZE, offset, source: source || undefined })
  );

  const total = data?.total ?? 0;
  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const pages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-primary">Articles</h1>
          <p className="mt-0.5 text-sm text-muted">{total.toLocaleString()} total</p>
        </div>
        <input
          type="text"
          placeholder="Filter by source…"
          value={source}
          onChange={(e) => { setSource(e.target.value); setOffset(0); }}
          className="h-8 rounded-lg border border-line bg-raised px-3 text-xs text-primary placeholder:text-muted focus:border-accent focus:outline-none"
        />
      </div>

      {isLoading && (
        <div className="flex justify-center py-20"><Spinner /></div>
      )}

      {!isLoading && !data?.items.length && (
        <EmptyState icon={<Newspaper className="h-8 w-8" />} title="No articles found" />
      )}

      {data?.items && (
        <div className="space-y-2">
          {data.items.map((a) => (
            <Card key={a.id} className="hover:border-subtle transition-colors">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-primary leading-snug">{a.title}</p>
                  {a.summary && (
                    <p className="mt-1 line-clamp-2 text-xs text-secondary leading-relaxed">{a.summary}</p>
                  )}
                  <div className="mt-2 flex items-center gap-3">
                    <span className="text-2xs font-medium text-accent">{a.source}</span>
                    <span className="text-2xs text-muted">{fmtRelative(a.published_at)}</span>
                  </div>
                </div>
                {a.url && (
                  <a
                    href={a.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="shrink-0 rounded border border-line px-2 py-1 text-2xs text-muted hover:border-accent hover:text-accent transition-colors"
                  >
                    Source
                  </a>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      {pages > 1 && (
        <div className="flex items-center justify-center gap-4 pt-2">
          <button
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            disabled={offset === 0}
            className="flex items-center gap-1 rounded px-2 py-1 text-xs text-secondary hover:text-primary disabled:opacity-30"
          >
            <ChevronLeft className="h-3.5 w-3.5" /> Prev
          </button>
          <span className="text-xs text-muted">{page} / {pages}</span>
          <button
            onClick={() => setOffset(offset + PAGE_SIZE)}
            disabled={offset + PAGE_SIZE >= total}
            className="flex items-center gap-1 rounded px-2 py-1 text-xs text-secondary hover:text-primary disabled:opacity-30"
          >
            Next <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}
