"""

    Support Tools used Across the BioVida API
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


"""
# Imports
import os
import re
import numpy as np
import pandas as pd
from collections import Hashable
from itertools import chain


def dict_reverse(d):
    """

    Reverse a dict.

    :param d:
    :return:
    """
    return {v: k for k, v in d.items()}


def n_sub_dirs(dir):
    """

    :param dir: a path
    :type dir: ``str``
    :return: number of subdirectories in the dir
    """
    if not os.path.isdir(dir):
        raise FileNotFoundError("'{0}' is not a directory.".format(dir))
    return len([k for i, j, k in os.walk(dir)]) - 1


def pstr(s):
    """

    Convert to any obect to a string using pandas.
    Source: https://github.com/TariqAHassan/EasyMoney

    :param s: item to be converted to a string.
    :type s: ``any``
    :return: a string
    :rtype: ``str``
    """
    return pd.Series([s]).astype('unicode')[0]


def items_null(element):
    """

    Check if an object is a NaN, including all the elements in an iterable.
    Source: https://github.com/TariqAHassan/EasyMoney

    :param element: a python object.
    :type element: ``any``
    :return: assessment of whether or not `element` is a NaN.
    :rtype: ``bool``
    """
    if isinstance(element, (list, tuple)) or 'ndarray' in str(type(element)):
        return True if all(pd.isnull(i) for i in element) else False
    else:
        return pd.isnull(element)


def list_to_bulletpoints(l, sort_elements=True):
    """

    Convert a list to bullet points.

    :param l: a list (in the colloquial sense) of strings.
    :type l: ``list`` or ``tuple``
    :param sort_elements: if ``True``, sort the elements in the list. Defaults to ``True``.
    :type sort_elements: ``bool``
    :return: list itmes formatted as a string of bullet points (with line breaks).
    :rtype: ``str``
    """
    to_format = sorted(l) if sort_elements else list(l)
    return "".join(map(lambda x: "  - '{0}'\n".format(x), to_format))[:-1]


def header(string, flank=True):
    """

    Generate a Header String

    :param string: a string.
    :type string: ``str``
    :param flank: if True, flank the header with line breaks.
    :type flank: ``bool``
    :return:
    """
    # Compute seperating line
    sep_line = "-" * len(string)

    # Display
    if flank:
        print("\n")
    print("\n{0}\n{1}\n{2}\n".format(sep_line, string, sep_line))
    if flank:
        print("\n")


def camel_to_snake_case(name):
    """

    Source: http://stackoverflow.com/a/1176023/4898004

    :param name:
    :return:
    """
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def cln(i, extent=1, strip=True):
    """

    String white space 'cleaner'.

    :param i: input str
    :type i: ``str``
    :param extent: 1 --> all white space reduced to length 1; 2 --> removal of all white space.
    :param strip: call str.strip()
    :tyoe strip: ``bool``
    :return: cleaned string
    :rtype: ``str``
    """
    to_return = ""
    if isinstance(i, str) and i != "":
        if extent == 1:
            to_return = re.sub(r"\s\s+", " ", i)
        elif extent == 2:
            to_return = re.sub(r"\s+", "", i)
    else:
        return i

    return to_return.strip() if strip else to_return


def n_split(s, n=2, delim='_'):
    """

    Splits a string into ``n`` groups on a given delimiter.

    Source: http://stackoverflow.com/a/17060409/4898004

    :param s: any string
    :type s: ``str``
    :param n: number of groups. Defaults to `2`.
    :type n: ``int``
    :param delim: a delimiter. Defaults to '_'.
    :type delim: ``str``
    :return: a tuple of with length``n``.
    :rtype: ``tuple``
    """
    groups = s.split(delim)
    return delim.join(groups[:n]), delim.join(groups[n:])


def hashable_cols(data_frame, block_override=[]):
    """

    Check which columns in a dataframe can be hashed.
    Note: Likely will be slow as scale and columns with type inhomogeneity.

    If we let:
        - c = columns in data_frame
        - n = rows in data_frame

    then we have O(c*n) complexity.
    However if we say that c = 41, as we always have with the `OpenInterface()` search result dataframes where
    this will be called, we get O(41*n), which is really just O(n).
    In short, if `n` is very large, this *could* become very slow, with a high burden being imposed by
    columns with type inhomogeneity (e.g., a single item that cannot be hashed being be the last one).

    However, the code below impliments two techniques to block looping through
    the whole column if doing so is not needed.
    Namely:
        1. if the column has dtype int64 or float64 (this can be hashed).
        2. the inner loop breaks if it encounters a single element that is not hashable.

    :param data_frame: any DataFrame.
    :rtype data_frame: ``Pandas DataFrame``
    :param override: columns to block regardless of what the procedure determines.
    :rtype override: ``list``
    :return: only those columns in the DataFrame that can be hashed.
    :rtype: ``list``
    """
    cannot_hash = list()
    for c in data_frame.columns:
        if c in block_override:
            cannot_hash.append(c)
        elif not data_frame[c].dtype in ['float64', 'int64']:
            for i in data_frame[c]:
                if not isinstance(i, Hashable):
                    cannot_hash.append(c)
                    break

    return [i for i in data_frame.columns if i not in cannot_hash] # no real cost with c = 41.


def same_dict(dict1, dict2, assumption=None):
    """

    Dict. values must be either str, int, float, tuples or lists.
    Tuples or lists must be homogenous with respect to type.
    Values that are lists of lists, lists of tuples or
    tuples of tuples or tuples of lists will break this function.

    :param dict1:
    :param dict2:
    :param assumption: assumption to make if no evaluation of dict. values could be made.
                       See description above for inputs which may return `assumption`. Defaults to ``None``.
    :return:
    """
    # Check Keys
    if not all(k2 in dict1.keys() for k2 in dict2.keys()):
        return False

    evaluations = list()
    for k in dict1:
        if all(isinstance(d[k], (str, int, float)) for d in (dict1, dict2)):
            evaluations.append(dict1[k] == dict2[k])
        elif all(isinstance(d[k], (tuple, list)) for d in (dict1, dict2)):
            evaluations.append(sorted(dict1[k]) == sorted(dict2[k]))
        else:
            return assumption # encountered a data type that cannot be assessed.

    # If all evaluations are True, return True; else False.
    return all(evaluations)


def unique_dics(list_of_dicts):
    """

    :param list_of_dicts:
    :return:
    """
    list_of_unique_dicts = list()

    for d in list_of_dicts:
        if not len(list_of_unique_dicts):
            list_of_unique_dicts.append(d)
        elif not any(same_dict(d, ud) for ud in list_of_unique_dicts):
            list_of_unique_dicts.append(d)

    return list_of_unique_dicts


def combine_dicts(dict_a, dict_b):
    """

    :param dict_a:
    :param dict_b:
    :return:
    """
    new = dict_a.copy()
    new.update(dict_b)
    return new


def images_in_dir(dir, return_len=False):
    """

    :param dir:
    :param return_len:
    :return:
    :rtype: ``int`` or ``list``
    """
    if not os.path.isdir(dir):
        raise FileNotFoundError("'{0}' does not exist.".format(str(dir)))
    image_types = (".png", ".jpg", ".tiff", ".gif")
    unnested_list = chain(*[k for i, j, k in os.walk(dir)])
    n_images = [i for i in unnested_list if any(t in i.lower() for t in image_types)]

    return len(n_images) if return_len else n_images


def only_numeric(s):
    """

    Remove all non-numeric characters from a string
    (excluding decimals).

    :param s: a string containing numbers
    :type s: ``str``
    :return: the number contained within ``s``.
    :rtype: ``float`` or ``None``
    """
    # See: http://stackoverflow.com/a/947789/4898004
    cleaned = re.sub(r'[^\d.]+', '', s).strip()
    return float(cleaned) if len(cleaned) else np.NaN












