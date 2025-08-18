"""Test JSON related utilities: none present, so basic encode_image coverage."""

from src.utils.utils import encode_image


def test_encode_image_invalid_path(tmp_path):
	# Provide a non-existent path -> expect exception handled by caller; encode_image itself will raise FileNotFoundError
	p = tmp_path / "nope.png"
	try:
		encode_image(str(p))
	except FileNotFoundError:
		# Acceptable outcome
		return
	else:  # pragma: no cover - unlikely branch
		assert False, "Expected FileNotFoundError for missing file"

