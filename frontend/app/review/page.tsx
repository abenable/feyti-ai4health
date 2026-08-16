import { redirect } from "next/navigation";

// The review workspace moved to /dossier (structure) and /dossier/[...path]
// (per-document workspace with Source/Analysis/Draft/Validation tabs).
export default function ReviewRedirect() {
  redirect("/dossier");
}
