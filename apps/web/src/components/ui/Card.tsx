import { cn } from "@/lib/utils";

export function Card({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("surface p-4 sm:p-6", className)} {...props}>
      {children}
    </div>
  );
}
