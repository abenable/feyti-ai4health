"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  Activity,
  Calendar,
  FilePlus2,
  Loader2,
  Pill,
  ShieldAlert,
  User,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { apiFetch, dossierApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ADRReport } from "@/lib/types";

function statusClasses(status: string) {
  switch (status) {
    case "submitted":
      return "bg-emerald-100 text-emerald-800 border-emerald-200";
    case "followup":
      return "bg-amber-100 text-amber-800 border-amber-200";
    case "nullified":
      return "bg-slate-100 text-slate-500 border-slate-200";
    default:
      return "bg-indigo-100 text-indigo-800 border-indigo-200";
  }
}

function formatDate(value?: string | null) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function PVReportsPage() {
  const { dossierId } = useParams<{ dossierId: string }>();
  const [reports, setReports] = useState<ADRReport[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<ADRReport[]>(dossierApi(dossierId, "/pv/reports"))
      .then(setReports)
      .catch(() => setReports([]))
      .finally(() => setLoading(false));
  }, [dossierId]);

  const stats = useMemo(
    () => ({
      total: reports.length,
      serious: reports.filter((report) => report.is_serious).length,
      susar: reports.filter((report) => report.is_susar).length,
      drafts: reports.filter((report) => report.status === "draft").length,
    }),
    [reports]
  );

  return (
    <div className="min-h-screen bg-slate-50/60 text-slate-900">
      <div className="mx-auto w-full max-w-6xl space-y-6 px-6 py-8">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-600 to-violet-500 text-white shadow-lg shadow-indigo-200">
                <Activity className="h-6 w-6" />
              </div>
              <div>
                <h1 className="font-serif text-3xl font-bold leading-none">Pharmacovigilance</h1>
                <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  ADR / ICSR reporting
                </p>
              </div>
            </div>
            <p className="max-w-2xl text-sm text-slate-600">
              Create, validate, code, and export adverse drug reaction reports as E2B(R3) ICSRs.
            </p>
          </div>
          <Link href={`/d/${dossierId}/pv/new`} className={cn(buttonVariants(), "w-fit")}>
            <FilePlus2 className="h-4 w-4" />
            New report
          </Link>
        </header>

        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[
            { label: "Total reports", value: stats.total },
            { label: "Serious cases", value: stats.serious },
            { label: "SUSARs", value: stats.susar },
            { label: "Drafts", value: stats.drafts },
          ].map((stat) => (
            <Card key={stat.label} className="border-slate-200/70 bg-white/90">
              <CardContent className="space-y-1 pt-0">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{stat.label}</p>
                <p className="font-serif text-3xl font-bold text-slate-900">{stat.value}</p>
              </CardContent>
            </Card>
          ))}
        </div>

        {loading ? (
          <Card className="border-slate-200/70 bg-white/90">
            <CardContent className="flex items-center justify-center py-16 text-slate-500">
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              Loading reports…
            </CardContent>
          </Card>
        ) : reports.length === 0 ? (
          <Card className="border-dashed border-slate-300 bg-white/80">
            <CardContent className="flex flex-col items-center justify-center gap-4 py-16 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-3xl bg-slate-100 text-slate-400">
                <Activity className="h-8 w-8" />
              </div>
              <div>
                <h2 className="font-serif text-xl font-semibold text-slate-800">No ADR reports yet</h2>
                <p className="mt-1 text-sm text-slate-500">
                  Create a report manually or extract one from an uploaded CIOMS-style source document.
                </p>
              </div>
              <Link href={`/d/${dossierId}/pv/new`} className={buttonVariants()}>
                <FilePlus2 className="h-4 w-4" />
                Create the first report
              </Link>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {reports.map((report) => (
              <Card
                key={report.report_id}
                className="group border-slate-200/70 bg-white/90 transition-all hover:border-indigo-200 hover:shadow-lg"
              >
                <CardHeader className="border-b border-slate-100 pb-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 space-y-1">
                      <CardTitle className="truncate font-serif text-lg text-slate-800">
                        {report.reaction_meddra_term || report.reaction_description || "Untitled reaction"}
                      </CardTitle>
                      <CardDescription className="flex flex-wrap items-center gap-2 text-xs">
                        <span className="inline-flex items-center gap-1">
                          <Pill className="h-3.5 w-3.5" />
                          {report.product_name || "Unknown product"}
                        </span>
                        <span className="inline-flex items-center gap-1">
                          <User className="h-3.5 w-3.5" />
                          {report.patient?.identifier || report.patient?.initials || "Unknown patient"}
                        </span>
                        <span className="inline-flex items-center gap-1">
                          <Calendar className="h-3.5 w-3.5" />
                          {formatDate(report.first_received_date)}
                        </span>
                      </CardDescription>
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-2">
                      <Badge variant="outline" className={`capitalize ${statusClasses(report.status)}`}>
                        {report.status.replaceAll("_", " ")}
                      </Badge>
                      {report.is_serious && (
                        <Badge className="border-none bg-rose-100 text-rose-800">
                          <ShieldAlert className="h-3 w-3" />
                          Serious
                        </Badge>
                      )}
                      {report.is_susar && (
                        <Badge className="border-none bg-amber-100 text-amber-800">SUSAR</Badge>
                      )}
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4 pt-4">
                  <div className="space-y-2 text-sm text-slate-600">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-xs font-semibold uppercase text-slate-400">Reporter</span>
                      <span className="truncate">{report.reporter_name || report.reporter_organisation || "Unknown"}</span>
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-xs font-semibold uppercase text-slate-400">Severity</span>
                      <span className="capitalize">{report.severity?.replaceAll("_", " ") || "Not assessed"}</span>
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-xs font-semibold uppercase text-slate-400">MedDRA</span>
                      <span className="truncate">
                        {report.reaction_pt_name
                          ? `${report.reaction_pt_name}${report.reaction_pt_code ? ` (${report.reaction_pt_code})` : ""}`
                          : "Uncoded"}
                      </span>
                    </div>
                  </div>
                  <Link
                    href={`/d/${dossierId}/pv/${report.report_id}`}
                    className={cn(buttonVariants({ variant: "outline" }), "w-full")}
                  >
                    Open report
                  </Link>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
