export interface Article {
  id: number;
  title: string;
  body: string | null;
  summary: string | null;
  url: string;
  source: string;
  published_at: string;
  created_at: string;
}

export interface ArticleAnalysis {
  article_id: number;
  event_type: string;
  event_confidence: number;
  processed_at: string;
  sentiments: CompanySentiment[];
}

export interface CompanySentiment {
  id: number;
  article_id: number;
  company_name: string;
  ticker: string | null;
  sentiment: "positive" | "negative" | "neutral";
  sentiment_score: number;
  reason: string | null;
}

export interface CompanySentimentFeed {
  article_id: number;
  title: string;
  published_at: string;
  sentiment: "positive" | "negative" | "neutral";
  sentiment_score: number;
  reason: string | null;
  event_type: string | null;
}

export interface CompanySentimentSummary {
  ticker: string;
  total: number;
  positive: number;
  negative: number;
  neutral: number;
  weighted_score: number;
}

export interface EventArticle {
  article_id: number;
  title: string;
  published_at: string;
  source: string;
  event_type: string | null;
  event_confidence: number;
  companies: string[];
}

export interface Stock {
  ticker: string;
  name: string;
  exchange: string | null;
  sector: string | null;
  industry: string | null;
  description: string | null;
  website: string | null;
  metrics: StockMetrics | null;
}

export interface StockMetrics {
  ticker: string;
  market_cap: number | null;
  price: number | null;
  volume: number | null;
  avg_volume: number | null;
  pe_ratio: number | null;
  dividend_yield: number | null;
  week52_high: number | null;
  week52_low: number | null;
  updated_at: string | null;
}

export interface NLSearchResult {
  query: string;
  reasoning: string;
  stocks: Stock[];
}

export interface ScreenerParams {
  sector?: string;
  exchange?: string;
  min_market_cap?: number;
  max_market_cap?: number;
  min_price?: number;
  max_price?: number;
  min_volume?: number;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
  limit?: number;
  offset?: number;
}

export interface ScreenerResult {
  total: number;
  stocks: Stock[];
}

export interface HealthStatus {
  status: string;
  db: string;
  redis: string;
  kafka: string;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export const EVENT_TYPES = [
  "earnings_release",
  "merger_acquisition",
  "ipo",
  "secondary_offering",
  "dividend_announcement",
  "stock_buyback",
  "executive_change",
  "regulatory_action",
  "product_launch",
  "partnership",
  "legal_dispute",
  "bankruptcy",
  "spinoff",
  "credit_rating_change",
  "analyst_upgrade",
  "analyst_downgrade",
  "macro_economic",
  "other",
] as const;

export type EventType = (typeof EVENT_TYPES)[number];
