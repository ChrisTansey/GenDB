from gendb_app.filehandling.handling import csv_to_markers, csv_to_individuals, csv_to_phenotypes, csv_to_genotypes
from io import StringIO
import csv


def file_to_obj_list(file_type, file_handle, project_id):
    contents = file_handle.stream.read().decode('utf-8')
    stream = StringIO(contents, newline=None)
    csv_input = csv.reader(stream)

    if file_type == "MARKERS":
        return csv_to_markers(csv_input)
    elif file_type == "INDIVIDUALS":
        return csv_to_individuals(csv_input, project_id)
    elif file_type == "PHENOTYPES":
        return csv_to_phenotypes(csv_input, project_id)
    elif file_type == "GENOTYPES":
        return csv_to_genotypes(csv_input, project_id)

    # TODO else statement
