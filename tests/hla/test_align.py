import sys
import traceback
import os
import datetime
import pytest
import numpy as np
from astropy.table import Table

from stwcs import updatewcs

from .base_test import BaseHLATest
from drizzlepac import alignimages
import drizzlepac.hlautils.astrometric_utils as amutils
from ci_watson.artifactory_helpers import get_bigdata

# Nominal acceptable RMS limit for a good solution (IMPROVE THIS)
RMS_LIMIT = 10.0 

@pytest.mark.bigdata
class TestAlignMosaic(BaseHLATest):
    """ Tests which validate whether mosaics can be aligned to an astrometric standard.

        Characeteristics of these tests:
          * A single astrometric catalog was obtained with both GAIA and non-GAIA
            (PanSTARRS?) sources for the entire combined field-of-view using the GSSS
            server.
              * These tests assume combined input exposures for each test have enough
                astrometric sources from the external catalog to perform a high quality
                fit.
          * This test only determines the fit between sources
            extracted from the images by Tweakreg and the source positions included in
            the astrometric catalog.
          * The WCS information for the input exposures do not get updated in this test.
          * No mosaic gets generated.

        Success Criteria:
          * Success criteria hard-coded for this test represents 10mas RMS for the
            WFC3 images based on the fit of source positions to the astrometric catalog
            source positions.
              * RMS values are extracted from optional shiftfile output from `tweakreg`
              * Number of stars used for the fit and other information is not available
                with the current version of `tweakreg`.

        The environment variable needs to be set in the following manner:
            export TEST_BIGDATA=https://bytesalad.stsci.edu/artifactory/
     
        This test file can be executed in the following manner:
            $ pytest -s --bigdata test_align.py >& test_align_output.txt &
            $ tail -f test_align_output.txt

    """

    ref_loc = ['truth']

    def test_align_ngc188(self):
        """ Verify whether NGC188 exposures can be aligned to an astrometric standard.

        Characeteristics of this test:
          * Input exposures include both ACS and WFC3 images of the same general field-of-view
            of NGC188 suitable for creating a combined mosaic using both instruments.
        """
        self.input_repo = 'hst-hla-pipeline'
        self.input_loc = 'mosaic_ngc188'
        totalRMS = 0.0
        input_filenames = ['iaal01hxq_flc.fits', 'iaala3btq_flc.fits',
                            'iaal01hyq_flc.fits', 'iaala3bsq_flc.fits',
                            'j8boa1m8q_flc.fits', 'j8boa1m4q_flc.fits',
                            'j8boa1maq_flc.fits', 'j8boa1m6q_flc.fits']

        data_path = ['hst-hla-pipeline','dev','mosaic_ngc188']
        try:
            datasetTable = alignimages.perform_align(input_filenames,archive=False,clobber=True,debug=False,
                update_hdr_wcs=False,print_fit_parameters=True,print_git_info=False,output=False,regtest=True,
                test_data_path=data_path)

            # Examine the output table to extract the RMS for the entire fit and the compromised information
            if (datasetTable):
                totalRMS = datasetTable['total_rms'][0]

        except Exception:
            exc_type, exc_value, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_tb, file=sys.stdout)

        # Perform some clean up
        #if os.path.exists('ref_cat.ecsv'): os.remove('ref_cat.ecsv')
        #if os.path.exists('refcatalog.cat'): os.remove('refcatalog.cat')
        #for filename in os.listdir():
        #    if filename.endswith('flt.fits') or filename.endswith('flc.fits'):

        #reference_wcs = amutils.build_reference_wcs(input_filenames)
        #test_limit = self.fit_limit / reference_wcs.pscale
        assert (0.0 < totalRMS <= RMS_LIMIT)

    def test_align_47tuc(self):
        """ Verify whether 47Tuc exposures can be aligned to an astrometric standard.

        Characeteristics of this test:
          * Input exposures include both ACS and WFC3 images of the same general field-of-view
            of 47Tuc suitable for creating a combined mosaic using both instruments.
        """
        self.input_loc = 'mosaic_47tuc'
        totalRMS = 0.0
        input_filenames = ['ib6v06c4q_flc.fits','ib6v06c7q_flc.fits',
                                'ib6v25aqq_flc.fits','ib6v25atq_flc.fits',
                                'jddh02gjq_flc.fits','jddh02glq_flc.fits',
                                'jddh02goq_flc.fits']
        data_path = ['hst-hla-pipeline','dev','mosaic_47tuc']
        try:
            datasetTable = alignimages.perform_align(input_filenames,archive=False,clobber=True,debug=False,
                update_hdr_wcs=False,print_fit_parameters=True,print_git_info=False,output=False,regtest=True,
                test_data_path=data_path)

            # Examine the output table to extract the RMS for the entire fit and the compromised information
            if (datasetTable):
                totalRMS = datasetTable['total_rms'][0]

        except Exception:
            exc_type, exc_value, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_tb, file=sys.stdout)

        assert (0.0 < totalRMS <= RMS_LIMIT)

    @pytest.mark.xfail
    @pytest.mark.parametrize("input_filenames", [['j8ura1j1q_flt.fits','j8ura1j2q_flt.fits',
                                                  'j8ura1j4q_flt.fits','j8ura1j6q_flt.fits',
                                                  'j8ura1j7q_flt.fits','j8ura1j8q_flt.fits',
                                                  'j8ura1j9q_flt.fits','j8ura1jaq_flt.fits',
                                                  'j8ura1jbq_flt.fits','j8ura1jcq_flt.fits',
                                                  'j8ura1jdq_flt.fits','j8ura1jeq_flt.fits',
                                                  'j8ura1jfq_flt.fits','j8ura1jgq_flt.fits',
                                                  'j8ura1jhq_flt.fits','j8ura1jiq_flt.fits',
                                                  'j8ura1jjq_flt.fits','j8ura1jkq_flt.fits'],
                                                 ['j92c01b4q_flc.fits','j92c01b5q_flc.fits',
                                                  'j92c01b7q_flc.fits','j92c01b9q_flc.fits'],
                                                 ['jbqf02gzq_flc.fits', 'jbqf02h5q_flc.fits',
                                                  'jbqf02h7q_flc.fits', 'jbqf02hdq_flc.fits',
                                                  'jbqf02hjq_flc.fits', 'jbqf02hoq_flc.fits',
                                                  'jbqf02hqq_flc.fits', 'jbqf02hxq_flc.fits',
                                                  'jbqf02i3q_flc.fits', 'jbqf02i8q_flc.fits',
                                                  'jbqf02iaq_flc.fits'],
                                                 ['ib2u12kaq_flt.fits', 'ib2u12keq_flt.fits',
                                                  'ib2u12kiq_flt.fits', 'ib2u12klq_flt.fits'],
                                                 ['ibjt01a1q_flc.fits', 'ibjt01a8q_flc.fits',
                                                  'ibjt01aiq_flt.fits', 'ibjt01amq_flt.fits',
                                                  'ibjt01aqq_flt.fits', 'ibjt01auq_flt.fits',
                                                  'ibjt01yqq_flc.fits', 'ibjt01z0q_flc.fits',
                                                  'ibjt01zwq_flc.fits', 'ibjt01a4q_flc.fits',
                                                  'ibjt01acq_flc.fits', 'ibjt01akq_flt.fits',
                                                  'ibjt01aoq_flt.fits', 'ibjt01asq_flt.fits',
                                                  'ibjt01avq_flt.fits', 'ibjt01yuq_flc.fits',
                                                  'ibjt01ztq_flc.fits'],
                                                 ['ibnh02coq_flc.fits','ibnh02cmq_flc.fits',
                                                  'ibnh02c7q_flc.fits','ibnh02c5q_flc.fits',
                                                  'ibnh02cpq_flc.fits','ibnh02c9q_flc.fits',
                                                  'ibnh02bfq_flc.fits','ibnh02beq_flc.fits']])
    def test_align_single_visits(self,input_filenames):
        """ Verify whether single-visit exposures can be aligned to an astrometric standard.

        Characteristics of these tests:
          * Input exposures include exposures from a number of single visit datasets to explore what impact differing
            observing modes (differing instruments, detectors, filters, subarray size, etc.) have on astrometry.

        The following datasets are used in these tests:

            * ACS dataset 10048_a1: 2x F344N, 1x F435W, 1x F475W, 2x F502N, 2x F550M, 1x F555W, 1x F606W, 1x F625W,
              2x F658N, 1x F775W, 1x F814W, 1x F850LP, and 2x F892N ACS/HRC images
            * ACS dataset 10265_01: 4x F606W full-frame ACS/WFC images
            * ACS dataset 12580_02: 5x F475W & 6x F814W ACS/WFC images
            * WFC3 dataset 11663_12: 4x F160W full-frame WFC3/IR images
            * WFC3 dataset 12219_01: 8x F160W full-frame WFC3/IR images, 9x F336W full-frame WFC3/UVIS images
            * WFC3 dataset 12379_02: 4X F606W, 4x F502N full-frame WFC3/UVIS images

        """
        self.input_loc = 'base_tests'
        self.curdir = os.getcwd()
        totalRMS = 0.0
        data_path = ['hst-hla-pipeline','dev','base_tests']
        try:
            datasetTable = alignimages.perform_align(input_filenames,archive=False,clobber=True,debug=False,
                update_hdr_wcs=False,print_fit_parameters=True,print_git_info=False,output=False,regtest=True,
                test_data_path=data_path)

            # Examine the output table to extract the RMS for the entire fit and the compromised information
            if (datasetTable):
                totalRMS = datasetTable['total_rms'][0]

        except Exception:
            exc_type, exc_value, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_tb, file=sys.stdout)

        assert (0.0 < totalRMS <= RMS_LIMIT)

    def test_astroquery(self):
        """Verify that new astroquery interface will work"""
        #self.curdir = os.getcwd()
        #self.input_loc = ''

        totalRMS = 0.0
        try:
            datasetTable = alignimages.perform_align(['IB6V06060'],archive=False,clobber=True,debug=False,
                update_hdr_wcs=False,print_fit_parameters=True,print_git_info=False,output=False,regtest=False,
                test_data_path=None)

            # Examine the output table to extract the RMS for the entire fit and the compromised information
            if (datasetTable):
                totalRMS = datasetTable['total_rms'][0]

        except Exception:
            exc_type, exc_value, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_tb, file=sys.stdout)
            sys.exit()

        assert (0.0 < totalRMS <= RMS_LIMIT)