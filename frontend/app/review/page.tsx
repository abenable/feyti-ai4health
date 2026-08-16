import { redirect } from "next/navigation";

// The review workspace moved to /d/[dossierId]/structure (CTD plan) and
// /d/[dossierId]/structure/[...path] (per-document workspace). There's no
// longer a single default dossier, so send legacy links to the picker.
export default function ReviewRedirect() {
  redirect("/");
}
