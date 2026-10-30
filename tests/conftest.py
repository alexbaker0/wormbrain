import pytest

from wormbrain.connectome import build_connectome, load_config
from wormbrain.data import load_raw

CONFIG = "configs/connectome.yaml"


@pytest.fixture(scope="session")
def raw():
    return load_raw()


@pytest.fixture(scope="session")
def conn(raw):
    return build_connectome(load_config(CONFIG), raw)
