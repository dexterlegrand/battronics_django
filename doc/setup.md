# Setup
In this section is explained how to set up the project.

## Prerequisites
- [Anaconda](https://www.anaconda.com/) or preferred [Miniconda](https://docs.conda.io/en/latest/miniconda.html) installed
  - Update to latest version with ```conda update conda``` 
- [Git installed](https://gitforwindows.org/) (or any git-tool)
- *optional* IDE installed ([IntelliJ](https://www.jetbrains.com/idea/), [PyCharm](https://www.jetbrains.com/pycharm/), or similar)

Everything has to be updated to the latest version!
## Get Project
Open Gitbash or your favourite Git-tool to clone the repository to your local machine.
- ```git clone git@gitlab.ti.bfh.ch:automatedbatterydatabase/ABD_Webapp.git```

This will clone the git repo via SSH (requires to add a SSH-Key to the project in GitLab)  
You are now in the master branch. If you want to test the changes in another branch you have to use the 'checkout'-command:
- ```git checkout development``` // development is the placeholder for any existing branch name!
## Get Environment
Run following command in your IDE-Terminal or in the 'Anaconda prompt':
````bash
conda env create -f environment.yml
````

If you already have an environment called ``abd-env``, delete it first:
````bash
conda remove --name abd-env --all
````

If your running the command from the Anaconda prompt you have to add the full path to the environment.yml  
If you are using the IDE-Terminal the file should already be at the right place.

If everything worked you should be able to activate the newly created environment
- ```conda activate abd-env```

With the following command you can double-check if it worked. abd-env should appear in the list:
 - ```conda env list```

Also you should be able to start the server without any errors with following command:
 - ```manage.py runserver```
## Create Postgres DB
Alternatively to your own local Postgres installation you can use the provided docker container, 
see [here](#database-docker-container).

First we need to create the Postgres database, and we need to apply the migrations to the DB.  
Step one is to install Postgres and the timescale-extension. Follow this [tutorial](https://www.postgresqltutorial.com/install-postgresql/) for postgres and this [tutorial](https://docs.timescale.com/install/latest/#install-timescaledb) for timescale.  
Next step is to connect to postgres with the CLI using ```psql -U postgres``` password is "admin"  
Then we need to create the database with ```CREATE DATABASE abd_test;``` and switch to the created database ```\c abd_test``` and add the timescale extension with ```CREATE EXTENSION IF NOT EXISTS timescaledb;```

If you set up your config.json file correct you can now create the tables according to your models.  
Following command will do this:
- ```py manage.py migrate```

You can ensure the DB is generated correctly by viewing the tables created in an DB-tool for Postgres ('PgAdmin' as example).  
There should be a table per Model defined. Some of them are: BatteryTable, CellTest, ChemicalType, ect.
### Create Super User
Now that the Database is created we can add an admin account with all the rights on the server. To do that we call following command:
- ```manage.py createsuperuser```

You are asked to enter an username, email-address and a password. You are free to set it as you want.  
I recommend to set it as following:
- Username: 'admin'
- Email: **empty**
- Password: 'admin'

If you set your password to 'admin' you are reminded, that the password is too similar to the username. You can ignore that by just entering 'y'.

[//]: # (### Load initial data)

[//]: # ()
[//]: # (To create initial data and load it into to the database you have to run following command:)

[//]: # (- ```manage.py loaddata data```)

## Database docker container
Use this docker container as an alternative for a local PostgreSQL installation. 
The database state corresponds to the master-branch status, and it is preloaded with some data.

As prerequisite, you need Docker for Windows and WSL2, see
[https://docs.docker.com/desktop/install/windows-install/](https://docs.docker.com/desktop/install/windows-install/)

### Get the image
To download the docker image from the registry execute following commands:
````shell
docker login registry.gitlab.ti.bfh.ch
docker pull registry.gitlab.ti.bfh.ch/automatedbatterydatabase/abd_webapp/db-with-data:pg15-latest
````
### Run the container
Start the container with following command. The name and POSTGRES_PASSWORD can be chosen individually.
````shell
docker run -d --name abd-db -p 127.0.0.1:5432:5432 -e POSTGRES_PASSWORD=password registry.gitlab.ti.bfh.ch/automatedbatterydatabase/abd_webapp/db-with-data:pg15-latest
````

### Configure config.json
Set the entries in the config.json file as follows such that django can connect to the postgres database running 
in the container
````json
"db_name": "abd_dev",
"db_user": "abd_user",
"db_pwd": "test",
"db_host": "localhost",
"db_port": 5432
````

## Run the server
Now you are able to run the webservice and see how it looks and feels.  
To start the service you need to run following:
 - ```manage.py runserver```

To stop the server again you have to press "Ctrl + C"
