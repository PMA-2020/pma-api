# Developer Documentation
#### `master` [![CircleCI](https://circleci.com/gh/PMA-2020/pma-api/tree/master.svg?style=svg&circle-token=3cd5fffe3dad1d27e6cc1000307bc299e2ef3e77)](https://circleci.com/gh/PMA-2020/pma-api/tree/master) |  `develop` [![CircleCI](https://circleci.com/gh/PMA-2020/pma-api/tree/develop.svg?style=svg&circle-token=3cd5fffe3dad1d27e6cc1000307bc299e2ef3e77)](https://circleci.com/gh/PMA-2020/pma-api/tree/develop)

## Relational Database Diagram
<img src="https://raw.githubusercontent.com/joeflack4/pma-api/develop/pma_api/docs/source/_static/apiClassDiagramV4.png" data-canonical-src="https://raw.githubusercontent.com/joeflack4/pma-api/develop/pma_api/docs/source/_static/apiClassDiagramV4.png" width="620" height="513" />

## Usage, endpoint info, and other user documentation
Extensive user documentation is available at either of the following sites:
- http://api.pma2020.org
- http://api-docs.pma2020.org

## Installation
### System dependencies
- [Python3](https://www.python.org/downloads/)
- SQLite: There are several options. We reccomend [this](https://www.sqlite.org/download.html) for CLI, or [this](https://sqlitebrowser.org/) for GUI.

### Clone the project
1. Change directory to `PATH` where you want to clone: `cd PATH`
2. Clone: `git clone https://github.com/PMA-2020/pma-api.git`

### Virtual environment _(optional, but recommended)_
A Python virtual environment is a way to isolate applications and their dependencies from one another in order to avoid conflicts. We recommend that you install virtualenv. [The virtualenv documentation](https://virtualenv.pypa.io/en/stable/) has installation steps as well as more information about the usefulness of virtual environments. Here's a summary of the installation steps:

1. Install `virtualenv` globally: `python3 -m pip install virtualenv`
2. Change directory to where `pma-api` was cloned: `cd PATH/pma-api`
3. Create a virtual environment called `env`: `virtualenv env`

**IMPORTANT**: If you do not create a virtual environment, makefile commands will not work. To get them to work without a virtual environment, in the makefile you would have to change `PYTHON=./env/bin/python3` to `PYTHON=python3`.

### Install project dependencies
- `python3 -m pip install -r requirements.txt`

### Create the database _(optional)_
1. Create the database via the following `makefile` command: `make db`
_This will execute a script that populates a database using data taken from the `data` directory. In a properly set up staging or production environment, PostgreSQL will be used. In a development environment, SQLite is used. This step is considered optional in a development environment as there should already be an up-to-date `dev.db` in the root directory._
2. Examine database to verify that all looks well. _(optional)_
This can be done via CLI or GUI tool, such as recommended previously.

## Running locally
1. Run `pma-api` on a local server process via the following makefile command: `make serve`
    - _If no virtual environment is set up, run `make serve-no-env` instead, or follow the stepped marked "IMPORTANT" under the "Virtual environment" setup step._
2. Verify that it is running in the browser by going to: `http://localhost:5000/v1/resources`
3. Navigate the API further by either (a) utilizing the URL links shown in the browser, or (b) looking at the available endpoints in the [pma-api documentation](https://www.github.com/PMA-2020/pma-api).
4. Read the [pma-api documentation](https://www.github.com/PMA-2020/pma-api) for more information on use.

## Server management
### Pushing to staging
`make push-staging`

### Pushing to production
`make push-production`
