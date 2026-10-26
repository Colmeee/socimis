"""Lanza toda la batería sin red: `SOCIMIS_SIN_RED=1 python3 pruebas/correr.py` (lo hace probar.sh)."""
import os
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
os.environ["SOCIMIS_SIN_RED"] = "1"

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.discover(AQUI, pattern="test_*.py")
    r = unittest.TextTestRunner(verbosity=1).run(suite)
    print("%d pruebas, %d mal" % (r.testsRun, len(r.failures) + len(r.errors)))
    sys.exit(0 if r.wasSuccessful() else 1)
