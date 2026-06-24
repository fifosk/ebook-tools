type PlayerPanelSentenceJumpDatalistProps = {
  id: string;
  suggestions: number[];
};

export function PlayerPanelSentenceJumpDatalist({
  id,
  suggestions,
}: PlayerPanelSentenceJumpDatalistProps) {
  if (suggestions.length === 0) {
    return null;
  }

  return (
    <datalist id={id}>
      {suggestions.map((value) => (
        <option key={value} value={value} />
      ))}
    </datalist>
  );
}
