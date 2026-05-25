import type {
  Article,
  ArticleAnalysis,
  CompanySentimentFeed,
  CompanySentimentSummary,
  EventArticle,
  Stock,
  NLSearchResult,
  ScreenerParams,
  ScreenerResult,
  HealthStatus,
  Paginated,
} from "./types";

const BASE = "/api";

async function get<T>(path: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
  const url = new URL(BASE + path, typeof window !== "undefined" ? window.location.origin : "http://localhost:3000");
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, String(v));
    });
  }
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export const api = {
  articles: {
    list: (params?: { limit?: number; offset?: number; source?: string }) =>
      get<Paginated<Article>>("/articles", params),
    get: (id: number) => get<Article>(`/articles/${id}`),
  },

  analysis: {
    forArticle: (id: number) => get<ArticleAnalysis>(`/analysis/articles/${id}`),
    companySentimentFeed: (ticker: string, params?: { days?: number; sentiment?: string; limit?: number; offset?: number }) =>
      get<Paginated<CompanySentimentFeed>>(`/analysis/companies/${ticker}/sentiment`, params),
    companySentimentSummary: (ticker: string, days?: number) =>
      get<CompanySentimentSummary>(`/analysis/companies/${ticker}/summary`, days ? { days } : undefined),
    events: (params?: { event_type?: string; limit?: number; offset?: number }) =>
      get<Paginated<EventArticle>>("/analysis/events", params),
  },

  stocks: {
    get: (ticker: string) => get<Stock>(`/stocks/${ticker}`),
    search: (q: string) => get<NLSearchResult>("/stocks/search", { q }),
    screen: (params: ScreenerParams) => get<ScreenerResult>("/stocks/screen", params as Record<string, string | number | boolean | undefined>),
  },

  ops: {
    health: () => get<HealthStatus>("/health"),
  },
};

export function wsUrl(path: string): string {
  if (typeof window === "undefined") return "";
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${window.location.host}/api${path}`;
}
