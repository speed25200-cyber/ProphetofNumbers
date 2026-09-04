import tempfile
import unittest
import zipfile
from pathlib import Path

import campaign_snapshot


class CampaignSnapshotTests(unittest.TestCase):
    def test_round_trip_preserves_verified_empty_campaign(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            campaign = root / "campaign"
            campaign.mkdir()
            (campaign / "private-note.txt").write_text("checkpoint\n")
            snapshot = root / "campaign.zip"
            created = campaign_snapshot.create_snapshot(campaign, snapshot)
            restored = root / "restored"
            extracted = campaign_snapshot.extract_snapshot(snapshot, restored)
            self.assertEqual((restored / "private-note.txt").read_text(), "checkpoint\n")
            self.assertEqual(created["archive_sha256"], extracted["archive_sha256"])
            self.assertEqual(created["verified_draws"], 0)

    def test_snapshot_is_immutable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            campaign = root / "campaign"
            campaign.mkdir()
            snapshot = root / "campaign.zip"
            campaign_snapshot.create_snapshot(campaign, snapshot)
            before = snapshot.read_bytes()
            with self.assertRaisesRegex(campaign_snapshot.SnapshotError, "overwrite"):
                campaign_snapshot.create_snapshot(campaign, snapshot)
            self.assertEqual(snapshot.read_bytes(), before)

    def test_unlisted_or_traversal_member_is_rejected(self):
        for name in ("extra.txt", "../escape.txt"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                campaign = root / "campaign"
                campaign.mkdir()
                snapshot = root / "campaign.zip"
                campaign_snapshot.create_snapshot(campaign, snapshot)
                changed = root / "changed.zip"
                with zipfile.ZipFile(snapshot) as source, zipfile.ZipFile(changed, "w") as target:
                    for info in source.infolist():
                        target.writestr(info, source.read(info.filename))
                    target.writestr(name, b"bad")
                with self.assertRaises(campaign_snapshot.SnapshotError):
                    campaign_snapshot.verify_snapshot(changed)

    def test_changed_member_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            campaign = root / "campaign"
            campaign.mkdir()
            (campaign / "value.txt").write_text("one")
            snapshot = root / "campaign.zip"
            campaign_snapshot.create_snapshot(campaign, snapshot)
            changed = root / "changed.zip"
            with zipfile.ZipFile(snapshot) as source, zipfile.ZipFile(changed, "w") as target:
                for info in source.infolist():
                    data = b"two" if info.filename == "value.txt" else source.read(info.filename)
                    target.writestr(info, data)
            with self.assertRaisesRegex(campaign_snapshot.SnapshotError, "hash/length"):
                campaign_snapshot.verify_snapshot(changed)

    def test_manifest_with_duplicate_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "bad.zip"
            manifest = {
                "schema": campaign_snapshot.SCHEMA,
                "version": campaign_snapshot.VERSION,
                "campaign_status": {},
                "files": [
                    {"path": "x", "bytes": 0, "sha256": campaign_snapshot.sha256(b""), "mode": 0o600},
                    {"path": "x", "bytes": 0, "sha256": campaign_snapshot.sha256(b""), "mode": 0o600},
                ],
            }
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(
                    campaign_snapshot.MANIFEST_NAME,
                    campaign_snapshot.canonical_bytes(manifest) + b"\n",
                )
                archive.writestr("x", b"")
            with self.assertRaisesRegex(campaign_snapshot.SnapshotError, "duplicate path"):
                campaign_snapshot.verify_snapshot(path)

    def test_snapshot_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            campaign = root / "campaign"
            campaign.mkdir()
            snapshot = root / "campaign.zip"
            campaign_snapshot.create_snapshot(campaign, snapshot)
            link = root / "linked.zip"
            link.symlink_to(snapshot)
            with self.assertRaisesRegex(campaign_snapshot.SnapshotError, "regular file"):
                campaign_snapshot.verify_snapshot(link)

    def test_symlinked_campaign_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            campaign = root / "campaign"
            campaign.mkdir()
            link = root / "linked-campaign"
            link.symlink_to(campaign, target_is_directory=True)
            with self.assertRaisesRegex(campaign_snapshot.SnapshotError, "must not"):
                campaign_snapshot.create_snapshot(link, root / "campaign.zip")


if __name__ == "__main__":
    unittest.main()
