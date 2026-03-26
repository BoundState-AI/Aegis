import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type SpicyTooltipBodyProps = {
  children: ReactNode;
  className?: string;
  avatarClassName?: string;
};

export function SpicyTooltipBody({ children, className, avatarClassName }: SpicyTooltipBodyProps) {
  return (
    <div className={cn("flex items-start gap-3", className)}>
      <img
        src="/spicy-avatar.svg"
        alt=""
        aria-hidden="true"
        title="スパイシーがお手伝いします"
        className={cn(
          "h-10 w-10 shrink-0 rounded-full border border-white/50 object-cover object-[58%_34%] shadow-sm",
          "opacity-0 translate-y-1 scale-95 transition-all duration-300 ease-out",
          "group-data-[state=delayed-open]/tooltip:translate-y-0 group-data-[state=delayed-open]/tooltip:scale-100 group-data-[state=delayed-open]/tooltip:opacity-100",
          "group-data-[state=instant-open]/tooltip:translate-y-0 group-data-[state=instant-open]/tooltip:scale-100 group-data-[state=instant-open]/tooltip:opacity-100",
          avatarClassName,
        )}
      />
      <div className="min-w-0 flex-1 space-y-2">{children}</div>
    </div>
  );
}
