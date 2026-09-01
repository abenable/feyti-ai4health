"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { BookOpen, ExternalLink, FilePlus2, History, Loader2, Search } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { apiFetch, apiJson, dossierApi } from "@/lib/api";
import type { LiteratureResult, LiteratureSavedSearch, LiteratureSearchEntry } from "@/lib/types";

const inputClass = "h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100";

export default function LiteratureSearchPage() {
  const { dossierId } = useParams<{ dossierId: string }>();
  const [query, setQuery] = useState("");
  const [region, setRegion] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [topics, setTopics] = useState("");
  const [results, setResults] = useState<LiteratureResult[]>([]);
  const [searches, setSearches] = useState<LiteratureSearchEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [filingUrl, setFilingUrl] = useState<string | null>(null);

  const loadSearches = useCallback(async () => {
    try {
      setSearches(await apiFetch<LiteratureSearchEntry[]>(dossierApi(dossierId, "/literature/searches")));
    } catch {
      setSearches([]);
    }
  }, [dossierId]);

  useEffect(() => { void loadSearches(); }, [loadSearches]);

  const search = async () => {
    if (!query.trim()) {
      toast.error("Enter a search query.");
      return;
    }
    setLoading(true);
    try {
      const data = (await apiJson(dossierApi(dossierId, "/literature/search"), "POST", {
        query: query.trim(),
        region: region.trim() || null,
        date_from: dateFrom || null,
        date_to: dateTo || null,
        topics: topics.split(",").map((topic) => topic.trim()).filter(Boolean),
      })) as LiteratureResult[];
      setResults(data);
      await loadSearches();
      toast.success(`${data.length} results found.`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Literature search failed.");
    } finally {
      setLoading(false);
    }
  };

  const replay = async (savedQuery: string) => {
    setQuery(savedQuery);
    setLoading(true);
    try {
      const saved = await apiFetch<LiteratureSavedSearch>(
        dossierApi(dossierId, `/literature/searches/${encodeURIComponent(savedQuery)}`)
      );
      setResults(saved.results || []);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load saved search.");
    } finally {
      setLoading(false);
    }
  };

  const fileResult = async (result: LiteratureResult) => {
    setFilingUrl(result.url);
    try {
      await apiJson(dossierApi(dossierId, "/literature/file"), "POST", {
        query: query.trim() || result.title,
        url: result.url,
      });
      toast.success("Reference filed into Module 5.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to file reference.");
    } finally {
      setFilingUrl(null);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50/60 px-6 py-8 text-slate-900">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="space-y-2">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-600 to-violet-500 text-white shadow-lg shadow-indigo-200">
              <BookOpen className="h-6 w-6" />
            </div>
            <div>
              <h1 className="font-serif text-3xl font-bold leading-none">Literature Search</h1>
              <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Global and African sources</p>
            </div>
          </div>
          <p className="max-w-2xl text-sm text-slate-600">
            Search PubMed, Semantic Scholar, PLoS, Springer, BMC, PAMJ, and Uganda MoH. File references into Module 5.
          </p>
        </header>

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-4">
          <Card className="lg:col-span-3">
            <CardHeader className="border-b border-slate-100 pb-4">
              <CardTitle className="font-serif text-lg">Search</CardTitle>
              <CardDescription>Server-side query building, parallel search, and heuristic ranking</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 pt-4">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5 lg:items-end">
                <label className="space-y-1.5 lg:col-span-2">
                  <span className="text-xs font-semibold text-slate-600">Query</span>
                  <input className={inputClass} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="artemisinin resistance Uganda" />
                </label>
                <label className="space-y-1.5">
                  <span className="text-xs font-semibold text-slate-600">Region</span>
                  <input className={inputClass} value={region} onChange={(event) => setRegion(event.target.value)} placeholder="Uganda" />
                </label>
                <label className="space-y-1.5">
                  <span className="text-xs font-semibold text-slate-600">From</span>
                  <input type="date" className={inputClass} value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
                </label>
                <label className="space-y-1.5">
                  <span className="text-xs font-semibold text-slate-600">To</span>
                  <input type="date" className={inputClass} value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
                </label>
                <label className="space-y-1.5 lg:col-span-4">
                  <span className="text-xs font-semibold text-slate-600">Topics</span>
                  <input className={inputClass} value={topics} onChange={(event) => setTopics(event.target.value)} placeholder="safety, efficacy, resistance" />
                </label>
                <Button className="lg:col-span-1" onClick={search} disabled={loading}>
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
                  Search
                </Button>
              </div>

              <div className="space-y-3">
                {results.map((result) => (
                  <div key={result.url} className="rounded-2xl border border-slate-200 bg-white p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0 space-y-1">
                        <a href={result.url} target="_blank" rel="noreferrer" className="font-semibold text-slate-800 hover:text-indigo-700">
                          {result.title}
                        </a>
                        <p className="text-xs text-slate-500">
                          {result.source} · {result.year || "n.d."} · relevance {result.relevance_score}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <a href={result.url} target="_blank" rel="noreferrer" className="text-slate-400 hover:text-indigo-600">
                          <ExternalLink className="h-4 w-4" />
                        </a>
                        <Button size="sm" variant="outline" onClick={() => fileResult(result)} disabled={filingUrl === result.url}>
                          {filingUrl === result.url ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FilePlus2 className="h-3.5 w-3.5" />}
                          File
                        </Button>
                      </div>
                    </div>
                    {result.abstract && <p className="mt-3 line-clamp-3 text-sm text-slate-600">{result.abstract}</p>}
                  </div>
                ))}
                {!loading && results.length === 0 && (
                  <p className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-500">
                    No results yet. Run a search to populate this list.
                  </p>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="border-b border-slate-100 pb-4">
              <CardTitle className="font-serif text-lg">Past searches</CardTitle>
              <CardDescription>Replay saved queries instantly</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 pt-4">
              {searches.map((entry) => (
                <button
                  key={entry.query}
                  type="button"
                  onClick={() => replay(entry.query)}
                  className="w-full rounded-xl border border-slate-200 bg-white p-3 text-left transition-colors hover:border-indigo-300 hover:bg-indigo-50/40"
                >
                  <p className="truncate text-sm font-semibold text-slate-800">{entry.query}</p>
                  <p className="flex items-center gap-1 text-xs text-slate-500">
                    <History className="h-3 w-3" />
                    {entry.count} results · {new Date(entry.date).toLocaleString()}
                  </p>
                </button>
              ))}
              {searches.length === 0 && (
                <p className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-500">
                  No saved searches yet.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
