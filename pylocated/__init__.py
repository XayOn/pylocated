""" Python locate interface library """

from subprocess import PIPE as pipe
from subprocess import Popen
import os
import re
import sys
import inspect

# pylint: disable=no-value-for-parameter
# pylint can't see genericmethod acts a bit like classmethod if needed
# import StringIO according to Python version


PY2 = sys.version_info[0] == 2

if PY2:
    from cStringIO import StringIO
else:
    if sys.version_info.minor <= 3:
        from StringIO import StringIO
    else:
        from io import StringIO


def genericmethod(class_):
    """ Decorator to call a classmethod with the given class as
        first argument and a method with the instance.

    This differs from using classmethod directly in that whenever
    we're calling it from an instance, the first argument will be
    the instance, not the class.
    """
    def _decor(func):
        def _wrapper(*args, **kwargs):
            if args and isinstance(args[0], class_):
                return func(args[0], *args[1:], **kwargs)
            return func(class_, *args, **kwargs)
        return _wrapper
    return _decor


def toint(what):
    """ Convert string to long or int (py3) """
    if not PY2:
        long = int
    return long(what)


class PyLocatedException(Exception):
    """ Base Exception for all pylocated error """
    pass


class FileSystem(object):
    """ Filesystem object. Given a stats string, sets a few useful properties

    - Files: Number of files
    - Directories: Number of directories
    - Total space: Total space
    - Used space: Used space
    - DB Path: db path
    """
    # pylint: disable=too-few-public-methods
    def __init__(self, statics_string):
        parsed = statics_string.split("\n\t")
        self.files = toint(parsed[1].strip().split()[0].replace(',', ''))
        self.directories = toint(parsed[2].strip().split()[0].replace(',', ''))
        self.total_space = toint(parsed[3].strip().split()[0].replace(',', ''))
        self.used_space = toint(parsed[4].strip().split()[0].replace(',', ''))
        self.db_path = toint(parsed[0].strip().split()[1])


def _docommand(args):
    try:
        out, err = Popen(args, stdout=pipe, stderr=pipe).communicate()
        if err:
            raise PyLocatedException(err)
        return out.decode() if not PY2 else out
    except Exception as err:
        # Eating up real exceptions type is questionable...
        raise PyLocatedException(str(err))


def _get_args(*args):
    _args = tuple()
    for condition, largs in args:
        if condition:
            _args += largs
    return _args


def _get_buffer_from_pipe(process_pipe, regex):
    """ Returns a filelike object containing all lines found and filtered """
    process_pipe = (a for a in process_pipe.split("\n") if a)
    if regex:
        compiled = re.compile(regex)
        process_pipe = (a for a in process_pipe if compiled.match(a) and a)

    buffer_ = StringIO()
    buffer_.writelines("\n".join(process_pipe))
    return buffer_


# pylint: disable=invalid-name
class Base(object):
    """ Locatedb base class """
    # pylint: disable=too-few-public-methods
    db_path = None


class locatedb(Base):
    """ Locatedb main class """
    def __init__(self, db_path=None):
        self.db_path = db_path
        # Invoke updatedb if a custom db_path is given and which does not exist
        if db_path is not None and os.path.isfile(db_path) is False:
            self.__class__.updatedb(db_path=self.db_path)

    @classmethod
    def version(cls):
        """ Return locate version """
        return _docommand(['locate', '-V']).split("\n")[0].split()[1]

    @classmethod
    def updatedb(cls, db_path=None):
        """ Used to update the located db.

        Equivalent to `updatedb`
        """
        return _docommand(cls.extend_with_dbpath(['updatedb'], db_path))

    @genericmethod(Base)
    def extend_with_dbpath(self, args, db_path=None):
        """ If we're a class, extract db path from the one set on ourselves

        Otherwise set it to given db_path if available
        """
        if not inspect.isclass(self) and self.db_path:
            args.extend(['-d', self.db_path])
        elif db_path:
            args.extend(['-d', db_path])
        return args

    @genericmethod(Base)
    def count(self, name, ignore_case=False):
        """ Count """
        return _docommand(self.extend_with_dbpath(_get_args(
            (True, ('locate', '-c', name)),
            (ignore_case, ('-i')))))

    @genericmethod(Base)
    def find(self, name, ignore_case=False, limit=None, regex=None):
        """ Find """
        args = self.extend_with_dbpath(_get_args(
            (True, ('locate', name)),
            (ignore_case, ('-i')),
            (str(limit).isnumeric(), ('-l', str(limit)))))
        return _get_buffer_from_pipe(_docommand(args), regex)

    @genericmethod(Base)
    def statistics(self):
        """ Statistics """
        if inspect.isclass(self):
            return None
        return _docommand(self.extend_with_dbpath(_get_args(
            (True, ('locate', '-S', 'name')))))
