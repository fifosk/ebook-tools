import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  BOOK_NARRATION_SECTION_META,
  BOOK_NARRATION_TAB_SECTIONS
} from './bookNarrationFormDefaults';
import type { BookNarrationFormProps, BookNarrationFormSection } from './bookNarrationFormTypes';
import { resolveBookNarrationSectionMeta } from './bookNarrationFormUtils';

type UseBookNarrationSectionStateOptions = {
  activeSection?: BookNarrationFormSection;
  tabSections?: BookNarrationFormSection[];
  sectionOverrides?: BookNarrationFormProps['sectionOverrides'];
  onSectionChange?: (section: BookNarrationFormSection) => void;
};

export function useBookNarrationSectionState({
  activeSection,
  tabSections = BOOK_NARRATION_TAB_SECTIONS,
  sectionOverrides = {},
  onSectionChange,
}: UseBookNarrationSectionStateOptions) {
  const sectionMeta = useMemo(() => {
    return resolveBookNarrationSectionMeta(BOOK_NARRATION_SECTION_META, sectionOverrides);
  }, [sectionOverrides]);

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
    sectionMeta,
    tabSections,
  };
}
