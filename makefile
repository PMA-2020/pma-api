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

DEV_SERVE=gunicorn --bind 0.0.0.0:5000 run:app \
	--access-logfile logs/access-logfile.log \
	--error-logfile logs/error-logfile.log \
	--capture-output \
	--pythonpath python3

.PHONY: lint linttest lintall pylint pylinttest pylintall code codetest codeall doc doctest docall test testdoc serve shell db translations production staging gunicorn tags ltags serve-dev serve-production

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

shell:
	${MANAGE} shell

db:
	${MANAGE} initdb --overwrite

db-production:
	python3 manage.py initdb --overwrite

translations:
	${MANAGE} initdb --translations

production:  # connects to server
	heroku run bash --app pma-api

staging:  # connects to server
	heroku run bash --app pma-api-staging

production-push:
	git checkout production && git push trunk production
	
staging-push:
	git checkout staging && git push trunk staging --force

push-production: production-push

push-staging: staging-push

serve-production:
	gunicorn run:app

serve-dev:
	${DEV_SERVE}

# CTAGS
tags:
	ctags -R --python-kinds=-i .

ltags:
	ctags -R --python-kinds=-i ./${CODE_SRC}
