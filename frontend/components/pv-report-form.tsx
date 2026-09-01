"use client";

import { Loader2, Save } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  PV_ACTION_OPTIONS,
  PV_CAUSALITY_OPTIONS,
  PV_OUTCOME_OPTIONS,
  PV_SEVERITY_OPTIONS,
  PV_SERIOUSNESS_OPTIONS,
} from "@/lib/pv";
import type {
  ADRReport,
  PVActionTaken,
  PVCausality,
  PVDrug,
  PVOutcome,
  PVPatient,
  PVReportStatus,
  PVSeverity,
} from "@/lib/types";

const inputClass =
  "h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none transition-colors focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100";
const selectClass = `${inputClass} appearance-none bg-white`;
const textareaClass =
  "min-h-28 w-full rounded-xl border border-slate-200 bg-white p-3 text-sm text-slate-800 outline-none transition-colors focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100";

type PVReportFormProps = {
  value: ADRReport;
  onChange: (value: ADRReport) => void;
  onSubmit: () => void | Promise<void>;
  submitLabel?: string;
  busy?: boolean;
};

function Field({
  label,
  children,
  className = "",
}: {
  label: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <label className={`flex flex-col gap-1.5 ${className}`}>
      <span className="text-xs font-semibold text-slate-600">{label}</span>
      {children}
    </label>
  );
}

function SectionCard({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <Card className="border-slate-200/70 bg-white/90 shadow-sm">
      <CardHeader className="border-b border-slate-100 pb-4">
        <CardTitle className="font-serif text-lg text-slate-800">{title}</CardTitle>
        <CardDescription className="text-xs">{description}</CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-4 pt-4 sm:grid-cols-2 lg:grid-cols-3">
        {children}
      </CardContent>
    </Card>
  );
}

export function PVReportForm({
  value,
  onChange,
  onSubmit,
  submitLabel = "Save report",
  busy = false,
}: PVReportFormProps) {
  const set = <K extends keyof ADRReport>(key: K, next: ADRReport[K]) =>
    onChange({ ...value, [key]: next });

  const setPatient = (patch: Partial<PVPatient>) =>
    onChange({ ...value, patient: { ...value.patient, ...patch } });

  const setDrug = (patch: Partial<PVDrug>) =>
    onChange({ ...value, drug: { ...value.drug, ...patch } });

  const toggleSeriousness = (criterion: string, checked: boolean) => {
    const current = new Set(value.seriousness_criteria || []);
    if (checked) current.add(criterion);
    else current.delete(criterion);
    set("seriousness_criteria", Array.from(current));
  };

  return (
    <form
      className="space-y-5"
      onSubmit={(event) => {
        event.preventDefault();
        void onSubmit();
      }}
    >
      <SectionCard title="Case" description="Core identifiers and submission status">
        <Field label="Product / suspect drug">
          <input
            className={inputClass}
            value={value.product_name}
            onChange={(event) => set("product_name", event.target.value)}
            required
          />
        </Field>
        <Field label="Worldwide unique ID">
          <input
            className={inputClass}
            value={value.worldwide_unique_id ?? ""}
            onChange={(event) => set("worldwide_unique_id", event.target.value)}
            placeholder="Auto-generated when left blank"
          />
        </Field>
        <Field label="First received date">
          <input
            type="date"
            className={inputClass}
            value={value.first_received_date ?? ""}
            onChange={(event) => set("first_received_date", event.target.value || null)}
          />
        </Field>
        <Field label="Case type">
          <select
            className={selectClass}
            value={value.case_report_type}
            onChange={(event) =>
              set("case_report_type", event.target.value as ADRReport["case_report_type"])
            }
          >
            <option value="initial">Initial</option>
            <option value="followup">Follow-up</option>
            <option value="nullification">Nullification</option>
          </select>
        </Field>
        <Field label="Status">
          <select
            className={selectClass}
            value={value.status}
            onChange={(event) => set("status", event.target.value as PVReportStatus)}
          >
            <option value="draft">Draft</option>
            <option value="submitted">Submitted</option>
            <option value="followup">Follow-up</option>
            <option value="nullified">Nullified</option>
          </select>
        </Field>
        <Field label="Organisation">
          <input
            className={inputClass}
            value={value.organization ?? ""}
            onChange={(event) => set("organization", event.target.value)}
          />
        </Field>
      </SectionCard>

      <SectionCard title="Patient" description="One field is enough to identify the case">
        <Field label="Identifier">
          <input
            className={inputClass}
            value={value.patient?.identifier ?? ""}
            onChange={(event) => setPatient({ identifier: event.target.value })}
          />
        </Field>
        <Field label="Initials">
          <input
            className={inputClass}
            value={value.patient?.initials ?? ""}
            onChange={(event) => setPatient({ initials: event.target.value })}
          />
        </Field>
        <Field label="Age">
          <input
            type="number"
            min={0}
            className={inputClass}
            value={value.patient?.age ?? ""}
            onChange={(event) =>
              setPatient({ age: event.target.value ? Number(event.target.value) : null })
            }
          />
        </Field>
        <Field label="Sex">
          <select
            className={selectClass}
            value={value.patient?.sex ?? ""}
            onChange={(event) => setPatient({ sex: event.target.value || null })}
          >
            <option value="">Unknown</option>
            <option value="male">Male</option>
            <option value="female">Female</option>
          </select>
        </Field>
        <Field label="Age group">
          <input
            className={inputClass}
            value={value.patient?.age_group ?? ""}
            onChange={(event) => setPatient({ age_group: event.target.value })}
          />
        </Field>
        <Field label="Date of birth">
          <input
            type="date"
            className={inputClass}
            value={value.patient?.dob ?? ""}
            onChange={(event) => setPatient({ dob: event.target.value || null })}
          />
        </Field>
      </SectionCard>

      <SectionCard title="Reporter" description="Contact details for the primary reporter">
        <Field label="Name">
          <input
            className={inputClass}
            value={value.reporter_name ?? ""}
            onChange={(event) => set("reporter_name", event.target.value)}
          />
        </Field>
        <Field label="Organisation">
          <input
            className={inputClass}
            value={value.reporter_organisation ?? ""}
            onChange={(event) => set("reporter_organisation", event.target.value)}
          />
        </Field>
        <Field label="Email">
          <input
            type="email"
            className={inputClass}
            value={value.reporter_email ?? ""}
            onChange={(event) => set("reporter_email", event.target.value)}
          />
        </Field>
        <Field label="Phone">
          <input
            className={inputClass}
            value={value.reporter_phone ?? ""}
            onChange={(event) => set("reporter_phone", event.target.value)}
          />
        </Field>
        <Field label="Country">
          <input
            className={inputClass}
            value={value.reporter_country ?? ""}
            onChange={(event) => set("reporter_country", event.target.value)}
          />
        </Field>
        <Field label="Qualification">
          <input
            className={inputClass}
            value={value.reporter_qualification ?? ""}
            onChange={(event) => set("reporter_qualification", event.target.value)}
          />
        </Field>
      </SectionCard>

      <SectionCard title="Drug" description="Suspect medication and exposure details">
        <Field label="Drug name">
          <input
            className={inputClass}
            value={value.drug?.name ?? ""}
            onChange={(event) => setDrug({ name: event.target.value })}
          />
        </Field>
        <Field label="Dose">
          <input
            className={inputClass}
            value={value.drug?.dose_text ?? ""}
            onChange={(event) => setDrug({ dose_text: event.target.value })}
          />
        </Field>
        <Field label="Route">
          <input
            className={inputClass}
            value={value.drug?.route_of_administration ?? ""}
            onChange={(event) => setDrug({ route_of_administration: event.target.value })}
          />
        </Field>
        <Field label="Indication">
          <input
            className={inputClass}
            value={value.drug?.indication ?? ""}
            onChange={(event) => setDrug({ indication: event.target.value })}
          />
        </Field>
        <Field label="Batch number">
          <input
            className={inputClass}
            value={value.drug?.batch_number ?? ""}
            onChange={(event) => setDrug({ batch_number: event.target.value })}
          />
        </Field>
        <Field label="Action taken">
          <select
            className={selectClass}
            value={value.drug?.action_taken ?? ""}
            onChange={(event) =>
              setDrug({ action_taken: (event.target.value || null) as PVActionTaken | null })
            }
          >
            <option value="">Unknown</option>
            {PV_ACTION_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Therapy start">
          <input
            type="date"
            className={inputClass}
            value={value.drug?.therapy_start_date ?? ""}
            onChange={(event) => setDrug({ therapy_start_date: event.target.value || null })}
          />
        </Field>
        <Field label="Therapy end">
          <input
            type="date"
            className={inputClass}
            value={value.drug?.therapy_end_date ?? ""}
            onChange={(event) => setDrug({ therapy_end_date: event.target.value || null })}
          />
        </Field>
      </SectionCard>

      <SectionCard title="Reaction" description="Clinical event, severity, causality, and outcome">
        <Field label="Reaction term" className="sm:col-span-2">
          <input
            className={inputClass}
            value={value.reaction_meddra_term ?? ""}
            onChange={(event) => set("reaction_meddra_term", event.target.value)}
          />
        </Field>
        <Field label="Reaction onset">
          <input
            type="date"
            className={inputClass}
            value={value.reaction_start_date ?? ""}
            onChange={(event) => set("reaction_start_date", event.target.value || null)}
          />
        </Field>
        <Field label="Severity">
          <select
            className={selectClass}
            value={value.severity ?? ""}
            onChange={(event) =>
              set("severity", (event.target.value || null) as PVSeverity | null)
            }
          >
            <option value="">Not assessed</option>
            {PV_SEVERITY_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Causality">
          <select
            className={selectClass}
            value={value.causality ?? ""}
            onChange={(event) =>
              set("causality", (event.target.value || null) as PVCausality | null)
            }
          >
            <option value="">Not assessed</option>
            {PV_CAUSALITY_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Outcome">
          <select
            className={selectClass}
            value={value.outcome ?? ""}
            onChange={(event) =>
              set("outcome", (event.target.value || null) as PVOutcome | null)
            }
          >
            <option value="">Unknown</option>
            {PV_OUTCOME_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>
        <div className="flex items-end">
          <label className="flex h-10 items-center gap-2 rounded-xl border border-slate-200 px-3 text-sm text-slate-700">
            <input
              type="checkbox"
              className="h-4 w-4 accent-indigo-600"
              checked={value.is_serious}
              onChange={(event) => set("is_serious", event.target.checked)}
            />
            Serious case
          </label>
        </div>
        <div className="sm:col-span-2 lg:col-span-3">
          <span className="mb-2 block text-xs font-semibold text-slate-600">
            Seriousness criteria
          </span>
          <div className="flex flex-wrap gap-2">
            {PV_SERIOUSNESS_OPTIONS.map((criterion) => (
              <label
                key={criterion}
                className="flex items-center gap-2 rounded-full border border-slate-200 px-3 py-1.5 text-xs text-slate-700"
              >
                <input
                  type="checkbox"
                  className="h-3.5 w-3.5 accent-indigo-600"
                  checked={value.seriousness_criteria?.includes(criterion) ?? false}
                  onChange={(event) => toggleSeriousness(criterion, event.target.checked)}
                />
                {criterion.replaceAll("_", " ")}
              </label>
            ))}
          </div>
        </div>
        <Field label="Narrative / case description" className="sm:col-span-2 lg:col-span-3">
          <textarea
            className={textareaClass}
            value={value.reaction_description ?? ""}
            onChange={(event) => set("reaction_description", event.target.value)}
          />
        </Field>
      </SectionCard>

      <div className="flex justify-end">
        <Button type="submit" disabled={busy}>
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          {submitLabel}
        </Button>
      </div>
    </form>
  );
}
