import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { PlayerPanelSentenceJumpDatalist } from '../player-panel/PlayerPanelSentenceJumpDatalist';

describe('PlayerPanelSentenceJumpDatalist', () => {
  it('renders sentence suggestions for the shared jump input list', () => {
    const { container } = render(
      <PlayerPanelSentenceJumpDatalist id="sentence-list" suggestions={[1, 7, 42]} />,
    );

    const datalist = container.querySelector('datalist');
    const options = Array.from(container.querySelectorAll('option'));

    expect(datalist).toHaveAttribute('id', 'sentence-list');
    expect(options.map((option) => option.getAttribute('value'))).toEqual(['1', '7', '42']);
  });

  it('renders nothing when there are no suggestions', () => {
    const { container } = render(<PlayerPanelSentenceJumpDatalist id="sentence-list" suggestions={[]} />);

    expect(container).toBeEmptyDOMElement();
  });
});
