# GenDB
## A database system for genetic and phenotypic data

The system comprises of a MySQL database part and a Python Flask server part - these parts may run individually on different machines or may run together on the same machine.

## Preparation of the MySQL database part

1) If not already done, install MySQL server by the most recent recommendations on the machine that will be used for data storage

2) Using the MySQL CLI, create a database named `gendb`

        bash> mysql -u root -p
        mysql> CREATE DATABASE gendb;
        
3) Create a MySQL user account to access the database from the Flask server. Change the wildcard `%` to `localhost` if the Flask server will run on the same machine. Hash the password if you see fit.

        mysql> CREATE USER 'gendb_user'@'%' IDENTIFIED BY 'gendb_password';
        mysql> GRANT ALL PRIVILEGES ON gendb.* TO 'gendb_user'@'%';
        mysql> FLUSH PRIVILEGES;
        mysql> EXIT

## Preparation of the Python Flask part

1) On the machine that will be used to host the server: move the `gendb_deploy` directory to the desired location and navigate into it from within the terminal. If not already done, install python3 and python3-venv

2) Create a Python virtual environment - necessary for step 4 without making system-wide changes

        bash> python3 -m venv venv_dir

3) Activate the virtual environment

        bash> source venv_dir/bin/activate

4) Enforce the use of Python 3 within the virtual environment
    
        bash> alias python=python3

5) Install the prerequisites for your OS listed at: https://pypi.org/project/mysqlclient/. Don't go as far as the pip install instruction

6) Install python modules. You may get multiple warnings of "failed building wheel for ...", this is not a problem
    
        bash> pip install -r requirements.txt

7) Open `config.py` and edit `SQLALCHEMY_DATABASE_URI` to match your system configuration.

8) Perform the database migration to populate the schema of the MySQL database

        bash> flask db upgrade

9) Run the Flask server. The system can then be accessed at the socket printed to the CLI. If you want GenDB to only be accessible from `localhost`, then remove `--host=0.0.0.0`

        bash> flask run --host=0.0.0.0

10) If intended for longer term execution, daemonize the process in the standard way for your OS.

11) To setup the first administrator account for the system, navigate to the system setup page; e.g. `localhost:5000/setup`

## Re-running the Python Flask part at a later point

If the steps above have already been followed, restarting the Flask server is as follows:

1) Navigate into the `gendb_deploy` directory and activate the virtual environment

        bash> source venv_dir/bin/activate

2) Run the flask server, or daemonize as you see fit

        bash> flask run
