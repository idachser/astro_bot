from datetime import datetime, timezone

from astro_bot.services import digest_state


SLOT = datetime(2026, 8, 8, 9, tzinfo=timezone.utc)


class TestDigestMarker:
    def test_round_trips_the_slot(self, tmp_path) -> None:
        path = str(tmp_path / "last_digest")
        digest_state.record_slot(SLOT, path)

        assert digest_state.read_last_slot(path) == SLOT

    def test_keeps_the_timezone(self, tmp_path) -> None:
        # compared against slots the scheduler builds as aware UTC; a
        # naive read back would never match and every restart would
        # re-broadcast
        path = str(tmp_path / "last_digest")
        digest_state.record_slot(SLOT, path)

        assert digest_state.read_last_slot(path).tzinfo is not None

    def test_missing_file_is_no_record(self, tmp_path) -> None:
        # first run on a fresh volume
        path = str(tmp_path / "never_written")

        assert digest_state.read_last_slot(path) is None

    def test_unreadable_content_is_no_record(self, tmp_path) -> None:
        # a torn write costs one duplicate, never a crash: this runs
        # inside the scheduler, the bot's only broadcaster
        path = tmp_path / "last_digest"
        path.write_text("2026-08-0")

        assert digest_state.read_last_slot(str(path)) is None

    def test_recording_into_a_missing_directory_does_not_raise(
        self, tmp_path
    ) -> None:
        path = str(tmp_path / "absent" / "last_digest")

        digest_state.record_slot(SLOT, path)  # logged, not raised

        assert digest_state.read_last_slot(path) is None

    def test_overwrites_the_previous_slot(self, tmp_path) -> None:
        path = str(tmp_path / "last_digest")
        digest_state.record_slot(SLOT, path)
        later = datetime(2026, 8, 15, 9, tzinfo=timezone.utc)
        digest_state.record_slot(later, path)

        assert digest_state.read_last_slot(path) == later
