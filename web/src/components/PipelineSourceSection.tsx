import { DragEvent } from 'react';

type SourceSectionProps = {
  headingId: string;
  title: string;
  description: string;
  inputFile: string;
  baseOutputFile: string;
  onInputFileChange: (value: string) => void;
  onBaseOutputFileChange: (value: string) => void;
  onBrowseClick: (type: 'input' | 'output') => void;
  canBrowseFiles: boolean;
  isLoadingFiles: boolean;
  fileDialogError: string | null;
  isDraggingFile: boolean;
  isUploadingFile: boolean;
  onDropzoneDragOver: (event: DragEvent<HTMLDivElement>) => void;
  onDropzoneDragLeave: (event: DragEvent<HTMLDivElement>) => void;
  onDropzoneDrop: (event: DragEvent<HTMLDivElement>) => void;
  onUploadFile: (file: File) => void | Promise<void>;
  uploadError: string | null;
  recentUploadName: string | null;
  configOverrides: string;
  environmentOverrides: string;
  pipelineOverrides: string;
  bookMetadata: string;
  onConfigOverridesChange: (value: string) => void;
  onEnvironmentOverridesChange: (value: string) => void;
  onPipelineOverridesChange: (value: string) => void;
  onBookMetadataChange: (value: string) => void;
};

const PipelineSourceSection = ({
  headingId,
  title,
  description,
  inputFile,
  baseOutputFile,
  onInputFileChange,
  onBaseOutputFileChange,
  onBrowseClick,
  canBrowseFiles,
  isLoadingFiles,
  fileDialogError,
  isDraggingFile,
  isUploadingFile,
  onDropzoneDragOver,
  onDropzoneDragLeave,
  onDropzoneDrop,
  onUploadFile,
  uploadError,
  recentUploadName,
  configOverrides,
  environmentOverrides,
  pipelineOverrides,
  bookMetadata,
  onConfigOverridesChange,
  onEnvironmentOverridesChange,
  onPipelineOverridesChange,
  onBookMetadataChange
}: SourceSectionProps) => {
  const dropzoneClassNames = ['file-dropzone'];
  if (isDraggingFile) {
    dropzoneClassNames.push('file-dropzone--dragging');
  }
  if (isUploadingFile) {
    dropzoneClassNames.push('file-dropzone--uploading');
  }
  const dropzoneClassName = dropzoneClassNames.join(' ');

  return (
    <section className="pipeline-card" aria-labelledby={headingId}>
      <header className="pipeline-card__header">
        <h3 id={headingId}>{title}</h3>
        <p>{description}</p>
      </header>
      <div className="pipeline-card__body">
        <label htmlFor="input_file">Input file path</label>
        <input
          id="input_file"
          name="input_file"
          type="text"
          value={inputFile}
          onChange={(event) => onInputFileChange(event.target.value)}
          placeholder="/storage/ebooks/source.epub"
          required
        />
        <div className="pipeline-card__actions">
          <button
            type="button"
            className="link-button"
            onClick={() => onBrowseClick('input')}
            disabled={!canBrowseFiles || isLoadingFiles}
          >
            {isLoadingFiles ? 'Loading…' : 'Browse ebooks'}
          </button>
        </div>
        {fileDialogError ? (
          <p className="form-help-text" role="status">
            {fileDialogError}
          </p>
        ) : null}
        <div
          className={dropzoneClassName}
          onDragEnter={onDropzoneDragOver}
          onDragOver={onDropzoneDragOver}
          onDragLeave={onDropzoneDragLeave}
          onDrop={onDropzoneDrop}
        >
          <label htmlFor="epub-upload-input">
            <strong>{isUploadingFile ? 'Uploading EPUB…' : 'Drag & drop an EPUB file'}</strong>
            <span>or click to choose a file from your computer.</span>
          </label>
          <input
            id="epub-upload-input"
            type="file"
            accept=".epub"
            onChange={(event) => {
              const nextFile = event.target.files?.[0] ?? null;
              if (nextFile) {
                onUploadFile(nextFile);
              }
              event.target.value = '';
            }}
            disabled={isUploadingFile}
          />
        </div>
        {uploadError ? (
          <p className="form-help-text form-help-text--error" role="alert">
            {uploadError}
          </p>
        ) : null}
        {recentUploadName ? (
          <p className="form-help-text form-help-text--success" role="status">
            Uploaded <strong>{recentUploadName}</strong> to the ebooks library.
          </p>
        ) : null}
        <label htmlFor="base_output_file">Base output file</label>
        <input
          id="base_output_file"
          name="base_output_file"
          type="text"
          value={baseOutputFile}
          onChange={(event) => onBaseOutputFileChange(event.target.value)}
          placeholder="ebooks/output"
          required
        />
        <div className="pipeline-card__actions">
          <button
            type="button"
            className="link-button"
            onClick={() => onBrowseClick('output')}
            disabled={!canBrowseFiles || isLoadingFiles}
          >
            {isLoadingFiles ? 'Loading…' : 'Browse output paths'}
          </button>
        </div>
      </div>
      <details open className="collapsible">
        <summary>Advanced overrides</summary>
        <p className="form-help-text">
          Provide JSON overrides to tweak pipeline behaviour or prefill book metadata. Leave blank to
          use the defaults from the backend.
        </p>
        <label htmlFor="config_overrides">
          Config overrides JSON
          <textarea
            id="config_overrides"
            name="config_overrides"
            rows={3}
            value={configOverrides}
            onChange={(event) => onConfigOverridesChange(event.target.value)}
            spellCheck={false}
          />
        </label>
        <label htmlFor="environment_overrides">
          Environment overrides JSON
          <textarea
            id="environment_overrides"
            name="environment_overrides"
            rows={2}
            value={environmentOverrides}
            onChange={(event) => onEnvironmentOverridesChange(event.target.value)}
            spellCheck={false}
          />
        </label>
        <label htmlFor="pipeline_overrides">
          Pipeline overrides JSON
          <textarea
            id="pipeline_overrides"
            name="pipeline_overrides"
            rows={3}
            value={pipelineOverrides}
            onChange={(event) => onPipelineOverridesChange(event.target.value)}
            spellCheck={false}
          />
        </label>
        <label htmlFor="book_metadata">
          Book metadata JSON
          <textarea
            id="book_metadata"
            name="book_metadata"
            rows={3}
            value={bookMetadata}
            onChange={(event) => onBookMetadataChange(event.target.value)}
            spellCheck={false}
          />
        </label>
      </details>
    </section>
  );
};

export default PipelineSourceSection;
