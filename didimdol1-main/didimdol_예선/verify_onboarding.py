"""이전 테스트 명령의 호환성 유지: python verify_onboarding.py"""
from verify_lpa import LpaTests, DatabaseTests  # noqa: F401
import unittest

if __name__ == '__main__':
    unittest.main(verbosity=2)
