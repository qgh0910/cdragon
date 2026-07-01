.PHONY: check-i18n

check-i18n:
	uv run python scripts/check_i18n_completeness.py
