"""Test that memory optimization args env variable style is parsable."""


def test_browser_args_split():
	env_value = "--disable-gpu|--single-process|--flag=1"
	parsed = [p for p in env_value.split("|") if p]
	assert parsed == ["--disable-gpu", "--single-process", "--flag=1"]

