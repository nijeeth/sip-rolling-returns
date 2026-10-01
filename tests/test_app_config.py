"""Settings live in app_config so they are not Streamlit's config module."""

import app_config
import streamlit.config as streamlit_config


def test_settings_module_is_not_streamlit_config():
    assert app_config.__name__ == "app_config"
    assert app_config.__file__.endswith("app_config.py")
    assert app_config.__file__ != streamlit_config.__file__
    # Names app.py imports at startup. A clash with streamlit.config raises
    # ImportError here because that module does not define them.
    assert app_config.DEFAULT_LUMPSUM_AMOUNT == 100_000
    assert app_config.CREATOR_EMAIL == "nijeethfish@gmail.com"
    assert app_config.DEFAULT_SIP_AMOUNT == 10_000
    assert app_config.ROLLING_PERIOD_OPTIONS == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert app_config.MIN_SEARCH_QUERY_LENGTH == 4
    assert app_config.MAX_SEARCH_RESULTS == 30
    assert not hasattr(streamlit_config, "DEFAULT_LUMPSUM_AMOUNT")
