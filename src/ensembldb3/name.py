import re

from .species import Species


__author__ = "Gavin Huttley"
__copyright__ = "Copyright 2016-, The EnsemblDb3 Project"
__credits__ = ["Gavin Huttley"]
__license__ = "BSD"
__version__ = "2021.04.01"
__maintainer__ = "Gavin Huttley"
__email__ = "Gavin.Huttley@anu.edu.au"
__status__ = "alpha"

_release = re.compile("\d+")


def get_version_from_name(name):
    """returns the release and build identifiers from an ensembl db_name"""
    r = _release.search(name)
    if r is None:
        return None, None

    # first number run is release, followed by build
    # note, for the ensemblgenomes naming system, the second digit run is the
    # standard Ensembl release and the first is for the specified genome
    release = name[r.start() : r.end()]
    b = [s for s in _name_delim.split(name[r.end() :]) if s]

    return release, b


_name_delim = re.compile("_")


def get_dbtype_from_name(name):
    """returns the data base type from the name"""
    try:
        name = _release.split(name)
        name = [s for s in _name_delim.split(name[0]) if s]
    except TypeError as msg:
        print("Error:")
        print(name, type(name), msg)
        raise
    dbtype = None
    return name[1] if name[0] == "ensembl" else name[-1]


def get_db_prefix(name):
    """returns the db prefix, typically an organism or `ensembl'"""
    name = _release.split(name)
    name = [s for s in _name_delim.split(name[0]) if s]
    if name[0] == "ensembl":
        prefix = "ensembl"
    elif len(name) > 2:
        prefix = "_".join(name[:-1])
    else:
        raise RuntimeError(f"Unknown name structure: {'_'.join(name)}")
    return prefix


class EnsemblDbName(object):
    """container for a db name, inferring different attributes from the name,
    such as species, version, build"""

    def __init__(self, db_name):
        """db_name: and Emsembl database name"""
        if isinstance(db_name, EnsemblDbName):
            db_name = db_name.name
        self.name = db_name
        self.type = get_dbtype_from_name(db_name)
        self.prefix = get_db_prefix(db_name)

        release, build = get_version_from_name(db_name)
        self.release = release
        self.general_release = self.release

        if build and len(build) == 1:
            if self.type != "compara":
                self.build = build[0]
            else:
                self.build = None
                self.general_release = build[0]
        elif build:
            self.build = build[1]
            self.general_release = build[0]
        else:
            self.build = None

        self.species = None
        self.species = Species.get_species_name(self.prefix)

    def __repr__(self):
        build = ["", f"; build='{self.build}'"][self.build is not None]
        return f"db(prefix='{self.prefix}'; type='{self.type}'; release='{self.release}'{build})"

    def __str__(self):
        return self.name

    def __lt__(self, other):
        if isinstance(other, type(self)):
            other = other.name
        return self.name < other

    def __eq__(self, other):
        if isinstance(other, type(self)):
            other = other.name
        return self.name == other

    def __ne__(self, other):
        if isinstance(other, type(self)):
            other = other.name
        return self.name != other

    def __hash__(self):
        return hash(self.name)
