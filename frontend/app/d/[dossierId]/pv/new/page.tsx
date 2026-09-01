"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useParams } from "next/navigation";
import { FileText, Loader2, Sparkles, WandSparkles } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PVReportForm } from "@/components/pv-report-form";
import { apiFetch, apiJson, dossierApi } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import { applyPVReportDraft, createEmptyPVReport } from "@/lib/pv";
import type {
  ADRReport,
  GeneratedDoc,
  ProductContext,
  PVExtractionSource,
  PVReportDraft,
} from "@/lib/types";

const inputClass =
  "h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none transition-colors focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100";

export default function NewPVReportPage() {
  const { dossierId } = useParams<{ dossierId: string }>();
  const router = useRouter();
  const [form, setForm] = useState<ADRReport>(() => createEmptyPVReport());
  const [docs, setDocs] = useState<GeneratedDoc[]>([]);
  const [selectedDocKey, setSelectedDocKey] = useState("");
  const [extracting, setExtracting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [extractionSource, setExtractionSource] = useState<PVExtractionSource | null>(null);
  const { t } = useLanguage();

  const selectedDoc = useMemo(
    () => docs.find((doc) => `${doc.section_path}|${doc.stem}` === selectedDocKey),
    [docs, selectedDocKey]
  );

  useEffect(() => {
    apiFetch<GeneratedDoc[]>(dossierApi(dossierId, "/documents"))
      .then(setDocs)
      .catch(() => setDocs([]));
  }, [dossierId]);

  useEffect(() => {
    apiFetch<ProductContext>(dossierApi(dossierId, "/context"))
      .then((context) => {
        setForm((prev) => ({
          ...prev,
          product_name: context.product_name || prev.product_name,
          drug: { ...prev.drug, name: context.product_name || prev.drug?.name || "" },
        }));
      })
      .catch(() => undefined);
  }, [dossierId]);

  const extractFromSource = async () => {
    if (!selectedDoc) {
      toast.error("Select a source document first.");
      return;
    }
    setExtracting(true);
    try {
      const draft = (await apiJson(
        dossierApi(dossierId, "/pv/reports/extract"),
        "POST",
        { section_path: selectedDoc.section_path, stem: selectedDoc.stem }
      )) as PVReportDraft;
      setForm((prev) => applyPVReportDraft(prev, draft));
      setExtractionSource(draft.extraction_source);
      toast.success(
        draft.extraction_source === "llm"
          ? "Extracted with AI — review every field before saving."
          : "Used deterministic label extraction — review every field."
      );
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Source extraction failed.");
    } finally {
      setExtracting(false);
    }
  };

  const save = async () => {
    setSaving(true);
    try {
      const saved = (await apiJson(dossierApi(dossierId, "/pv/reports"), "POST", form)) as ADRReport;
      toast.success("ADR report created.");
      router.push(`/d/${dossierId}/pv/${saved.report_id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create report.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50/60 text-slate-900">
      <div className="mx-auto w-full max-w-6xl space-y-6 px-6 py-8">
        <header className="space-y-2">
          <h1 className="font-serif text-3xl font-bold">{t.pv.newReport}</h1>
          <p className="text-sm text-slate-600">
            Start from a filed source document or enter the case manually. The four ICSR minimum criteria are
            validated as you work.
          </p>
        </header>

        <Card className="border-slate-200/70 bg-white/90">
          <CardHeader className="border-b border-slate-100 pb-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-100 text-indigo-600">
                <FileText className="h-5 w-5" />
              </div>
              <div>
                <CardTitle className="font-serif text-lg">{t.pv.sourceDocument}</CardTitle>
                <CardDescription className="text-xs">
                  Optional — extracts fields from an already-uploaded CIOMS/ADR document
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
              <label className="flex flex-col gap-1.5">
                <span className="text-xs font-semibold text-slate-600">Filed document</span>
                <select
                  className={inputClass}
                  value={selectedDocKey}
                  onChange={(event) => setSelectedDocKey(event.target.value)}
                >
                  <option value="">Select a source document…</option>
                  {docs.map((doc) => (
                    <option key={`${doc.section_path}|${doc.stem}`} value={`${doc.section_path}|${doc.stem}`}>
                      {doc.filename || doc.title || doc.stem} · {doc.module}
                    </option>
                  ))}
                </select>
              </label>
              <Button type="button" onClick={extractFromSource} disabled={extracting || !selectedDoc}>
                {extracting ? <Loader2 className="h-4 w-4 animate-spin" /> : <WandSparkles className="h-4 w-4" />}
                Extract
              </Button>
            </div>

            {extractionSource && (
              <div className="flex flex-wrap items-center gap-2 rounded-xl border border-indigo-100 bg-indigo-50/60 px-3 py-2 text-xs text-indigo-800">
                <Sparkles className="h-3.5 w-3.5" />
                <span>
                  {extractionSource === "llm"
                    ? "AI extraction applied. Review every field before saving."
                    : "Deterministic label extraction applied. Review every field before saving."}
                </span>
                <Badge variant="outline" className="ml-auto border-indigo-200 bg-white text-indigo-700">
                  {extractionSource === "llm" ? "AI" : "Rules"}
                </Badge>
              </div>
            )}

            {docs.length === 0 && (
              <p className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-500">
                No filed documents are available yet. Upload a CIOMS-style PDF or DOCX from the dossier dashboard,
                then return here to extract it.
              </p>
            )}
          </CardContent>
        </Card>

        <PVReportForm value={form} onChange={setForm} onSubmit={save} submitLabel={t.pv.create} busy={saving} />
      </div>
    </div>
  );
}
