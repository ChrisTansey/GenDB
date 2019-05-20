class ErrorObject(object):
    def __init__(self, message, error=None):
        self.message = message
        self.error = error

    def __str__(self):
        return self.message


class IncorrectNumberOfColumnsError(ValueError):
    def __init__(self, message):
        super().__init__(message)


class DataAlreadyInDatabaseError(ValueError):
    def __init__(self, message):
        super().__init__(message)


class NoObjectToInsertException(Exception):
    def __init(self):
        super().__init__()


# TODO: move specific errors over to this general error with column number
class CsvCellError(ValueError):
    def __init__(self, col_num, message):
        super().__init__(message)
        self.col_num = col_num


class IndividualIDFormatError(ValueError):
    def __init__(self, message):
        super().__init__(message)


class IndividualMemberIDError(ValueError):
    def __init__(self, message):
        super().__init__(message)


class IndividualGenderError(ValueError):
    def __init__(self, message):
        super().__init__(message)


class IndividualIDNotPresentError(ValueError):
    def __init__(self, message):
        super().__init__(message)


class PhenotypeValueError(ValueError):
    def __init__(self, col_num, message):
        self.col_num = col_num
        super().__init__(message)


class MarkerNumAllelesError(ValueError):
    def __init__(self, message):
        super().__init__(message)


class MarkerChromosomeOutOfRange(ValueError):
    def __init__(self, message):
        super().__init__(message)