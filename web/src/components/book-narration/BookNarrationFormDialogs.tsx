import type {
  AcquisitionCandidate,
  AcquisitionDiscoveryResponse,
  PipelineFileBrowserResponse,
  PipelineFileEntry,
} from '../../api/dtos';
import { BookNarrationDiscoveryDialog } from './BookNarrationDiscoveryDialog';
import type {
  BookNarrationDiscoveryProvider,
  BookNarrationDiscoveryProviderOption,
} from './bookNarrationDiscoveryProviders';
import {
  BookNarrationFileDialog,
  type BookNarrationFileDialogMode,
} from './BookNarrationFileDialog';

type BookNarrationFormDialogsProps = {
  activeFileDialog: BookNarrationFileDialogMode | null;
  fileOptions: PipelineFileBrowserResponse | null;
  onInputFileSelect: (path: string) => void;
  onOutputPathSelect: (path: string) => void;
  onCloseFileDialog: () => void;
  onDeleteEbook: (entry: PipelineFileEntry) => void | Promise<void>;
  activeDiscoveryDialog: boolean;
  discoveryProvider: BookNarrationDiscoveryProvider;
  discoveryQuery: string;
  discoveryCandidates: AcquisitionCandidate[];
  discoveryResponse: AcquisitionDiscoveryResponse | null;
  discoveryError: string | null;
  isDiscovering: boolean;
  isLoadingProviders: boolean;
  acquiringCandidateId: string | null;
  providerOptions: BookNarrationDiscoveryProviderOption[];
  providerError: string | null;
  selectedProviderUnavailableMessage: string | null;
  onDiscoveryProviderChange: (provider: BookNarrationDiscoveryProvider) => void;
  onDiscoveryQueryChange: (value: string) => void;
  onDiscoverySearch: (query: string) => void | Promise<void>;
  onDiscoverySelect: (candidate: AcquisitionCandidate) => void;
  onCloseDiscoveryDialog: () => void;
};

export function BookNarrationFormDialogs({
  activeFileDialog,
  fileOptions,
  onInputFileSelect,
  onOutputPathSelect,
  onCloseFileDialog,
  onDeleteEbook,
  activeDiscoveryDialog,
  discoveryProvider,
  discoveryQuery,
  discoveryCandidates,
  discoveryResponse,
  discoveryError,
  isDiscovering,
  isLoadingProviders,
  acquiringCandidateId,
  providerOptions,
  providerError,
  selectedProviderUnavailableMessage,
  onDiscoveryProviderChange,
  onDiscoveryQueryChange,
  onDiscoverySearch,
  onDiscoverySelect,
  onCloseDiscoveryDialog,
}: BookNarrationFormDialogsProps) {
  return (
    <>
      <BookNarrationFileDialog
        activeFileDialog={activeFileDialog}
        fileOptions={fileOptions}
        onInputFileSelect={onInputFileSelect}
        onOutputPathSelect={onOutputPathSelect}
        onClose={onCloseFileDialog}
        onDeleteEbook={(entry) => {
          void onDeleteEbook(entry);
        }}
      />
      <BookNarrationDiscoveryDialog
        active={activeDiscoveryDialog}
        provider={discoveryProvider}
        query={discoveryQuery}
        candidates={discoveryCandidates}
        policyNotes={discoveryResponse?.policy_notes ?? []}
        providersQueried={discoveryResponse?.providers_queried ?? []}
        isLoading={isDiscovering}
        isLoadingProviders={isLoadingProviders}
        acquiringCandidateId={acquiringCandidateId}
        providerOptions={providerOptions}
        error={discoveryError}
        providerError={providerError}
        selectedProviderUnavailableMessage={selectedProviderUnavailableMessage}
        onProviderChange={onDiscoveryProviderChange}
        onQueryChange={onDiscoveryQueryChange}
        onSearch={(query) => {
          void onDiscoverySearch(query);
        }}
        onSelect={onDiscoverySelect}
        onClose={onCloseDiscoveryDialog}
      />
    </>
  );
}

export default BookNarrationFormDialogs;
