"""Code that evaluates the quality of the MVM products generated by the drizzlepac package.

This module is ONLY for generating the output JSON information.  Visualization is
done by mvm_quality_graphics.py.

The JSON files generated here can be converted directly into a Pandas DataFrame
using the syntax:

>>> import json
>>> import pandas as pd
>>> with open("<rootname>_astrometry_resids.json") as jfile:
>>>     resids = json.load(jfile)
>>> pdtab = pd.DataFrame(resids)

These DataFrames can then be concatenated using:

>>> allpd = pdtab.concat([pdtab2, pdtab3])

where 'pdtab2' and 'pdtab3' are DataFrames generated from other datasets.  For
more information on how to merge DataFrames, see

https://pandas.pydata.org/pandas-docs/stable/user_guide/merging.html

Visualization of these Pandas DataFrames with Bokeh can follow the example
from:

https://programminghistorian.org/en/lessons/visualizing-with-bokeh

"""

# Standard library imports
import argparse
from datetime import datetime
import os
import pickle
import sys
import time

# Related third party imports
from astropy.io import fits

# Local application imports
from drizzlepac import util, wcs_functions
import drizzlepac.haputils.diagnostic_utils as du
import numpy as np
from stsci.tools import logutil
from stwcs.wcsutil import HSTWCS

__taskname__ = 'mvm_quality_analysis'

MSG_DATEFMT = '%Y%j%H%M%S'
SPLUNK_MSG_FORMAT = '%(asctime)s %(levelname)s src=%(name)s- %(message)s'
log = logutil.create_logger(__name__, level=logutil.logging.NOTSET, stream=sys.stdout,
                            format=SPLUNK_MSG_FORMAT, datefmt=MSG_DATEFMT)
# ----------------------------------------------------------------------------------------------------------------------

def report_wcsname(total_product_list, json_timestamp=None, json_time_since_epoch=None,
               log_level=logutil.logging.NOTSET):
    """Report the WCSNAME for each input exposure of an MVM product

    Parameters
    ----------
    total_product_list: list of HAP TotalProduct objects, one object per instrument detector
    (drizzlepac.haputils.Product.TotalProduct)

    json_timestamp: str, optional
        Universal .json file generation date and time (local timezone) that will be used in the instantiation
        of the HapDiagnostic object. Format: MM/DD/YYYYTHH:MM:SS (Example: 05/04/2020T13:46:35). If not
        specified, default value is logical 'None'

    json_time_since_epoch : float
        Universal .json file generation time that will be used in the instantiation of the HapDiagnostic
        object. Format: Time (in seconds) elapsed since January 1, 1970, 00:00:00 (UTC). If not specified,
        default value is logical 'None'

    log_level : int, optional
        The desired level of verboseness in the log statements displayed on the screen and
        written to the .log file.  Default value is 'NOTSET'.
    """
    log.setLevel(log_level)
    log.info('\n\n*****     Begin Quality Analysis Test: report_wcsname.     *****\n')

    # Generate a separate JSON file for each TotalProduct which is really a filter-level product for MVM processing
    # The "total product" references are a throw-back to SVM processing
    for total_product in total_product_list:

        instrument = total_product.instrument
        detector = total_product.detector

        # Construct the output JSON filename
        json_filename = '_'.join([total_product.product_basename, 'mvm_wcsname.json'])

        # Set up the diagnostic object
        diagnostic_obj = du.HapDiagnostic()
        diagnostic_obj.instantiate_from_hap_obj(total_product,
                                                data_source='{}.report_wcsname'.format(__taskname__),
                                                description='WCS information',
                                                timestamp=json_timestamp,
                                                time_since_epoch=json_time_since_epoch)

        # Get the WCS for the entire MVM layer
        metawcs = HSTWCS(total_product.drizzle_filename, ext=1)

        # Numerical count of the SCI extensions to pick out the
        # correct numpy array from the sregion
        counter = 0

        # Loop over all the individual exposures in the list which comprise the layer
        for edp_object in total_product.edp_list:
            
            # Open the exposure file
            exp = fits.open(edp_object.full_filename)

            # Each chip belonging to the same exposure/image in a filter-level product
            # will be assigned a value of 2**n so the exposure/image can be uniquely identified
            expo_img_value = 2**counter

            # Determine the number of extensions ...
            sci_extns = wcs_functions.get_extns(exp)
            if len(sci_extns) == 0 and '_single' in edp_object.full_filename:
                sci_extns = [0]

            # ... and loop over the SCI extensions (each SCI extension is a chip)
            for sci in sci_extns:
                wcs = HSTWCS(exp, ext=sci)

                # Get the WCSNAME for this specific exposure/chip
                wcsname = exp[sci].header['WCSNAME']

                # If this is a multi-chip exposure, get the CHIP number
                chip_number = 0
                try:
                    chip_number = exp[sci].header['CCDCHIP']
                except:
                    pass

                # Compute the sky footprint for this chip and then the X and Y positions
                radec = wcs.calc_footprint().tolist()
                radec.append(radec[0])  # close the polygon/chip
                ra = [item[0] for item in radec]
                dec = [item[1] for item in radec]

                # Also save those corner positions as X,Y positions in the footprint
                # User the xc and yc in visualization
                xycorners = metawcs.all_world2pix(radec, 0).astype(np.int32).tolist()
                xc = [item[0] for item in xycorners]
                yc = [item[1] for item in xycorners]

                # Load the dictionary with the collected data for this exposure
                active_wcs_dict = {'filename': edp_object.full_filename,
                                   'instrument': instrument,
                                   'detector': detector,
                                   'primary_wcsname': wcsname,
                                   'chip_number': chip_number,
                                   'value': expo_img_value,
                                   'RA': ra,
                                   'Dec': dec,
                                   'X': xc,
                                   'Y': yc}

                # Make the PrimaryWCS unique for every exposure/chip to ensure no entry is overwritten.
                diagnostic_obj.add_data_item(active_wcs_dict, 'PrimaryWCS' + str(counter) + "_" + str(chip_number), 
                                             descriptions={'filename': 'Exposure filename',
                                                           'instrument': 'Instrument',
                                                           'detector': 'Detector',
                                                           'primary_wcsname': 'Active WCS',
                                                           'chip_number': 'CCD Chip Number',
                                                           'value': 'Value (2^n) to assign to the footprint',
                                                           'RA': 'Right Ascension of Polygon which defines footprint corners',
                                                           'Dec': 'Declination of Polygon which defines footprint corners',
                                                           'X': 'X position of Polygon which defines footprint corners',
                                                           'Y': 'Y position of Polygon which defines footprint corners'},
                                             units={'filename': 'unitless',
                                                    'instrument': 'unitless',
                                                    'detector': 'unitless',
                                                    'primary_wcsname': 'unitless',
                                                    'chip_number': 'unitless',
                                                    'value': 'unitless',
                                                    'RA': 'degrees',
                                                    'Dec': 'degrees',
                                                    'X': 'pixels',
                                                    'Y': 'pixels'})

            # Clean up and get ready for the next exposure
            counter += 1
            exp.close()

        # Write out the file
        diagnostic_obj.write_json_file(json_filename)

        # Clean up
        del diagnostic_obj

# ----------------------------------------------------------------------------------------------------------------------
def run_quality_analysis(total_obj_list,
                         run_report_wcsname=True,
                         log_level=logutil.logging.NOTSET):
    """Run the quality analysis functions

    Parameters
    ----------
    total_obj_list : list
        List of SkyCellProducts (equivalent of SVM FilterDataProducts)

    run_report_wcsname : bool, optional
        Run 'report_wcsname' test? Devault value is True.

    log_level : int, optional
        The desired level of verboseness in the log statements displayed on the screen and written to the
        .log file. Default value is 'NOTSET'.

    Returns
    -------
    Nothing.
    """
    log.setLevel(log_level)

    # generate a timestamp values that will be used to make creation time, creation date and epoch values
    # common to each json file
    json_timestamp = datetime.now().strftime("%m/%d/%YT%H:%M:%S")
    json_time_since_epoch = time.time()

    # Report WCSNAME
    if run_report_wcsname:
        try:
            report_wcsname(total_obj_list, json_timestamp=json_timestamp, json_time_since_epoch=json_time_since_epoch,
                       log_level=log_level)
        except Exception:
            log.warning("WCS reporting (report_wcsname) encountered a problem.")
            log.exception("message")
            log.warning("Continuing to next test...")


# ============================================================================================================


if __name__ == "__main__":
    # process command-line inputs with argparse
    parser = argparse.ArgumentParser(description='Perform quality assessments of the MVM products generated '
                                                 'by the drizzlepac package. NOTE: if no QA switches '
                                                 'are specified, ALL QA steps will be executed.')
    parser.add_argument('input_filename', help='_total_list.pickle file that holds vital information about '
                                               'the processing run')
    parser.add_argument('-wcs', '--run_report_wcsname', required=False, action='store_true',
                        help="Report the WCSNAME information for each exposure of an MVM layer product")
    parser.add_argument('-l', '--log_level', required=False, default='info',
                        choices=['critical', 'error', 'warning', 'info', 'debug'],
                        help='The desired level of verbosity in the log statements displayed on the screen '
                             'and written to the .log file. The level of verbosity increases from left to right, and '
                             'includes all log statements with a log_level left of the specified level. '
                             'Specifying "critical" will only record/display "critical" log statements, and '
                             'specifying "error" will record/display both "error" and "critical" log '
                             'statements, and so on.')
    user_args = parser.parse_args()

    # set up logging
    log_dict = {"critical": logutil.logging.CRITICAL,
                "error": logutil.logging.ERROR,
                "warning": logutil.logging.WARNING,
                "info": logutil.logging.INFO,
                "debug": logutil.logging.DEBUG}
    log_level = log_dict[user_args.log_level]
    log.setLevel(log_level)

    # verify that input file exists
    if not os.path.exists(user_args.input_filename):
        err_msg = "File {} doesn't exist.".format(user_args.input_filename)
        log.critical(err_msg)
        raise Exception(err_msg)

    #  check that at least one QA switch is turned on
    all_qa_steps_off = True
    max_step_str_length = 0
    for kv_pair in user_args._get_kwargs():
        if kv_pair[0] not in ['input_filename', 'run_all', 'log_level']:
            if len(kv_pair[0])-4 > max_step_str_length:
                max_step_str_length = len(kv_pair[0])-4
            if kv_pair[1]:
                all_qa_steps_off = False

    # if no QA steps are explicitly turned on in the command-line call, run ALL the QA steps
    if all_qa_steps_off:
        log.info("No specific QA switches were turned on. All QA steps will be executed.")
        user_args.run_report_wcs = True

    # display status summary indicating which QA steps are turned on and which steps are turned off
    toplinestring = "-"*(int(max_step_str_length/2)-6)
    log.info("{}QA step run status{}".format(toplinestring, toplinestring))
    for kv_pair in user_args._get_kwargs():
        if kv_pair[0] not in ['input_filename', 'run_all', 'log_level']:
            if kv_pair[1]:
                run_status = "ON"
            else:
                run_status = "off"
            log.info("{}{}   {}".format(kv_pair[0][4:], " "*(max_step_str_length-(len(kv_pair[0])-4)),
                                        run_status))
    log.info("-"*(max_step_str_length+6))

    # execute specified tests
    filehandler = open(user_args.input_filename, 'rb')
    total_obj_list = pickle.load(filehandler)
    run_quality_analysis(total_obj_list,
                         run_report_wcs=user_args.run_report_wcs,
                         log_level=log_level)


