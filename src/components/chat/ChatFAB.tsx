import { MessageCircle } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";

type ChatFABProps = {
  onClick: () => void;
};

export function ChatFAB({ onClick }: ChatFABProps) {
  const { t } = useTranslation();
  return (
    <Button
      type="button"
      onClick={onClick}
      className="fixed bottom-24 right-4 z-40 rounded-full bg-daikin-blue px-4 py-6 text-white shadow-lg hover:bg-daikin-blue/90"
    >
      <MessageCircle className="mr-2 h-5 w-5" />
      {t("chat.askAegis")}
    </Button>
  );
}
