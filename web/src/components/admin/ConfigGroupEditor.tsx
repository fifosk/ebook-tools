import { useEffect, useMemo, useState } from 'react';
import type { ConfigGroup, ConfigKeyMetadata, ValidationError } from '../../api/client';
import { fetchLlmModels } from '../../api/client';

interface ConfigGroupEditorProps {
  group: ConfigGroup;
  pendingChanges: Record<string, unknown>;
  onChangeValue: (key: string, value: unknown) => void;
  validationErrors: ValidationError[];
  validationWarnings: ValidationError[];
}

interface ConfigKeyFieldProps {
  config: ConfigKeyMetadata;
  value: unknown;
  onChange: (value: unknown) => void;
  error?: ValidationError;
  warning?: ValidationError;
  dynamicChoices?: string[];
  dynamicChoicesLoading?: boolean;
  dynamicChoicesError?: string | null;
}

function ConfigKeyField({
  config,
  value,
  onChange,
  error,
  warning,
  dynamicChoices,
  dynamicChoicesLoading,
  dynamicChoicesError
}: ConfigKeyFieldProps) {
  const renderInput = () => {
    switch (config.type) {
      case 'boolean':
        return (
          <label className="config-field__toggle">
            <input
              type="checkbox"
              checked={Boolean(value)}
              onChange={e => onChange(e.target.checked)}
              disabled={config.isEnvOverride}
            />
            <span className="config-field__toggle-label">
              {value ? 'Enabled' : 'Disabled'}
            </span>
          </label>
        );

      case 'integer':
      case 'number':
        return (
          <input
            type="number"
            value={value as number ?? ''}
            onChange={e => {
              const val = e.target.value;
              if (val === '') {
                onChange(config.type === 'integer' ? 0 : 0.0);
              } else {
                onChange(config.type === 'integer' ? parseInt(val, 10) : parseFloat(val));
              }
            }}
            min={config.validationRules?.min as number}
            max={config.validationRules?.max as number}
            step={config.type === 'integer' ? 1 : 'any'}
            disabled={config.isEnvOverride}
            className="config-field__input"
          />
        );

      case 'secret':
        return (
          <input
            type="password"
            value={value as string ?? ''}
            onChange={e => onChange(e.target.value)}
            placeholder={config.isSensitive && value === '***REDACTED***' ? '(encrypted)' : ''}
            disabled={config.isEnvOverride}
            className="config-field__input"
          />
        );

      case 'string':
      default:
        // Static choices from validation rules
        if (config.validationRules?.choices) {
          const choices = config.validationRules.choices as string[];
          return (
            <select
              value={value as string ?? ''}
              onChange={e => onChange(e.target.value)}
              disabled={config.isEnvOverride}
              className="config-field__select"
            >
              {choices.map(choice => (
                <option key={choice} value={choice}>
                  {choice}
                </option>
              ))}
            </select>
          );
        }

        // Dynamic choices (e.g., LLM models)
        if (config.validationRules?.dynamicChoicesSource && dynamicChoices) {
          const currentValue = (value as string) ?? '';
          // Build options list: include current value if not in list, plus all fetched options
          const allOptions = currentValue && !dynamicChoices.includes(currentValue)
            ? [currentValue, ...dynamicChoices]
            : dynamicChoices;

          return (
            <div className="config-field__dynamic-select">
              <select
                value={currentValue}
                onChange={e => onChange(e.target.value)}
                disabled={config.isEnvOverride || (dynamicChoicesLoading && dynamicChoices.length === 0)}
                className="config-field__select"
              >
                <option value="">Use server default</option>
                {allOptions.map(choice => (
                  <option key={choice} value={choice}>
                    {choice}
                  </option>
                ))}
              </select>
              {dynamicChoicesLoading && (
                <span className="config-field__loading">Loading models...</span>
              )}
              {dynamicChoicesError && (
                <span className="config-field__dynamic-error">{dynamicChoicesError}</span>
              )}
            </div>
          );
        }

        return (
          <input
            type="text"
            value={value as string ?? ''}
            onChange={e => onChange(e.target.value)}
            disabled={config.isEnvOverride}
            className="config-field__input"
          />
        );
    }
  };

  return (
    <div className={`config-field ${error ? 'config-field--error' : ''}`}>
      <div className="config-field__header">
        <label className="config-field__label">
          {config.displayName || config.key}
          {config.requiresRestart && (
            <span className="config-field__badge config-field__badge--restart" title="Requires restart">
              Restart
            </span>
          )}
          {config.isSensitive && (
            <span className="config-field__badge config-field__badge--sensitive" title="Sensitive value">
              Sensitive
            </span>
          )}
          {config.isEnvOverride && (
            <span className="config-field__badge config-field__badge--env" title="Set via environment variable">
              ENV
            </span>
          )}
        </label>
      </div>

      {config.description && (
        <p className="config-field__description">{config.description}</p>
      )}

      <div className="config-field__input-wrapper">
        {renderInput()}
      </div>

      {error && (
        <p className="config-field__error" role="alert">
          {error.message}
        </p>
      )}

      {warning && !error && (
        <p className="config-field__warning" role="status">
          {warning.message}
        </p>
      )}

      {config.validationRules && (
        <p className="config-field__hint">
          {config.validationRules.min !== undefined && config.validationRules.max !== undefined && (
            <span>Range: {String(config.validationRules.min)} - {String(config.validationRules.max)}</span>
          )}
          {Array.isArray(config.validationRules.choices) && (
            <span>Options: {(config.validationRules.choices as string[]).join(', ')}</span>
          )}
        </p>
      )}
    </div>
  );
}

export default function ConfigGroupEditor({
  group,
  pendingChanges,
  onChangeValue,
  validationErrors,
  validationWarnings
}: ConfigGroupEditorProps) {
  // LLM models state for dynamic choices
  const [llmModels, setLlmModels] = useState<string[]>([]);
  const [llmModelsLoading, setLlmModelsLoading] = useState(false);
  const [llmModelsError, setLlmModelsError] = useState<string | null>(null);

  // Check if any key in this group needs LLM models
  const needsLlmModels = useMemo(() => {
    if (!group.keys) return false;
    return group.keys.some(
      key => key.validationRules?.dynamicChoicesSource === 'llm_models'
    );
  }, [group.keys]);

  // Fetch LLM models when needed
  useEffect(() => {
    if (!needsLlmModels) return;

    let cancelled = false;
    const loadModels = async () => {
      setLlmModelsLoading(true);
      setLlmModelsError(null);
      try {
        const models = await fetchLlmModels();
        if (!cancelled) {
          setLlmModels(models ?? []);
        }
      } catch (err) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : 'Failed to load models';
          setLlmModelsError(message);
        }
      } finally {
        if (!cancelled) {
          setLlmModelsLoading(false);
        }
      }
    };
    void loadModels();
    return () => {
      cancelled = true;
    };
  }, [needsLlmModels]);

  // Create maps for quick lookup
  const errorMap = useMemo(
    () => new Map(validationErrors.map(e => [e.key, e])),
    [validationErrors]
  );
  const warningMap = useMemo(
    () => new Map(validationWarnings.map(w => [w.key, w])),
    [validationWarnings]
  );

  // Sort keys: modified first, then alphabetically
  const sortedKeys = useMemo(() => {
    if (!group.keys || !Array.isArray(group.keys)) {
      return [];
    }
    return [...group.keys].sort((a, b) => {
      const aModified = a.key in pendingChanges;
      const bModified = b.key in pendingChanges;
      if (aModified && !bModified) return -1;
      if (!aModified && bModified) return 1;
      const aName = a.displayName || a.key || '';
      const bName = b.displayName || b.key || '';
      return aName.localeCompare(bName);
    });
  }, [group.keys, pendingChanges]);

  // Get dynamic choices for a key based on its source
  const getDynamicChoices = (key: ConfigKeyMetadata) => {
    const source = key.validationRules?.dynamicChoicesSource;
    if (source === 'llm_models') {
      return {
        choices: llmModels,
        loading: llmModelsLoading,
        error: llmModelsError
      };
    }
    return null;
  };

  return (
    <div className="config-group-editor">
      <header className="config-group-editor__header">
        <h3>{group.metadata?.displayName || group.group}</h3>
        <p className="config-group-editor__description">{group.metadata?.description}</p>
      </header>

      <div className="config-group-editor__fields">
        {sortedKeys.map(keyConfig => {
          const currentValue = keyConfig.key in pendingChanges
            ? pendingChanges[keyConfig.key]
            : keyConfig.currentValue;

          const dynamicData = getDynamicChoices(keyConfig);

          return (
            <ConfigKeyField
              key={keyConfig.key}
              config={keyConfig}
              value={currentValue}
              onChange={value => onChangeValue(keyConfig.key, value)}
              error={errorMap.get(keyConfig.key)}
              warning={warningMap.get(keyConfig.key)}
              dynamicChoices={dynamicData?.choices}
              dynamicChoicesLoading={dynamicData?.loading}
              dynamicChoicesError={dynamicData?.error}
            />
          );
        })}
      </div>

      {(!group.keys || group.keys.length === 0) && (
        <p className="config-group-editor__empty">
          No settings available in this group.
        </p>
      )}
    </div>
  );
}
