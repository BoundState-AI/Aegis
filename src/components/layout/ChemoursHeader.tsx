import { ReactNode } from "react";
import PageHelp from "@/components/layout/PageHelp";
import type { HelpContent } from "@/config/helpContent";

interface ChemoursHeaderProps {
  title: string;
  subtitle?: string;
  children?: ReactNode;
  helpContent?: HelpContent;
}

const ChemoursHeader = ({ title, subtitle, children, helpContent }: ChemoursHeaderProps) => {
  return (
    <header className="border-b border-gray-200 bg-white sticky top-0 z-40 shadow-sm">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          {/* Left side - Title */}
          <div className="flex items-center gap-4">
            <div>
              <h1 className="text-xl font-bold text-chemours-dark flex items-center gap-2">
                {title}
                {helpContent && <PageHelp content={helpContent} />}
              </h1>
              {subtitle && (
                <p className="text-sm text-gray-500">{subtitle}</p>
              )}
              <div className="h-0.5 w-16 mt-1 bg-gradient-to-r from-chemours-red to-chemours-orange" />
            </div>
          </div>

          {/* Center - Optional children (stats, etc.) */}
          {children && (
            <div className="hidden md:flex items-center gap-6 text-sm">
              {children}
            </div>
          )}

          {/* Right side - Chemours Branding */}
          <div className="flex items-center gap-2">
            <img
              src="/chemours-logo.png"
              alt="Chemours"
              className="h-14 sm:h-16 md:h-20 lg:h-24 xl:h-28 w-auto"
            />
          </div>
        </div>
      </div>
    </header>
  );
};

export default ChemoursHeader;
