"""Test simple splitting logic used for BYKILT_BROWSER_ARGS env in patches."""


def test_pipe_args_split():
	raw = "--a|--b|--c=1"
	assert raw.split("|") == ["--a", "--b", "--c=1"]

