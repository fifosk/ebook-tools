import { PipelineFileEntry } from '../api/dtos';

type Props = {
  title: string;
  files: PipelineFileEntry[];
  onSelect: (path: string) => void;
  onClose: () => void;
  description?: string;
  onDelete?: (entry: PipelineFileEntry) => void;
};

function formatEntryDescription(entry: PipelineFileEntry): string {
  if (entry.type === 'directory') {
    return 'Directory';
  }
  return 'File';
}

export function FileSelectionDialog({ title, files, onSelect, onClose, description, onDelete }: Props) {
  return (
    <div className="modal-backdrop" role="presentation">
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="file-dialog-title">
        <header className="modal__header">
          <h3 id="file-dialog-title">{title}</h3>
          {description ? <p className="modal__description">{description}</p> : null}
        </header>
        <div className="modal__content">
          {files.length === 0 ? (
            <p role="status">No entries found.</p>
          ) : (
            <ul className="file-list" role="list">
              {files.map((entry) => (
                <li key={entry.path} className="file-list__item">
                  <div
                    className="file-list__item-row"
                    style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}
                  >
                    <button
                      type="button"
                      className="file-list__button"
                      onClick={() => onSelect(entry.path)}
                      aria-label={`Select ${entry.name}`}
                    >
                      <span className="file-list__name">{entry.name}</span>
                      <span className="file-list__meta">
                        {formatEntryDescription(entry)} · {entry.path}
                      </span>
                    </button>
                    {entry.type === 'file' && onDelete ? (
                      <button
                        type="button"
                        className="link-button"
                        onClick={(event) => {
                          event.preventDefault();
                          event.stopPropagation();
                          onDelete(entry);
                        }}
                        aria-label={`Delete ${entry.name}`}
                      >
                        Delete
                      </button>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          )}
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

export default FileSelectionDialog;
