import { resolveGeneratedFileRecord } from './jobProgressUtils';

export default function TranslationFlowStatus({ generatedFiles }: { generatedFiles: unknown }) {
  const flow = resolveGeneratedFileRecord(generatedFiles, 'translation_flow');
  const preflight = resolveGeneratedFileRecord(generatedFiles, 'translation_preflight');
  const output = resolveGeneratedFileRecord(generatedFiles, 'subtitle_output');
  if (!flow && !preflight && !output) return null;
  const count = (key: string) => {
    const value = flow?.[key];
    return typeof value === 'number' && Number.isFinite(value) ? Math.max(0, value) : 0;
  };
  return (
    <div aria-label="Translation and output progress">
      {flow ? <p>
        Validated translations: {count('accepted')} · Reused: {count('cached')} · Repaired: {count('repaired')}
        {count('failed') > 0 ? ` · Needs attention: ${count('failed')}` : ''}
        {typeof flow['in_flight'] === 'number' ? <>
          <br />
          Requests in flight: {count('in_flight')} · Repairs waiting: {count('repairs_waiting')}
          {count('concurrency') > 0 ? ` · Worker limit: ${count('concurrency')}` : ''}
        </> : null}
      </p> : null}
      {output ? <p>
        {output['audio_enabled'] === true ? 'Subtitles + audio' : 'Subtitles only'}
        {typeof output['phase'] === 'string' ? ` · ${output['phase']}` : ''}
        {typeof output['audio_exported'] === 'number' ? ` · Audio chunks exported: ${output['audio_exported']}` : ''}
      </p> : null}
      {preflight && typeof preflight['message'] === 'string' ? <p>{preflight['message']}</p> : null}
    </div>
  );
}
