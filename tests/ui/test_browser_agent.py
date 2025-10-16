import types
from unittest import mock

import pytest

from src.ui import browser_agent


class _DummyContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _DummyButton:
    def __init__(self):
        self.click_args = []

    def click(self, **kwargs):
        self.click_args.append(kwargs)


class _DummyState:
    def __init__(self, value):
        self.value = value


@pytest.fixture(autouse=True)
def patch_gradio(monkeypatch):
    fake_block = _DummyContext()
    fake_box = _DummyContext()
    fake_row = _DummyContext()
    buttons = []

    monkeypatch.setattr(browser_agent, "gr", mock.Mock(), raising=False)
    browser_agent.gr.Blocks.return_value = fake_block
    browser_agent.gr.Box.return_value = fake_box
    browser_agent.gr.Row.return_value = fake_row

    def button_factory(*args, **kwargs):
        button = _DummyButton()
        buttons.append(button)
        return button

    browser_agent.gr.Button.side_effect = button_factory
    browser_agent.gr.Markdown.side_effect = lambda *args, **kwargs: None
    browser_agent.gr.State.side_effect = lambda value=None: _DummyState(value)

    yield buttons

    browser_agent.gr.reset_mock()


def test_chrome_restart_dialog_wires_callable_callbacks(patch_gradio):
    buttons = patch_gradio

    dialog = browser_agent.chrome_restart_dialog()

    assert dialog is not None
    assert len(buttons) == 2

    yes_click = buttons[0].click_args[0]
    no_click = buttons[1].click_args[0]

    assert callable(yes_click["fn"])
    assert callable(no_click["fn"])
    assert yes_click["fn"]() == "yes"
    assert no_click["fn"]() == "no"
