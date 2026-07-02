import { DEFAULT_LANGUAGE_FLAG, resolveLanguageFlag } from '../../constants/languageCodes';
import { normalizeLanguageLabel } from '../../utils/languages';
import EmojiIcon from '../EmojiIcon';
import styles from '../LibraryList.module.css';

type LibraryLanguageLabelProps = {
  language: string | null | undefined;
};

export function LibraryLanguageLabel({ language }: LibraryLanguageLabelProps) {
  const label = normalizeLanguageLabel(language) || 'Unknown';
  const flag = resolveLanguageFlag(language ?? label) ?? DEFAULT_LANGUAGE_FLAG;
  return (
    <span className={styles.languageLabel}>
      <EmojiIcon emoji={flag} className={styles.languageFlag} />
      <span>{label}</span>
    </span>
  );
}
