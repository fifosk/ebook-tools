import { useCallback, useEffect, useMemo, useState } from 'react';
import type { AcquisitionCandidate } from '../../api/dtos';
import {
  buildBookDiscoveryTemplateState,
  resolveBookDiscoveryTemplateStateForInput,
  resolveBookNarrationTemplatePayloadExtras,
} from './bookNarrationTemplates';
import type { BookNarrationDiscoverySelection } from './useBookNarrationDiscovery';
import type { BookNarrationFormSection } from './bookNarrationFormTypes';

type UseBookNarrationDiscoverySelectionArgs = {
  acquireDiscoveryCandidate: (candidate: AcquisitionCandidate) => Promise<BookNarrationDiscoverySelection | null>;
  applyDiscoveryMetadataCandidate: (candidate: AcquisitionCandidate) => boolean;
  closeDiscoveryDialog: () => void;
  discoverInternetArchiveCandidatesForCandidate: (candidate: AcquisitionCandidate) => Promise<boolean>;
  discoveryProvider: string;
  discoveryQuery: string;
  handleInputFileChange: (value: string) => void;
  handleSectionChange: (section: BookNarrationFormSection) => void;
  inputFile: string;
  selectDiscoveryCandidate: (candidate: AcquisitionCandidate) => Promise<BookNarrationDiscoverySelection | null>;
  sourceMode: 'upload' | 'generated';
  templatePayloadExtras?: Record<string, unknown> | null;
};

export function useBookNarrationDiscoverySelection({
  acquireDiscoveryCandidate,
  applyDiscoveryMetadataCandidate,
  closeDiscoveryDialog,
  discoverInternetArchiveCandidatesForCandidate,
  discoveryProvider,
  discoveryQuery,
  handleInputFileChange,
  handleSectionChange,
  inputFile,
  selectDiscoveryCandidate,
  sourceMode,
  templatePayloadExtras,
}: UseBookNarrationDiscoverySelectionArgs) {
  const [selectedDiscoveryTemplateState, setSelectedDiscoveryTemplateState] =
    useState<Record<string, unknown> | null>(null);

  const mergedTemplatePayloadExtras = useMemo(() => resolveBookNarrationTemplatePayloadExtras({
    selectedDiscoveryTemplateState,
    sourceMode,
    discoveryProvider,
    discoveryQuery,
    templatePayloadExtras,
  }), [discoveryProvider, discoveryQuery, selectedDiscoveryTemplateState, sourceMode, templatePayloadExtras]);

  useEffect(() => {
    const nextDiscoveryTemplateState = resolveBookDiscoveryTemplateStateForInput(
      selectedDiscoveryTemplateState,
      inputFile
    );
    if (nextDiscoveryTemplateState === selectedDiscoveryTemplateState) {
      return;
    }
    setSelectedDiscoveryTemplateState(nextDiscoveryTemplateState);
  }, [inputFile, selectedDiscoveryTemplateState]);

  const handleDiscoveryCandidateSelect = useCallback((candidate: AcquisitionCandidate) => {
    void (async () => {
      const selection = (await selectDiscoveryCandidate(candidate))
        ?? (candidate.capabilities.includes('acquire')
          ? await acquireDiscoveryCandidate(candidate)
          : null);
      if (selection?.selectedPath) {
        setSelectedDiscoveryTemplateState(buildBookDiscoveryTemplateState(candidate, {
          query: discoveryQuery,
          provider: discoveryProvider,
          selectedPath: selection.selectedPath,
          preparedMetadata: selection.preparedMetadata,
        }));
        handleInputFileChange(selection.selectedPath);
        closeDiscoveryDialog();
        return;
      }
      if (!candidate.capabilities.includes('acquire')) {
        const handledArchiveBridge = await discoverInternetArchiveCandidatesForCandidate(candidate);
        if (handledArchiveBridge) {
          return;
        }
      }
      if (!candidate.capabilities.includes('acquire') && applyDiscoveryMetadataCandidate(candidate)) {
        setSelectedDiscoveryTemplateState(buildBookDiscoveryTemplateState(candidate, {
          query: discoveryQuery,
          provider: discoveryProvider,
        }));
        handleSectionChange('metadata');
        closeDiscoveryDialog();
      }
    })();
  }, [
    acquireDiscoveryCandidate,
    applyDiscoveryMetadataCandidate,
    closeDiscoveryDialog,
    discoverInternetArchiveCandidatesForCandidate,
    discoveryProvider,
    discoveryQuery,
    handleInputFileChange,
    handleSectionChange,
    selectDiscoveryCandidate,
  ]);

  return {
    handleDiscoveryCandidateSelect,
    mergedTemplatePayloadExtras,
    selectedDiscoveryTemplateState,
    setSelectedDiscoveryTemplateState,
  };
}
