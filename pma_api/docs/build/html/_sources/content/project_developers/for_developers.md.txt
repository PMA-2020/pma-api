# Developer Documentation
#### `master` [![CircleCI](https://circleci.com/gh/PMA-2020/pma-api/tree/master.svg?style=svg&circle-token=3cd5fffe3dad1d27e6cc1000307bc299e2ef3e77)](https://circleci.com/gh/PMA-2020/pma-api/tree/master) |  `develop` [![CircleCI](https://circleci.com/gh/PMA-2020/pma-api/tree/develop.svg?style=svg&circle-token=3cd5fffe3dad1d27e6cc1000307bc299e2ef3e77)](https://circleci.com/gh/PMA-2020/pma-api/tree/develop)

<!--
// We should uncomment this when it is up-to-date.
## Relational Database Diagram
<img src="https://raw.githubusercontent.com/joeflack4/pma-api/develop/pma_api/docs/source/_static/apiClassDiagramV4.png" data-canonical-src="https://raw.githubusercontent.com/joeflack4/pma-api/develop/pma_api/docs/source/_static/apiClassDiagramV4.png" width="620" height="513" />
-->

## Usage, endpoint info, and other user documentation
Extensive user documentation is available at either of the following sites:
- http://api.pma2020.org
- http://api-docs.pma2020.org

## Installation
### 1. System dependencies
- [Python3](https://www.python.org/downloads/)
- [PostgreSQL](http://www.postgresqltutorial.com/install-postgresql/)

### 2. Clone the project
1. Change directory to `PATH` where you want to clone: `cd PATH`
2. Clone: `git clone https://github.com/PMA-2020/pma-api.git`

### 3. Virtual environment
A Python virtual environment is a way to isolate applications and their dependencies from one another in order to avoid conflicts. We recommend that you install virtualenv. [The virtualenv documentation](https://virtualenv.pypa.io/en/stable/) has installation steps as well as more information about the usefulness of virtual environments. Here's a summary of the installation steps:

1. Install `virtualenv` globally: `python3 -m pip install virtualenv`
2. Change directory to where `pma-api` was cloned: `cd PATH/pma-api`
3. Create a virtual environment called `env`: `virtualenv env`
4. Use the virtualenv every time you want to work on the project
    4a. Activate the virtuale environment: `cd PATH/pma-api` && `source env/bin/activate`
    4b. Deactivate when you're done. You can do this by closing the terminal session, or running: `deactivate`

### 4. Install project dependencies
- `python3 -m pip install -r requirements.txt`

### 5. Create the database
#### 5.1. Set up PostgreSQL DB
You can use a command line interface (e.g. _psql_) or graphical user interface (e.g. [PgAadmin4](https://www.pgadmin.org/download/)) to set up the DB.
i. Create database a called 'pma-api'. `CREATE DATABASE pma-api;`  
ii. Create a user called 'pma-api'. `CREATE USER pma-api;`  
iii. Set a password for this user, by default 'pma-api'. You can change this later. `ALTER USER pma-api WITH PASSWORD 'pma-api';`  
iv. Make user 'pma-api' a super user for DB 'pma-api'. `GRANT ALL PRIVILEGES ON DATABASE pma-api TO pma-api;`  

#### 5.2. Environmental variables
a. **_Virtualenv_ setups:** After installing the virtual environment, you should have a folder called `env`. Open up `env/bin/activate` in a text editor. Add the following text to the bottom of the file.
```bash
export ENV_NAME="development"
export DATABASE_URL="postgresql+psycopg2://pmaapi:pmaapi@localhost/pmaapi"
export STAGING_URL="http://api-staging.pma2020.org"
export PRODUCTION_URL="http://api.pma2020.org"
```
b. **_Virtualenvwrapper_ setups:** Add the following to your postactivate script. This is found in the root directory of wherever you installed virtualenvwrapper. Also, the text below assumes that you named your virtual environment "pma-api". If you are using virtualenvwrapper and named it something else, replace the text "pma-api" with whatever you named your environment.
```bash
if [ "$VIRTUAL_ENV" = "path/to/virtualenvs/pma-api" ]; then
	export ENV_NAME="development"
	export DATABASE_URL="postgresql+psycopg2://pmaapi:pmaapi@localhost/pmaapi"
	export STAGING_URL="http://api-staging.pma2020.org"
	export PRODUCTION_URL="http://api.pma2020.org"
fi
```

#### 5.3. Seed data into DB `makefile` command: `make db`
Seed data into DB `makefile` command: `make db`. If you are on a Windows system or another system that cannot run makefiles, you can open up the makefile in a text editor and use it as a reference to run common commands. In the case of "`make db`", the equivalent command will be: `python3 manage.py initdb --overwrite`. This will execute a script that populates a database using data taken from the `data` directory.

After running the command to seed data into DB, check the terminal to see if it was a success. If you do not see any error messages and one of the last lines says "COMMIT", this means the process was probably successful. 

## 6. Running locally
1. Run `pma-api` on a local server process via the following makefile command: `make serve`. The equivalent command is: `python3 manage.py runserver`.
2. Verify that it is running in the browser by going to: `http://localhost:5000/v1/resources`

## Getting to know the API
You can:
i. Navigate the API further by either (a) utilizing the URL links shown in the browser, or (b) looking at the available endpoints in the [pma-api documentation](https://api.pma2020.org).
ii. Read the [pma-api documentation](https://api.pma2020.org) for more information on use.

## Server management
### Pushing to staging
Run: `make push-staging`

### Pushing to production
Run: `make push-production`
