import type { FormEvent } from 'react';
import type { AcquisitionCandidate } from '../../api/dtos';
import type {
  BookNarrationDiscoveryProvider,
  BookNarrationDiscoveryProviderOption
} from './bookNarrationDiscoveryProviders';

type BookNarrationDiscoveryDialogProps = {
  active: boolean;
  provider: BookNarrationDiscoveryProvider;
  query: string;
  candidates: AcquisitionCandidate[];
  policyNotes: string[];
  providersQueried: string[];
  isLoading: boolean;
  isLoadingProviders: boolean;
  acquiringCandidateId: string | null;
  providerOptions: BookNarrationDiscoveryProviderOption[];
  error: string | null;
  providerError: string | null;
  selectedProviderUnavailableMessage: string | null;
  onProviderChange: (provider: BookNarrationDiscoveryProvider) => void;
  onQueryChange: (value: string) => void;
  onSearch: (query: string) => void;
  onSelect: (candidate: AcquisitionCandidate) => void;
  onClose: () => void;
};

function formatCandidateMeta(candidate: AcquisitionCandidate): string {
  const sourceKind = candidate.provider === 'openlibrary' ? 'metadata catalog' : 'public catalog';
  const parts = [
    candidate.provider,
    candidate.rights.replace(/_/g, ' '),
    candidate.contributors[0],
    candidate.language,
    candidate.local_path,
    candidate.source_url ? sourceKind : null,
    candidate.modified_at ? `modified ${new Date(candidate.modified_at).toLocaleDateString()}` : null,
  ].filter((value): value is string => Boolean(value));
  return parts.join(' · ');
}

function canSelectCandidate(candidate: AcquisitionCandidate): boolean {
  return Boolean(
    candidate.local_path?.trim()
      || candidate.capabilities.includes('acquire')
      || candidate.capabilities.includes('metadata')
  );
}

function internetArchiveIds(candidate: AcquisitionCandidate): string[] {
  const value = candidate.metadata.internet_archive_ids;
  const ids = Array.isArray(value) ? value : [value];
  return ids
    .filter((entry): entry is string => typeof entry === 'string')
    .map((entry) => entry.trim())
    .filter(Boolean);
}

function candidateActionLabel(candidate: AcquisitionCandidate, acquiringCandidateId: string | null): string {
  if (acquiringCandidateId === candidate.candidate_id) {
    return internetArchiveIds(candidate).length > 0 && !candidate.capabilities.includes('acquire')
      ? 'Finding...'
      : 'Acquiring...';
  }
  if (candidate.local_path?.trim()) {
    return 'Use';
  }
  if (candidate.capabilities.includes('acquire')) {
    return 'Acquire';
  }
  if (internetArchiveIds(candidate).length > 0) {
    return 'Find EPUB';
  }
  return candidate.capabilities.includes('metadata') ? 'Apply metadata' : 'Review';
}

export function BookNarrationDiscoveryDialog({
  active,
  provider,
  query,
  candidates,
  policyNotes,
  providersQueried,
  isLoading,
  isLoadingProviders,
  acquiringCandidateId,
  providerOptions,
  error,
  providerError,
  selectedProviderUnavailableMessage,
  onProviderChange,
  onQueryChange,
  onSearch,
  onSelect,
  onClose
}: BookNarrationDiscoveryDialogProps) {
  if (!active) {
    return null;
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSearch(query);
  };

  return (
    <div className="modal-backdrop" role="presentation">
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="discovery-dialog-title">
        <header className="modal__header">
          <h3 id="discovery-dialog-title">Discover ebook sources</h3>
          <p className="modal__description">
            Search local EPUBs or public catalog candidates and select one for Narrate Ebook.
          </p>
        </header>
        <div className="modal__content">
          <div className="discovery-provider-toggle" role="group" aria-label="Ebook discovery source">
            {providerOptions.map((option) => (
              <button
                key={option.id}
                type="button"
                className={`discovery-provider-toggle__button${provider === option.id ? ' is-active' : ''}`}
                aria-pressed={provider === option.id}
                onClick={() => onProviderChange(option.id)}
                disabled={isLoading || isLoadingProviders || Boolean(acquiringCandidateId)}
                title={option.unavailableMessage ?? option.label}
              >
                {option.label}
              </button>
            ))}
          </div>
          <form className="discovery-search" onSubmit={handleSubmit}>
            <label htmlFor="ebook-discovery-query">Search</label>
            <div className="discovery-search__controls">
              <input
                id="ebook-discovery-query"
                type="search"
                value={query}
                onChange={(event) => onQueryChange(event.target.value)}
                placeholder="Title, author, or filename"
              />
              <button
                type="submit"
                className="link-button"
                disabled={isLoading || isLoadingProviders || Boolean(selectedProviderUnavailableMessage)}
              >
                {isLoading || isLoadingProviders ? 'Searching…' : 'Search'}
              </button>
            </div>
          </form>
          {providersQueried.length > 0 ? (
            <p className="form-help-text">
              Checked {providersQueried.map((provider) => provider.replace(/_/g, ' ')).join(', ')}.
            </p>
          ) : null}
          {selectedProviderUnavailableMessage ? (
            <p className="form-help-text form-help-text--error" role="alert">
              {selectedProviderUnavailableMessage}
            </p>
          ) : error ? (
            <p className="form-help-text form-help-text--error" role="alert">
              {error}
            </p>
          ) : providerError ? (
            <p className="form-help-text form-help-text--error" role="alert">
              {providerError}
            </p>
          ) : null}
          {policyNotes.length > 0 ? (
            <p className="form-help-text">{policyNotes[0]}</p>
          ) : null}
          {isLoading && candidates.length === 0 ? <p role="status">Searching sources…</p> : null}
          {!isLoading
            && !selectedProviderUnavailableMessage
            && !error
            && !providerError
            && candidates.length === 0 ? (
            <p role="status">No discovery candidates found.</p>
          ) : null}
          {candidates.length > 0 ? (
            <ul className="file-list" role="list">
              {candidates.map((candidate) => (
                <li key={candidate.candidate_id} className="file-list__item">
                  <button
                    type="button"
                    className="file-list__button"
                    onClick={() => onSelect(candidate)}
                    disabled={Boolean(acquiringCandidateId) || !canSelectCandidate(candidate)}
                    aria-label={`${candidateActionLabel(candidate, acquiringCandidateId)} ${candidate.title}`}
                  >
                    <span className="file-list__row">
                      <span className="file-list__name">{candidate.title}</span>
                      <span className="file-list__action">{candidateActionLabel(candidate, acquiringCandidateId)}</span>
                    </span>
                    <span className="file-list__meta">{formatCandidateMeta(candidate)}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
        <footer className="modal__footer">
          <button type="button" className="link-button" onClick={onClose}>
            Close
          </button>
        </footer>
      </div>
    </div>
  );
}

export default BookNarrationDiscoveryDialog;
