"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  AlertTriangle,
  CalendarPlus,
  CheckCircle2,
  FileDown,
  Loader2,
  Save,
  ShieldCheck,
  Sparkles,
  Trash2,
} from "lucide-react";
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
import { apiFetch, apiJson, dossierApi, downloadFromApi } from "@/lib/api";
import { pvCausalityLabel, pvSeverityLabel, pvStatusLabel, useLanguage } from "@/lib/i18n";
import {
  PV_CAUSALITY_OPTIONS,
  PV_SEVERITY_OPTIONS,
  evaluatePVMinimumCriteria,
} from "@/lib/pv";
import { cn } from "@/lib/utils";
import type {
  ADRReport,
  MedDRACoding,
  PVExpectedReaction,
  PVMinimumCriteriaCheck,
} from "@/lib/types";

const inputClass =
  "h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none transition-colors focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100";
const selectClass = `${inputClass} appearance-none bg-white`;

function CriterionPill({ label, met }: { label: string; met: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold",
        met
          ? "border-emerald-200 bg-emerald-50 text-emerald-700"
          : "border-rose-200 bg-rose-50 text-700 text-rose-700"
      )}
    >
      {met ? <CheckCircle2 className="h-3.5 w-3.5" /> : <AlertTriangle className="h-3.5 w-3.5" />}
      {label}
    </span>
  );
}

export default function PVReportDetailPage() {
  const { dossierId, reportId } = useParams<{ dossierId: string; reportId: string }>();
  const [form, setForm] = useState<ADRReport | null>(null);
  const [criteria, setCriteria] = useState<PVMinimumCriteriaCheck | null>(null);
  const [expected, setExpected] = useState<PVExpectedReaction[]>([]);
  const [meddraSuggestion, setMeddraSuggestion] = useState<MedDRACoding | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [suggesting, setSuggesting] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [savingExpected, setSavingExpected] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [followDate, setFollowDate] = useState(new Date().toISOString().slice(0, 10));
  const [followNote, setFollowNote] = useState("");
  const [addingFollowUp, setAddingFollowUp] = useState(false);
  const { t } = useLanguage();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [report, expectedReactions, criteriaCheck] = await Promise.all([
        apiFetch<ADRReport>(dossierApi(dossierId, `/pv/reports/${reportId}`)),
        apiFetch<PVExpectedReaction[]>(dossierApi(dossierId, "/pv/expected-reactions")).catch(() => []),
        apiFetch<PVMinimumCriteriaCheck>(
          dossierApi(dossierId, `/pv/reports/${reportId}/minimum-criteria`)
        ),
      ]);
      setForm(report);
      setExpected(expectedReactions);
      setCriteria(criteriaCheck);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t.pvDetail.loadFailedToast);
    } finally {
      setLoading(false);
    }
  }, [dossierId, reportId, t]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (form) setCriteria(evaluatePVMinimumCriteria(form));
  }, [form]);

  const refreshCriteria = useCallback(async () => {
    try {
      setCriteria(
        await apiFetch<PVMinimumCriteriaCheck>(
          dossierApi(dossierId, `/pv/reports/${reportId}/minimum-criteria`)
        )
      );
    } catch {
      if (form) setCriteria(evaluatePVMinimumCriteria(form));
    }
  }, [dossierId, form, reportId]);

  const save = async () => {
    if (!form) return;
    setSaving(true);
    try {
      const saved = (await apiJson(
        dossierApi(dossierId, `/pv/reports/${reportId}`),
        "PUT",
        form
      )) as ADRReport;
      setForm(saved);
      await refreshCriteria();
      toast.success(t.pvDetail.savedToast);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t.pvDetail.saveFailedToast);
    } finally {
      setSaving(false);
    }
  };

  const suggestMeddra = async () => {
    if (!form) return;
    const term = form.reaction_meddra_term || form.reaction_description;
    if (!term?.trim()) {
      toast.error(t.pvDetail.enterTermFirstToast);
      return;
    }

    setSuggesting(true);
    try {
      const suggestion = await apiFetch<MedDRACoding>(
        dossierApi(dossierId, `/pv/meddra/suggest?term=${encodeURIComponent(term)}`),
        { method: "POST" }
      );
      setMeddraSuggestion(suggestion);
      toast.success(t.pvDetail.suggestionReadyToast);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t.pvDetail.suggestionFailedToast);
    } finally {
      setSuggesting(false);
    }
  };

  const confirmMeddra = async () => {
    if (!form) return;
    setConfirming(true);
    try {
      const term = form.reaction_meddra_term || form.reaction_description || "";
      const confirmed = await apiFetch<ADRReport>(
        dossierApi(
          dossierId,
          `/pv/meddra/confirm?report_id=${encodeURIComponent(reportId)}&term=${encodeURIComponent(term)}`
        ),
        { method: "PUT" }
      );
      setForm(confirmed);
      setMeddraSuggestion(null);
      toast.success(t.pvDetail.meddraConfirmedToast);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t.pvDetail.meddraConfirmFailedToast);
    } finally {
      setConfirming(false);
    }
  };

  const addFollowUp = async () => {
    setAddingFollowUp(true);
    try {
      const params = new URLSearchParams({ report_id: reportId, date: followDate });
      if (followNote.trim()) params.set("description", followNote.trim());
      const updated = await apiFetch<ADRReport>(
        dossierApi(dossierId, `/pv/follow-ups?${params.toString()}`),
        { method: "POST" }
      );
      setForm(updated);
      setFollowNote("");
      toast.success(t.pvDetail.followUpAddedToast);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t.pvDetail.followUpFailedToast);
    } finally {
      setAddingFollowUp(false);
    }
  };

  const saveExpected = async () => {
    setSavingExpected(true);
    try {
      await apiJson(dossierApi(dossierId, "/pv/expected-reactions"), "PUT", expected);
      toast.success(t.pvDetail.rsiSavedToast);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t.pvDetail.rsiFailedToast);
    } finally {
      setSavingExpected(false);
    }
  };

  const exportE2B = async () => {
    setExporting(true);
    try {
      await downloadFromApi(
        dossierApi(dossierId, `/pv/reports/${reportId}/e2b`),
        `${reportId}-e2b-r3.xml`
      );
      toast.success(t.pvDetail.e2bDownloadedToast);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t.pvDetail.e2bFailedToast);
    } finally {
      setExporting(false);
    }
  };

  if (loading || !form) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 text-slate-500">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
        {t.pvDetail.loading}
      </div>
    );
  }

  const confirmed = form.meddra?.source === "user_confirmed";

  return (
    <div className="min-h-screen bg-slate-50/60 text-slate-900">
      <div className="mx-auto w-full max-w-6xl space-y-6 px-6 py-8">
        <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-2">
            <Link
              href={`/d/${dossierId}/pv`}
              className="text-xs font-semibold text-indigo-600 hover:text-indigo-700"
            >
              {t.pvDetail.allReports}
            </Link>
            <h1 className="font-serif text-3xl font-bold leading-none">
              {form.reaction_meddra_term || form.reaction_description || t.pvDetail.untitledReport}
            </h1>
            <p className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
              <Badge variant="outline" className="capitalize">
                {pvStatusLabel(t, form.status)}
              </Badge>
              {form.is_serious && (
                <Badge className="border-none bg-rose-100 text-rose-800">{t.pv.serious}</Badge>
              )}
              {form.is_susar && (
                <Badge className="border-none bg-amber-100 text-amber-800">{t.pv.susar}</Badge>
              )}
              <span className="font-mono">{form.report_id}</span>
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={exportE2B} disabled={exporting}>
              {exporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileDown className="h-4 w-4" />}
              {t.pv.e2b}
            </Button>
            <Button onClick={save} disabled={saving}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              {t.pv.save}
            </Button>
          </div>
        </header>

        {criteria && (
          <Card
            className={cn(
              "border",
              criteria.missing.length === 0
                ? "border-emerald-200 bg-emerald-50/70"
                : "border-amber-200 bg-amber-50/70"
            )}
          >
            <CardContent className="flex flex-col gap-3 pt-0 sm:flex-row sm:items-center sm:justify-between">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  {criteria.missing.length === 0 ? (
                    <ShieldCheck className="h-5 w-5 text-emerald-700" />
                  ) : (
                    <AlertTriangle className="h-5 w-5 text-amber-700" />
                  )}
                  <span className="font-serif text-lg font-semibold text-slate-800">
                    {t.pvDetail.minimumCriteria}
                  </span>
                </div>
                <div className="flex flex-wrap gap-2">
                  <CriterionPill label={t.pvDetail.critPatient} met={criteria.patient} />
                  <CriterionPill label={t.pvDetail.critReporter} met={criteria.reporter} />
                  <CriterionPill label={t.pvDetail.critProduct} met={criteria.product} />
                  <CriterionPill label={t.pvDetail.critReaction} met={criteria.reaction} />
                </div>
              </div>
              {criteria.description && (
                <p className="max-w-sm text-sm text-amber-800">{criteria.description}</p>
              )}
            </CardContent>
          </Card>
        )}

        <PVReportForm value={form} onChange={setForm} onSubmit={save} submitLabel={t.pv.save} busy={saving} />

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          <Card className="border-slate-200/70 bg-white/90">
            <CardHeader className="border-b border-slate-100 pb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-100 text-indigo-600">
                  <Sparkles className="h-5 w-5" />
                </div>
                <div>
                  <CardTitle className="font-serif text-lg">{t.pv.meddra}</CardTitle>
                  <CardDescription className="text-xs">{t.pvDetail.meddraHint}</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4 pt-4">
              {form.reaction_pt_name ? (
                <div className="rounded-xl border border-emerald-200 bg-emerald-50/70 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-semibold text-emerald-900">{form.reaction_pt_name}</p>
                      <p className="font-mono text-xs text-emerald-700">
                        {form.reaction_pt_code || t.pvDetail.noCodeAvailable}
                      </p>
                    </div>
                    <Badge className="border-none bg-emerald-100 text-emerald-800">
                      {confirmed ? t.pvDetail.confirmed : t.pvDetail.coded}
                    </Badge>
                  </div>
                </div>
              ) : (
                <p className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-500">
                  {t.pvDetail.notCodedYet}
                </p>
              )}

              <div className="flex flex-wrap gap-2">
                <Button type="button" variant="outline" onClick={suggestMeddra} disabled={suggesting}>
                  {suggesting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                  {t.pvDetail.suggestMeddra}
                </Button>
                {meddraSuggestion && (
                  <Button type="button" onClick={confirmMeddra} disabled={confirming}>
                    {confirming ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                    {t.pvDetail.confirmCoding}
                  </Button>
                )}
              </div>

              {meddraSuggestion && (
                <div className="rounded-xl border border-indigo-200 bg-indigo-50/70 p-4 text-sm">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-semibold text-indigo-900">
                      {meddraSuggestion.pt_name || form.reaction_meddra_term}
                    </span>
                    <span className="font-mono text-xs text-indigo-700">
                      {meddraSuggestion.pt_code || t.pvDetail.noCode}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-indigo-800">{t.pvDetail.unconfirmedSuggestion}</p>
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border-slate-200/70 bg-white/90">
            <CardHeader className="border-b border-slate-100 pb-4">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-100 text-amber-600">
                    <CalendarPlus className="h-5 w-5" />
                  </div>
                  <div>
                    <CardTitle className="font-serif text-lg">{t.pv.followUps}</CardTitle>
                    <CardDescription className="text-xs">{t.pvDetail.followUpsHint}</CardDescription>
                  </div>
                </div>
                <Badge variant="outline">{form.follow_ups?.length ?? 0}</Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4 pt-4">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-[140px_1fr_auto] sm:items-end">
                <label className="flex flex-col gap-1.5">
                  <span className="text-xs font-semibold text-slate-600">{t.pvDetail.date}</span>
                  <input
                    type="date"
                    className={inputClass}
                    value={followDate}
                    onChange={(event) => setFollowDate(event.target.value)}
                  />
                </label>
                <label className="flex flex-col gap-1.5">
                  <span className="text-xs font-semibold text-slate-600">{t.pvDetail.note}</span>
                  <input
                    className={inputClass}
                    value={followNote}
                    onChange={(event) => setFollowNote(event.target.value)}
                    placeholder={t.pvDetail.followUpNotePlaceholder}
                  />
                </label>
                <Button type="button" onClick={addFollowUp} disabled={addingFollowUp}>
                  {addingFollowUp ? <Loader2 className="h-4 w-4 animate-spin" /> : <CalendarPlus className="h-4 w-4" />}
                  {t.pvDetail.add}
                </Button>
              </div>

              <div className="space-y-2">
                {form.follow_ups?.length ? (
                  form.follow_ups.map((followUp, index) => (
                    <div
                      key={`${followUp.date}-${index}`}
                      className="rounded-xl border border-slate-200 bg-slate-50/70 p-3 text-sm"
                    >
                      <p className="font-semibold text-slate-700">
                        {new Date(followUp.date).toLocaleDateString()}
                      </p>
                      {followUp.description && (
                        <p className="mt-1 text-slate-600">{followUp.description}</p>
                      )}
                    </div>
                  ))
                ) : (
                  <p className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-500">
                    {t.pvDetail.noFollowUps}
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        <Card className="border-slate-200/70 bg-white/90">
          <CardHeader className="border-b border-slate-100 pb-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <CardTitle className="font-serif text-lg">{t.pv.expectedReactions}</CardTitle>
                <CardDescription className="text-xs">{t.pvDetail.expectedReactionsHint}</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() =>
                    setExpected((prev) => [
                      ...prev,
                      { pt_code: "", pt_name: "", severity: null, causality: null, notes: "" },
                    ])
                  }
                >
                  {t.pvDetail.addReaction}
                </Button>
                <Button type="button" onClick={saveExpected} disabled={savingExpected}>
                  {savingExpected ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                  {t.pvDetail.saveRsi}
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 pt-4">
            {expected.length === 0 ? (
              <p className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-500">
                {t.pvDetail.noExpectedReactions}
              </p>
            ) : (
              expected.map((reaction, index) => (
                <div
                  key={index}
                  className="grid grid-cols-1 gap-3 rounded-xl border border-slate-200 bg-slate-50/60 p-3 sm:grid-cols-2 lg:grid-cols-[1fr_1fr_1fr_1fr_2fr_auto] lg:items-end"
                >
                  <label className="flex flex-col gap-1.5">
                    <span className="text-xs font-semibold text-slate-600">{t.pvDetail.ptCode}</span>
                    <input
                      className={inputClass}
                      value={reaction.pt_code}
                      onChange={(event) =>
                        setExpected((prev) =>
                          prev.map((item, i) => (i === index ? { ...item, pt_code: event.target.value } : item))
                        )
                      }
                    />
                  </label>
                  <label className="flex flex-col gap-1.5">
                    <span className="text-xs font-semibold text-slate-600">{t.pvDetail.ptName}</span>
                    <input
                      className={inputClass}
                      value={reaction.pt_name}
                      onChange={(event) =>
                        setExpected((prev) =>
                          prev.map((item, i) => (i === index ? { ...item, pt_name: event.target.value } : item))
                        )
                      }
                    />
                  </label>
                  <label className="flex flex-col gap-1.5">
                    <span className="text-xs font-semibold text-slate-600">{t.pvForm.severity}</span>
                    <select
                      className={selectClass}
                      value={reaction.severity ?? ""}
                      onChange={(event) =>
                        setExpected((prev) =>
                          prev.map((item, i) =>
                            i === index
                              ? { ...item, severity: (event.target.value || null) as PVExpectedReaction["severity"] }
                              : item
                          )
                        )
                      }
                    >
                      <option value="">{t.pvDetail.any}</option>
                      {PV_SEVERITY_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {pvSeverityLabel(t, option.value)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="flex flex-col gap-1.5">
                    <span className="text-xs font-semibold text-slate-600">{t.pvForm.causality}</span>
                    <select
                      className={selectClass}
                      value={reaction.causality ?? ""}
                      onChange={(event) =>
                        setExpected((prev) =>
                          prev.map((item, i) =>
                            i === index
                              ? { ...item, causality: (event.target.value || null) as PVExpectedReaction["causality"] }
                              : item
                          )
                        )
                      }
                    >
                      <option value="">{t.pvDetail.any}</option>
                      {PV_CAUSALITY_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {pvCausalityLabel(t, option.value)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="flex flex-col gap-1.5">
                    <span className="text-xs font-semibold text-slate-600">{t.pvDetail.notes}</span>
                    <input
                      className={inputClass}
                      value={reaction.notes ?? ""}
                      onChange={(event) =>
                        setExpected((prev) =>
                          prev.map((item, i) => (i === index ? { ...item, notes: event.target.value } : item))
                        )
                      }
                    />
                  </label>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => setExpected((prev) => prev.filter((_, i) => i !== index))}
                    aria-label={t.pvDetail.removeExpectedReaction}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
