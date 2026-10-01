import unittest
from dataclasses import FrozenInstanceError

from tenant_crm import InvalidInput, TenantContext


class TenantContextTests(unittest.TestCase):
    def test_rejects_invalid_tenant_identifiers(self):
        for value in (None, 42, True, "", " ", " alpha", "alpha ",
                      "a' OR 1=1--", "tenant/other", "A", "a" * 65):
            with self.subTest(value=value):
                with self.assertRaises(InvalidInput):
                    TenantContext(value)

    def test_accepts_separate_immutable_contexts(self):
        alpha = TenantContext("alpha")
        self.assertEqual(alpha.tenant_id, "alpha")
        self.assertNotEqual(alpha, TenantContext("beta"))
        with self.assertRaises(FrozenInstanceError):
            alpha.tenant_id = "beta"


if __name__ == "__main__":
    unittest.main()
