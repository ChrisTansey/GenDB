import os
basedir = os.path.abspath(os.path.dirname(__file__))


# This needs changing to be correct in the production system
class Config(object):
    # Needs to be unique to each system
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'change-for-production-system'

    # Database connection string
    #SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'gendb_app.db')
    SQLALCHEMY_DATABASE_URI = 'mysql+mysqldb://gendb_user:gendb_password@localhost/gendb'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Password hashing configuration
    HASH_METHOD = "pbkdf2:sha512"
    SALT_LENGTH = 64
