.PHONY: dev clean

# Development setup with system site-packages (for PyGObject/GTK access)
dev:
	rm -rf .venv
	python3 -m venv .venv --system-site-packages
	.venv/bin/pip install --upgrade pip -q
	.venv/bin/pip install -e . -q
	@echo ""
	@echo "✓ Dev environment ready!"
	@echo "  Run: source .venv/bin/activate"

# Clean up
clean:
	rm -rf .venv
	rm -rf *.egg-info
	rm -rf __pycache__ lisn/__pycache__ tests/__pycache__
	@echo "✓ Cleaned"
