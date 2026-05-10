.PHONY: seed

seed:
	cd backend && uv run python seed.py
