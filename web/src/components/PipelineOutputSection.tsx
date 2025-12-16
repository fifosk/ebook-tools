import { MenuOption } from '../constants/menuOptions';
import { formatLanguageWithFlag } from '../utils/languages';

type VoicePreviewStatus = 'idle' | 'loading' | 'playing';

type LanguageEntry = {
  label: string;
  code: string | null;
};

type PipelineOutputSectionProps = {
  headingId: string;
  title: string;
  description: string;
  generateAudio: boolean;
  audioMode: string;
  selectedVoice: string;
  writtenMode: string;
  outputHtml: boolean;
  outputPdf: boolean;
  includeTransliteration: boolean;
  tempo: number;
  generateVideo: boolean;
  addImages: boolean;
  availableAudioModes: MenuOption[];
  availableVoices: MenuOption[];
  availableWrittenModes: MenuOption[];
  languagesForOverride: LanguageEntry[];
  voiceOverrides: Record<string, string>;
  voicePreviewStatus: Record<string, VoicePreviewStatus>;
  voicePreviewError: Record<string, string>;
  isLoadingVoiceInventory: boolean;
  voiceInventoryError: string | null;
  buildVoiceOptions: (languageLabel: string, languageCode: string | null) => MenuOption[];
  onGenerateAudioChange: (value: boolean) => void;
  onAudioModeChange: (value: string) => void;
  onSelectedVoiceChange: (value: string) => void;
  onVoiceOverrideChange: (languageCode: string, voiceValue: string) => void;
  onWrittenModeChange: (value: string) => void;
  onOutputHtmlChange: (value: boolean) => void;
  onOutputPdfChange: (value: boolean) => void;
  onAddImagesChange: (value: boolean) => void;
  onIncludeTransliterationChange: (value: boolean) => void;
  onTempoChange: (value: number) => void;
  onGenerateVideoChange: (value: boolean) => void;
  onPlayVoicePreview: (languageCode: string, languageLabel: string) => Promise<void> | void;
};

const PipelineOutputSection = ({
  headingId,
  title,
  description,
  generateAudio,
  audioMode,
  selectedVoice,
  writtenMode,
  outputHtml,
  outputPdf,
  addImages,
  includeTransliteration,
  tempo,
  generateVideo,
  availableAudioModes,
  availableVoices,
  availableWrittenModes,
  languagesForOverride,
  voiceOverrides,
  voicePreviewStatus,
  voicePreviewError,
  isLoadingVoiceInventory,
  voiceInventoryError,
  buildVoiceOptions,
  onGenerateAudioChange,
  onAudioModeChange,
  onSelectedVoiceChange,
  onVoiceOverrideChange,
  onWrittenModeChange,
  onOutputHtmlChange,
  onOutputPdfChange,
  onAddImagesChange,
  onIncludeTransliterationChange,
  onTempoChange,
  onGenerateVideoChange,
  onPlayVoicePreview
}: PipelineOutputSectionProps) => {
  const selectedAudioOption =
    availableAudioModes.find((option) => option.value === audioMode) ?? null;
  const selectedVoiceOption =
    availableVoices.find((option) => option.value === selectedVoice) ?? null;
  const selectedWrittenOption =
    availableWrittenModes.find((option) => option.value === writtenMode) ?? null;

  return (
    <section className="pipeline-card" aria-labelledby={headingId}>
      <header className="pipeline-card__header">
        <h3 id={headingId}>{title}</h3>
        <p>{description}</p>
      </header>
      <div className="pipeline-card__body">
        <label className="checkbox">
          <input
            type="checkbox"
            name="generate_audio"
            checked={generateAudio}
            onChange={(event) => onGenerateAudioChange(event.target.checked)}
          />
          Generate narration tracks
        </label>
        <label htmlFor={`${headingId}-audio-mode`}>Audio mode</label>
        <select
          id={`${headingId}-audio-mode`}
          value={audioMode}
          onChange={(event) => onAudioModeChange(event.target.value)}
        >
          {availableAudioModes.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {selectedAudioOption?.description ? (
          <p className="form-help-text">{selectedAudioOption.description}</p>
        ) : null}
        <label htmlFor={`${headingId}-voice`}>Narration voice</label>
        <select
          id={`${headingId}-voice`}
          value={selectedVoice}
          onChange={(event) => onSelectedVoiceChange(event.target.value)}
        >
          {availableVoices.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {selectedVoiceOption?.description ? (
          <p className="form-help-text">{selectedVoiceOption.description}</p>
        ) : null}
        <div className="voice-overrides">
          <h4>Language-specific voices</h4>
          <p className="form-help-text">
            Override the narration voice for individual languages. Leave as default to use the
            selection above.
          </p>
          {isLoadingVoiceInventory ? (
            <p className="form-help-text" role="status">
              Loading voice inventory…
            </p>
          ) : null}
          {voiceInventoryError ? (
            <p className="form-help-text form-help-text--error" role="alert">
              {voiceInventoryError}
            </p>
          ) : null}
          <div className="voice-override-list">
          {languagesForOverride.map(({ label, code }) => {
            const effectiveCode = code ?? '';
            const options = buildVoiceOptions(label, code);
            const overrideValue = code ? voiceOverrides[code] ?? '' : '';
            const status = voicePreviewStatus[effectiveCode] ?? 'idle';
            const previewError = voicePreviewError[effectiveCode];
            const defaultVoiceLabel =
              availableVoices.find((option) => option.value === selectedVoice)?.label ||
              selectedVoice;
            const flaggedLabel = formatLanguageWithFlag(label) || label;
            return (
              <div key={effectiveCode || label} className="voice-override-row">
                <div className="voice-override-info">
                  <strong>{flaggedLabel}</strong>
                  <span className="voice-override-code">{code ?? 'Unknown code'}</span>
                </div>
                {code && options.length > 0 ? (
                  <div className="voice-override-controls">
                    <select
                      aria-label={`Voice override for ${label}`}
                      value={overrideValue}
                      onChange={(event) => onVoiceOverrideChange(code, event.target.value)}
                      >
                        <option value="">{`Default (${defaultVoiceLabel})`}</option>
                        {options.map((option) => (
                          <option key={option.value} value={option.value} title={option.description}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                      <button
                        type="button"
                        className="link-button"
                        onClick={() => void onPlayVoicePreview(code, label)}
                        disabled={status === 'loading' || isLoadingVoiceInventory}
                      >
                        {status === 'loading'
                          ? 'Loading preview…'
                          : status === 'playing'
                          ? 'Playing preview…'
                          : 'Play sample'}
                      </button>
                    </div>
                  ) : (
                    <p className="form-help-text">No voice inventory available for this language.</p>
                  )}
                  {previewError ? (
                    <p className="form-help-text form-help-text--error" role="status">
                      {previewError}
                    </p>
                  ) : null}
                </div>
              );
            })}
          </div>
        </div>
        <label htmlFor={`${headingId}-written-mode`}>Written mode</label>
        <select
          id={`${headingId}-written-mode`}
          value={writtenMode}
          onChange={(event) => onWrittenModeChange(event.target.value)}
        >
          {availableWrittenModes.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {selectedWrittenOption?.description ? (
          <p className="form-help-text">{selectedWrittenOption.description}</p>
        ) : null}
        <label className="checkbox">
          <input
            type="checkbox"
            name="output_html"
            checked={outputHtml}
            onChange={(event) => onOutputHtmlChange(event.target.checked)}
          />
          Generate HTML output
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            name="output_pdf"
            checked={outputPdf}
            onChange={(event) => onOutputPdfChange(event.target.checked)}
          />
          Generate PDF output
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            name="add_images"
            checked={addImages}
            onChange={(event) => onAddImagesChange(event.target.checked)}
          />
          Add AI-generated images to interactive reader
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            name="include_transliteration"
            checked={includeTransliteration}
            onChange={(event) => onIncludeTransliterationChange(event.target.checked)}
          />
          Include transliteration in written output
        </label>
        <label htmlFor="tempo">
          Tempo
          <input
            id="tempo"
            name="tempo"
            type="number"
            step={0.1}
            min={0.5}
            value={tempo}
            onChange={(event) => onTempoChange(Number(event.target.value))}
          />
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            name="generate_video"
            checked={generateVideo}
            onChange={(event) => onGenerateVideoChange(event.target.checked)}
          />
          Generate stitched video assets
        </label>
      </div>
    </section>
  );
};

export default PipelineOutputSection;
