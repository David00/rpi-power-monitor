import pytest


def f():
    raise SystemExit(1)

def test_mytest():
    with pytest.raises(SystemExit):
        f()