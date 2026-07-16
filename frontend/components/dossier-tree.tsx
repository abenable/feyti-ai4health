"use client";

import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Folder, FileText, ChevronDown, ChevronRight } from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { DossierTree } from "@/app/page";

function confidenceColor(confidence: number) {
  if (confidence >= 0.75) return "bg-emerald-500";
  if (confidence >= 0.4) return "bg-amber-500";
  return "bg-red-500";
}

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function DossierTreePanel({
  tree,
  flashName,
}: {
  tree: DossierTree[] | null;
  flashName: string | null;
}) {
  const totalDocs =
    tree?.reduce(
      (sum, moduleGroup) =>
        sum +
        moduleGroup.sections.reduce(
          (secSum, section) => secSum + section.documents.length,
          0,
        ),
      0,
    ) ?? 0;

  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  // Auto-expand new modules while preserving user toggles.
  const mergedExpanded = useMemo(() => {
    if (!tree) return {};
    const next = { ...expanded };
    let changed = false;
    for (const moduleGroup of tree) {
      if (!(moduleGroup.module in next)) {
        next[moduleGroup.module] = true;
        changed = true;
      }
    }
    return changed ? next : expanded;
  }, [tree, expanded]);

  return (
    <Card className="border-slate-200/60 shadow-xl shadow-indigo-100/20 bg-white/80 backdrop-blur-xl overflow-hidden rounded-3xl">
      <CardHeader className="bg-slate-50/50 border-b border-slate-100/60 pb-5 px-6 sm:px-8 pt-6">
        <CardTitle className="text-xl font-serif text-slate-800 flex items-center gap-2">
          <Folder className="w-5 h-5 text-indigo-500" />
          Live Dossier
        </CardTitle>
      </CardHeader>
      <CardContent className="p-6 sm:p-8">
        {totalDocs === 0 ? (
          <div className="text-center py-12 text-slate-500">
            <Folder className="w-10 h-10 mx-auto mb-3 text-slate-300" />
            <p className="font-medium">No documents filed yet.</p>
            <p className="text-sm mt-1">
              Upload a document to see your dossier grow.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {tree!.map((moduleGroup) => (
              <div
                key={moduleGroup.module}
                className="border border-slate-100 rounded-2xl overflow-hidden"
              >
                <button
                  onClick={() =>
                    setExpanded((prev) => ({
                      ...prev,
                      [moduleGroup.module]: !prev[moduleGroup.module],
                    }))
                  }
                  className="w-full flex items-center justify-between gap-3 px-4 py-3 bg-slate-50/50 hover:bg-slate-100/50 transition-colors text-left"
                >
                  <span className="font-semibold text-slate-800">
                    {moduleGroup.module}
                  </span>
                  {mergedExpanded[moduleGroup.module] ? (
                    <ChevronDown className="w-4 h-4 text-slate-400" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-slate-400" />
                  )}
                </button>

                {mergedExpanded[moduleGroup.module] && (
                  <div className="p-3 space-y-2">
                    {moduleGroup.sections.map((section) => (
                      <div key={section.section_path} className="space-y-1">
                        <div className="flex items-center gap-2 text-sm font-medium text-slate-700 px-2 py-1.5 bg-slate-50 rounded-lg">
                          <Folder className="w-4 h-4 text-indigo-400" />
                          <span className="truncate">
                            {section.section_path} {section.title}
                          </span>
                        </div>

                        <div className="pl-6 space-y-1">
                          {section.documents.map((doc) => {
                            const isFlash = flashName === doc.name;
                            return (
                              <motion.div
                                key={`${section.section_path}-${doc.name}`}
                                animate={{
                                  backgroundColor: isFlash
                                    ? "rgba(16, 185, 129, 0.12)"
                                    : "rgba(16, 185, 129, 0)",
                                }}
                                transition={{ duration: 0.6 }}
                                className="flex items-center gap-3 px-2 py-1.5 rounded-lg text-sm text-slate-700"
                              >
                                <FileText className="w-4 h-4 text-slate-400 flex-shrink-0" />
                                <span className="flex-1 truncate">
                                  {doc.name}
                                </span>
                                <span
                                  className={`w-2 h-2 rounded-full ${confidenceColor(
                                    doc.confidence,
                                  )}`}
                                  title={`${Math.round(
                                    doc.confidence * 100,
                                  )}% confidence`}
                                />
                                <span className="text-xs text-slate-400 tabular-nums hidden sm:inline">
                                  {formatDate(doc.uploaded_at)}
                                </span>
                              </motion.div>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
