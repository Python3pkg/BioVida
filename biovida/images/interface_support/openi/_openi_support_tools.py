"""

    Support Tools for the `images` Subpackage
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
# Imports
import re
from itertools import chain
from urllib.parse import urlsplit # handle python 2

# General Support tools
from biovida.support_tools.support_tools import cln
from biovida.support_tools._support_data import age_dict
from biovida.support_tools.support_tools import unescape
from biovida.support_tools.support_tools import items_null

# Regex for ``extract_float()``
non_decimal = re.compile(r'[^\d.]+')


# ----------------------------------------------------------------------------------------------------------
# General Support Tools
# ----------------------------------------------------------------------------------------------------------


class ImageProblemBasedOnText(Exception):
    pass


def iter_join(t, join_on="_"):
    """

    Convert an iterabe (``t``) to a string by joining on ``join_on``.

    :param t: any iterable.
    :type t: ``iterable``
    :param join_on: a string to join ``t`` on.
    :type join_on: ``str``
    :return: ``t`` as a string.
    :rtype: ``str``
    """
    return join_on.join(t) if isinstance(t, (list, tuple)) else i


def null_convert(i):
    """

    Convert ``i`` to ``None`` if it is void else ``i`` is returned.

    :param i: any.
    :type i: ``any``
    :return: None ``i`` is void (e.g., '' or []) else ``i``.
    :rtype: ``None`` else ``type(i)``
    """
    return None if not i else i


def url_combine(url1, url2):
    """

    Combines two urls into one.

    :param url1: a URL.
    :type url1: ``str``
    :param url2: a URL.
    :type url2: ``str``
    :return: a string of the form ``url1/url2``.
    :rtype: ``None`` or ``str``
    """
    if any(x is None or items_null(x) for x in [url1, url2]):
        return None
    else:
        left = url1[:-1] if url1.endswith("/") else url1
        right = url2[1:] if url2.startswith("/") else url2
        return "{0}/{1}".format(left, right)


def item_extract(i, list_len=1):
    """

    Extract the first item in a list or tuple, else return ``None``.

    :param i: any list or tuple.
    :type i: ``list`` or ``tuple``
    :param list_len: required length of ``i``. Defaults to `1`.
    :type list_len: ``int``
    :return: the first element in ``i`` if ``i`` is a ``list`` or ``tuple`` and ``len(i) == list_len``.
    :rtype: ``type(i[0])`` or ``None``
    """
    return i[0] if isinstance(i, (list, tuple)) and len(i) == list_len else None


def extract_float(i):
    """

    Extract a d from a string ``i``

    :param i: a string.
    :type i: ``str``
    :return: the floating point number in ``i`` as a string.
    :rtype: ``str``
    """
    # Source: http://stackoverflow.com/a/947789/4898004
    return non_decimal.sub('', i)


def multiple_decimal_remove(s):
    """

    Remove multiple decimal from a string (``s``)

    :param s: a string.
    :type s: ``str``
    :return: ``s`` with only one.
    :rtype: ``None`` or ``str``
    """
    if isinstance(s, (int, float)):
        return s

    s_cln = cln(extract_float(str(s)), extent=2)
    if s_cln.startswith('.') and s_cln.endswith('.'):
        return None

    s_repeats_rmv = re.sub(r'\.+', '.', s_cln)
    if s_repeats_rmv.count('.') > 1:
        return None
    else:
        return cln(s_repeats_rmv, extent=2)


def filter_unnest(l, filter_for=None):
    """

    Filters out ``filter_for`` and flattens ``l``.

    :param l: a 2D iterable.
    :type l: ``iterable``
    :param filter_for: items to be removed. Defaults to ``None``.
    :type filter_for: any
    :return: ``l`` flattened with ``filter_for`` removed.
    :rtype: ``list``
    """
    return list(chain(*filter(filter_for, l)))


def num_word_to_int(input_str):
    """

    Replace natural numbers from 1 to 130 with integers.

    :param input_str: any string.
    :rtype input_str: ``str``
    :return: ``input_str`` with all numbers from 1-130 in natural language (e.g., 'twenty-five')
             with the integer equivalent.
    :rtype: ``str``
    """
    for w, i in age_dict.items():
        for case in [w.upper(), w.lower(), w.title()]: # not perfect, but should do
            input_str = input_str.replace(case, str(i))
    return input_str


def url_path_extract(url):
    """

    Extracts the path for a given URL.

    :param url: a Uniform Resource Locator (URL).
    :rtype url: ``str``
    :return: the path for ``url``.
    :rtype: ``str``
    """
    return urlsplit(url).path[1:].replace("/", "__")


def _mesh_cleaner(mesh):
    """

    Clean mesh terms by cleaning them.

    :param mesh: a list of mesh terms.
    :type mesh: ``tuple`` or ``list``
    :return: a cleaned tuple of mesh terms.
    :rtype: ``tuple`` or ``type(mesh)``
    """
    if isinstance(mesh, (list, tuple)):
        return tuple([cln(unescape(i)) if isinstance(i, str) else i for i in mesh])
    else:
        return mesh


def ensure_records_db_hashable(data_frame):
    """

    Ensure the records dataframe can be hashed (i.e., ensure pandas.DataFrame.drop_duplicates does not fail).

    :param data_frame: the dataframe evolved inside ``biovida.images.openi_interface._OpeniRecords()._df_processing()``.
    :type data_frame: ``Pandas DataFrame``
    :return: ``data_frame`` corrected such that all columns considered can be hashed.
    :rtype: ``Pandas DataFrame``
    """
    # Escape HTML elements in the 'image_caption' and 'image_mention' columns.
    for c in ('image_caption', 'image_mention'):
        data_frame[c] = data_frame[c].map(lambda x: cln(unescape(x)) if isinstance(x, str) else x, na_action='ignore')

    # Clean mesh terms
    for c in ('mesh_major', 'mesh_minor'):
        data_frame[c] = data_frame[c].map(_mesh_cleaner, na_action='ignore')

    # Conver all elements in the 'license_type' and 'license_url' columns to string.
    for c in ('license_type', 'license_url'):
        data_frame[c] = data_frame[c].map(lambda x: "; ".join(map(str, x)) if isinstance(x, (list, tuple)) else x,
                                          na_action='ignore')

    return data_frame

















