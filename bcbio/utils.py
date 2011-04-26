"""Helpful utilities for building analysis pipelines.
"""
import os
import tempfile
import shutil
import contextlib
import itertools
import functools
import warnings

try:
    import multiprocessing
    from multiprocessing.pool import IMapIterator
except ImportError:
    multiprocessing = None
try:
    ipclient = None
    #with warnings.catch_warnings():
    #    warnings.filterwarnings("ignore", category=DeprecationWarning)
    #    from IPython.kernel import client as ipclient
except ImportError:
    ipclient = None

@contextlib.contextmanager
def cpmap(cores=1, ipython=False):
    """Configurable parallel map context manager.

    Returns appropriate map compatible function based on configuration:
    - Local single core (the default)
    - Multiple local cores
    - Parallelized on a cluster using ipython.
    """
    if ipython or cores=="ipython":
        raise NotImplementedError("Not working yet")
        if ipclient is None:
            raise ImportError("ipython parallelization not available.")
        mec = ipclient.MultiEngineClient()
        # Would be ideal to have an imap style lazy map
        yield mec.map
    elif int(cores) == 1:
        yield itertools.imap
    else:
        if multiprocessing is None:
            raise ImportError("multiprocessing not available")
        # Fix to allow keyboard interrupts in multiprocessing: https://gist.github.com/626518
        def wrapper(func):
            def wrap(self, timeout=None):
                return func(self, timeout=timeout if timeout is not None else 1e100)
            return wrap
        IMapIterator.next = wrapper(IMapIterator.next)
        pool = multiprocessing.Pool(int(cores))
        yield pool.imap
        pool.terminate()

def map_wrap(f):
    """Wrap standard function to easily pass into 'map' processing.
    """
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return apply(f, *args, **kwargs)
    return wrapper

def safe_makedir(dname):
    """Make a directory if it doesn't exist, handling concurrent race conditions.
    """
    if not os.path.exists(dname):
        # we could get an error here if multiple processes are creating
        # the directory at the same time. Grr, concurrency.
        try:
            os.makedirs(dname)
        except OSError:
            assert os.path.isdir(dname)

@contextlib.contextmanager
def curdir_tmpdir():
    """Context manager to create and remove a temporary directory.
    """
    tmp_dir_base = os.path.join(os.getcwd(), "tmp")
    safe_makedir(tmp_dir_base)
    tmp_dir = tempfile.mkdtemp(dir=tmp_dir_base)
    safe_makedir(tmp_dir)
    try :
        yield tmp_dir
    finally :
        shutil.rmtree(tmp_dir)

@contextlib.contextmanager
def chdir(new_dir):
    """Context manager to temporarily change to a new directory.

    http://lucentbeing.com/blog/context-managers-and-the-with-statement-in-python/
    """
    cur_dir = os.getcwd()
    safe_makedir(new_dir)
    os.chdir(new_dir)
    try :
        yield
    finally :
        os.chdir(cur_dir)

@contextlib.contextmanager
def tmpfile(*args, **kwargs):
    """Make a tempfile, safely cleaning up file descriptors on completion.
    """
    (fd, fname) = tempfile.mkstemp(*args, **kwargs)
    try:
        yield fname
    finally:
        os.close(fd)
        if os.path.exists(fname):
            os.remove(fname)

def create_dirs(config, names=None):
    if names is None:
        names = config["dir"].keys()
    for dname in names:
        d = config["dir"][dname]
        safe_makedir(d)