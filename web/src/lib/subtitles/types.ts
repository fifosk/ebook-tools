export interface SubtitleTrack {
  url: string;
  label?: string;
  kind?: string;
  language?: string;
  format?: string;
}

export interface CueVisibility {
  original: boolean;
  transliteration: boolean;
  translation: boolean;
}
