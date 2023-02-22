help:
	@echo "Available targets:\n\
		lint  - run code formatters and linters\n\
		docs  - generate documentation site\n\
		dist  - generate release archives\n\
	\n\
	Remember to 'mamba activate pyimagej-dev' first!"

check:
	@bin/check.sh

lint: check
	bin/lint.sh

docs: check
	cd doc && $(MAKE) html; cd ..

dist: check clean
	python -m build

.PHONY: tests
