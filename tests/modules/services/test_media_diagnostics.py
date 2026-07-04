from modules.services.media_diagnostics import count_media_gaps


def test_count_media_gaps_sums_warning_counters() -> None:
    assert count_media_gaps(
        chunks_without_files=2,
        chunks_without_metadata=3,
        files_without_url=5,
        files_without_size=7,
    ) == 17
