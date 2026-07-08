.PHONY: check-i18n check-backend-i18n check-frontend-i18n

check-backend-i18n:
	uv run python scripts/check_i18n_completeness.py

check-frontend-i18n:
	uv run python scripts/check_frontend_i18n.py

check-i18n: check-backend-i18n check-frontend-i18n
