"""Placeholder functional test ensuring utils.encode_image handles None."""

from src.utils import utils


def test_encode_image_none():
	assert utils.encode_image(None) is None

