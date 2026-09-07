import { redirect } from "next/navigation";

export default function LegacyScamRedirect() {
  redirect("/check/scam");
}
