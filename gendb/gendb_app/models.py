from gendb_app import app, db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import UniqueConstraint
from datetime import datetime


@login.user_loader
def load_user(email):
    return User.query.get(email)


class User(UserMixin, db.Model):
    email = db.Column(db.String(120), primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(250), nullable=False)
    is_sys_admin = db.Column(db.Boolean, nullable=False)

    memships = db.relationship('ProjectMemship', backref='user', lazy='dynamic')

    def __repr__(self):
        return '<User {} - {}>'.format(self.email, self.full_name)

    def __str__(self):
        return self.full_name + " - " + self.email

    def get_id(self):
        return self.email

    def set_password(self, password):
        self.password_hash = generate_password_hash(password,
                                                    method=app.config['HASH_METHOD'],
                                                    salt_length=app.config['SALT_LENGTH'])

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_projects(self):
        projects = []
        for memship in self.memships:
            projects.append(memship.project)
        return projects


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    desc = db.Column(db.String(300), nullable=False)

    memships = db.relationship('ProjectMemship', backref='project',
                               lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return '<Project {}>'.format(self.id)

    def __str__(self):
        return str(self.id) + " : " + self.title

    def get_members(self):
        # Each element is a tuple of the user object and whether they are a project admin
        members = []
        for memship in self.memships:
            memship.user.is_project_admin = memship.is_project_admin
            members.append(memship.user)
        return members


class ProjectMemship(db.Model):
    user_email = db.Column(db.String(120), db.ForeignKey('user.email'), primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), primary_key=True)
    is_project_admin = db.Column(db.Boolean, nullable=False)

    def __repr__(self):
        return "<ProjectMemship - User: {} - Project: {}>".format(self.user_email, self.project_id)


class Individual(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    clinic_id = db.Column(db.String(5), nullable=False)
    family_id = db.Column(db.String(15), nullable=False)
    member_id = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint('project_id', 'clinic_id', 'family_id',
                         'member_id', name="_individual_uc"),
        {}
    )

    def __repr__(self):
        return "<Individual - ID: {}>".format(self.id)

    def get_full_id(self):
        return self.clinic_id + "_" + self.family_id + "_" + self.member_id


class Phenotype(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ind_id = db.Column(db.Integer, db.ForeignKey('individual.id'), nullable=False)
    name = db.Column(db.String(30), nullable=False)
    value = db.Column(db.String(50), nullable=False)

    __table_args__ = (
        UniqueConstraint('ind_id', 'name',
                         name="_pheno_uc"),
        {}
    )

    def __repr__(self):
        return "<Phenotype - ID: {}>".format(self.id)

    @staticmethod
    def query_by_project(proj_id):
        subquery = db.session.query(Individual.id).filter_by(project_id=proj_id)
        return Phenotype.query.filter(Phenotype.ind_id.in_(subquery))


class Genotype(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ind_id = db.Column(db.Integer, db.ForeignKey('individual.id'), nullable=False)
    marker = db.Column(db.String(20), db.ForeignKey('marker.id'), nullable=False)
    call_1 = db.Column(db.String(1), nullable=False)
    call_2 = db.Column(db.String(2), nullable=False)

    __table_args__ = (
        UniqueConstraint('ind_id', 'marker',
                         name="_geno_uc"),
        {}
    )

    def __repr__(self):
        return "<Genotype - ID: {}>".format(self.id)

    @staticmethod
    def query_by_project(proj_id):
        subquery = db.session.query(Individual.id).filter_by(project_id=proj_id)
        return Genotype.query.filter(Genotype.ind_id.in_(subquery))


class Marker(db.Model):
    id = db.Column(db.String(15), primary_key=True)
    chromosome = db.Column(db.Integer, nullable=False)
    position = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return "<Marker - ID: {}>".format(self.id)


class MarkerAllele(db.Model):
    marker = db.Column(db.String(15), db.ForeignKey('marker.id'), primary_key=True)
    allele = db.Column(db.String(1), primary_key=True)

    def __repr__(self):
        return "<MarkerAllele - Marker: {} - Allele: {}>".format(self.marker, self.allele)


class SystemLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    time = db.Column(db.DateTime, default=datetime.utcnow)
    message = db.Column(db.String(150), nullable=False)
    user_ip = db.Column(db.String(15), nullable=False)
    # User email not stored as foreign key so that logs will persist
    # after users are deleted
    user_email = db.Column(db.String(120), nullable=False)

    def __init__(self, user_ip, user_email, message):
        self.message = message
        self.user_ip = user_ip
        self.user_email = user_email

    def __repr__(self):
        return "<SystemLog - ID: {}>".format(self.id)


class ProjectLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    time = db.Column(db.DateTime, default=datetime.utcnow)
    message = db.Column(db.String(150), nullable=False)
    user_ip = db.Column(db.String(15), nullable=False)
    # User email and project id not stored as foreign keys so that
    # logs will persist after users and projects are deleted
    user_email = db.Column(db.String(120), nullable=False)
    project_id = db.Column(db.Integer, nullable=False)

    def __init__(self, project_id, user_ip, user_email, message):
        self.project_id = project_id
        self.message = message
        self.user_ip = user_ip
        self.user_email = user_email

    def __repr__(self):
        return "<ProjectLog - ID: {}".format(self.id)


# NOTE: composite foreign keys: https://stackoverflow.com/questions/7504753/relations-on-composite-keys-using-sqlalchemy
