import { useCallback, useEffect, useState } from 'react';
import type { BookNarrationFormSection } from './bookNarrationFormTypes';

type UseBookNarrationSectionStateOptions = {
  activeSection?: BookNarrationFormSection;
  tabSections: BookNarrationFormSection[];
  onSectionChange?: (section: BookNarrationFormSection) => void;
};

export function useBookNarrationSectionState({
  activeSection,
  tabSections,
  onSectionChange,
}: UseBookNarrationSectionStateOptions) {
  const [activeTab, setActiveTab] = useState<BookNarrationFormSection>(() => {
    if (activeSection && tabSections.includes(activeSection)) {
      return activeSection;
    }
    return 'source';
  });

  const handleSectionChange = useCallback(
    (section: BookNarrationFormSection) => {
      setActiveTab(section);
      onSectionChange?.(section);
    },
    [onSectionChange],
  );

  useEffect(() => {
    if (activeSection && tabSections.includes(activeSection)) {
      setActiveTab(activeSection);
    }
  }, [activeSection, tabSections]);

  return {
    activeTab,
    handleSectionChange,
  };
}
