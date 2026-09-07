import { redirect } from "next/navigation";

/** Legacy UUID detail under /check/[id] → /v/[id] */
export default function LegacyCheckDetailRedirect({
  params,
}: {
  params: { id: string };
}) {
  const reserved = ["scam", "fact", "media"];
  if (reserved.includes(params.id)) {
    redirect(`/check/${params.id}`);
  }
  redirect(`/v/${params.id}`);
}
