"""ENGINE-001 V19 fixed-source loss audit synthetic regressions."""
import hashlib
import tempfile
import unittest
from pathlib import Path
import zipfile
import numpy as np
from PIL import Image

from run_engine001_anilines_v19_audit import (
    SOURCE_SHA, B_SHA, missed_components, frozen_b, pinned, analyze,
)


class V19AuditTests(unittest.TestCase):
    def test_component_bins_and_deterministic_order(self):
        mask=np.zeros((320,200),dtype=bool)
        mask[10,10]=True
        mask[20,20:22]=True
        mask[50,30:33]=True
        mask[70,70:75]=True
        groups,top,amount=missed_components(mask)
        self.assertEqual(amount,4)
        self.assertEqual(groups,{"1":1,"2":1,"3-4":1,"5-9":1,"10+":0})
        self.assertEqual(top[0]["pixels"],5)

    def test_blank_components_are_valid_zero(self):
        groups,top,n=missed_components(np.zeros((320,200),dtype=bool))
        self.assertEqual(n,0)
        self.assertEqual(sum(groups.values()),0)
        self.assertEqual(top,[])

    def test_wrong_pin_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"source.png"
            Image.fromarray(np.zeros((320,200,3),np.uint8)).save(p)
            with self.assertRaises(ValueError):
                pinned(p,SOURCE_SHA)
            with self.assertRaises(ValueError):
                frozen_b(p)

    def test_required_v18_sha_bindings(self):
        self.assertEqual(B_SHA["B-source-path-mask.png"],
                         "99647975bcc6437a0180626ba967ea72cc588bebebb2b363ef08f6a068fb1235")
        self.assertEqual(B_SHA["B-paths.json"],
                         "752dbc5ff55e90b0d38f492fadfde9be8811b70ebc66bce4999f716c4a86ed57")

    def test_repo_pinned_source(self):
        source=Path(__file__).resolve().parents[1]/"testImages"/"wV6VeZI9S1Y.png"
        self.assertEqual(source.stat().st_size,97308)
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),SOURCE_SHA)


if __name__=="__main__":
    unittest.main()
