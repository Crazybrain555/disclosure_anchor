"""Unit tests for domain value objects (ContentHash, ProviderRef)."""

import unittest

from disclosure_anchor.domain.value_objects.common import ContentHash, ProviderRef


class ContentHashTests(unittest.TestCase):
    def test_parse_lowercases_digest_and_round_trips(self) -> None:
        digest = "A" * 64
        parsed = ContentHash.parse(f"sha256:{digest}")
        self.assertEqual(parsed.algorithm, "sha256")
        self.assertEqual(parsed.digest, digest.lower())
        self.assertEqual(str(parsed), f"sha256:{digest.lower()}")

    def test_parse_requires_algorithm_separator(self) -> None:
        with self.assertRaises(ValueError):
            ContentHash.parse("a" * 64)

    def test_only_sha256_is_supported(self) -> None:
        with self.assertRaises(ValueError):
            ContentHash(algorithm="md5", digest="a" * 32)

    def test_digest_is_required(self) -> None:
        with self.assertRaises(ValueError):
            ContentHash(algorithm="sha256", digest="")


class ProviderRefTests(unittest.TestCase):
    def test_accepts_populated_fields(self) -> None:
        ref = ProviderRef(provider="cninfo", provider_document_id="1225087169")
        self.assertEqual(ref.provider, "cninfo")
        self.assertEqual(ref.provider_document_id, "1225087169")

    def test_provider_is_required(self) -> None:
        with self.assertRaises(ValueError):
            ProviderRef(provider="", provider_document_id="1225087169")

    def test_provider_document_id_is_required(self) -> None:
        with self.assertRaises(ValueError):
            ProviderRef(provider="cninfo", provider_document_id="")


if __name__ == "__main__":
    unittest.main()
