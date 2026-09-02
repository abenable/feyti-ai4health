"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, FolderOpen, Loader2, Plus, X } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiFetch, apiJson } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type { DossierSummary } from "@/lib/types";

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  } catch {
    return iso;
  }
}

export default function DossierPickerPage() {
  const router = useRouter();
  const { t } = useLanguage();
  const [dossiers, setDossiers] = useState<DossierSummary[] | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);

  const fetchDossiers = useCallback(async () => {
    try {
      setDossiers(await apiFetch<DossierSummary[]>("/api/v1/dossiers"));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t.home.loadFailed);
      setDossiers([]);
    }
  }, [t.home.loadFailed]);

  useEffect(() => {
    // fetchDossiers only calls setState after its internal `await` resolves,
    // same pattern as fetchPlan on the structure page — not a synchronous
    // setState. eslint's heuristic here reads as a false positive.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchDossiers();
  }, [fetchDossiers]);

  const createDossier = async () => {
    if (!name.trim()) return;
    setCreating(true);
    try {
      const dossier = await apiJson("/api/v1/dossiers", "POST", { name: name.trim() }) as DossierSummary;
      toast.success(t.home.created.replace("{name}", dossier.name));
      router.push(`/d/${dossier.id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t.home.createFailed);
      setCreating(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50/50 text-slate-900 flex flex-col relative overflow-hidden">
      <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-full bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:40px_40px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)]" />
        <div className="absolute -top-[300px] left-[50%] -translate-x-1/2 w-[800px] h-[600px] bg-indigo-500/10 rounded-full blur-[100px]" />
      </div>

      <header className="w-full mx-auto relative z-10 flex flex-col items-center justify-center pt-16 pb-12 px-6 text-center">
        <h1 className="font-serif text-5xl sm:text-6xl font-bold text-slate-900 tracking-tight leading-none">
          Feyti
        </h1>
        <p className="text-sm sm:text-base text-slate-500 font-medium tracking-[0.2em] uppercase mt-3">
          {t.home.tagline}
        </p>
        <p className="text-slate-600 text-base sm:text-lg leading-relaxed max-w-2xl mt-6">
          {t.home.description}
        </p>

        <div className="flex flex-wrap items-center justify-center gap-3 mt-8">
          <Button size="lg" onClick={() => setCreateOpen(true)}>
            <Plus className="w-4 h-4" />
            {t.home.newDossier}
          </Button>
          {dossiers && dossiers.length > 0 && (
            <Button size="lg" variant="outline" onClick={() => router.push(`/d/${dossiers[0].id}`)}>
              {t.home.continueWith.replace("{name}", dossiers[0].name)}
              <ArrowRight className="w-4 h-4" />
            </Button>
          )}
        </div>
      </header>

      <main className="flex-1 w-full max-w-5xl mx-auto px-6 pb-16 relative z-10">
        <h2 className="font-serif text-xl text-slate-800 mb-6">{t.home.yourDossiers}</h2>

        {dossiers === null ? (
          <div className="flex items-center justify-center h-40 text-slate-500">
            <Loader2 className="w-5 h-5 animate-spin mr-2" />
            {t.home.loading}
          </div>
        ) : dossiers.length === 0 ? (
          <Card className="border-slate-200/60 shadow-xl shadow-indigo-100/20 bg-white/80 backdrop-blur-xl rounded-3xl overflow-hidden">
            <CardContent className="flex flex-col items-center text-center py-16 px-8">
              <div className="w-16 h-16 rounded-3xl bg-indigo-100 flex items-center justify-center text-indigo-600 mb-4">
                <FolderOpen className="w-8 h-8" />
              </div>
              <h3 className="font-serif text-xl text-slate-800 mb-1">{t.home.noDossiersTitle}</h3>
              <p className="text-slate-500 text-sm max-w-sm mb-6">{t.home.noDossiersBody}</p>
              <Button onClick={() => setCreateOpen(true)}>
                <Plus className="w-4 h-4" />
                {t.home.createFirst}
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {dossiers.map((d) => (
              <button
                key={d.id}
                onClick={() => router.push(`/d/${d.id}`)}
                className="text-left"
              >
                <Card className="h-full border-slate-200/60 shadow-lg hover:shadow-xl hover:border-indigo-300 bg-white/80 backdrop-blur-xl rounded-2xl overflow-hidden transition-all">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base font-serif text-slate-800 line-clamp-1">{d.name}</CardTitle>
                    {d.product_name && (
                      <p className="text-xs text-slate-500 line-clamp-1">{d.product_name}</p>
                    )}
                  </CardHeader>
                  <CardContent className="pt-0 flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      <Badge variant="outline" className="text-[10px] px-2 py-0 rounded-full">
                        {d.filed} {t.home.filed}
                      </Badge>
                      <Badge variant="outline" className="text-[10px] px-2 py-0 rounded-full bg-emerald-50 border-emerald-200 text-emerald-700">
                        {d.approved} {t.home.approved}
                      </Badge>
                    </div>
                    <span className="text-[11px] text-slate-400">{formatDate(d.created_at)}</span>
                  </CardContent>
                </Card>
              </button>
            ))}
          </div>
        )}
      </main>

      <AnimatePresence>
        {createOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm"
            onClick={() => !creating && setCreateOpen(false)}
          >
            <motion.div
              role="dialog"
              aria-modal="true"
              aria-label={t.home.createDialogAria}
              initial={{ opacity: 0, scale: 0.96, y: 8 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: 8 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-md bg-white rounded-3xl shadow-2xl border border-slate-200 overflow-hidden"
            >
              <div className="flex items-center justify-between gap-4 px-6 py-4 border-b border-slate-100 bg-slate-50/50">
                <h2 className="font-serif text-lg text-slate-800">{t.home.createDialogTitle}</h2>
                <button
                  type="button"
                  onClick={() => setCreateOpen(false)}
                  disabled={creating}
                  className="text-slate-400 hover:text-slate-700 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="p-6 space-y-4">
                <label className="flex flex-col gap-1.5">
                  <span className="text-xs font-medium text-slate-600">{t.home.dossierName}</span>
                  <input
                    autoFocus
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") createDossier();
                    }}
                    placeholder={t.home.namePlaceholder}
                    className="h-10 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
                  />
                </label>
                <Button className="w-full" onClick={createDossier} disabled={creating || !name.trim()}>
                  {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                  {t.home.createDossier}
                </Button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <footer className="w-full max-w-5xl mx-auto py-6 mt-auto flex justify-center items-center border-t border-slate-200/60 relative z-10">
        <p className="text-sm text-slate-500 font-medium tracking-wide">
          © {new Date().getFullYear()}{" "}
          <span className="text-slate-900 font-semibold font-serif italic">Feyti AIcyclinder</span>
        </p>
      </footer>
    </div>
  );
}
