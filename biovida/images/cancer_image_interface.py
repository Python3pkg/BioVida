"""

    The Cancer Imaging Archive Interface
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
import io
import os
import dicom
import pickle
import shutil
import zipfile
import requests
import numpy as np
import pandas as pd
from tqdm import tqdm
from PIL import Image
from itertools import chain

from biovida.images.ci_api_key import API_KEY

from biovida.support_tools._cache_management import package_cache_creator
from biovida.images._resources.cancer_image_parameters import CancerImgArchiveParams

from biovida.support_tools.support_tools import cln
from biovida.support_tools.support_tools import header
from biovida.support_tools.support_tools import only_numeric
from biovida.support_tools.support_tools import combine_dicts

cparam = CancerImgArchiveParams()
ref = cparam.cancer_img_api_ref()
dicom_m = cparam.dicom_modality_abbreviations('dict')


# ---------------------------------------------------------------------------------------------
# Summarize Studies Provided Through The Cancer Imaging Archive
# ---------------------------------------------------------------------------------------------


class CancerImgArchiveOverview(object):
    """

    Overview of Information Available on The Cancer Imaging Archive.

    :param cache_path: path to the location of the BioVida cache. If a cache does not exist in this location,
                        one will created. Default to ``None``, which will generate a cache in the home folder.
    :type cache_path: ``str`` or ``None``
    :param verbose: if ``True`` print additional information. Defaults to ``False``.
    :type verbose: ``bool``
    :param tcia_homepage: URL to the The Cancer Imaging Archive's homepage.
    :type tcia_homepage: ``str``
    """

    def __init__(self, verbose=False, cache_path=None, tcia_homepage='http://www.cancerimagingarchive.net'):
        self._verbose = verbose
        self._tcia_homepage = tcia_homepage
        _, self._created_img_dirs = package_cache_creator(sub_dir='images', cache_path=cache_path, to_create=['aux'])
        self.dicom_m = cparam.dicom_modality_abbreviations('dict')

    def _all_studies_parser(self):
        """

        Get a record of all studies on The Cancer Imaging Archive.

        :return: the table on the homepage
        :rtype: ``Pandas DataFrame``
        """
        # Extract the main summary table from the home page
        summary_df = pd.read_html(str(requests.get(self._tcia_homepage).text), header=0)[0]

        # Drop Studies which are 'Coming Soon'.
        summary_df = summary_df[summary_df['Status'].str.strip().str.lower() != 'coming soon']

        # Drop Studies which are on phantoms
        summary_df = summary_df[~summary_df['Location'].str.lower().str.contains('phantom')]

        # Drop Studies which are on mice or phantoms
        summary_df = summary_df[~summary_df['Collection'].str.lower().str.contains('mouse|phantom')]

        # Only Keep Studies which are public
        summary_df = summary_df[summary_df['Access'].str.strip().str.lower() == 'public'].reset_index(drop=True)

        # Add Full Name for Modalities
        summary_df['ModalitiesFull'] = summary_df['Modalities'].map(
            lambda x: [dicom_m.get(cln(i), i) for i in cln(x).split(", ")])

        # Parse the Location Column (and account for special case: 'Head-Neck').
        summary_df['Location'] = summary_df['Location'].map(
            lambda x: cln(x.replace(" and ", ", ").replace("Head-Neck", "Head, Neck")).split(", "))

        # Convert 'Update' to Datetime
        summary_df['Updated'] = pd.to_datetime(summary_df['Updated'], infer_datetime_format=True)

        # Clean Column names
        summary_df.columns = list(map(lambda x: cln(x, extent=2), summary_df.columns))

        return summary_df

    def _all_studies_cache_mngt(self, download_override):
        """

        Obtain and Manage a copy the table which summarizes the The Cancer Imaging Archive
        on the organization's homepage.

        :param download_override: If ``True``, override any existing database currently cached and download a new one.
        :type download_override: ``bool``
        :return: summary table hosted on the home page of The Cancer Imaging Archive.
        :rtype: ``Pandas DataFrame``
        """
        # Define the path to save the data
        save_path = os.path.join(self._created_img_dirs['aux'], 'all_tcia_studies.p')

        if not os.path.isfile(save_path) or download_override:
            if self._verbose:
                header("Downloading Record of Available Studies... ", flank=False)
            summary_df = self._all_studies_parser()
            summary_df.to_pickle(save_path)
        else:
            summary_df = pd.read_pickle(save_path)

        return summary_df

    def _studies_filter(self, summary_df, cancer_type, location, modality):
        """

        Apply Filters passed to ``studies()``.

        :param summary_df: see: ``studies()``.
        :type summary_df: ``Pandas DataFrame``
        :param cancer_type: see: ``studies()``.
        :type cancer_type: ``str``, ``iterable`` or ``None``
        :param location: see: ``studies()``.
        :type location: ``str``, ``iterable`` or ``None``
        :param modality: see: ``studies()``.
        :type modality: ``str``, ``iterable`` or ``None``
        :return: ``summary_df`` with filters applied.
        :type: ``Pandas DataFrame``
        """
        # Filter by `cancer_type`
        if isinstance(cancer_type, (str, list, tuple)):
            if isinstance(cancer_type, (list, tuple)):
                cancer_type = "|".join(map(lambda x: cln(x).lower(), cancer_type))
            else:
                cancer_type = cln(cancer_type).lower()
            summary_df = summary_df[summary_df['CancerType'].str.lower().str.contains(cancer_type)]

        # Filter by `location`
        if isinstance(location, (str, list, tuple)):
            location = [location] if isinstance(location, str) else location
            summary_df = summary_df[summary_df['Location'].map(
                lambda x: any([cln(l).lower() in i.lower() for i in x for l in location]))]

        # Filter by `modality`.
        if isinstance(modality, (str, list, tuple)):
            modality = [modality] if isinstance(modality, str) else modality
            summary_df = summary_df[summary_df['Modalities'].map(
                lambda x: any([cln(m).lower() in i.lower() for i in cln(x).split(", ") for m in modality]))]

        return summary_df

    def studies(self, collection=None, cancer_type=None, location=None, modality=None, download_override=False):
        """

        Method to Search for studies on The Cancer Imaging Archive.

        :param collection: a collection (study) hosted by The Cancer Imaging Archive.
        :type collection: ``str`` or ``None``
        :param cancer_type: a string or list/tuple of specifying cancer types.
        :type cancer_type: ``str``, ``iterable`` or ``None``
        :param location: a string or list/tuple of specifying body locations.
        :type location: ``str``, ``iterable`` or ``None``
        :param modality: see: ``CancerImgArchiveOverview().dicom_m`` for valid values (the keys must be used).
        :type modality: ``str``, ``iterable`` or ``None``
        :param download_override: If ``True``, override any existing database currently cached and download a new one.
                                  Defaults to ``False``.
        :return: a dataframe containing the search results.
        :rtype: ``Pandas DataFrame``

        :Example:

        >>> CancerImgArchiveOverview().studies(cancer_type=['Squamous'], location=['head'])
        ...
           Collection               CancerType               Modalities  Subjects     Location    Metadata  ...
        0  TCGA-HNSC  Head and Neck Squamous Cell Carcinoma  CT, MR, PT     164     [Head, Neck]    Yes     ...

        """
        # Load the Summary Table
        summary_df = self._all_studies_cache_mngt(download_override)

        # Filter by `collection`
        if isinstance(collection, str) and any(i is not None for i in (cancer_type, location)):
            raise ValueError("Both `cancer_types` and `location` must be ``None`` if a `collection` name is passed.")
        elif isinstance(collection, str):
            summary_df = summary_df[summary_df['Collection'].str.strip().str.lower() == collection.strip().lower()]
            if summary_df.shape[0] == 0:
                raise AttributeError("No Collection with the name '{0}' could be found.".format(collection))
            else:
                return summary_df

        # Apply Filters
        summary_df = self._studies_filter(summary_df, cancer_type, location, modality)

        if summary_df.shape[0] == 0:
            raise AttributeError("No Results Found. Try Broadening the Search Criteria.")
        else:
            return summary_df.reset_index(drop=True)


# ---------------------------------------------------------------------------------------------
# Pull Records from The Cancer Imaging Archive
# ---------------------------------------------------------------------------------------------


study = 'ISPY1'
root_url = 'https://services.cancerimagingarchive.net/services/v3/TCIA'

# Overview:
#     1. Pick a Study
#     2. Download all the patients in that study
#     3. Make API calls as the program loops though getSeries' queries.
#     4. patient_limit to baseline images (from StudyInstanceUID)


def _extract_study(study):
    """

    Download all patients in a given study.

    :param study:
    :type study: ``str``
    :return:
    """
    url = '{0}/query/getPatientStudy?Collection={1}&format=csv&api_key={2}'.format(root_url, study, API_KEY)
    return pd.DataFrame.from_csv(url).reset_index()


def _date_index_map(list_of_dates):
    """

    Returns a dict of the form: ``{date: index in ``list_of_dates``, ...}``

    :param list_of_dates:
    :type list_of_dates:
    :return:
    """
    return {k: i for i, k in enumerate(sorted(list_of_dates), start=1)}


def _summarize_study_by_patient(study):
    """

    Summarizes a study by patient.
    Note: patient_limits summary to baseline (i.e., follow ups are excluded).

    :param study:
    :type study: ``str``
    :return: nested dictionary of the form:

            ``{PatientID: {StudyInstanceUID: {'sex':..., 'age': ..., 'session': ..., 'StudyDate': ...}}}``

    :rtype: ``dict``
    """
    # Download a summary of all patients in a study
    study_df = _extract_study(study)

    # Convert StudyDate to datetime
    study_df['StudyDate'] = pd.to_datetime(study_df['StudyDate'], infer_datetime_format=True)

    # Divide Study into stages (e.g., Baseline (session 1); Baseline + 1 Month (session 2), etc.
    stages = study_df.groupby('PatientID').apply(lambda x: _date_index_map(x['StudyDate'].tolist())).to_dict()

    # Apply stages
    study_df['Session'] = study_df.apply(lambda x: stages[x['PatientID']][x['StudyDate']], axis=1)

    # Define Columns to Extract from study_df
    valuable_cols = ('PatientID', 'StudyInstanceUID', 'Session', 'PatientSex', 'PatientAge', 'StudyDate')

    # Convert to a nested dictionary
    patient_dict = dict()
    for pid, si_uid, session, sex, age, date in zip(*[study_df[c] for c in valuable_cols]):
        inner_nest = {'sex': sex, 'age': age, 'session': session, 'StudyDate': date}
        if pid not in patient_dict:
            patient_dict[pid] = {si_uid: inner_nest}
        else:
            patient_dict[pid] = combine_dicts(patient_dict[pid], {si_uid: inner_nest})

    return patient_dict


def _patient_img_summary(patient, patient_dict):
    """

    Harvests the Cancer Image Archive's Text Record of all baseline images for a given patient
    in a given study.

    :param patient:
    :return:
    """
    # Select an individual Patient
    url = '{0}/query/getSeries?Collection=ISPY1&PatientID={1}&format=csv&api_key={2}'.format(
        root_url, patient, API_KEY)
    patient_df = pd.DataFrame.from_csv(url).reset_index()

    def upper_first(s):
        return "{0}{1}".format(s[0].upper(), s[1:])

    # Add Sex, Age, Session, and StudyDate
    patient_info = patient_df['StudyInstanceUID'].map(
        lambda x: {upper_first(k): patient_dict[x][k] for k in ('sex', 'age', 'session', 'StudyDate')})
    patient_df = patient_df.join(pd.DataFrame(patient_info.tolist()))

    # Add PatientID
    patient_df['PatientID'] = patient

    return patient_df


def _clean_patient_study_df(patient_study_df):
    """

    Cleans the input in the following ways:

    - convert 'F' --> 'Female' and 'M' --> 'Male'

    - Converts the 'Age' column to numeric (years)

    - Remove line breaks in the 'ProtocolName' and 'SeriesDescription' columns

    - Add Full name for modality (ModalityFull)

    - Convert the 'SeriesDate' column to datetime

    :param patient_study_df: the ``patient_study_df`` dataframe evolved inside ``_pull_records()``.
    :type patient_study_df: ``Pandas DataFrame``
    :return: a cleaned ``patient_study_df``
    :rtype: ``Pandas DataFrame``
    """
    # convert 'F' --> 'female' and 'M' --> 'male'.
    patient_study_df['Sex'] = patient_study_df['Sex'].map(
        lambda x: {'F': 'female', 'M': 'male'}.get(cln(str(x)).upper(), x), na_action='ignore')

    # Convert entries in the 'Age' Column to floats.
    patient_study_df['Age'] = patient_study_df['Age'].map(
        lambda x: only_numeric(x) / 12.0 if 'M' in str(x).upper() else only_numeric(x), na_action='ignore')

    # Remove unneeded line break marker
    for c in ('ProtocolName', 'SeriesDescription'):
        patient_study_df[c] = patient_study_df[c].map(lambda x: cln(x.replace("\/", " ")), na_action='ignore')

    # Add the full name for modality.
    patient_study_df['ModalityFull'] = patient_study_df['Modality'].map(
        lambda x: dicom_m.get(x, np.NaN), na_action='ignore')

    # Convert SeriesDate to datetime
    patient_study_df['SeriesDate'] = pd.to_datetime(patient_study_df['SeriesDate'], infer_datetime_format=True)

    # Sort and Return
    return patient_study_df.sort_values(by=['PatientID', 'Session'])


def _pull_records(study, patient_limit=3):
    """

    Extract record of all images for all patients in a given study.

    :param study:
    :type study: ``str``
    :param patient_limit: patient_limit on the number of patients to extract.
                         Patient IDs are sorted prior to this patient_limit being imposed.
                         If ``None``, no patient_limit will be imposed. Defaults to `3`.
    :type patient_limit: ``int`` or ``None``
    :return: a dataframe of all baseline images
    :rtype: ``Pandas DataFrame``
    """
    # ToDo: add illness name to dataframe.
    # Summarize a study by patient
    study_dict = _summarize_study_by_patient(study)

    # Check for invalid `patient_limit` values:
    if not isinstance(patient_limit, int) and patient_limit is not None:
        raise ValueError('`patient_limit` must be an integer or `None`.')
    elif isinstance(patient_limit, int) and patient_limit < 1:
        raise ValueError('If `patient_limit` is an integer it must be greater than or equal to 1.')

    # Define number of patients to extract
    s_patients = sorted(study_dict.keys())
    patients_to_obtain = s_patients[:patient_limit] if isinstance(patient_limit, int) else s_patients

    # Evolve a dataframe ('frame') for the baseline images of all patients
    frames = list()
    for patient in tqdm(patients_to_obtain):
        frames.append(_patient_img_summary(patient, patient_dict=study_dict[patient]))

    # Concatenate baselines frame for each patient
    patient_study_df = pd.concat(frames, ignore_index=True)

    # Add Study name
    patient_study_df['StudyName'] = study

    # Clean the dataframe and return
    return _clean_patient_study_df(patient_study_df)


def _download_zip(url, save_location="/Users/tariq/Desktop/temp"):
    """

    :param url:
    :param save_location:
    :return: list of paths to the new files.
    """
    # See: http://stackoverflow.com/a/14260592/4898004
    r = requests.get(url)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    z.extractall(save_location)
    def file_path_full(f):
        base_name = cln(os.path.basename(f.filename))
        return os.path.join(save_location, base_name) if len(base_name) else None
    return list(filter(None, [file_path_full(f) for f in z.filelist]))


def _image_processing(f, pull_position, conversion, save_location, new_file_name, img_format, override_existing=False):
    """

    This method handles the act of saving images.
    An image (``f``) can be either 2 or 3 Dimensional.

    :param f:
    :param pull_position: the position of the file in the list of files pulled from the database.
    :type pull_position: ``int``
    :param conversion:
    :param save_location:
    :param new_file_name:
    :type new_file_name: ``str``
    :param img_format:
    :type img_format: ``str``
    :return:
    """
    # Define a list to populate with a record of all images saved
    all_save_paths = list()

    # Extract a pixel array from the dicom file.
    pixel_arr = f.pixel_array

    def save_path(instance):
        """Define the path to save the image to."""
        head = "{0}_{1}".format(instance, pull_position)
        file_name = "{0}__{1}__D.{2}".format(head, os.path.basename(new_file_name), img_format.replace(".", ""))
        return os.path.join(save_location, file_name)

    if pixel_arr.ndim == 2:
        # Define save name by combining the images instance in the set, `new_file_name` and `img_format`.
        instance = cln(str(f.InstanceNumber)) if len(cln(str(f.InstanceNumber))) else '0'
        path = save_path(instance)
        if not os.path.isfile(path) or override_existing:
            Image.fromarray(pixel_arr).convert(conversion).save(path)
        all_save_paths.append(path)
    # If ``f`` is a 3D image (e.g., segmentation dicom files), save each layer as a seperate file/image.
    elif pixel_arr.ndim == 3:
        for instance, layer in enumerate(range(pixel_arr.shape[0]), start=1):
            path = save_path(instance)
            if not os.path.isfile(path) or override_existing:
                Image.fromarray(pixel_arr[layer:layer + 1][0]).convert(conversion).save(path)
            all_save_paths.append(path)
    else:
        raise ValueError("Cannot coerce {0} dimensional image arrays. Images must be 2D or 3D.".format(pixel_arr.ndim))

    return all_save_paths


def _save_dicom(path_to_dicom_file, save_location, pull_position, save_name=None, color=False, img_format='png'):
    """

    Save a DICOM image as a more common file format.

    :param path_to_dicom_file: path to a dicom image
    :type path_to_dicom_file: ``str``
    :param save_location: directory to save the converted image to
    :type save_location: ``str``
    :param pull_position:
    :type pull_position: ``int``
    :param save_name: name of the new file (do *NOT* include a file extension).
                      To specifiy a file format, use ``img_format``.
                      If ``None``, name from ``path_to_dicom_file`` will be conserved.
    :type save_name: ``str``
    :param color: If ``True``, convert the image to RGB before saving. If ``False``, save as a grayscale image.
                  Defaults to ``False``
    :type color: ``bool``
    :param img_format: format for the image, e.g., 'png', 'jpg', etc. Defaults to 'png'.
    :type img_format: ``str``
    """
    # Load the DICOM file into RAM
    f = dicom.read_file(path_to_dicom_file)

    # Conversion (needed so the resultant image is not pure black)
    conversion = 'RGB' if color else 'LA'  # note: 'LA' = grayscale.

    if isinstance(save_name, str):
        new_file_name = save_name
    else:
        # Remove the file extension and then extract the base name from the path.
        new_file_name = os.path.basename(os.path.splitext(path_to_dicom_file)[0])

    # Convert the image into a PIL object and Save
    return _image_processing(f, pull_position, conversion, save_location, new_file_name, img_format)


def _move_dicom_files(dicom_files, series_abbreviation, dicoms_save_location):
    """

    Move the dicom source files to ``dicoms_save_location``.
    Employ to prevent the raw dicom files from being destroyed.

    :param dicom_files:
    :param series_abbreviation:
    :param dicoms_save_location:
    :return:
    """
    new_dircom_paths = list()
    for f in dicom_files:
        f_parsed = list(os.path.splitext(os.path.basename(f)))
        new_dicom_file_name = "{0}__{1}{2}".format(f_parsed[0], series_abbreviation, f_parsed[1])

        # Define the location of the new files
        new_location = os.path.join(dicoms_save_location, new_dicom_file_name)
        new_dircom_paths.append(new_location)

        # Move the dicom file from __temp__ --> to --> new location
        os.rename(f, new_location)

    return tuple(new_dircom_paths)


def _image_downloads_engine(img_records, save_location, dicoms_save_location, img_format):
    """

    :param img_records:
    :return:
    """
    converted_files, raw_dicom_files = list(), list()

    # Note: tqdm appears to be unstable with generators (hence `list()`).
    pairings = list(zip(*[img_records[c] for c in ('SeriesInstanceUID', 'PatientID')]))

    for series_uid, patient_id in tqdm(pairings):
        # Define a temporary folder to save the raw dicom files to
        temp_folder = os.path.join(save_location, "__temp__")
        if os.path.isdir(temp_folder):
            shutil.rmtree(temp_folder, ignore_errors=True)
        os.makedirs(temp_folder)

        # Define URL to extract the images from
        url = '{0}/query/getImage?SeriesInstanceUID={1}&format=csv&api_key={2}'.format(root_url, series_uid, API_KEY)

        # Download the images into a temp. folder
        dicom_files = _download_zip(url, temp_folder)

        # Compose central part of the file name from 'PatientID' and the last ten digits of 'SeriesInstanceUID'
        # (the last ten digits is what the cancer imaging archive uses to reference images cached in their database).
        series_abbreviation = "{0}_{1}".format(patient_id, str(series_uid)[-10:])

        # Save all images in the Series
        cfs = [_save_dicom(f, save_location, pull_position=e, save_name=series_abbreviation, img_format=img_format)
               for e, f in enumerate(dicom_files, start=1)]
        converted_files.append(cfs)

        # ToDo: add real-time record keeping for files as they download.
        if isinstance(dicoms_save_location, str):
            raw_dicom_files.append(_move_dicom_files(dicom_files, series_abbreviation, dicoms_save_location))
        else:
            raw_dicom_files.append(np.NaN)

        # Delete the `__temp__` folder.
        shutil.rmtree(temp_folder, ignore_errors=True)

    # Return the position of all files (flatten the inner most dimension for `converted_files` first).
    return [tuple(chain(*cf)) for cf in converted_files], raw_dicom_files


def _pull_images(records, save_location, session_limit=1, img_format='png', dicoms_save_location=None):
    """

    :param records:
    :param save_location:
    :param session_limit: restruct image harvesting to the first ``n`` sessions, where ``n`` is the value passed
                          to this parameter. If ``None``, no limit will be imposed. Defaults to 1.
    :type session_limit: ``int``
    :param img_format:
    :param dicoms_save_location:
    :return:
    """
    # ToDo: move `img_format` to class' init.

    # Apply limit on number of sessions, if any
    if isinstance(session_limit, int):
        if session_limit < 1:
            raise ValueError("`session_limit` must be an intiger greater than or equal to 1.")
        img_records = records[records['Session'].map(
            lambda x: float(x) <= session_limit if pd.notnull(x) else False)].reset_index(drop=True)

    # if verbose:
    #   header("Downloading Batches of Images... ")
    # Harvest images
    converted_files, raw_dicom_files = _image_downloads_engine(img_records,
                                                               save_location,
                                                               dicoms_save_location,
                                                               img_format)

    # Add paths to the images
    img_records['ConvertedFilesPaths'] = converted_files
    img_records['RawDicomFilesPaths'] = raw_dicom_files

    return img_records










































