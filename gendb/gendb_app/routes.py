from sqlalchemy import func
from werkzeug.utils import secure_filename

from gendb_app import app, db
from gendb_app.forms import LoginForm, AddProjectForm, SetupForm, ChangePasswordForm
from gendb_app.models import Marker, MarkerAllele, User, Project, ProjectMemship, Individual, Phenotype, SystemLog, ProjectLog, Genotype
from gendb_app.filehandling import file_to_obj_list
from flask import render_template, url_for, flash, redirect, request
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.urls import url_parse
from functools import wraps


#
#
#   HELPER FUNCTIONS
#
#


# Decorator only allowing access if the user is a system administrator
def sys_admin_only(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if current_user.is_sys_admin:
            return fn(*args, **kwargs)
        else:
            flash("Only administrators may view this page", "danger")
            return redirect(url_for('login'))

    return wrapper


# Decorator only allowing access if the user is a member of a given project
# 'arg_name' should be the name of the project id argument passed to the called function
def proj_member_only(arg_name):
    def real_decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            project_id = kwargs.get(arg_name)
            memship_count = ProjectMemship.query.filter_by(user_email=current_user.email,
                                                           project_id=project_id).count()

            if memship_count < 1:
                flash("You are not a member of this project", "danger")
                return redirect(url_for('index'))
            else:
                return fn(*args, **kwargs)
        return wrapper
    return real_decorator


# Decorator only allowing access if the user is an administrator of a given project
# 'arg_name' should be the name of the project id argument passed to the called function
def proj_admin_only(arg_name):
    def real_decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            project_id = kwargs.get(arg_name)
            memship_count = ProjectMemship.query.filter_by(user_email=current_user.email,
                                                           project_id=project_id,
                                                           is_project_admin=True).count()
            if memship_count < 1:
                flash("You are not an administrator of this project", "danger")
                return redirect(url_for('index'))
            else:
                return fn(*args, **kwargs)
        return wrapper
    return real_decorator


#
#
#   AUTHENTICATION HANDLERS
#
#


@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.get(form.email.data)

        if user is None:
            flash("No user registered with this email address", "danger")
            log = SystemLog(request.remote_addr, form.email.data,
                            "Failed login to an account that does not exist")
            db.session.add(log)
            db.session.commit()
            return redirect(url_for('login'))

        if not user.check_password(form.password.data):
            flash("Invalid password", "danger")
            log = SystemLog(request.remote_addr, form.email.data,
                            "Failed login with invalid password")
            db.session.add(log)
            db.session.commit()
            return redirect(url_for('login'))

        login_user(user)

        log = SystemLog(request.remote_addr, user.email,
                        "Successful login")
        db.session.add(log)
        db.session.commit()

        # Determine page to redirect the user to
        # Default to index if not given or the location is outside this domain
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')

        return redirect(next_page)

    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    flash("Successfully logged out", "success")
    return redirect(url_for('login'))


@app.route('/setup', methods=['GET', 'POST'])
def setup():
    # Allows creation of the first admin account
    num_admins = User.query.filter_by(is_sys_admin=True).count()

    if current_user.is_authenticated or num_admins != 0:
        flash("The system has already been set up", "danger")
        return redirect(url_for('login'))

    form = SetupForm()

    if form.validate_on_submit():
        user = User(email=form.email.data,
                    full_name=form.full_name.data,
                    is_sys_admin=True)
        user.set_password(form.password.data)
        db.session.add(user)

        # System log entry
        log = SystemLog(request.remote_addr, user.email,
                        "Setup the system with the first admin account")
        db.session.add(log)
        db.session.commit()

        flash("Administrator account registered", "success")
        return redirect(url_for('login'))

    return render_template('setup.html', title='Setup', form=form)


@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()

    if form.validate_on_submit():
        if current_user.check_password(form.current.data):
            current_user.set_password(form.new_1.data)

            flash("Successfully changed password", "success")
            log = SystemLog(request.remote_addr, current_user.email,
                            "Successfully changed password")
            db.session.add(log)
            db.session.commit()
            return redirect(url_for('index'))
        else:
            flash("Current password incorrect", "danger")
            log = SystemLog(request.remote_addr, current_user.email,
                            "Failed password change attempt (current password incorrect)")
            db.session.add(log)
            db.session.commit()
            return redirect(url_for('change_password'))

    return render_template('change_password.html', title="Change Password", form=form)


#
#
#   MARKER MANAGEMENT
#
#

@app.route('/markers')
@login_required
def manage_markers():
    markers = db.session.query(
        Marker.id,
        Marker.chromosome,
        Marker.position,
        func.group_concat(MarkerAllele.allele)
    ).filter(Marker.id == MarkerAllele.marker).group_by(Marker.id).all()

    return render_template("manage_markers.html",
                           title="Manage Markers",
                           markers=markers)


@app.route('/markers/upload', methods=['POST'])
def upload_markers():
    markers_file = request.files['markers']
    filename = secure_filename(markers_file.filename)

    # TODO: Also test the file is a CSV
    if markers_file:
        error, result = file_to_obj_list("MARKERS", markers_file, None)

        if error:
            return render_template('upload_error_report.html',
                                   title='Markers Upload Error Report',
                                   filename=filename,
                                   headers=['Marker', 'Chromosome', 'Position',
                                            'Number of possible alleles', 'Possible alleles'],
                                   errors=result)

        markers, alleles = result
        with db.session.no_autoflush:
            for marker in markers:
                db.session.add(marker)

            # TODO: Remove this
            db.session.commit()

            for allele in alleles:
                db.session.add(allele)

            # Project log entry
            log = SystemLog(request.remote_addr, current_user.email,
                             "Uploaded Markers File: '{}'".format(filename))
            db.session.add(log)
            db.session.commit()

        flash("Successfully uploaded markers file: '{}'".format(filename), "success")

    return redirect(url_for('manage_markers'))



#
#
#   MAIN HANDLERS
#
#


@app.route('/index')
@login_required
def index():
    project_count = Project.query.count()
    ind_count = Individual.query.count()
    # TODO Possibly change what is considered a 'distinct' genotype
    gen_count = db.session.query(Genotype.marker).distinct().count()
    phen_count = db.session.query(Phenotype.name).distinct().count()

    user_projects = current_user.get_projects()

    return render_template('index.html', title="Projects Dashboard",
                           project_count=project_count, projects=user_projects,
                           ind_count=ind_count, gen_count=gen_count,
                           phen_count=phen_count)


@app.route('/add_project', methods=['GET', 'POST'])
@login_required
def add_project():
    form = AddProjectForm()

    if form.validate_on_submit():
        project = Project(title=form.title.data, desc=form.desc.data)
        memship = ProjectMemship(user=current_user, project=project, is_project_admin=True)
        db.session.add(project)
        db.session.add(memship)

        # Need to commit to give the project an id
        db.session.commit()

        # Project log entry
        log = ProjectLog(project.id, request.remote_addr, current_user.email,
                        ("Created project " + str(project)))
        db.session.add(log)
        db.session.commit()
        flash("Added new project", "success")
        return redirect(url_for('project', id=project.id))

    return render_template('add_project.html', title='Add Project', form=form)


@app.route('/delete_project/<id>')
@login_required
@proj_admin_only('id')
def delete_project(id):
    # Delete all members
    ProjectMemship.query.filter_by(project_id=id).delete()

    # TODO Delete all geno, pheno, group, indv
    Genotype.query_by_project(id).delete(synchronize_session=False)
    Phenotype.query_by_project(id).delete(synchronize_session=False)
    Individual.query.filter_by(project_id=id).\
        delete()

    # Delete the project itself
    Project.query.filter_by(id=id).delete()

    # Project log entry
    log = ProjectLog(id, request.remote_addr, current_user.email,
                     "Deleted project {}".format(id))
    db.session.add(log)
    db.session.commit()

    flash("Project deleted successfully", "success")
    return redirect(url_for('index'))


@app.route('/project/<id>')
@login_required
@proj_member_only('id')
def project(id):
    project = Project.query.get(id)
    members = project.get_members()

    # TODO: Get the actual values
    proj_ind_count = Individual.query.filter_by(project_id=id).count()
    genos_proj = Genotype.query_by_project(id).count()
    proj_pheno_count = Phenotype.query_by_project(id).count()

    return render_template('project.html', title=project.title,
                           project=project, members=members,
                           proj_ind_count=proj_ind_count, genos_proj=genos_proj,
                           proj_pheno_count=proj_pheno_count)


@app.route('/add_member/<proj_id>', methods=['POST'])
@login_required
@proj_admin_only('proj_id')
def add_member(proj_id):
    project_memship = ProjectMemship(user_email=request.form.get('email'),
                                     project_id=proj_id,
                                     is_project_admin=(request.form.get('is_project_admin') == 'on'))
    db.session.add(project_memship)

    # Project log entry
    message = "Added user " + project_memship.user_email + " as "
    if project_memship.is_project_admin:
        message += "administrator"
    else:
        message += "contributor"
    log = ProjectLog(proj_id, request.remote_addr, current_user.email,
                     message)
    db.session.add(log)
    db.session.commit()

    flash("Member added to project", "success")
    return redirect(url_for('project', id=proj_id))


# TODO: Work out a POST alternative
@app.route('/remove_member/<user_email>/<proj_id>')
@login_required
@proj_admin_only('proj_id')
def remove_member(user_email, proj_id):
    num_admins = ProjectMemship.query.filter_by(project_id=proj_id, is_project_admin=True).count()

    if num_admins == 1 and current_user.email == user_email:
        flash("Cannot delete oneself if there is no other project administrator", "danger")
        return redirect(url_for('project', id=proj_id))

    ProjectMemship.query.filter(ProjectMemship.user_email == user_email and
                                ProjectMemship.project_id == proj_id).delete()

    # Project log entry
    log = ProjectLog(proj_id, request.remote_addr, current_user.email,
                     ("Removed user " + user_email))
    db.session.add(log)
    db.session.commit()

    flash("User removed successfully", "success")

    if current_user.email == user_email:
        return redirect(url_for('index'))
    else:
        return redirect(url_for('project', id=proj_id))


#
#
#   FILE UPLOAD
#
#


@app.route('/project/<proj_id>/upload/individuals', methods=['POST'])
@login_required
@proj_member_only('proj_id')
def upload_individuals(proj_id):
    ind_file = request.files['individuals']
    filename = secure_filename(ind_file.filename)

    # TODO Also test the file is a CSV
    if ind_file:
        error, result = file_to_obj_list("INDIVIDUALS", ind_file, proj_id)

        if error:
            return render_template('upload_error_report.html',
                                   title="Individuals Upload Error Report",
                                   filename=filename,
                                   headers=["ID", "Gender"],
                                   errors=result)

        for ind in result:
            # TODO Test the individual does not already exist
            # TODO Create dummy parents?
            db.session.add(ind)

        # Project log entry
        log = ProjectLog(proj_id, request.remote_addr, current_user.email,
                         "Uploaded Individuals File: '{}'".format(filename))
        db.session.add(log)
        db.session.commit()

        flash("Successfully uploaded individuals file: '{}'".format(filename), "success")
    else:
        flash("No individuals file", "danger")

    return redirect(url_for('project', id=proj_id))


@app.route('/project/<proj_id>/upload/group', methods=['POST'])
@login_required
@proj_member_only('proj_id')
def upload_group(proj_id):
    flash("Not yet implemented", "danger")
    return redirect(url_for('index'))


@app.route('/project/<proj_id>/upload/phenotypes', methods=['POST'])
@login_required
@proj_member_only('proj_id')
def upload_phenotypes(proj_id):
    pheno_file = request.files['phenotypes']
    filename = secure_filename(pheno_file.filename)

    # TODO: Also test the file is a CSV
    if pheno_file:
        error, result = file_to_obj_list("PHENOTYPES", pheno_file, proj_id)

        if error:
            headers, error_list = result
            return render_template('upload_error_report.html',
                                   title="Phenotypes Upload Error Report",
                                   filename=filename,
                                   headers=headers,
                                   errors=error_list)

        for pheno in result:
            db.session.add(pheno)

        # Project log entry
        log = ProjectLog(proj_id, request.remote_addr, current_user.email,
                         "Uploaded Phenotypes File: '{}'".format(filename))
        db.session.add(log)
        db.session.commit()

        flash("Successfully uploaded phenotypes file: '{}'".format(filename), "success")
    else:
        flash("No phenotypes file", "danger")
    return redirect(url_for('project', id=proj_id))


@app.route('/project/<proj_id>/upload/genotypes', methods=['POST'])
@login_required
@proj_member_only('proj_id')
def upload_genotypes(proj_id):
    geno_file = request.files['genotypes']
    filename = secure_filename(geno_file.filename)

    # TODO: Also test the file is a CSV
    if geno_file:
        error, result = file_to_obj_list("GENOTYPES", geno_file, proj_id)

        if error:
            return render_template('upload_error_report.html',
                                   title="Genotypes Upload Error Report",
                                   filename=filename,
                                   headers=["ID", "Marker", "Allele 1", "Allele 2"],
                                   errors=result)

        for geno in result:
            db.session.add(geno)

        # Project log entry
        log = ProjectLog(proj_id, request.remote_addr, current_user.email,
                         "Uploaded Genotypes File: '{}'".format(filename))
        db.session.add(log)
        db.session.commit()

        flash("Successfully uploaded genotypes file: '{}'".format(filename), "success")
    else:
        flash("No genotypes file", "danger")
    return redirect(url_for('project', id=proj_id))


#
#
#   ADMIN FUNCTIONALITY HANDLERS
#
#


@app.route('/admin')
@login_required
@sys_admin_only
def admin():
    return render_template('admin.html', title="Admin Dashboard")


@app.route('/admin/users')
@login_required
@sys_admin_only
def users():
    user_list = User.query.all()
    return render_template('users.html', title='Users', users=user_list)


@app.route('/add_user', methods=['POST'])
@login_required
@sys_admin_only
def add_user():
    user = User(email=request.form.get('email'),
                full_name=request.form.get('full_name'),
                is_sys_admin=(request.form.get('is_sys_admin') == 'on'))
    user.set_password(request.form.get('password'))
    db.session.add(user)

    flash("Successfully created user account", "success")
    log = SystemLog(request.remote_addr, current_user.email,
                    "Created user account <" + user.email + ">")
    db.session.add(log)
    db.session.commit()
    return redirect(url_for('users'))


@app.route('/admin/sys_logs')
@app.route('/admin/sys_logs/page/<int:page>')
@sys_admin_only
def sys_logs(page=1):
    logs = SystemLog.query.order_by(SystemLog.time.desc()).\
        paginate(page, 20, False)
    return render_template('admin_sys_logs.html', title="System Logs", logs=logs)


@app.route('/admin/proj_logs')
@app.route('/admin/proj_logs/page/<int:page>')
@sys_admin_only
def admin_proj_logs(page=1):
    logs = ProjectLog.query.order_by(ProjectLog.time.desc()).\
        paginate(page, 20, False)
    return render_template('admin_proj_logs.html', title="Project Logs", logs=logs)


#
#
#   DEPRECATED HANDLERS, EACH SHOULD FLASH A 'DANGER' ISSUE
#
#


@app.route('/projects')
@login_required
def projects():
    flash("Issue Num. 01 - Please raise this issue with project developer", "danger")
    return redirect(url_for('index'))


@app.route('/project_page/<id>')
@login_required
def project_page(id):
    flash("Issue Num. 02 - Please raise this issue with project developer", "danger")
    return redirect(url_for('index'))


@app.route('/log_page')
@login_required
def old_log_page():
    flash("Issue Num. 03 - Please raise this issue with project developer", "danger")
    return redirect(url_for('index'))


@app.route('/users')
@login_required
def old_users():
    flash("Issue Num. 04 - Please raise this issue with project developer", "danger")
    return redirect(url_for('index'))


@app.route('/delete_member')
@login_required
def delete_member():
    flash("Issue Num. 05 - Please raise this issue with project developer", "danger")
    return redirect(url_for('index'))


@app.route('/upload_individual')
@login_required
def upload_individual():
    flash("Issue Num. 06 - Please raise this issue with project developer", "danger")
    return redirect(url_for('index'))


@app.route('/admin/log_page')
def log_page():
    flash("Issue Num. 07 - Please raise this issue with project developer", "danger")
    return redirect(url_for('index'))


@app.route('/single_geno')
def single_geno():
    flash("Issue Num. 08 - Please raise this issue with project developer", "danger")
    return redirect(url_for('index'))


#
#
#   TEMPORARY HANDLERS
#
#


@app.route('/project/<proj_id>/download_ped')
def download_ped(proj_id):
    flash("Not yet implemented", "danger")
    return redirect(url_for('index'))


@app.route('/help')
def help():
    flash("Not yet implemented", "danger")
    return redirect(url_for('index'))


@app.route('/bulk_pheno')
def bulk_pheno():
    flash("Not yet implemented", "danger")
    return redirect(url_for('index'))


@app.route('/bulk_geno')
def bulk_geno():
    flash("Not yet implemented", "danger")
    return redirect(url_for('index'))


@app.route('/download_dat')
def download_dat():
    flash("Not yet implemented", "danger")
    return redirect(url_for('index'))
