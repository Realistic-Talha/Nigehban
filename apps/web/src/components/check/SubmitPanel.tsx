"use client";

import { useRef, useState } from "react";
import { Camera, Upload, X } from "lucide-react";
import { Textarea } from "@/components/ui/Textarea";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useLocale } from "@/providers/locale-provider";
import { cn } from "@/lib/utils";

export interface SubmitPanelProps {
  mode: "text" | "file" | "both";
  onSubmit: (data: { text?: string; file?: File; url?: string }) => void;
  isProcessing?: boolean;
  defaultText?: string;
  acceptUrl?: boolean;
}

export function SubmitPanel({
  mode,
  onSubmit,
  isProcessing,
  defaultText,
  acceptUrl,
}: SubmitPanelProps) {
  const { t } = useLocale();
  const [text, setText] = useState(defaultText ?? "");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      text: text.trim() || undefined,
      file: file ?? undefined,
      url: url.trim() || undefined,
    });
  };

  const disabled =
    isProcessing ||
    (mode === "text" && !text.trim() && !(acceptUrl && url.trim())) ||
    (mode === "both" && !text.trim() && !file && !(acceptUrl && url.trim())) ||
    (mode === "file" && !file && !(acceptUrl && url.trim()));

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {(mode === "text" || mode === "both") && (
        <Textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={t("check.paste")}
          disabled={isProcessing}
          aria-label="Submission text"
        />
      )}

      {acceptUrl && (
        <Input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://"
          disabled={isProcessing}
          className="rounded-[20px]"
        />
      )}

      {(mode === "file" || mode === "both") && (
        <div className="space-y-2">
          {!file ? (
            <div
              className={cn(
                "flex min-h-[148px] cursor-pointer flex-col items-center justify-center gap-3 rounded-[24px] border-2 border-dashed border-border bg-paper-2 p-5 transition-colors hover:border-accent hover:bg-paper-3",
              )}
              onClick={() => fileRef.current?.click()}
              onKeyDown={(e) => e.key === "Enter" && fileRef.current?.click()}
              role="button"
              tabIndex={0}
            >
              <Upload className="h-7 w-7 text-ink-subtle" />
              <span className="text-sm text-ink-muted">{t("check.upload")}</span>
              <Button
                type="button"
                variant="secondary"
                onClick={(e) => {
                  e.stopPropagation();
                  cameraRef.current?.click();
                }}
              >
                <Camera className="h-4 w-4" /> {t("check.camera")}
              </Button>
              <input
                ref={fileRef}
                type="file"
                accept="image/*,video/*"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              <input
                ref={cameraRef}
                type="file"
                accept="image/*"
                capture="environment"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </div>
          ) : (
            <div className="flex items-center gap-3 rounded-[20px] border border-border bg-paper-2 p-3.5">
              <span className="flex-1 truncate text-sm">{file.name}</span>
              <button
                type="button"
                onClick={() => setFile(null)}
                className="flex h-10 w-10 items-center justify-center rounded-full hover:bg-paper-3"
                aria-label="Remove file"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>
      )}

      <div className="flex justify-end">
        <Button type="submit" state={isProcessing ? "loading" : "default"} disabled={disabled}>
          {isProcessing ? t("check.processing") : t("check.submit")}
        </Button>
      </div>
    </form>
  );
}
