export function normalizeDiscoveryPolicyNotes(
  policyNotes: readonly string[] | null | undefined
): string[] {
  return (policyNotes ?? []).reduce<string[]>((notes, rawNote) => {
    const note = rawNote.trim();
    if (note && !notes.includes(note)) {
      notes.push(note);
    }
    return notes;
  }, []);
}
