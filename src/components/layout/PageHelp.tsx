import { useTranslation } from "react-i18next";
import { HelpCircle, CheckCircle2, Lightbulb, ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogTrigger,
} from "@/components/ui/dialog";
import type { HelpContent } from "@/config/helpContent";

interface PageHelpProps {
  content: HelpContent;
}

const PageHelp = ({ content }: PageHelpProps) => {
  const { t } = useTranslation();

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 text-gray-400 hover:text-chemours-red"
          title={t('pageHelp.title', 'Page help')}
        >
          <HelpCircle className="h-4 w-4" />
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-lg">{content.title}</DialogTitle>
          <DialogDescription className="text-sm">
            {content.description}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 mt-2">
          {/* What It Does */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">
              {t('pageHelp.whatItDoes', 'What This Page Does')}
            </h3>
            <ul className="space-y-1.5">
              {content.whatItDoes.map((item, i) => (
                <li key={i} className="flex gap-2 text-sm text-gray-600">
                  <CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </section>

          {/* How To Use */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">
              {t('pageHelp.howToUse', 'How To Use')}
            </h3>
            <ol className="space-y-1.5">
              {content.howToUse.map((step, i) => (
                <li key={i} className="flex gap-2 text-sm text-gray-600">
                  <span className="flex-shrink-0 h-5 w-5 rounded-full bg-chemours-red/10 text-chemours-red text-xs font-medium flex items-center justify-center mt-0.5">
                    {i + 1}
                  </span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>
          </section>

          {/* Use Cases */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">
              {t('pageHelp.useCases', 'Example Use Cases')}
            </h3>
            <div className="space-y-1.5">
              {content.useCases.map((uc, i) => (
                <div
                  key={i}
                  className="text-sm text-gray-600 bg-blue-50 border border-blue-100 rounded-md px-3 py-2"
                >
                  {uc}
                </div>
              ))}
            </div>
          </section>

          {/* Tips (optional) */}
          {content.tips && content.tips.length > 0 && (
            <section>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">
                {t('pageHelp.tips', 'Pro Tips')}
              </h3>
              <ul className="space-y-1.5">
                {content.tips.map((tip, i) => (
                  <li key={i} className="flex gap-2 text-sm text-gray-600">
                    <Lightbulb className="h-4 w-4 text-amber-500 mt-0.5 flex-shrink-0" />
                    <span>{tip}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Flags and Statuses (optional) */}
          {content.flagsAndStatuses && content.flagsAndStatuses.length > 0 && (
            <section>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">
                {t('pageHelp.flagsAndStatuses', 'Flags and Statuses')}
              </h3>
              <div className="space-y-2">
                {content.flagsAndStatuses.map((item, i) => (
                  <div
                    key={i}
                    className="rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-sm"
                  >
                    <div className="font-medium text-gray-800">{item.label}</div>
                    <div className="text-gray-600">{item.meaning}</div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Actions and Buttons (optional) */}
          {content.actionsAndButtons && content.actionsAndButtons.length > 0 && (
            <section>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">
                {t('pageHelp.actionsAndButtons', 'Buttons and Actions')}
              </h3>
              <div className="space-y-2">
                {content.actionsAndButtons.map((item, i) => (
                  <div
                    key={i}
                    className="rounded-md border border-blue-100 bg-blue-50 px-3 py-2 text-sm"
                  >
                    <div className="font-medium text-gray-800">{item.action}</div>
                    <div className="text-gray-600">{item.effect}</div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Related Pages (optional) */}
          {content.relatedPages && content.relatedPages.length > 0 && (
            <section>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">
                {t('pageHelp.relatedPages', 'Related Pages')}
              </h3>
              <div className="flex flex-wrap gap-2">
                {content.relatedPages.map((page) => (
                  <Link key={page.path} to={page.path}>
                    <Badge
                      variant="outline"
                      className="cursor-pointer hover:bg-chemours-red/10 hover:text-chemours-red transition-colors"
                    >
                      {page.name}
                      <ArrowRight className="h-3 w-3 ml-1" />
                    </Badge>
                  </Link>
                ))}
              </div>
            </section>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default PageHelp;
