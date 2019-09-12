"""Utilities to interpret the pipeline poller obset information and generate product filenames

The function, interpret_obset_input, parses the file generated by the pipeline
poller, and produces a tree listing of the output products.  The function,
parse_obset_tree, converts the tree into product catagories.

"""
import sys
from stsci.tools import logutil

from astropy.table import Table, Column
from drizzlepac.hlautils.product import ExposureProduct, FilterProduct, TotalProduct

# Define information/formatted strings to be included in output dict
SEP_STR = 'single exposure product {:02d}'
FP_STR = 'filter product {:02d}'
TDP_STR = 'total detection product {:02d}'

# Define the mapping between the first character of the filename and the associated instrument
INSTRUMENT_DICT = {'i': 'WFC3', 'j': 'ACS', 'o': 'STIS', 'u': 'WFPC2', 'x': 'FOC', 'w': 'WFPC'}

__taskname__ = 'poller_utils'
log = logutil.create_logger('poller_utils', level=logutil.logging.INFO, stream=sys.stdout)

def interpret_obset_input(results):
    """
    Interpret the database query for a given obset to prepare the returned
    values for use in generating the names of all the expected output products.

    Input will have format of:
        ib4606c5q_flc.fits,11665,B46,06,1.0,F555W,UVIS,/ifs/archive/ops/hst/public/ib46/ib4606c5q/ib4606c5q_flc.fits
        which are
        filename, proposal_id, program_id, obset_id, exptime, filters, detector, pathname

    Output dict will have format (as needed by further code for creating the
        product filenames) of:

        obs_info_dict["single exposure product 00": {"info": '11665 06 wfc3 uvis ib4606c5q f555w drc',
                                                     "files": ['ib4606c5q_flc.fits']}
        .
        .
        .
        obs_info_dict["single exposure product 08": {"info": '11665 06 wfc3 ir ib4606clq f110w drz',
                                                     "files": ['ib4606clq_flt.fits']}

        obs_info_dict["filter product 00": {"info": '11665 06 wfc3 uvis ib4606c5q f555w drc',
                                            "files": ['ib4606c5q_flc.fits', 'ib4606c6q_flc.fits']},
        .
        .
        .
        obs_info_dict["filter product 01": {"info": '11665 06 wfc3 ir ib4606cmq f160w drz',
                                            "files": ['ib4606cmq_flt.fits', 'ib4606crq_flt.fits']},


        obs_info_dict["total detection product 00": {"info": '11665 06 wfc3 uvis ib4606c5q f555w drc',
                                                     "files": ['ib4606c5q_flc.fits', 'ib4606c6q_flc.fits']}
        .
        .
        .
        obs_info_dict["total detection product 01": {"info": '11665 06 wfc3 ir ib4606cmq f160w drz',
                                                     "files": ['ib4606cmq_flt.fits', 'ib4606crq_flt.fits']}

    """
    log.info("Interpret the poller file for the observation set.")
    colnames = ['filename', 'proposal_id', 'program_id', 'obset_id',
                'exptime', 'filters', 'detector', 'pathname']
    obset_table = Table.read(results, format='ascii.fast_no_header', names=colnames)
    # Add INSTRUMENT column
    instr = INSTRUMENT_DICT[obset_table['filename'][0][0]]
    # convert input to an Astropy Table for parsing
    obset_table.add_column(Column([instr] * len(obset_table)), name='instrument')
    # parse Table into a tree-like dict
    log.info("Build the observation set tree.")
    obset_tree = build_obset_tree(obset_table)
    # Now create the output product objects
    log.info("Parse the observation set tree and create the exposure, filter, and total detection objects.")
    obset_dict, tdp_list = parse_obset_tree(obset_tree)

    return obset_dict, tdp_list

# Translate the database query on an obset into actionable lists of filenames
def build_obset_tree(obset_table):
    """Convert obset table into a tree listing all products to be created."""

    # Each product will consist of the appropriate string as the key and
    # a dict of 'info' and 'files' information

    # Start interpreting the obset table
    obset_tree = {}
    for row in obset_table:
        # Get some basic information from the first row - no need to check
        # for multiple instruments as data from different instruments will
        # not be combined.
        det = row['detector']
        orig_filt = row['filters']
        # Potentially need to manipulate the 'filters' string for instruments
        # with two filter wheels
        filt = determine_filter_name(orig_filt)
        row['filters'] = filt
        row_info, filename = create_row_info(row)
        # Initial population of the obset tree for this detector
        if det not in obset_tree:
            obset_tree[det] = {}
            obset_tree[det][filt] = [(row_info, filename)]
        else:
            det_node = obset_tree[det]
            if filt not in det_node:
                det_node[filt] = [(row_info, filename)]
            else:
                det_node[filt].append((row_info, filename))

    return obset_tree

def create_row_info(row):
    """Build info string for a row from the obset table"""
    info_list = [str(row['proposal_id']), "{:02d}".format(row['obset_id']), row['instrument'],
                 row['detector'], row['filename'][:row['filename'].find('_')], row['filters']]
    return ' '.join(map(str.upper, info_list)), row['filename']

def parse_obset_tree(det_tree):
    """Convert tree into products

    Tree generated by `create_row_info()` will always have the following
    levels:
          * detector
              * filters
                  * exposure
    Each exposure will have an entry dict with keys 'info' and 'filename'.

    Products created will be:
      * total detection product per detector
      * filter products per detector
      * single exposure product
    """
    # Initialize products dict
    obset_products = {}

    # For each level, define a product, starting with the detector used...
    prev_det_indx = 0
    det_indx = 0
    filt_indx = 0
    sep_indx = 0

    tdp_list = []

    # Determine if the individual files being processed are flt or flc and
    # set the filetype accordingly (flt->drz or flc->drc).
    filetype = ''

    # Setup products for each detector used
    for filt_tree in det_tree.values():
        totprod = TDP_STR.format(det_indx)
        obset_products[totprod] = {'info': "", 'files': []}
        det_indx += 1
        # Find all filters used...
        for filter_files in filt_tree.values():
            # Use this to create and populate filter product dictionary entry
            fprod = FP_STR.format(filt_indx)
            obset_products[fprod] = {'info': "", 'files': []}
            filt_indx += 1
            # Populate single exposure dictionary entry now as well
            for filename in filter_files:
                # Parse the first filename[1] to determine if the products are flt or flc
                if det_indx != prev_det_indx:
                    filetype = "drc"
                    if filename[1][10:13].lower().endswith("flt"):
                        filetype = "drz"
                    prev_det_indx = det_indx

                # Generate the full product dictionary information string:
                # proposal_id, obset_id, instrument, detector, ipppssoot, filter, and filetype
                prod_info = (filename[0] + " " + filetype).lower()

                # Set up the single exposure product dictionary
                sep = SEP_STR.format(sep_indx)
                obset_products[sep] = {'info': prod_info,
                                       'files': [filename[1]]}

                # Create a single exposure product object
                prod_list = prod_info.split(" ")
                sep_obj = ExposureProduct(prod_list[0], prod_list[1], prod_list[2], prod_list[3], filename[1], prod_list[5], prod_list[6])
                # Set up the filter product dictionary and create a filter product object
                # Initialize `info` key for this filter product dictionary
                if not obset_products[fprod]['info']:
                    obset_products[fprod]['info'] = prod_info

                    # Create a filter product object for this instrument/detector
                    filt_obj = FilterProduct(prod_list[0], prod_list[1], prod_list[2], prod_list[3], prod_list[4], prod_list[5], prod_list[6])
                # Append exposure object to the list of exposure objects for this specific filter product object
                filt_obj.add_member(sep_obj)
                # Populate filter product dictionary with input filename
                obset_products[fprod]['files'].append(filename[1])

                # Set up the total detection product dictionary and create a total detection product object
                # Initialize `info` key for total detection product
                if not obset_products[totprod]['info']:
                    obset_products[totprod]['info'] = prod_info

                    # Create a total detection product object for this instrument/detector
                    tdp_obj = TotalProduct(prod_list[0], prod_list[1], prod_list[2], prod_list[3], prod_list[4], prod_list[6])

                # Append exposure object to the list of exposure objects for this specific total detection product
                tdp_obj.add_member(sep_obj)
                # Populate total detection product dictionary with input filename
                obset_products[totprod]['files'].append(filename[1])

                # Increment single exposure index
                sep_indx += 1

            # Append filter object to the list of filter objects for this specific total product object
            log.info("Attach the filter object {} to its associated total detection product object {}/{}.".format(filt_obj.filters, tdp_obj.instrument, tdp_obj.detector))
            tdp_obj.add_product(filt_obj)

        # Add the total product object to the list of TotalProducts
        tdp_list.append(tdp_obj)

    # Done... return dict and object product list
    return obset_products, tdp_list

# ----------------------------------------------------------------------------------------------------------

def determine_filter_name(raw_filter):
    """
    Generate the final filter name to be used for an observation.

    Parameters
    ----------
    raw_filter : string
        filters component one exposure from an input observation visit

    Returns
    -------
    filter_name : string
        final filter name

    If the raw_filter is actually a combination of two filter names, as
    can be true for instruments with two filter wheels, then generate
    a new filter string according the following rules:
    - If one filter name is 'clear*', then use the other filter name.
    - If both filter names are 'clear*', then use 'clear'.
    - If there are two filters in use, then use 'filter1-filter2'.
    - If one filter is a polarizer ('pol*'), then always put the polarizer
      name second (e.g., 'f606w-pol60').
    - NOTE: There should always be at least one filter name provided to
      this routine or this input is invalid.
    """

    raw_filter = raw_filter.lower()

    # There might be two filters, so split the filter names into a list
    filter_list = raw_filter.split(';')
    output_filter_list = []

    for filt in filter_list:
        # Get the names of the non-clear filters
        if 'clear' not in filt:
            output_filter_list.append(filt)

    if not output_filter_list:
        filter_name = 'clear'
    else:
        if output_filter_list[0].startswith('pol'):
            output_filter_list.reverse()

        delimiter = '-'
        filter_name = delimiter.join(output_filter_list)

    return filter_name