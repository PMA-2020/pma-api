SRC=./pma_api/
TEST=./test/

PYLINT=python3 -m pylint --output-format=colorized --reports=n
PYCODESTYLE=python3 -m pycodestyle
PYDOCSTYLE=python3 -m pydocstyle

LINT_SRC=${PYLINT} ${SRC}
LINT_TEST=${PYLINT} ${TEST}

CODE_SRC=${PYCODESTYLE} ${SRC}
CODE_TEST=${PYCODESTYLE} ${TEST}

DOC_SRC=${PYDOCSTYLE} ${SRC}
DOC_TEST=${PYDOCSTYLE} ${TEST}

.PHONY: lint linttest lintall pylint pylinttest pylintall code codetest \
codeall doc doctest docall test testdoc serve shell db translations \
production staging tags ltags serve-dev serve-production \
serve-dev-network-accessible circleci-validate-config install-redis-osx \
redis-osx-install start-redis redis-start build-docs open-docs create-docs \
docs-create docs-build typical-sphinx-setup setup-docs docs-push push-docs \
docs setup-docs-no-open build-docs-no-open docs-push-production \
docs-push-staging serve-dev-network-accessible circleci-validate-config logs \
logs-staging virtualenv-make virtualenvwrapper-make virtualenv-activate \
virtualenvwrapper-activate deactivate virtualenv-deactivate connect-staging \
virtualenvwrapper-deactivate restore restore-test backup % connect-production \
migrate_db migrate upgrade_db upgrade list-backups list list-api-data \
list-datasets list-ui-data backup-source-files

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
	python3 -m unittest discover -v
test-dataset:
	python -m test.test_dataset
testdoc:
	python3 -m test.test --doctests-only

# VIRTUAL ENVIRONMENTS
virtualenv-make:
	virtualenv env
virtualenvwrapper-make:
	mkvirtualenv pma-api
virtualenv-activate:
	source ./env/bin/activate
virtualenvwrapper-activate:
	workon pma-api
deactivate:
	deactivate
virtualenv-deactivate: deactivate
virtualenvwrapper-deactivate: deactivate

# DB
db:
	python3 manage.py initdb --overwrite
db-production: db
translations:
	python3 manage.py initdb --translations
migrate_db:
	@python3 manage.py db migrate
	@echo
	@echo Please follow up this command by checking the file just created in \
	the migrations/versions directory.
	@echo
	@echo From the documentation:
	@echo The migration script needs to be reviewed and edited, as Alembic \
	currently does not detect every change you make to your models. In \
	particular, Alembic is currently unable to detect table name changes, \
	column name changes, or anonymously named constraints. A detailed summary \
	of limitations can be found in the Alembic autogenerate documentation. \
	Once finalized, the migration script also needs to be added to version \
	control.
	@echo https://flask-migrate.readthedocs.io/en/latest/
migrate: migrate_db
upgrade_db:
	@python3 manage.py db upgrade
upgrade: upgrade_db
list-ui-data:
	@python3 manage.py list_ui_data
list-datasets:
	@python3 manage.py list_datasets
list-api-data: list-datasets
list:
	@echo Backups:
	@make list-backups
	@echo
	@echo Datasets:
	@make list-datasets
	@echo
	@echo UI Data:
	@make list-ui-data

# Serve / Deploy
serve:
	python3 manage.py runserver
serve-dev: serve
serve-dev-network-accessible:
	gunicorn --bind 0.0.0.0:5000 run:app \
	--access-logfile logs/access-logfile.log \
	--error-logfile logs/error-logfile.log \
	--capture-output \
	--pythonpath python3
# serve-production: D="run in background, p="path to save file w/ process ID"
# TODO: pass the port explicitly
serve-production:
	gunicorn run:app -D -p pma-api_process-id.pid
connect-production:
	heroku run bash --app pma-api
connect-staging:
	heroku run bash --app pma-api-staging
production-push:
	git status
	printf "\nGit status should have reported 'nothing to commit, working tree\
	 clean'. Otherwise you should cancel this command, make sure changes are\
	  committed, and run it again.\n\n"
	git checkout master
	git branch -D production
	git checkout -b production
	git push -u trunk production --force
	git branch -D NULL
	git checkout develop
	git checkout -b NULL
	clear
	git status
	git branch
staging-push:
	git status
	printf "\nGit status should have reported 'nothing to commit, working \
	tree clean'. Otherwise you should cancel this command, make sure changes \
	are committed, and run it again.\n\n"
	git checkout develop
	git branch -D staging
	git checkout -b staging
	git push -u trunk staging --force
	git branch -D NULL
	git checkout develop
	git checkout -b NULL
	clear
	git status
	git branch
logs:
	heroku logs --app ppp-web
logs-staging:
	heroku logs --app ppp-web-staging
push-production: production-push
push-staging: staging-push
production:  push-production
staging:  push-staging
push-docs: docs-push
redis:
	sh scripts/run-redis.sh

# DEVOPS
circleci-validate-config:
	echo Make sure that Docker is running, or this command will fail.
	circleci config validate

# Docs
# About Sphinx API-Doc
# usage: sphinx-apidoc [OPTIONS] -o <OUTPUT_PATH> <MODULE_PATH>
# [EXCLUDE_PATTERN, ...]
#
# Look recursively in <MODULE_PATH> for Python modules and packages and create
# one reST file with automodule directives per package in the <OUTPUT_PATH>.
# The <EXCLUDE_PATTERN>s can be file and/or directory patterns that will be
# excluded from generation. Note: By default this script will not overwrite
# already created files.
#  -f, --force           overwrite existing files
#  -o DESTDIR, --output-dir DESTDIR directory to place all output
#
# I replaced this command: (cd pma_api/docs && sphinx-apidoc -f -o source/
# ../pma_api/

typical-sphinx-setup:
	sphinx-quickstart
open-docs:
	open pma_api/docs/build/html/index.html
readme-to-docs:
	cp README.md pma_api/docs/source/content/developers/for_developers.md
build-docs-no-open:
	rm -rf pma_api/docslocal/build/
	make readme-to-docs
	(cd pma_api/docs
	sphinx-apidoc -f -o source/ ..
	make html)
	printf "\nAbout WARNINGs\nNot all warnings should be ignored, but you can
	ignore the following.\n- pma_api.rst not being in a toctree.\n<autoflask>
	:1: WARNING: duplicate label...\n\n"
build-docs:
	make build-docs-no-open
	make open-docs

docs-push-production:
	aws s3 sync pma_api/docs/build/html s3://api-docs.pma2020.org \
	--region us-west-2 --profile work
#docs-push-production:
#	make setup-docs
#	aws s3 sync pma_api/docs/build/html s3://api-docs.pma2020.org
# --region us-west-2 --profile work
docs-push-staging:
	aws s3 sync pma_api/docs/build/html s3://api-docs-staging.pma2020.org \
	--region us-west-2 --profile work
docs-push:
	make docs-push-staging
	make docs-push-production
create-docs: build-docs
docs-create: build-docs
docs-build: build-docs
docs: build-docs

# Text editors / CTAGS
tags:
	ctags -R --python-kinds=-i .
ltags:
	ctags -R --python-kinds=-i ./${CODE_SRC}

# Manage / Troubleshoot
shell:
	python3 manage.py shell

# Backup
backup-source-files:
	@python3 manage.py backup_source_files
backup:
	@python3 manage.py backup
	@make backup-source-files
restore-test:
	python manage.py restore --path=\
	data/db_backups/pma-api-backup_2019-01-28_16-51-43.130543.dump
restore:
	@echo Please run the following command:
	@echo python3 manage.py restore --path=PATH/TO/BACKUP
list-backups:
	@python3 manage.py list_backups

# Task ques
celery:
	celery worker --app=pma_api.tasks.celery --loglevel=info
