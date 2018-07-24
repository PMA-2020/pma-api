PYTHON=./env/bin/python3
SRC=./pma_api/
TEST=./test/

PYLINT=${PYTHON} -m pylint --output-format=colorized --reports=n
PYCODESTYLE=${PYTHON} -m pycodestyle
PYDOCSTYLE=${PYTHON} -m pydocstyle

LINT_SRC=${PYLINT} ${SRC}
LINT_TEST=${PYLINT} ${TEST}

CODE_SRC=${PYCODESTYLE} ${SRC}
CODE_TEST=${PYCODESTYLE} ${TEST}

DOC_SRC=${PYDOCSTYLE} ${SRC}
DOC_TEST=${PYDOCSTYLE} ${TEST}

MANAGE=${PYTHON} manage.py

.PHONY: lint linttest lintall pylint pylinttest pylintall code codetest \
codeall doc doctest docall test testdoc serve shell db translations \
production staging gunicorn tags ltags serve-dev serve-production \
serve-dev-network-accessible circleci-validate-config install-redis-osx \
redis-osx-install start-redis redis-start build-docs open-docs create-docs \
docs-create docs-build typical-sphinx-setup setup-docs docs-push push-docs \
docs setup-docs-no-open build-docs-no-open docs-push-production \
docs-push-staging serve-dev-network-accessible circleci-validate-config logs logs-staging

# ALL LINTING
lint:
	${LINT_SRC} && ${CODE_SRC} && ${DOC_SRC}

linttest:
	${LINT_TEST} && ${CODE_TEST} && ${DOC_TEST}

lintall: lint linttest


# PYLINT
pylint:
	${LINT_SRC}

pylinttest:
	${LINT_TEST}

pylintall: pylint pylinttest

# PYCODESTYLE
code:
	${CODE_SRC}

codetest:
	${CODE_TEST}

codeall: code codetest


# PYDOCSTYLE
doc:
	${DOC_SRC}

doctest:
	${DOC_TEST}

docall: doc doctest


# TESTING
test:
	${PYTHON} -m unittest discover -v

testdoc:
	${PYTHON} -m test.test --doctests-only


# DB & SERVER MANAGEMENT
serve:
	${MANAGE} runserver

serve-dev: serve

serve-dev-network-accessible:
	gunicorn --bind 0.0.0.0:5000 run:app \
	--access-logfile logs/access-logfile.log \
	--error-logfile logs/error-logfile.log \
	--capture-output \
	--pythonpath python3

serve-production:
	gunicorn run:app

shell:
	${MANAGE} shell

db:
	${MANAGE} initdb --overwrite

db-production:
	python3 manage.py initdb --overwrite

translations:
	${MANAGE} initdb --translations

production:  # connects to server shell
	heroku run bash --app pma-api

staging:  # connects to server shell
	heroku run bash --app pma-api-staging

production-push:
	git status && \
	printf "\nGit status should have reported 'nothing to commit, working tree\
	 clean'. Otherwise you should cancel this command, make sure changes are\
	  committed, and run it again.\n\n" && \
	git checkout master && \
	git branch -D production && \
	git checkout -b production && \
	git push -u trunk production --force && \
	git branch -D NULL && \
	git checkout develop && \
	git checkout -b NULL && \
	clear && \
	git status && \
	git branch
	
staging-push:
	git status && \
	printf "\nGit status should have reported 'nothing to commit, working \
	tree clean'. Otherwise you should cancel this command, make sure changes \
	are committed, and run it again.\n\n" && \
	git checkout develop && \
	git branch -D staging && \
	git checkout -b staging && \
	git push -u trunk staging --force && \
	git branch -D NULL && \
	git checkout develop && \
	git checkout -b NULL && \
	clear && \
	git status && \
	git branch

logs:
	heroku logs --app ppp-web

logs-staging:
	heroku logs --app ppp-web-staging

push-production: production-push

push-staging: staging-push

push-docs: docs-push


# DEVOPS
circleci-validate-config:
	echo Make sure that Docker is running, or this command will fail. && \
	circleci config validate

# Docs
typical-sphinx-setup:
	sphinx-quickstart

open-docs:
	open pma_api/docs/build/html/index.html

readme-to-docs:
	cp README.md pma_api/docs/source/content/developers/for_developers.md

# About Sphinx API-Doc
# usage: sphinx-apidoc [OPTIONS] -o <OUTPUT_PATH> <MODULE_PATH> [EXCLUDE_PATTERN, ...]
#
# Look recursively in <MODULE_PATH> for Python modules and packages and create
# one reST file with automodule directives per package in the <OUTPUT_PATH>. The
# <EXCLUDE_PATTERN>s can be file and/or directory patterns that will be excluded
# from generation. Note: By default this script will not overwrite already
# created files.
#  -f, --force           overwrite existing files
#  -o DESTDIR, --output-dir DESTDIR directory to place all output
#
# I replaced this command: (cd pma_api/docs && sphinx-apidoc -f -o source/ ../pma_api/ && \

build-docs-no-open:
	rm -rf pma_api/docs/build/ && \
	make readme-to-docs && \
	(cd pma_api/docs && \
	sphinx-apidoc -f -o source/ .. && \
	make html) && \
	printf "\nAbout WARNINGs\nNot all warnings should be ignored, but you can ignore the following.\n- pma_api.rst not being in a toctree.\n<autoflask>:1: WARNING: duplicate label...\n\n"

build-docs:
	make build-docs-no-open && \
	make open-docs

#docs-push-production:
#	make setup-docs && \
#	aws s3 sync pma_api/docs/build/html s3://api-docs.pma2020.org --region us-west-2 --profile work

docs-push-production:
	aws s3 sync pma_api/docs/build/html s3://api-docs.pma2020.org --region us-west-2 --profile work

docs-push-staging:
	aws s3 sync pma_api/docs/build/html s3://api-docs-staging.pma2020.org --region us-west-2 --profile work

docs-push:
	make docs-push-staging && \
	make docs-push-production

create-docs: build-docs
docs-create: build-docs
docs-build: build-docs
docs: build-docs

# CTAGS
tags:
	ctags -R --python-kinds=-i .

ltags:
	ctags -R --python-kinds=-i ./${CODE_SRC}
