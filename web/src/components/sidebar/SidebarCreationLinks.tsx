import type { SelectedView } from '../../App';
import { isPipelineView } from './sidebarUtils';

interface SidebarCreationLinksProps {
  selectedView: SelectedView;
  onSelectView: (view: SelectedView) => void;
  createBookView: SelectedView;
  subtitlesView: SelectedView;
  youtubeSubtitlesView: SelectedView;
  youtubeDubView: SelectedView;
}

export function SidebarCreationLinks({
  selectedView,
  onSelectView,
  createBookView,
  subtitlesView,
  youtubeSubtitlesView,
  youtubeDubView
}: SidebarCreationLinksProps) {
  const isAddBookActive = isPipelineView(selectedView);

  return (
    <>
      <details className="sidebar__section" open>
        <summary>🎧 Audiobooks</summary>
        <ul className="sidebar__list">
          <li>
            <button
              type="button"
              className={`sidebar__link ${isAddBookActive ? 'is-active' : ''}`}
              onClick={() => onSelectView('pipeline:source')}
            >
              📚 Book Page
            </button>
          </li>
          <li>
            <button
              type="button"
              className={`sidebar__link ${selectedView === createBookView ? 'is-active' : ''}`}
              onClick={() => onSelectView(createBookView)}
            >
              📝 Create Audiobook
            </button>
          </li>
        </ul>
      </details>
      <details className="sidebar__section" open>
        <summary>📺 Videos</summary>
        <ul className="sidebar__list">
          <li>
            <button
              type="button"
              className={`sidebar__link ${selectedView === subtitlesView ? 'is-active' : ''}`}
              onClick={() => onSelectView(subtitlesView)}
            >
              🎞️ Subtitles
            </button>
          </li>
          <li>
            <button
              type="button"
              className={`sidebar__link ${selectedView === youtubeSubtitlesView ? 'is-active' : ''}`}
              onClick={() => onSelectView(youtubeSubtitlesView)}
            >
              📺 YouTube Video
            </button>
          </li>
          <li>
            <button
              type="button"
              className={`sidebar__link ${selectedView === youtubeDubView ? 'is-active' : ''}`}
              onClick={() => onSelectView(youtubeDubView)}
            >
              🎙️ Dub Video
            </button>
          </li>
        </ul>
      </details>
    </>
  );
}
