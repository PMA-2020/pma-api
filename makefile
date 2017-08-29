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


.PHONY: lint linttest lintall pylint pylinttest pylintall code codetest codeall doc doctest docall test testdoc serve shell db ssh ssh_production production ssh_staging staging

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


# SERVER MANAGEMENT
serve:
	${MANAGE} runserver

shell:
	${MANAGE} shell

db:
	${MANAGE} initdb --overwrite

ssh:
	heroku run bash --app pma-api
ssh_production: ssh
production: ssh

ssh_staging:
	heroku run bash --app pma-api-staging
staging: ssh_staging

gunicorn:
	gunicorn run:app
