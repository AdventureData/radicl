from datetime import datetime
from os.path import join


def get_default_filename(output_dir='./'):
    """
    Creates a datetime path for writing to

    Returns:
        fname: csv path named by the datetime
    """
    t = datetime.now()
    fstr = "{0}-{1:02d}-{2:02d}--{3:02d}{4:02d}{5:02d}.csv"
    fname = fstr.format(t.year, t.month, t.day, t.hour, t.minute, t.second)
    return join(output_dir, fname)


def is_numbered(filename):
    """
    Checks if the filename has been numbered. Denoted by any file ending in
    somefname_<#>.csv Returns true or false.
    Args:
        filename: Path with potential some appended number scheme denoted by _
    Returns:
        bool: True if a separator and all numbers are found towards the end
    """
    info = filename.split('.')[0]
    sep = False
    numbered = False

    if '_' in info:
        numbers = info.split('_')[-1]
        sep = True
        numbered = all([c.isnumeric() for c in numbers])
    return sep and numbered


def increment_fnumber(filename):
    """
    Check for a file numbering. Increment if there is one. Otherwise add one
    """
    no_ext = filename.split('.')[0]

    if is_numbered(filename):
        info = no_ext.split('_')
        base_file = '_'.join(info[0:-1])
        count = int(info[-1])
        fcount = count + 1

    else:
        base_file = no_ext
        fcount = 1

    filename = f"{base_file}_{fcount}.csv"

    return filename


def add_ext(filename):
    """
    Check to see if the user provided the .csv ext in the filename
    and add it
    """
    if filename[-4:] != '.csv':
        f = filename.split('.')
        # Did the user try to add an ext
        if len(f) == 2:
            filename = f[0] + '.csv'
        else:
            filename += '.csv'

    return filename
