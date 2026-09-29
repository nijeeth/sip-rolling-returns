"""Settings live in app_config so they are not Streamlit's config module."""

import app_config
import streamlit.config as streamlit_config


def test_settings_module_is_not_streamlit_config():
    assert app_config.__name__ == "app_config"
    assert app_config.__file__.endswith("app_config.py")
    assert app_config.__file__ != streamlit_config.__file__
    # Names app.py imports at startup. A clash with streamlit.config raises
    # ImportError here because that module does not define them.
    assert app_config.DEFAULT_LUMPSUM_AMOUNT == 10_000
    assert app_config.CREATOR_EMAIL == "nijeethfish@gmail.com"
    assert app_config.DEFAULT_SIP_AMOUNT == 1000
    assert not hasattr(streamlit_config, "DEFAULT_LUMPSUM_AMOUNT")
