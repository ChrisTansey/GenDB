from sqlalchemy.orm.exc import NoResultFound

from gendb_app.models import Marker, MarkerAllele, Individual, Phenotype, Genotype
from gendb_app.filehandling.exceptions \
    import IndividualIDFormatError, IndividualMemberIDError, IndividualGenderError, ErrorObject, \
    IncorrectNumberOfColumnsError, IndividualIDNotPresentError, PhenotypeValueError, MarkerNumAllelesError, \
    DataAlreadyInDatabaseError, CsvCellError, NoObjectToInsertException

MISSING_DATA_SYM = 'x'
IND_ID_SEPARATOR = '_'
VALID_GENDER_VALUES = ['0', '1', '2']


# Takes a full individual ID and splits into its three parts
# Returns false if the format is invalid
def full_ind_id_to_parts(full_id):
    if full_id.count(IND_ID_SEPARATOR) < 2:
        raise IndividualIDFormatError("Individual IDs should have 3 parts")

    clinic, _, rhs = full_id.partition(IND_ID_SEPARATOR)
    family, _, member = rhs.rpartition(IND_ID_SEPARATOR)

    try:
        int(member)
    except ValueError:
        raise IndividualMemberIDError("Family member identifier must be a number")
    if int(member) < 1:
        raise IndividualMemberIDError("Invalid family member identifier")

    return clinic, family, member


# TODO: Change all handlers to use cleaner code with CsvCellError
def csv_to_markers(csv_input):
    markers = []
    alleles = []
    errors = []

    row_num = 0
    for row in csv_input:
        row_num += 1

        try:
            marker, mk_alleles = row_to_markers(row)
            markers.append(marker)
            alleles.extend(mk_alleles)
        except IncorrectNumberOfColumnsError as e:
            row_errors = [ErrorObject(str(row_num), error=str(e))]
            errors.append(row_errors)
        except MarkerNumAllelesError as e:
            row_errors = [ErrorObject(str(row_num))]
            for cell in row[0:3]:
                row_errors.append(ErrorObject(cell))
            row_errors.append(ErrorObject(row[3], error=str(e)))
            errors.append(row_errors)
        except DataAlreadyInDatabaseError as e:
            row_errors = [ErrorObject(str(row_num))]
            row_errors.append(ErrorObject(row[0], error=str(e)))
            for cell in row[1:]:
                row_errors.append(ErrorObject(cell))
            errors.append(row_errors)
        except CsvCellError as e:
            row_errors = [ErrorObject(str(row_num))]
            for col_num, cell in enumerate(row):
                if col_num == e.col_num:
                    row_errors.append(ErrorObject(cell, error=str(e)))
                else:
                    row_errors.append(ErrorObject(cell))
            errors.append(row_errors)

    error_found = len(errors) != 0
    if error_found:
        return error_found, errors
    else:
        return error_found, (markers, alleles)


def row_to_markers(row):
    # TODO Possibly add a test that the position is within range for that chromosome
    # TODO test all given alleles are different

    NUM_REQ_COLS = 4

    if len(row) < NUM_REQ_COLS:
        raise IncorrectNumberOfColumnsError("Expected a minimum of 4 columns, got {}".format(len(row)))

    try:
        num_alleles = int(row[3])
    except ValueError:
        raise MarkerNumAllelesError("Given number of alleles ({}) must be a number".format(row[3]))

    if len(row) != NUM_REQ_COLS + num_alleles:
        raise MarkerNumAllelesError("Given number of alleles ({}) does not match the number given".format(num_alleles))

    result = Marker.query.get(row[0])
    if result is not None:
        raise DataAlreadyInDatabaseError("Marker already in database")

    marker = Marker(id=row[0], chromosome=row[1], position=row[2])
    alleles = []

    col_num = NUM_REQ_COLS - 1
    for allele_symbol in row[NUM_REQ_COLS: (NUM_REQ_COLS + num_alleles)]:
        col_num += 1

        if len(allele_symbol) != 1:
            raise CsvCellError(col_num, "An allele can only be a single character")

        if not allele_symbol.isalnum():
            raise CsvCellError(col_num, "Alleles must be letters or numbers")

        if allele_symbol == MISSING_DATA_SYM:
            raise CsvCellError(col_num, "Cannot be the missing data symbol")

        # TODO Capitalise, same for genotype
        alleles.append(MarkerAllele(marker=row[0], allele=allele_symbol))

    return marker, alleles


def csv_to_individuals(csv_input, project_id):
    individuals = []
    errors = []

    row_num = 0
    for row in csv_input:
        row_num += 1
        try:
            ind = row_to_individual(row, project_id)
            individuals.append(ind)
        except IncorrectNumberOfColumnsError as e:
            row_errors = [ErrorObject(str(row_num), error=str(e))]
            errors.append(row_errors)
        except (IndividualIDFormatError, IndividualMemberIDError) as e:
            row_errors = [row_num,
                          ErrorObject(row[0], error=str(e)),
                          ErrorObject(row[1])]
            errors.append(row_errors)
        except IndividualGenderError as e:
            row_errors = [row_num,
                          ErrorObject(row[0]),
                          ErrorObject(row[1], error=str(e))]
            errors.append(row_errors)
        except CsvCellError as e:
            row_errors = [ErrorObject(str(row_num))]
            for col_num, cell in enumerate(row):
                if col_num == e.col_num:
                    row_errors.append(ErrorObject(cell, error=str(e)))
                else:
                    row_errors.append(ErrorObject(cell))
            errors.append(row_errors)

    error_found = len(errors) != 0
    if error_found:
        return error_found, errors
    else:
        return error_found, individuals


def row_to_individual(row, project_id):
    if len(row) != 2:
        raise IncorrectNumberOfColumnsError("Expected 2 columns, got {}".format(len(row)))

    clinic, family, member = full_ind_id_to_parts(row[0])
    gender = row[1]

    # Get integer individual ID
    try:
        ind = Individual.query.filter_by(project_id=project_id, clinic_id=clinic,
                                         family_id=family, member_id=member).one()

        # An existing individual with these details exists
        raise CsvCellError(0, "An individual with this ID already exists in this project")
    except NoResultFound:
        # Do nothing, expecting no result to already exist
        pass

    if gender not in VALID_GENDER_VALUES:
        raise IndividualGenderError("Not a valid gender value")
    if member == '1' and not gender == '1':
        raise IndividualGenderError("Father's gender should be male")
    if member == '2' and not gender == '2':
        raise IndividualGenderError("Mother's gender should be female")

    return Individual(project_id=project_id, clinic_id=clinic,
                      family_id=family, member_id=member,
                      gender=gender)


def csv_to_phenotypes(csv_input, project_id):
    error_found = False
    phenotypes = []
    errors = []

    # Read in list of phenotype names from header
    headers = next(csv_input, None)
    pheno_names = headers.copy()
    pheno_names.pop(0)

    row_num = 1
    for row in csv_input:
        row_num += 1
        try:
            phenos = row_to_phenotypes(row, project_id, pheno_names)
            phenotypes.extend(phenos)
        except IncorrectNumberOfColumnsError as e:
            error_found = True
            row_errors = [ErrorObject(str(row_num), error=str(e))]
            errors.append(row_errors)
        except IndividualIDNotPresentError as e:
            error_found = True
            row_errors = [ErrorObject(str(row_num)),
                          ErrorObject(row[0], error=str(e))]
            for cell in row[1:]:
                row_errors.append(ErrorObject(cell))
            errors.append(row_errors)
        except PhenotypeValueError as e:
            error_found = True
            row_errors = [ErrorObject(str(row_num))]
            for index, cell in enumerate(row):
                if index == e.col_num:
                    row_errors.append(ErrorObject(cell, error=str(e)))
                else:
                    row_errors.append(ErrorObject(cell))
            errors.append(row_errors)

    if error_found:
        return error_found, (headers, errors)
    else:
        return error_found, phenotypes


def row_to_phenotypes(row, project_id, pheno_names):
    expected_cols = len(pheno_names) + 1
    if len(row) != expected_cols:
        raise IncorrectNumberOfColumnsError("Expected {} columns, got {}".format(expected_cols, len(row)))

    full_id = row[0]
    clinic, family, member = full_ind_id_to_parts(full_id)

    # Get integer individual ID
    try:
        ind = Individual.query.filter_by(project_id=project_id, clinic_id=clinic,
                                     family_id=family, member_id=member).one()
    except NoResultFound:
        raise IndividualIDNotPresentError("No individual stored with the ID {}".format(full_id))
    ind_id = ind.id

    phenos = []
    index=0
    for pheno_val in row[1:]:

        if pheno_val is None or pheno_val == "":
            raise PhenotypeValueError(index+1, "Phenotype value cannot be blank")

        if pheno_val == MISSING_DATA_SYM:
            # Nothing to insert into the database
            continue

        pheno = Phenotype(ind_id=ind_id, name=pheno_names[index],
                          value=pheno_val)
        phenos.append(pheno)
        index += 1

    return phenos


def csv_to_genotypes(csv_input, project_id):
    genotypes = []
    errors = []

    row_num = 0
    for row in csv_input:
        row_num += 1

        try:
            geno = row_to_genotype(row, project_id)
            genotypes.append(geno)
        except NoObjectToInsertException:
            continue
        except IncorrectNumberOfColumnsError as e:
            row_errors = [ErrorObject(str(row_num), error=str(e))]
            errors.append(row_errors)
        except (IndividualIDFormatError, IndividualMemberIDError) as e:
            row_errors = [row_num,
                          ErrorObject(row[0], error=str(e))]
            for cell in row[1:]:
                row_errors.append(ErrorObject(cell))
            errors.append(row_errors)
        except CsvCellError as e:
            row_errors = [ErrorObject(str(row_num))]
            for col_num, cell in enumerate(row):
                if col_num == e.col_num:
                    row_errors.append(ErrorObject(cell, error=str(e)))
                else:
                    row_errors.append(ErrorObject(cell))
            errors.append(row_errors)

    error_found = len(errors) != 0
    if error_found:
        return error_found, errors
    else:
        return error_found, genotypes


def row_to_genotype(row, project_id):
    # TODO: Test if this ind already has this marker stored

    if len(row) != 4:
        raise IncorrectNumberOfColumnsError("Expected 4 columns, got {}".format(len(row)))

    clinic, family, member = full_ind_id_to_parts(row[0])
    marker = row[1]
    call_1 = row[2]
    call_2 = row[3]

    try:
        ind = Individual.query.filter_by(project_id=project_id, clinic_id=clinic,
                                     family_id=family, member_id=member).one()
    except NoResultFound:
        raise CsvCellError(0, "No individual stored with this ID")

    try:
        Marker.query.filter_by(id=marker).one()
    except NoResultFound:
        raise CsvCellError(1, "Invalid marker - not stored in marker management system")

    if call_1 == MISSING_DATA_SYM:
        if call_2 == MISSING_DATA_SYM:
            # Don't insert if data missing
            raise NoObjectToInsertException()
        else:
            raise CsvCellError(2, "Either both alleles must be missing, or neither")
    elif call_2 == MISSING_DATA_SYM:
        raise CsvCellError(3, "Either both alleles must be missing, or neither")

    try:
        MarkerAllele.query.filter_by(marker=marker, allele=call_1).one()
    except NoResultFound:
        raise CsvCellError(2, "Not a valid allele for this marker")

    try:
        MarkerAllele.query.filter_by(marker=marker, allele=call_2).one()
    except NoResultFound:
        raise CsvCellError(3, "Not a valid allele for this marker")

    return Genotype(ind_id=ind.id, marker=marker, call_1=call_1, call_2=call_2)
