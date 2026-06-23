import type { PipelineIntakeStatusResponse } from '../../api/dtos';
import { resolvePipelineIntakeStatusPresentation } from './createIntakeStatusUtils';

type CreateIntakeStatusCalloutProps = {
  status: PipelineIntakeStatusResponse | null;
  isLoading: boolean;
};

export function CreateIntakeStatusCallout({
  status,
  isLoading,
}: CreateIntakeStatusCalloutProps) {
  const presentation = resolvePipelineIntakeStatusPresentation(status, isLoading);
  if (!presentation) {
    return null;
  }

  return (
    <div className={`form-callout form-callout--${presentation.tone}`} role={presentation.role}>
      <div>{presentation.message}</div>
      {presentation.detailLines.length > 0 ? (
        <ul className="form-callout__details" aria-label="Job intake details">
          {presentation.detailLines.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
