"""

    Support Tools used Across the BioVida API
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


"""
# Imports
import re


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
    if isinstance(element, (list, tuple, type(np.array))):
        return True if all(pd.isnull(i) for i in element) else False
    else:
        return pd.isnull(element)


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
    sep_line = "".join(["-"] * len(string))

    # Display
    if flank: print("\n")
    print("\n{0}\n{1}\n{2}\n".format(sep_line, string, sep_line))
    if flank: print("\n")


def camel_to_snake_case(name):
    """Source: http://stackoverflow.com/a/1176023/4898004"""
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
































































