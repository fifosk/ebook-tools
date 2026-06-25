import type { FormEvent } from 'react';
import type { AcquisitionCandidate } from '../../api/dtos';

type BookNarrationDiscoveryDialogProps = {
  active: boolean;
  query: string;
  candidates: AcquisitionCandidate[];
  policyNotes: string[];
  providersQueried: string[];
  isLoading: boolean;
  error: string | null;
  onQueryChange: (value: string) => void;
  onSearch: (query: string) => void;
  onSelect: (candidate: AcquisitionCandidate) => void;
  onClose: () => void;
};

function formatCandidateMeta(candidate: AcquisitionCandidate): string {
  const parts = [
    candidate.provider,
    candidate.rights.replace(/_/g, ' '),
    candidate.local_path,
    candidate.modified_at ? `modified ${new Date(candidate.modified_at).toLocaleDateString()}` : null,
  ].filter((value): value is string => Boolean(value));
  return parts.join(' · ');
}

export function BookNarrationDiscoveryDialog({
  active,
  query,
  candidates,
  policyNotes,
  providersQueried,
  isLoading,
  error,
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
            Search backend-visible EPUB candidates and select one for Narrate Ebook.
          </p>
        </header>
        <div className="modal__content">
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
              <button type="submit" className="link-button" disabled={isLoading}>
                {isLoading ? 'Searching…' : 'Search'}
              </button>
            </div>
          </form>
          {providersQueried.length > 0 ? (
            <p className="form-help-text">
              Checked {providersQueried.map((provider) => provider.replace(/_/g, ' ')).join(', ')}.
            </p>
          ) : null}
          {error ? (
            <p className="form-help-text form-help-text--error" role="alert">
              {error}
            </p>
          ) : null}
          {policyNotes.length > 0 ? (
            <p className="form-help-text">{policyNotes[0]}</p>
          ) : null}
          {isLoading && candidates.length === 0 ? <p role="status">Searching sources…</p> : null}
          {!isLoading && !error && candidates.length === 0 ? (
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
                    aria-label={`Use ${candidate.title}`}
                  >
                    <span className="file-list__name">{candidate.title}</span>
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
