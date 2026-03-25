import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import { Languages } from 'lucide-react';

export const LanguageToggle = () => {
  const { i18n } = useTranslation();

  const toggleLanguage = () => {
    const newLang = i18n.language === 'ja' ? 'en' : 'ja';
    i18n.changeLanguage(newLang);
  };

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={toggleLanguage}
      className="flex items-center gap-1.5 text-gray-600 hover:text-daikin-blue hover:bg-gray-100"
    >
      <Languages className="h-4 w-4" />
      <span className="text-xs font-medium">
        {i18n.language === 'ja' ? 'EN' : 'JP'}
      </span>
    </Button>
  );
};

export default LanguageToggle;
