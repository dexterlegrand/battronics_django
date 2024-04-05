
class VersionError(Exception):
    def __init__(self, message="Version not supported"):

        super().__init__(message)
