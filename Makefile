# Default files to check for syntax
CHECK_SYNTAX_FILES ?= plugins/ tests/

# Help target
help:
	@echo "Available targets:"
	@echo "  check_black      - Run black syntax check"
	@echo "  check_flake8     - Run flake8 syntax check"
	@echo "  check_isort      - Run isort syntax check"
	@echo "  fix_black        - Run black to fix formatting"
	@echo "  fix_isort        - Run isort to fix import sorting"
	@echo "  lint_all         - Run all linting checks"
	@echo "  collection-docs  - Generate collection documentation"
	@echo "  collection-lint  - Run ansible-lint on the collection"

## Run black syntax check
check_black:
	tox -e black -- --check $(CHECK_SYNTAX_FILES)

## Run flake8 syntax check
check_flake8:
	tox -e flake8 -- $(CHECK_SYNTAX_FILES)

## Run isort syntax check
check_isort:
	tox -e isort -- --check $(CHECK_SYNTAX_FILES)

## Run black to fix formatting
fix_black:
	tox -e black -- $(CHECK_SYNTAX_FILES)

## Run isort to fix import sorting
fix_isort:
	tox -e isort -- $(CHECK_SYNTAX_FILES)

## Run all linting checks
lint_all: check_black check_flake8 check_isort

## Generate collection documentation
collection-docs:
	ansible-doc --list --type=module ansible_collections.hashicorp.terraform

## Run ansible-lint on the collection
collection-lint:
	ansible-lint

.PHONY: help check_black check_flake8 check_isort fix_black fix_isort lint_all collection-docs collection-lint 