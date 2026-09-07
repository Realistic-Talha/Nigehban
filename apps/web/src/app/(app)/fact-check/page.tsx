import { redirect } from "next/navigation";

export default function LegacyFactRedirect() {
  redirect("/check/fact");
}
