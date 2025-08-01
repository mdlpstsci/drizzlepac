.. _catalog_generation:

==================
Catalog Generation
==================

The Hubble Advanced Products (HAP) project generates, by default, two types of catalogs for each
detection image (i.e., all the images in the visit from the same detector drizzled together), and each
filter-product image (i.e., all the images in the visit acquired with the same detector and filter
drizzled together). The two types of catalogs are colloquially
referred to as the Point and Segment catalogs.  Both catalogs are generated using
utilities from `Photutils <https://photutils.readthedocs.io/en/stable/>`_
with the Point catalog created based upon functionality similar to DAOPhot-style photometry,
and the Segment catalog created with Source Extractor segmentation capabilities and output
in mind.  The HAP catalogs are intended to replicate the Hubble Source Catalog (HSC) by
`Whitmore et al. 2016 AJ, 151, 134W <http://adsabs.harvard.edu/abs/2016AJ....151..134W>`_.

The HAP catalogs provide aperture photometry in the ABmag system in two small apertures, but they are
calibrated using the photometric zeropoints corresponding to an 'infinite' aperture. To convert to total
magnitudes, **aperture corrections must be applied to account for flux falling outside of the selected 
aperture**.  For details, see Section 2.2.3 "Aperture Corrections".

   * For WFC3, see `Section 9.1.3 "Aperture and Encircled Energy Corrections" 
     <https://hst-docs.stsci.edu/wfc3dhb/chapter-9-wfc3-data-analysis/9-1-photometry#id-9.1Photometry-9.1.3ApertureandEncircledEnergyCorrections>`_ 
     in the `WFC3 Data Handbook <https://hst-docs.stsci.edu/wfc3dhb>`_ (Pagul & Rivera et. al. 2024). 
     The latest `WFC3/UVIS EE tables 
     <https://www.stsci.edu/hst/instrumentation/wfc3/data-analysis/photometric-calibration/uvis-encircled-energy>`_ and 
     `WFC3/IR EE tables <https://www.stsci.edu/hst/instrumentation/wfc3/data-analysis/photometric-calibration/ir-encircled-energy>`_ are also available for download.
   * For ACS, see `Section 5.1.2 "Aperture and Color Corrections" 
     <https://hst-docs.stsci.edu/acsdhb/chapter-5-acs-data-analysis/5-1-photometry#id-5.1Photometry-5.1.25.1.2ApertureandColorCorrections>`_ in the ACS Data Handbook (Lucas & Ryan et al. 2022). 
     `ACS EE tables <https://www.stsci.edu/hst/instrumentation/acs/data-analysis/aperture-corrections>`_ are available for download from the website.
   * For a discussion of HAP drizzled data products, see the 
     `DrizzlePac Handbook <https://hst-docs.stsci.edu/drizzpac>`_ (Anand, Mack et al. 2025).


1: Support Infrastructure for Catalog Generation
================================================

1.1: Important Clarifications
-----------------------------
As previously discussed in :ref:`singlevisit`, AstroDrizzle creates a single multi-filter, detector-level
drizzle-combined image for *source identification* and one or more detector/filter-level drizzle-combined images
(depending on
which filters were used in the dataset) for *photometry measurements*. The same set of sources identified in the
multi-filter detection image is used to measure photometry for each filter. We use this method to maximize the
signal across all available wavelengths at the source detection stage, thus providing photometry with the
best quality source list across all available input filters.

It should also be stressed here that the point and segment photometry source list generation algorithms
identify source catalogs independently of each other and DO NOT use a shared common source catalog for
photometry.

While the detection image for a specific catalog type is used to identify potential sources, 
unless the Flags entry for a source in all of the corresponding filter catalogs is 
less than the value of 5, the source will be removed from the associated total detection 
catalog. Finally, if somehow all measured values for a source in all the filter catalogs are marked as
invalid (value of -9999.0), then the source will be removed from the total detection catalog.  A
discussion of the flag values is found in Section 2.4.2.

.. note::
 A catalog file will always be written out for each type of catalog whether or not there are
 any identified sources in the exposure.  If there are no identified viable sources, the file will only
 contain header information and no source rows.


1.2: Generation of Pixel Masks
------------------------------
Every multi-filter, detector-level drizzle-combined image is associated with a boolean footprint mask which
defines the illuminated (True) and non-illuminated (False) portions of the image based upon its constituent
exposures and the corresponding WCS solution.  The boundary of the illuminated portion
is iteratively eroded or contracted to minimize the impact of regions where signal
quality is known to be degraded, and thereby, could affect source identification and subsequent
photometric measurements.  The erosion depth is approximately ten pixels and is done by using the
`ndimage.binary_erosion <https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.binary_erosion.html>`_ scipy tool.
For computational convenience, an inverse footprint mask is also available for functions
which utilize masks to indicate pixels which should be ignored during processing of the
input data.

1.3: Detection Image Background Determination
---------------------------------------------
For consistency, the same background and background RMS images are used by both the point and
segment algorithms.
To ensure optimal source detection, the multi-filter detection image must be background-subtracted.
In order to accommodate the different types of detectors, disparate signal levels, and highly varying
astronomical image content, three background computations are used as applicable.  The first category
of background definition is a special case situation, and if it is found to be applicable to the detection
image, the background and background RMS images are defined and no further background evaluation is done.

It has been observed that some background regions of ACS SBC drizzle-combined
detection images, *though the evaluation is done for all instrument detection images*,
are measured to have values identically
equal to zero.  If the number of identically zero pixels in the footprint portion of the detection image
exceeds a configurable percentage threshold value (default is 25%), then a two-dimensional background image
is constructed and set to the value of zero, hence the **Zero Background Algorithm**. Its companion
constructed RMS image set to the RMS
value computed for the non-zero pixels which reside within the footprint portion of the image.

If the **Zero Background Algorithm** is not applicable, then sigma-clipped statistics are
computed, known as the **Constant Background Algorithm**,
for the detection image using the
`astropy.stats.sigma_clipped_stats <https://docs.astropy.org/en/stable/api/astropy.stats.sigma_clipped_stats.html>`_
Astropy tool. This algorithm uses the detection image and its inverse footprint mask, as well
as a specification for the number of standard deviations and the maximum number of iterations
to compute the mean, median, and rms of the
sigma-clipped data.  The specification for the number of standard deviations and the maximum number
of iterations are configurable values which are set to 3.0 and 3 by default, respectively.

At this point the Pearson's second coefficient of skewness is computed.

.. math::
    skewness = 3.0 * (mean - median) / rms

The skewness compares our sample distribution with a normal distribution where the
larger the absolute value of the skewness, the more the sample distribution differs from
a normal distribution. The skewness is computed in this context to aid in determining
whether it is worth computing the background by other means (i.e., our third option of
a two-dimensional background).  For example, a high positive skew
value can be indicative of there being a significant number of sources in the image
which need to be taken into account with a more complex background.

Since the median and rms values will be used to generate the two-dimensional background and
RMS images, respectively, the values need to be deemed reasonable.  A negative mean or median value
is reset to zero, and a minimum rms value is computed for comparison to the sigma-clipped statistic
based upon FITS keyword values in
the detection image header.  For the CCD detectors only, a-to-d gain (ATODGN), read noise
(READNSE), number of drizzled images (NDRIZIM), and total exposure time (TEXPTIME) are employed
to compute a minimum rms, with the larger of the two rms values (sigma-clipped rms or minimum rms)
adopted for further use.  Once viable background and background RMS values are determined,
two-dimensional images matching the dimensions of the detection image are constructed.
Through a configuration setting, a user can specify the sigma-clipped statistics algorithm be
the chosen method used to compute the background and RMS images, though the special case of
identically zero background data will always be evaluated and will supersede the user request when
applicable.

For the final background determination algorithm, **Conformal Background Algorithm**, the
`photutils.background.Background2d <https://photutils.readthedocs.io/en/stable/api/photutils.background.Background2D.html>`_
Astropy tool is *only* invoked if the **Zero Background Algorithm** has not been applied,
the user has not requested that only the **Constant Background Algorithm** computed, and the
skewness value derived using the sigma-clipped statistics is less than a pre-defined and configurable
threshold (default value 0.5).

The **Conformal Background Algorithm** uses
sigma-clipped statistics to determine background and RMS values across the image, but in
a localized fashion in contrast to **Constant Background Algorithm**. An initial low-resolution
estimate of the background is performed by computing sigma-clipped median values in 27x27 pixel boxes across
the image. This low-resolution background image is then median-filtered using a 3x3 pixel sample window to
correct for local small-scale overestimates and/or underestimates.  Both the 27 and 3 pixel
settings are configurable variables for the user.

Once a background and RMS image are determined using this final technique, a preliminary
background-subtracted image is computed so it can be evaluated for the percentage of negative
values in the illuminated portion of the image. If the percentage of negative values exceeds a
configurable and defined threshold (default value 15%), the computation of the background and RMS image
from this
algorithm are discarded.  Instead the background and RMS images computed using **Constant Background Algorithm**,
with the associated updates, are ultimately chosen as the images to use.

.. attention::

    It cannot be emphasized enough that a well-determined background measurement,
    leading to a good threshold definition, is very crucial for proper and
    successful source identification.

1.3.1: Configurable Variables
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Through-out this section variables have been mentioned which can be configured by the user.  The
values used for these variables for generating the default catalogs are deemed to be the best for
the general situation, but users can tune these values to optimize for their own data.

To this end, users can adjust
parameter values in the <instrument>_<detector>_catalog_generation_all.json files in the following path:
/drizzlepac/pars/hap_pars/svm_parameters/<instrument>/<detector>/. Alternatively, a safer way for users to tune
configuration settings is to first utilize `~drizzlepac.haputils.generate_custom_svm_mvm_param_file` to generate a
custom parameter .json file. This parameter file, which is written to the user's current working directory by default,
contains all default pipeline parameters and allows users to adjust any/or all of these parameters as they wish without
overwriting the hard-coded default values stored in /drizzlepac/pars/hap_pars/svm_parameters/. To run the single-visit
mosaic pipeline using the custom parameter file, users simply need to specify the name of the file with the '-c'
optional command-line argument when using `~drizzlepac.runsinglehap` or the 'input_custom_pars_file' optional input
argument when executing ``run_hap_processing()`` in `~drizzlepac.hapsequencer` from Python or from another Python script.

.. warning::
    Modification of values in the parameter files stored in /drizzlepac/pars/hap_pars/svm_parameters/ is
    *strongly* discouraged as there is no way to revert these values back to their defaults once
    they have been changed.

1.3.2: Description of the variables in the catalog JSON files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Default values for the numeric configuration parameters are detector-dependent, though many of the values may be the same from detector to detector.  In the actual configuration files
the parameters are split into three sections: General (which is unlabeled), DAO (for the Point algorithm), and SOURCEX (for the Segmentation algorithm). The variables listed in the General section apply to both the Point and Segmentation algorithms.

GENERAL 
    * bkg_box_size: int (pixels)
        For Background2D, the size of the box within which the background is estimated using the sigma-clipped statistics algorithm.

    * bkg_filter_size: int (pixels)
        Window size of the 2D median filter to apply to the low resolution background map

    * good_fwhm: 
        DEPRECATED

    * skyannulus_arcsec: float (arcseconds)
        Photometry measurement: inner radius of the circular annulus

    * dskyannulus_arcsec: float (arcseconds)
        Photometry measurement: outer radius of the circular annulus

    * aperture_1: float (arcseconds)
        Photometry measurement: inner aperture radius

    * aperture_2: float (arcseconds)
        Photometry measurement: outer aperture radius

    * salgorithm: string (default = "mode")
        Photometry measurement: Statistic to use to calculate the background ("mean", "median", "mode"). All measurements are sigma-clipped.

    * scale: float
        Used as a scaling factor on a limit threshod for computation of weight masks

    * sensitivity: float
        Used for computation of weight masks to preserve the attribute of similarity

    * block_size: int
        Size of the block used by the FFT to deconvolve the drizzled image with the PSF

    * cr_residual: float
        Factor used to account for the influence of single-image cosmic-ray identification.  Single filter single-image exposures are only used to compute total detection image when there are only single exposures for *all* of the input filters.

    * flag_trim_value: int
        The value which is the high limit for good detected sources.  Sources with lower flag values are deemed good. Flags above the default limit represent:  multi-pixel saturation, faint magnitude, hot pixels, swarm detection, edge/chip gap, bleeding, and cosmic rays.

    * simple_bkg: bool (default = False)
        Forces use of the sigma_clipped_stats algorithm to compute the background of the input image.

    * zero_percent: float
        Percentage limit of the pure zero values in the illuminated portion of an input image.  If there are more zero values than the zero_percent limit, then the background is set to zero and the background rms is computed based on the pixels which are non-zero in the illuminated portion of the input image.

    * negative_percent: float
        If the background were determined by Background2D, but the background-subtracted image has more than the allowed limit of negative_percent, then the background should be determined by the sigma-clipped statistics algorithm.

    * nsigma_clip: float
        Parameter for the sigma_clipped_stats algorithm in the determination of the background of the input image. This is the number of standard deviations to use for both the lower and upper clipping limit.

    * maxiters: int
        The number of sigma-clipping iterations to perform when using the sigma_clipped_stats algorithm to compute the background of the input image.

    * background_skew_threshold: float
        Pearson’s second coefficient of skewness - this is a criterion for possibly computing a two-dimensional background fit.  If the skew is larger than this threshold, this implies a crowded field and a more complex background determination algorithm is warranted.

    * TWEAK_FWHMPSF: float
        Gaussian FWHM for source detection

DAO
    * bigsig_sf: 
        DEPRECATED

    * kernel_sd_aspect_ratio: 
        DEPRECATED

    * nsigma: float
        The "sigma" in threshold=(sigma * background_rms). Threshold is an image greater than the background which defines, on a pixel-by-pixel basis, the low signal limit above which sources are detected.  

    * starfinder_algorithm: string (default = "psf")
        Algorithm to use for source detection: "dao" (DAOStarFinder), "iraf" (IRAFStarFinder), and "psf" (UserStarFinder).

    * region_size: int
        Size of the box used to recognize a point source. Also, the kernel size for the maximum filter window when computing weight masks. In the latter case of "kernel size", the variable applies to both algorithms.

SOURCEX
    * source_box: int (pixels)
        Number of connected pixels needed for a source detection

    * segm_nsigma: float
        The "sigma" in threshold=(sigma * background_rms). Threshold is an image greater than the background which defines, on a pixel-by-pixel basis, the low signal limit above which sources are detected.  The value is applicable for the Gaussian smoothing kernel.

    * nlevels: int
        Number of multi-thresholding levels for deblending 

    * contrast: float
        Fraction of the total source flux that a local peak must have to be deblended as a separate object

    * border: 
        DEPRECATED

    * rw2d_size: int
        RickerWavelet kernel X- and Y-dimension in pixels

    * rw2d_nsigma: float
        The "sigma" in threshold=(sigma * background_rms). Threshold is an image greater than the background which defines, on a pixel-by-pixel basis, the low signal limit above which sources are detected.  The value is applicable for the RickerWavelet smoothing kernel.

    * rw2d_biggest_pixels: int (pixels)
        Pixel limit on biggest source for RickerWavelet kernel

    * rw2d_biggest_source: float
        Percentage limit on biggest source for RickerWavelet kernel

    * rw2d_source_fraction: float
        Percentage limit on source fraction over the image for RickerWavelet kernel

    * biggest_source_deblend_limit: float
        Percentage limit on biggest source deblending limit

    * source_fraction_deblend_limit: float
        Percentage limit on source fraction deblending limit

    * ratio_bigsource_limit: int
        Limit on the ratio of the "big sources" found with the Gaussian vs the RickerWavelent kernel.  The ratio is interpreted as indicative of overlapping PSFs vs nebulousity.  If the ratio is larger than this limit, the processing is allowed to proceed.

    * ratio_bigsource_deblend_limit: int
        Limit used to filter out prohibitively large segments as it a resource consuming task to try and deblend very large segments.  If the ratio of the area of the largest segment to the area of the next smaller segment is larger than this limit, segment is not deblended.

    * kron_scaling_radius: float
        Scaling parameter of the unscaled Kron radius

    * kron_minimum_radius: float (pixels)
        Minimum value for the unscaled Kron radius


1.4: Image Kernel
-----------------
By default, the software uses a 
two-dimensional Gaussian smoothing kernel on the multi-filter detection image
in an effort to identify sources.  The kernel is based upon the FWHM 
information provided in the detector-dependent catalog configuration files and the
`astropy.convolution.Gaussian2DKernel <https://docs.astropy.org/en/stable/api/astropy.convolution.Gaussian2DKernel.html>`_
Astropy tool.  In extreme cases, a large number of candidate sources may be 
blended together and are mistakenly identified as a single source covering a 
large percentage of the image.  To address this situation, an alternative kernel 
is derived using the
`astropy.convolution.RickerWavelet2DKernel <https://docs.astropy.org/en/stable/api/astropy.convolution.RickerWavelet2DKernel.html>`_
Astropy tool. 

2: Point (Aperture) Photometric Catalog Generation
==================================================

2.1: Source Identification Options
----------------------------------
A number of options have been implemented within the catalog generation code in order
to best match the contents of the exposure, including presence of saturated sources and
cosmic-rays.  The available options include:

  * dao : The `photutils DAOStarFinder class <https://photutils.readthedocs.io/en/stable/api/photutils.detection.DAOStarFinder.html#photutils.detection.DAOStarFinder>`_ that provides an implementation of the DAOFind algorithm.
  * iraf : The `photutils IRAFStarFinder class <https://photutils.readthedocs.io/en/stable/api/photutils.detection.IRAFStarFinder.html#photutils.detection.IRAFStarFinder>`_ that implements IRAF's *starfind* algorithm.
  * psf [DEFAULT] : This option is a modification of DAOStarFinder which relies on a library of TinyTim (model) PSFs to locate each source then uses DAOStarFinder to measure the final position and photometry of each identified source.

These options are selected through the "starfinder_algorithm" parameter in the JSON configuration files in the
``pars/hap_pars`` directory as used by `~drizzlepac.runsinglehap`.


2.1.1: Source Identification using DAOStarFinder
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
We use the `photutils.detection.DAOStarFinder <https://photutils.readthedocs.io/en/stable/api/photutils.detection.DAOStarFinder.html>`_ Astropy tool to identify sources in the background-subtracted
multi-filter detection image. Here, the background computed using one of the algorithms discussed in Section 1.3 is
applied to the science data to initialize point-source detection processing. This algorithm works by identifying local
brightness maxima with roughly gaussian distributions whose peak values are above a predefined minimum threshold. This
minimum threshold value is computed as the background noise times a detector-dependant scale factor (listed below in
table 0). Full details of the process are described in
`Stetson 1987; PASP 99, 191 <http://adsabs.harvard.edu/abs/1987PASP...99..191S>`_. The exact set of input parameters
fed into DAOStarFinder is detector-dependent. The parameters can be found in the
<instrument>_<detector>_catalog_generation_all.json files mentioned in the previous section.

.. table:: Table 0: Background scale factor values used to compute minimum detection thresholds

    +---------------------+--------------+
    | Instrument/Detector | Scale Factor |
    +=====================+==============+
    | ACS/HRC             | 5.0          |
    +---------------------+--------------+
    | ACS/SBC             | 6.0          |
    +---------------------+--------------+
    | ACS/WFC             | 5.0          |
    +---------------------+--------------+
    | WFC3/IR             | 1.0          |
    +---------------------+--------------+
    | WFC3/UVIS           | 5.0          |
    +---------------------+--------------+

2.1.2: Source Identification using PSFs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This option, introduced in Drizzlepac v3.3.0, drizzles model PSFs created using TinyTim to match the orientation and plate
scale of the observation to look for sources in the image.  Where DAOFind convolves the image with a perfect Gaussian whose
FWHM has been specified by the user, this option convolves the image with the model PSF to identify all sources which most
closely matches the PSF used.  Those positions are then turned into a list that is fed to
`photutils DAOStarFinder
<https://photutils.readthedocs.io/en/stable/api/photutils.detection.DAOStarFinder.html#photutils.detection.DAOStarFinder>`_
code to measure them using the Gaussian models with a FWHM measured from the model PSF.

One benefit of this method is that features in
the core of saturated or high S/N sources in the image that would normally be erroneously identified as a separate point-source
by DAOFind will be recognized as part of the full PSF as far out as the model PSF extends.

For exposures which are comprised of images taken in different filters, the model PSF used is the drizzle combination of the
model PSFs for each filter that comprised the image.  This allows the code to best match the PSF found in the image of the
``total detection`` image.   The model PSFs definitely do not exactly match the PSFs from the images due to focus changes and
other telescope effects.  However, they are close enough to allow for reasonably complete identification of actual
point-sources in the images.  Should the images suffer from extreme variations in the PSF, though, this algorithm will end up
not identifying valid sources from the image.  The user can provide their own library of PSFs to use in place of the model PSFs
included with this package in order to more reliably match and measure the sources from their data.  The user-provided PSFs
can be used to directly replace the PSFs installed with this package as long as they maintain the same naming convention.
All model PSFs installed with the code can be found in the ``pars/psfs`` directory, with all PSFs organized by instrument
and detector.  Each PSF file has a filename of ``<instrument>_<detector>_<filter_name>.fits``.  The model PSFs all extend
at least 3.0" in radius in order to recognize the features of the diffraction spikes out as far as possible to avoid as
many false detections as possible for saturated sources.


2.2: Aperture Photometry Measurements
-------------------------------------

2.2.1: Flux Determination
^^^^^^^^^^^^^^^^^^^^^^^^^
Aperture photometry is then computed for the identified sources using a pair of small, concentric 
apertures listed in Table 1 for each instrument/detector. The radii for the two aperture measurements 
(MagAper1 and MagAper2) are 1 and 3 pixels for ACS/WFC, 1.25 and 3.75 pixels for WFC3/UVIS, and 1.2 
and 3.5 pixels for WFC3/IR. See Table 1 for the corresponding sizes in arcsec. Both the Point and
Segment source catalogs contain aperture photometry in two small apertures (Aper1 and Aper2) which are 
listed in units of arcseconds and in pixels. Users must manually apply aperture corrections in order to 
correct HAP magnitude values to infinite aperture. 

.. table:: Table 1: For each HST Instrument/Detector, the scale of the HAP drizzled (drc/drz) image is given in column 2.

    +-------------+----------+--------+--------+-------+-------+
    | Instrument/ | Drizzled | Aper1  | Aper2  | Aper1 | Aper2 |
    | Detector    | Scale    | (")    | (")    | (pix) | (pix) |
    |             | ("/pix)  |        |        |       |       |
    +=============+==========+========+========+=======+=======+
    | WFC3/IR	  |  0.128   | 0.15   | 0.45   |  1.2  |  3.5  |
    +-------------+----------+--------+--------+-------+-------+
    | WFC3/UVIS   |  0.040   | 0.05   | 0.15   |  1.25 |  3.75 |
    +-------------+----------+--------+--------+-------+-------+
    | ACS/WFC	  |  0.050   | 0.05   | 0.15   |  1.0  |  3.0  |
    +-------------+----------+--------+--------+-------+-------+
    | ACS/HRC     |  0.025   | 0.03   | 0.125  |  1.2  |  5.0  |
    +-------------+----------+--------+--------+-------+-------+
    | ACS/SBC     |  0.025   | 0.07   | 0.125  |  2.8  |  5.0  |
    +-------------+----------+--------+--------+-------+-------+

Raw (non-background-subtracted) flux values are computed by summing up the enclosed flux within the two specified
apertures using the `photutils.aperture.aperture_photometry
<https://photutils.readthedocs.io/en/stable/api/photutils.aperture.aperture_photometry.html>`_
tool. Input values are detector-dependent, and can be found in the \*_catalog_generation_all.json files described above
in section 1.3.

Local background values are computed based on the 3-sigma-clipped mode of pixel values present in a circular annulus
with an inner radius of 0.25 arcseconds and an outer radius of 0.50 arcseconds surrounding each identified source. This
local background value is then subtracted from the raw inner and outer aperture flux values to compute the
background-subtracted inner and outer aperture flux values found in the output .ecsv catalog file by the formula

.. math::
    f_{bgs} = f_{raw} - f_{bg} \cdot a

where
    * :math:`f_{bgs}` is the background-subtracted flux, in electrons second\ :sup:`-1`
    * :math:`f_{raw}` is the raw, non-background-subtracted flux, in electrons second\ :sup:`-1`
    * :math:`f_{bg}` is the per-pixel background flux, in electrons second \ :sup:`-1` pixel\ :sup:`-1`
    * :math:`a` is the area of the photometric aperture, in pixels

The overall standard deviation and mode values of pixels in the background annulus are also reported for each
identified source in the output .ecsv catalog file in the “STDEV” and “MSKY” columns respectively (see Section 3 for
more details).

2.2.2: Computation of ABmag 
^^^^^^^^^^^^^^^^^^^^^^^^^^^
The conversion of the flux to ABmag is a two-step process.  The computations involve **photflam** and **photplam**
which are FITS keywords stored in the science extension header of the input drizzled image. References for these 
equations are: Whitmore et al. 2016 (https://iopscience.iop.org/article/10.3847/0004-6256/151/6/134/pdf), and  
Sirianni et al. 2005 (https://iopscience.iop.org/article/10.1086/444553/pdf).

First, convert flux according to the formula:

.. math::
    f_{lambda} = f \cdot photflam

where
    * :math:`{f_{lambda}}` is the mean flux density, in ergs cm\ :sup:`-2` A :sup:`-1` second\ :sup:`-1`
    * :math:`{f}` is the flux, in electrons second\ :sup:`-1`
    * :math:`{photflam}` is the inverse sensitivity, in ergs cm\ :sup:`-2` A :sup:`-1` electrons\ :sup:`-1`

Now convert the :math:`{f}_{lambda}` to STmag:

.. math::
    STmag = -2.5 \cdot log({f}_{lambda}) - 21.10

where
    * :math:`-2.5` is the ratio of brightness between two stars differing by one magnitude (Pogson's ratio)
    * :math:`21.10` is the STmag permanently set zeropoint stored in the FITS **photzpt** keyword in the science extension header

Finally, convert STmag to ABmag:

.. math::
    ABmag = STmag - 5.0 \cdot log(photplam) + 18.6921

where
    * :math:`{photplam}` is the bandpass pivot wavelength, in Angstroms

Some additional citations for the magnitude systems are the following: `ACS Data Handbook <https://hst-docs.stsci.edu/acsdhb/chapter-5-acs-data-analysis/5-1-photometry>`_, analysis of the
relationship between *photflam*, *photzpt*, and *photplam* to the *STmag* and *ABmag* zeropoints (`Bohlin et al. 2011 <https://ui.adsabs.harvard.edu/abs/2011AJ....141..173B/abstract>`_), discussion of *STmag* (`Koornneef, J. et al. 1986 <https://ui.adsabs.harvard.edu/abs/1986HiA.....7..833K/abstract>`_), and a discussion of *ABmag* (`Oke, J.B. 1964 <https://ui.adsabs.harvard.edu/abs/1964ApJ...140..689O/abstract>`_).

2.2.3: Aperture Corrections
^^^^^^^^^^^^^^^^^^^^^^^^^^^
HAP (and HSC) photometry is measured in small apertures in order to reduce errors due to source crowding or 
background variations. The photometric header keywords, on the other hand, correspond to an ‘infinite’ 
aperture enclosing all of the light from a source.  Aperture corrections are not applied to the point and 
segment catalogs and must be applied by the user to determine the total magnitude of the source. Blind 
application of aperture corrections using the EE tables should be avoided, since the measured 
photometry (and the EE fraction) in small apertures is strongly dependent on the telescope focus and 
orbital breathing effects.   

To convert aperture magnitudes to total magnitudes, a two-step process is recommended.  First small 
aperture photometry is corrected to a larger ‘standard’ aperture for each instrument, beyond which 
the fraction of enclosed light is insensitive to changes in telescope focus, orbital breathing 
effects, or spatial variations in the PSF 
(see `Mack et al. 2022 <https://www.stsci.edu/files/live/sites/www/files/home/hst/instrumentation/wfc3/documentation/instrument-science-reports-isrs/_documents/2022/WFC3-ISR-2022-06.pdf>`_).  This correction may be 
measured from isolated stars in the drizzled science frames, when possible.  Alternatively, the MAST PSF 
search tool can be used to download PSFs extracted from archival data at a similar focus level 
and detector position, and the appropriate aperture corrections can be calculated using these. For 
example, `WFC3 Observed PSFs <https://www.stsci.edu/hst/instrumentation/wfc3/data-analysis/psf/psf-search>`_  
can be accessed on the 
`MAST Portal interface <https://mast.stsci.edu/portal/Mashup/Clients/Mast/Portal.html>`_
by choosing the 'Select a collection' to 'WFC3 PSF'. For details, see 
`WFC3 ISR 2021-12 <https://www.stsci.edu/files/live/sites/www/files/home/hst/instrumentation/wfc3/documentation/instrument-science-reports-isrs/_documents/2021/ISR_2021_12.pdf>`_. 

Next, the ‘standard’ aperture is corrected to ‘infinite’ aperture using the encircled energy (EE) 
tables provided by the HST instrument teams. These tables are derived from high signal-to-noise ratio
observations of isolated stars out to large radii, where the EE fraction is converted to magnitude units.  
`ACS EE Tables <https://www.stsci.edu/hst/instrumentation/acs/data-analysis/aperture-corrections>`_ 
and interactive plots are available on the ACS website. The latest solutions are described in 
`Bohlin (2016 AJ....152) <https://ui.adsabs.harvard.edu/abs/2016AJ....152...60B/abstract>`_
for the WFC and HRC detectors and in 
`ACS ISR 2016-05 <https://www.stsci.edu/files/live/sites/www/files/home/hst/instrumentation/acs/documentation/instrument-science-reports-isrs/_documents/isr1605.pdf>`_ for the SBC detector.  
`WFC3/UVIS EE tables <https://www.stsci.edu/hst/instrumentation/wfc3/data-analysis/photometric-calibration/uvis-encircled-energy>`_
are available the WFC3 website and described in 
`WFC3 ISR 2021-04 <https://www.stsci.edu/files/live/sites/www/files/home/hst/instrumentation/wfc3/documentation/instrument-science-reports-isrs/_documents/2021/WFC3_ISR_2021-04.pdf>`_, and the 
`WFC3/IR EE tables <https://www.stsci.edu/hst/instrumentation/wfc3/data-analysis/photometric-calibration/ir-encircled-energy>`_ are described in 
`WFC3 ISR 2009-37 <https://www.stsci.edu/files/live/sites/www/files/home/hst/instrumentation/wfc3/documentation/instrument-science-reports-isrs/_documents/2009/WFC3-2009-37.pdf>`_.

2.2.4: Hubble Source Catalog
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The legacy `HSC FAQ page <https://archive.stsci.edu/hst/hscv1/help/HSC_faq.html>`_ 
links to an older set of 
`Aperture Corrections Tables <https://archive.stsci.edu/hst/hscv1/help/FAQ/aperture_corrections.txt>`_
recommended by `Whitmore et al. 2016 <https://ui.adsabs.harvard.edu/abs/2016AJ....151..134W/abstract>`_
for each HST detector. While these represented the best solutions at the time 
(e.g. `Sirianni et al. 2005 <https://iopscience.iop.org/article/10.1086/444553/pdf>`_ 
for ACS; `Hartig 2009 <https://www.stsci.edu/files/live/sites/www/files/home/hst/instrumentation/wfc3/documentation/instrument-science-reports-isrs/_documents/2009/WFC3-2009-37.pdf>`_ for WFC3), 
the updated encircled energy solutions from the instrument webpages should be used instead. See Section 2.2.3.

2.3: Calculation of Photometric Errors
--------------------------------------
2.3.1: Calculation of Flux Uncertainties
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
For every identified source, the `photutils.aperture_photometry()
<https://photutils.readthedocs.io/en/stable/api/photutils.aperture.aperture_photometry.html>`_
tool calculates standard deviation values for each aperture based on a 2-dimensional RMS array computed using the
`photutils.background.Background2d <https://photutils.readthedocs.io/en/stable/api/photutils.background.Background2D.html>`_
tool that we previously utilized to compute the 2-dimensional background array in order to background-subtract the
detection image for source identification. We then compute the final flux errors as seen in the output .ecsv catalog
file using the following formula:

.. math::
    \Delta f = \sqrt{\frac{\sigma^2 }{g}+(a\cdot\sigma_{bg}^{2})\cdot (1+\frac{a}{n_{sky}})}

where
    * :math:`{\Delta} f`  is the flux uncertainty, in electrons second\ :sup:`-1`
    * :math:`{\sigma}` is the standard deviation of photometric aperture signal, in counts second\ :sup:`-1`
    * :math:`{g}` is effective gain in electrons count\ :sup:`-1`
    * :math:`{a}` is the photometric aperture area, in pixels
    * :math:`{\sigma_{bg}}` is standard deviation of the background
    * :math:`{n_{sky}}` is the sky annulus area, in pixels

2.3.2: Calculation of ABmag Uncertainties
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Magnitude error calculation comes from computing :math:`{\frac{d(ABmag)}{d(flux)}}`. We use the following formula:

.. math::
    \Delta {ABmag} = 1.0857 \cdot  \frac{\Delta f}{f}

where
    * :math:`{\Delta {ABmag}}` is the uncertainty in ABmag
    * :math:`{\Delta f}` is the flux uncertainty, in electrons second\ :sup:`-1`
    * :math:`{f}` is the flux, in electrons second\ :sup:`-1`

2.4: Calculation of Concentration Index (CI) Values and Flag Values
-------------------------------------------------------------------
2.4.1: Calculation of Concentration Index (CI) Values
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The Concentration index is a measure of the "sharpness" of a given source’s PSF, and computed with the following
formula:

.. math::
    CI = m_{inner} - m_{outer}

where
    * :math:`{CI}` is the concentration index, in ABmag
    * :math:`{m_{inner}}` is the inner aperture ABmag
    * :math:`{m_{outer}}` is the outer aperture ABmag

We use the concentration index to classify automatically each identified photometric source as either a point source
(i.e. stars), an extended source (i.e. galaxies, nebulosity, etc.), or as an “anomalous” source (i.e. saturation,
hot pixels, cosmic ray hits, etc.). This designation is described by the value in the "flags" column.

.. _flag_generation:

2.4.2: Determination of Flag Values
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The flag value associated with each source provides users with a means to distinguish between legitimate point sources,
legitimate extended sources, and scientifically dubious sources (those likely impacted by low signal-to-noise ratio, detector
artifacts, saturation, cosmic rays, etc.). The values in the “flags” column of the catalog are a sum of a one or more of
these values. Specific flag values are defined below in table 2:

.. table:: Table 2: Flag definitions

    +------------+-----------------------------------------------------------+
    | Flag value | Meaning                                                   |
    +============+===========================================================+
    | 0          | Point source :math:`{(CI_{lower} < CI < CI_{upper})}`     |
    +------------+-----------------------------------------------------------+
    | 1          | Extended source :math:`{(CI > CI_{upper})}`               |
    +------------+-----------------------------------------------------------+
    | 2          | Bit value 2 not used in ACS or WFC3 sourcelists           |
    +------------+-----------------------------------------------------------+
    | 4          | Saturated Source                                          |
    +------------+-----------------------------------------------------------+
    | 8          | Faint Detection Limit                                     |
    +------------+-----------------------------------------------------------+
    | 16         | Hot pixels :math:`{(CI < CI_{lower})}`                    |
    +------------+-----------------------------------------------------------+
    | 32         | False Detection: Swarm Around Saturated Source            |
    +------------+-----------------------------------------------------------+
    | 64         | False detection due proximity of source to image edge     |
    |            | or other region with a low number of input images         |
    +------------+-----------------------------------------------------------+

.. attention::

    The final output filter-specific sourcelists do not contain all detected sources. Sources that are considered
    scientifically dubious are filtered out and not written to the final source catalogs. For all detectors, sources
    with a flag value greater than 5 are filtered out. Users can adjust this value using a custom input parameter file
    and changing the "flag_trim_value" parameter. For more details on how to create a custom parameter file, please
    refer to the `~drizzlepac.haputils.generate_custom_svm_mvm_param_file` documentation page.

2.4.2.1: Assignment of Flag Values 0 (Point Source), 1 (Extended Source), and 16 (Hot Pixels)
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
Assignment of flag values 0 (point source), 1 (extended source), and 16 (hot pixels) are determined purely based on the
concentration index (CI) value. The majority of commonly used filters for all ACS and WFC3 detectors have
filter-specific CI threshold values that are automatically set at run-time. However, if filter-specific CI threshold
values cannot be found, default instrument/detector-specific CI limits are used instead.  Instrument/detector/filter
combinations that do not have filter-specific CI threshold values are listed below in table 3 and  the default CI
values are listed below in table 4.

.. table:: Table 3: Instrument/detector/filter combinations that **do not** have filter-specific CI threshold values

    +------------------------+---------------------------------------------------+
    | Instrument/Detector    | Filters without specifically defined CI limits    |
    +========================+===================================================+
    | ACS/HRC                | F344N                                             |
    +------------------------+---------------------------------------------------+
    | ACS/SBC                | All ACS/SBC filters                               |
    +------------------------+---------------------------------------------------+
    | ACS/WFC                | F892N                                             |
    +------------------------+---------------------------------------------------+
    | WFC3/IR                | None                                              |
    +------------------------+---------------------------------------------------+
    | WFC3/UVIS              | None                                              |
    +------------------------+---------------------------------------------------+

.. note:: As photometry is not performed on observations that utilized grisms, prisms, polarizers, ramp filters, or quad filters, these elements were omitted from the above list.

.. table:: Table 4: Default concentration index threshold values

    +---------------------+----------------------+----------------------+
    | Instrument/Detector | :math:`{CI_{lower}}` | :math:`{CI_{upper}}` |
    +=====================+======================+======================+
    | ACS/HRC             | 0.9                  | 1.6                  |
    +---------------------+----------------------+----------------------+
    | ACS/SBC             | 0.15                 | 0.45                 |
    +---------------------+----------------------+----------------------+
    | ACS/WFC             | 0.9                  | 1.23                 |
    +---------------------+----------------------+----------------------+
    | WFC3/IR             | 0.25                 | 0.55                 |
    +---------------------+----------------------+----------------------+
    | WFC3/UVIS           | 0.75                 | 1.0                  |
    +---------------------+----------------------+----------------------+

2.4.2.2: Assignment of Flag Value 4 (Saturated Source)
""""""""""""""""""""""""""""""""""""""""""""""""""""""
A flag value of 4 is assigned to sources that are saturated. The process of identifying saturated sources starts by
first transforming the input image XY coordinates of all pixels flagged as saturated in the data quality arrays of each
input flc/flt.fits images (the images drizzled together to produce the drizzle-combined filter image being used to
measure photometry) from non-rectified, non-distortion-corrected coordinates to the rectified, distortion-corrected
frame of reference of the filter-combined image. We then identify impacted sources by cross-matching this list of
saturated pixel coordinates against the positions of sources in the newly created source catalog and assign flag values
where necessary.

2.4.2.3: Assignment of Flag Value 8 (Faint Detection Limit)
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
A flag value of 8 is assigned to sources whose signal-to-noise ratio is below a predefined value. We define sources as
being above the faint object limit if the following is true:

.. math::
    \Delta ABmag_{outer} \leq  \frac{2.5}{snr \cdot log(10))}

Where
    * :math:`{\Delta ABmag_{outer}}` is the outer aperture ABmag uncertainty
    * :math:`{snr}` is the signal-to-noise ratio, which is 1.5 for ACS/WFC and 5.0 for all other detectors.

2.4.2.4: Assignment of Flag Value 32 (False Detection: Swarm Around Saturated Source)
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
The source identification routine has been shown to identify false sources in regions near bright or saturated
sources, and in image artifacts associated with bright or saturated sources, such as diffraction spikes, and in the
pixels surrounding saturated PSF where the brightness level “plateaus” at saturation. We identify impacted sources by
locating all sources within a predefined radius of a given source and checking if the brightness of each of these
surrounding sources is less than a radially-dependent minimum brightness value defined by a pre-defined stepped
encircled energy curve. The parameters used to determine assignment of this flag are instrument-dependent, can be found
in the “swarm filter” section of the \*_quality_control_all.json files in the path described above in section 1.3.


2.4.2.5: Assignment of Flag Value 64 (False Detection Due Proximity of Source to Image Edge or Other Region with a Low Number of Input Images)
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
Sources flagged with a value of 64 are flagged as “bad” because they are inside of or in close proximity to regions
characterized by low or null input image contribution. These are areas where for some reason or another, very few or no
input images contributed to the pixel value(s) in the drizzle-combined image.
We identify sources impacted with this effect by creating a two-dimensional weight image that maps the number of
contributing exposures for every pixel. We then check each source against this map to ensure that all sources and flag
appropriately.

3: The Output Point Catalog File
================================
3.1: Filename Format
--------------------
Source positions and photometric information are written to a .ecsv (Enhanced Character Separated Values) file. The
naming of this file is fully automatic and follows the following format:
<TELESCOPE>_<PROPOSAL ID>_<OBSERVATION SET ID>_<INSTRUMENT>_<DETECTOR>_
<FILTER>_<DATASET NAME>_<CATALOG TYPE>.ecsv

So, for example if we have the following information:
    * Telescope = HST
    * Proposal ID = 98765
    * Observation set ID = 43
    * Instrument = acs
    * Detector = wfc
    * Filter name = f606w
    * Dataset name = j65c43
    * Catalog type = point-cat

The resulting auto-generated catalog filename will be:
    * hst_98765_43_acs_wfc_f606w_j65c43_point-cat.ecsv

3.2: File Format and Comparison to the HLA Catalog
--------------------------------------------------
The .ecsv file format is quite flexible and allows for the storage of not only character-separated datasets, but also
metadata. The first section (lines 4-17) contains a mapping that defines the datatype, units, and formatting
information for each data table column. The second section (lines 19-27) contains information explaining STScI’s use
policy for HAP data in refereed publications. The third section (lines 28-48) contains relevant image metadata. This
includes the following items:

    * WCS (world coordinate system) name
    * WCS (world coordinate system) type
    * Proposal ID
    * Image filename
    * Target name
    * Observation date
    * Observation time
    * Instrument
    * Detector
    * Target right ascension
    * Target declination
    * Orientation
    * Aperture right ascension
    * Aperture declination
    * Aperture position angle
    * Exposure start (MJD)
    * Total exposure duration in seconds
    * CCD Gain
    * Filter name
    * Total Number of sources in catalog

The next section (lines 50-66) contains important notes regarding the coordinate systems used, magnitude system used,
apertures used, concentration index definition and flag value definitions:

    * X, Y coordinates listed below use are zero-indexed (origin = 0,0)
    * RA and Dec values in this table are in sky coordinates (i.e. coordinates at the epoch of observation and fit to GAIADR1 (2015.0) or GAIADR2 (2015.5)).
    * Magnitude values in this table are in the ABmag system.
    * Inner aperture radius in pixels and arcseconds (based on detector platescale)
    * Outer aperture radius in pixels and arcseconds (based on detector platescale)
    * Concentration index (CI) formulaic definition
    * Flag value definitions

Finally, the last section contains the catalog of source locations and photometry values. It should be noted that the
specific columns and their ordering were deliberately chosen to facilitate a 1:1 exact mapping to the_daophot.txt
catalogs produced by Hubble Legacy Archive. As this code was designed to be the HLA's replacement, we sought to
minimize any issues caused by the transition. The column names are as follows (Note that this is the same left-to-right
ordering in the .ecsv file as well):

    * X-Center: 0-indexed X-coordinate position
    * Y-Center: 0-indexed Y-coordinate position
    * RA: Right ascension (sky coordinates), in degrees
    * DEC: Declination (sky coordinates), in degrees
    * ID: Object catalog index number
    * MagAp1: Inner aperture brightness, in ABmag
    * MagErrAp1: Inner aperture brightness uncertainty, in ABmag
    * MagAp2: Outer aperture brightness, in ABmag
    * MagErrAp2: Outer aperture brightness uncertainty, in ABmag
    * MSkyAp2: Outer aperture background brightness, in ABmag
    * StdevAp2: Standard deviation of the outer aperture background brightness, in ABmag
    * FluxAp2: Outer aperture flux, in electrons/sec
    * CI: Concentration index (MagAp1 – MagAp2), in ABmag
    * Flags: See Section 2.4.2 for flag value definitions

3.3 Rejection of Cosmic-Ray Dominated Catalogs
----------------------------------------------
Not all sets of observations contain multiple overlapping exposures in the same filter. This makes it impossible
to ignore all cosmic-rays that have impacted those single exposures.  The contributions of cosmic-rays often
overwhelm any catalog generated from those single exposures making recognizing astronomical sources almost
impossible amongst the noise of all the cosmic-rays.  As a result, those catalogs can not be trusted.  In an
effort to only publish catalogs which provide the highest science value, criteria developed by the Hubble Legacy
Archive (HLA) has been implemented to recognize those catalogs dominated by cosmic-rays and not provided as an
output product.

.. note::
  This rejection criteria is NOT applied to WFC3/IR or ACS/SBC data since they are not affected by cosmic-rays
  in the same way as the other detectors.

3.3.1 Single-image CR Rejection Algorithm
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
An algorithm has been implemented to identify and ignore cosmic-rays in single exposures.  This algorithm has
been used for ignoring cosmic-rays during the image alignment code used to determine the *a posteriori*
alignment to GAIA.

This algorithm starts by evaluating the central moments of all sources from the segment catalog.
Any source where the maximum central moment (as determined by
`photutils.segmentation.SourceProperties <https://photutils.readthedocs.io/en/stable/segmentation.html>`_
is 0 for both X and Y moments gets identified as cosmic-rays.  This indicates that the source has a
concentration of flux greater than a point-source and most probably represents a 'head-on cosmic-ray'.

In addition to these 'head-on cosmic-rays', 'glancing cosmic-rays' produce streaks across the detector.
Those are identified by identifying sources with a minimum width (semiminor_axis) less than the FWHM of a point source
and an elongation > 2.  The width and elongation are also properties defined by
`photutils.segmentation.SourceProperties <https://photutils.readthedocs.io/en/stable/segmentation.html>`_.
The combination of these criteria allows for the identification of a vast majority of cosmic-rays.  The DQ array
of the single exposure then gets updated to flag those pixels identified as cosmic-rays based on these criteria.
These DQ flags are then ONLY applied when creating the TotalProduct to limit the contribution of cosmic-rays
from the total detection image.  These flags are NOT used to generate any other product in order to avoid
affecting the photometry or astrometry of any source from the total detection image any more than necessary.

3.3.2 Rejection Criteria
^^^^^^^^^^^^^^^^^^^^^^^^
The rejection criteria has been defined so that if either the point source catalog or the segment catalog fails,
then both catalogs are rejected and deleted.

In its simplest form the criteria for rejection is:
        n_cat < thresh
where:
        thresh = crfactor * (n1_residual * n1_exposure_time)**2 / texptime
and:
        n_cat    : Number of good point and extended sources in the catalog (flag < 2)
        crfactor : Number of expected cosmic-rays per second across the entire detector
        n1_exposure_time : amount of exposure time for all single filter exposures
        texptime : Total exposure time of the combined drizzle product
        n1_residual : Remaining fraction of cosmic-rays after applying single-image CR removal

The value of ``crfactor`` should be adjusted for sub-arrays to account for the smaller area being read out, but
that logic has not yet been implemented.  The values used in the processing of single-visit mosaics are:

    segment-catalog crfactor : 300
    point-catalog crfactor   : 150

These numbers are deliberately set high to be conservative about which catalogs to keep.  The CR rate varies
with position in the orbit, and these are set high enough that it is rare for approved catalogs to be dominated
by CRs (even though they can obviously have some CRs included.)

Finally, the ``n1_residual`` term gets set as a configuration parameter with a default value of 5% (0.05).  This
indicates that the single-image cosmic-ray identification process was expected to leave 5% of the cosmic-rays
unflagged. This process can be affected by numerous factors, and having this as a user settable parameter allows
the user to account for these effects when reprocessing the data manually.  Pipeline processing, though, may
still be subject to situations where this process does not do as well which can result in a catalog with a
higher than expected contribution of cosmic-rays.  Should this number of sources trigger the rejection criteria,
these catalogs will be rejected and not written out.

Also note that we reject both the point and segment catalogs if either one fails this test.  The reasoning
behind that is that since the catalogs are based on the same image, it is unlikely that one catalog will be
good and the other contaminated.

Should the catalogs fail this test, neither type of catalogs will be written out to disk for this visit.


4: Segmentation Catalog Generation
==================================

4.1: Source Identification with PhotUtils
-----------------------------------------
For the segmentation algorithm the
`photutils.segmentation <https://photutils.readthedocs.io/en/stable/segmentation.html>`_ Astropy
tool is used to identify sources in the background-subtracted multi-filter detection image.
As is the case for the point-source detection algorithm, this is the juncture where the
common background computed in Section 1.3, relevant for both the point and segment
algorithms, is applied to the science data to begin the source detection process.
To identify a signal as a source, the signal must have a minimum number
of connected pixels, each of which is greater than its two-dimensional threshold image
counterpart.  Connectivity refers to how pixels are literally touching along their edges and
corners, and the threshold image is the background RMS image (Section 1.3)
multiplied by a configurable n-sigma value and modulated by a weighting scheme based
upon the WHT extension of the detection image. Before applying the threshold, the detection
image is filtered by the image kernel (Section 1.4) to smooth the data and enhance the ability
to identify signal which is similar in shape to the kernel. This process generates a two-dimensional
segmentation image or map where a segment is defined to be a number of connected pixels which are
all identified by a numeric label and are considered part of the same source.

The derived segmentation map is then evaluated in three ways. Both the fraction of sources which are
larger than a user-specified fraction of the image ("large" segments), as well as the total
fraction of the image covered by segments are computed. Additionally, the size in pixels of the
largest segment is checked to determine whether or not the size exceeds a user-specified limit.
If any of these scenarios are true, this is a strong indication the detection image is a
crowded astronomical field. In such a crowded field, the Gaussian kernel
(discussed in Section 1.4) can blend objects in close proximity together, making it difficult to
differentiate between the independent objects.  In extreme cases, a large number of astronomical objects
are blended together and are mistakenly identified as a single segment covering a large percent of the image.
To address this situation an alternative kernel is derived using the
`astropy.convolution.RickerWavelet2DKernel <https://docs.astropy.org/en/stable/api/astropy.convolution.RickerWavelet2DKernel.html>`_
Astropy tool. The RickerWavelet2DKernel is approximately a Gaussian surrounded by a negative
halo, and it is useful for peak or multi-scale detection.
This new kernel is then used for the generation of an improved segmentation
map from the multi-filter detection image.

The new segmentation map gets evaluated again to determine the number of "large" segments and the fraction
of the image covered by segments.  Should the new map indicate too many "large" segments or too much of the
image covered by segments, then deblending gets applied to the map.

Because different sources in close proximity can be mis-identified as a single source, it is necessary
to apply a deblending procedure to the segmentation map.  The deblending is a combination of
multi-thresholding, as is done by `Source Extractor <https://sextractor.readthedocs.io/en/latest/Introduction.html>`_
and the `watershed technique <https://en.wikipedia.org/wiki/Watershed_(image_processing)>`_.

.. caution::

    The deblending can be problematic if the background determination has not been well-determined, resulting in
    segments which are a large percentage of the map footprint.  In this case, the
    deblending can take unreasonable amounts of time (e.g., days) to conclude. This led to the
    implementation of logic to **limit the use of deblending to only those segments which are larger
    than the PSF kernel**.  This will result in some faint close sources being identified as a
    single source in the final catalog.

After deblending has successfully concluded, the resultant segmentation map is further evaluated
based on an algorithm developed for the `Hubble Legacy Archive
<https://hla.stsci.edu>`_ to determine if
big segments/blended regions persist or if a large percentage of the map is covered by segments.

The segmentation map derived from *and when used in conjunction with* the multi-filter detection image for
measuring source properties is **only** used to determine the centroids of sources.

.. note::

    Questionable centroids (e.g., values of nan or infinity) and their corresponding segments are
    removed from the catalog entirely.


4.2: Isophotal Photometry Measurements
--------------------------------------
The actual isophotal photometry measurements are made on the single-filter drizzled images using the
cleaned segmentation map derived from the multi-filter detection image.  As was the case for the
multi-filter detection image, the single-filter drizzled image is used in the determination of
appropriate background and RMS images (Section 1.3). In preparation for the photometry measurements,
the background-subtracted image, as well as the RMS image, are used to compute a total error array by
combining a background-only error array with the Poisson noise of sources.

The isophotal photometry and morphological measurements are then performed on the background-subtracted
single-filter drizzled image using the segmentation map derived from the multi-filter detection image,
the background and total error images, the image kernel, and the known WCS with the
`photutils.segmentation.source_properties <https://photutils.readthedocs.io/en/stable/segmentation.html>`_ tool. The measurements made using this tool and retained
for the output segment catalog are denoted in Table 5.

.. table:: Table 5: Isophotal Measurements - Subset of Segment Catalog Measurements and Descriptions

    +------------------------+----------------+------------------------------------------------------+
    | PhotUtils Variable     | Catalog Column | Description                                          |
    +========================+================+======================================================+
    | area                   | Area           | Total unmasked area of the source segment (pixels^2) |
    +------------------------+----------------+------------------------------------------------------+
    | background_at_centroid | Bck            | Background measured at the centroid position         |
    +------------------------+----------------+------------------------------------------------------+
    | bbox_xmin              | Xmin           | Min X pixel in the minimal bounding box segment      |
    +------------------------+----------------+------------------------------------------------------+
    | bbox_ymin              | Ymin           | Min Y pixel in the minimal bounding box segment      |
    +------------------------+----------------+------------------------------------------------------+
    | bbox_xmax              | Xmax           | Max X pixel in the minimal bounding box segment      |
    +------------------------+----------------+------------------------------------------------------+
    | bbox_ymax              | Ymax           | Max Y pixel in the minimal bounding box segment      |
    +------------------------+----------------+------------------------------------------------------+
    | covar_sigx2            | X2             | Variance of position along X (pixels^2)              |
    +------------------------+----------------+------------------------------------------------------+
    | covar_sigxy            | XY             | Covariance of position between X and Y (pixels^2)    |
    +------------------------+----------------+------------------------------------------------------+
    | covar_sigy2            | Y2             | Variance of position along Y (pixels^2)              |
    +------------------------+----------------+------------------------------------------------------+
    | cxx                    | CXX            | SExtractor's CXX ellipse parameter (pixel^-2)        |
    +------------------------+----------------+------------------------------------------------------+
    | cxy                    | CXY            | SExtractor's CXY ellipse parameter (pixel^-2)        |
    +------------------------+----------------+------------------------------------------------------+
    | cyy                    | CYY            | SExtractor's CYY ellipse parameter (pixel^-2)        |
    +------------------------+----------------+------------------------------------------------------+
    | elongation             | Elongation     | Ratio of the semi-major to the semi-minor length     |
    +------------------------+----------------+------------------------------------------------------+
    | ellipticity            | Ellipticity    | 1 minus the Elongation                               |
    +------------------------+----------------+------------------------------------------------------+
    | id                     | ID             | Numeric label of the segment/Catalog ID number       |
    +------------------------+----------------+------------------------------------------------------+
    | orientation            | Theta          | Angle between the semi-major and NAXIS1 axes         |
    +------------------------+----------------+------------------------------------------------------+
    | sky_centroid_icrs      | RA and DEC     | Equatorial coordinates in degrees                    |
    +------------------------+----------------+------------------------------------------------------+
    | source_sum             | FluxIso        | Sum of the unmasked data within the source segment   |
    +------------------------+----------------+------------------------------------------------------+
    | source_sum_err         | FluxIsoErr     | Uncertainty of FluxIso, propagated from input array  |
    +------------------------+----------------+------------------------------------------------------+
    | xcentroid              | X-Centroid     | X-coordinate of the centroid in the source segment   |
    +------------------------+----------------+------------------------------------------------------+
    | ycentroid              | Y-Centroid     | Y-coordinate of the centroid in the source segment   |
    +------------------------+----------------+------------------------------------------------------+


4.3: Aperture Photometry Measurements
-------------------------------------
The aperture photometry measurements included with the segmentation algorithm use the same configuration
variable values and literally follow the same steps as what is done for the point algorithm as
documented in Sections 2.2 - 2.4.  The fundamental difference between the point and segment computations is
the source position list used for the measurements.

5: The Output Segment Catalog Files
===================================
The metadata for the catalogs, both total detection and filter, as discussed in Sections 3.1 and 3.2,
is pre-dominantly the same.  The differences arise with respect to the specific columns present in the
catalog.  The naming convention for the catalogs is also the same except the filter name is replaced
by the literal *total* for the total detection catalog:
<TELESCOPE>_<PROPOSAL ID>_<OBSERVATION SET ID>_<INSTRUMENT>_<DETECTOR>_total_<DATASET NAME>_<CATALOG TYPE>.ecsv
where CATALOG TYPE is either *point-cat* or *segment-cat*.
Using the same example from Section 3.1, the resulting auto-generated segment total detection catalog
filename will be:

* hst_98765_43_acs_wfc_total_j65c43_segment-cat.ecsv

and the filter catalog filename will be:

* hst_98765_43_acs_wfc_f606w_j65c43_segment-cat.ecsv

5.1: Total Detection Segment Catalog
------------------------------------
The multi-filter detection level (aka total) catalog contains the fundamental position measurements of
the detected source: ID, X-Centroid, Y-Centroid, RA, and DEC, supplemented by some of the
aperture photometry measurements from *each* of the filter catalogs (ABmag of the outer aperture, Concentration
Index, and Flags).  Effectively, the output Total Detection Segment Catalog is a distilled version of all of
the Filter Segment Catalogs.

5.2: Filter Segment Catalog and Comparison to the HLA Catalog
-------------------------------------------------------------
Section 3.2 discusses the file format for the output filter catalogs, where the latter portion of this
section is specific to the point catalogs.  The general commentary is still relevant for the segment catalogs,
except for the specific columns.  In the case of the segment filter catalogs, the specific columns and the
order of the columns were designed to be similar to the Source Extractor catalogs produced by the
`Hubble Legacy Archive (HLA) <https://hla.stsci.edu>`_ project.

Having said this, the `PhotUtils/Segmentation <https://photutils.readthedocs.io/en/stable/segmentation.html>`_
tool is not as mature as Source Extractor, and it was not clear that all of the output columns in the HLA
product were relevant for most users.  As a result, some measurements in the HLA Source Extractor
catalog may be missing from the output segment catalog at this time.
The current Segment column measurements are as follows in Table 6 with the same left-to-right ordering as found
in the .ecsv:

.. table:: Table 6: Segment Filter Catalog Measurements and Descriptions

    +----------------+------------------+---------------------------------------------+---------------+
    | Segment Column | SExtactor Column | Description                                 | Units         |
    +================+==================+=============================================+===============+
    | X-Centroid     | X_IMAGE          | 0-indexed Coordinate position               | pixel         |
    +----------------+------------------+---------------------------------------------+---------------+
    | Y-Centroid     | Y_IMAGE          | 0-indexed Coordinate position               | pixel         |
    +----------------+------------------+---------------------------------------------+---------------+
    | RA             | RA               | Sky coordinate at epoch of observation      | degrees       |
    +----------------+------------------+---------------------------------------------+---------------+
    | DEC            | DEC              | Sky coordinate at epoch of observation      | degrees       |
    +----------------+------------------+---------------------------------------------+---------------+
    | ID             |                  | Catalog Object Identification Number        |               |
    +----------------+------------------+---------------------------------------------+---------------+
    | CI             | CI               | Concentration Index                         |               |
    +----------------+------------------+---------------------------------------------+---------------+
    | Flags          | FLAGS            |                                             |               |
    +----------------+------------------+---------------------------------------------+---------------+
    | MagAp1         | MAG_APER1        | ABmag of source, inner (smaller) aperture   | ABmag         |
    +----------------+------------------+---------------------------------------------+---------------+
    | MagErrAp1      | MAGERR_APER1     | Error of MagAp1                             | ABmag         |
    +----------------+------------------+---------------------------------------------+---------------+
    | FluxAp1        | FLUX_APER1       | Flux of source, inner (smaller) aperture    | electrons/s   |
    +----------------+------------------+---------------------------------------------+---------------+
    | FluxErrAp1     | FLUXERR_APER1    | Error of FluxAp1                            | electrons/s   |
    +----------------+------------------+---------------------------------------------+---------------+
    | MagAp2         | MAG_APER2        | ABmag of source, outer (larger) aperture    | ABmag         |
    +----------------+------------------+---------------------------------------------+---------------+
    | MagErrAp2      | MAGERR_APER2     | Error of MagAp2                             | ABmag         |
    +----------------+------------------+---------------------------------------------+---------------+
    | FluxAp2        | FLUX_APER2       | Flux of source, outer (larger) aperture     | electrons/s   |
    +----------------+------------------+---------------------------------------------+---------------+
    | FluxErrAp2     | FLUXERR_APER2    | Error of FluxAp2                            | electrons/s   |
    +----------------+------------------+---------------------------------------------+---------------+
    | MSkyAp2        |                  | ABmag of sky, outer (larger) aperture       | ABmag         |
    +----------------+------------------+---------------------------------------------+---------------+
    | Bck            | BACKGROUND       | Background, position of source centroid     | electrons/s   |
    +----------------+------------------+---------------------------------------------+---------------+
    | Area           |                  | Total unmasked area of the source segment   | pixels^2      |
    +----------------+------------------+---------------------------------------------+---------------+
    | MagIso         | MAG_ISO          | Magnitude corresponding to FluxIso          | ABmag         |
    +----------------+------------------+---------------------------------------------+---------------+
    | FluxIso        | FLUX_ISO         | Sum of unmasked data in source segment      | electrons/s   |
    +----------------+------------------+---------------------------------------------+---------------+
    | FluxIsoErr     | FLUXERR_ISO      | Uncertainty, propagated from input error    | electrons/s   |
    +----------------+------------------+---------------------------------------------+---------------+
    | Xmin           | XMIN_IMAGE       | Min X pixel in minimal bounding box segment | pixels        |
    +----------------+------------------+---------------------------------------------+---------------+
    | Ymin           | YMIN_IMAGE       | Min Y pixel in minimal bounding box segment | pixels        |
    +----------------+------------------+---------------------------------------------+---------------+
    | Xmax           | XMAX_IMAGE       | Max X pixel in minimal bounding box segment | pixels        |
    +----------------+------------------+---------------------------------------------+---------------+
    | Ymax           | YMAX_IMAGE       | Max Y pixel in minimal bounding box segment | pixels        |
    +----------------+------------------+---------------------------------------------+---------------+
    | X2             | X2_IMAGE         | Variance along X                            | pixel^2       |
    +----------------+------------------+---------------------------------------------+---------------+
    | Y2             | Y2_IMAGE         | Variance along Y                            | pixel^2       |
    +----------------+------------------+---------------------------------------------+---------------+
    | XY             | XY_IMAGE         | Covariance of position between X and Y      | pixel^2       |
    +----------------+------------------+---------------------------------------------+---------------+
    | CXX            | CXX_IMAGE        | SExtractor's ellipse parameter              | pixel^2       |
    +----------------+------------------+---------------------------------------------+---------------+
    | CYY            | CYY_IMAGE        | SExtractor's ellipse parameter              | pixel^2       |
    +----------------+------------------+---------------------------------------------+---------------+
    | CXY            | CXY_IMAGE        | SExtractor's ellipse parameter              | pixel^2       |
    +----------------+------------------+---------------------------------------------+---------------+
    | Elongation     | ELONGATION       | Ratio of semi-major to semi-minor length    |               |
    +----------------+------------------+---------------------------------------------+---------------+
    | Ellipticity    | ELLIPTICITY      | The value of 1 minus the elongation         |               |
    +----------------+------------------+---------------------------------------------+---------------+
    | Theta          | THETA_IMAGE      | Angle between semi-major and NAXIS1 axes    | radians       |
    +----------------+------------------+---------------------------------------------+---------------+

6: Reading The Output Catalog Files
===================================
All of the Point and Segmentation catalogs, filter and total, are Enhanced Character-Separated Values (ECSV)
files which are human-readable ASCII tables. As such, it is straight-foward to access the astronomical
source data contained in the rows of the files in a programmatic way via Astropy or Pandas.

An Astropy example with a Segmentation filter catalog will generate the following Astropy table (abridged view)::

    >>> from astropy.table import Table
    >>> astro_tab=Table.read("hst_15064_11_acs_wfc_f814w_jdjb11_segment-cat.ecsv", format="ascii.ecsv")
    >>> astro_tab
    <Table length=375>
    X-Centroid Y-Centroid       RA           DEC         ID      CI   ...    CYY       CXY    Elongation Ellipticity  Theta
       pix        pix          deg           deg              mag(AB) ...  1 / pix2  1 / pix2                          rad
     float64    float64      float64       float64     int64  float64 ...  float64   float64   float64     float64   float64
    ---------- ---------- ------------- ------------- ------- ------- ... --------- --------- ---------- ----------- --------
      3774.045     87.935   313.5799763    -0.1839533       1   2.144 ...   0.25651  -0.13623       1.30        0.23   52.349
      3630.189    101.246   313.5819743    -0.1837685       2   1.642 ...   0.12165  -0.00195       1.03        0.03   82.412

The “comment" parameter in this Pandas example is necessary so that the reader will skip over the header lines which it cannot
parse.  The first line which is actually read is the “line 0" (header=0) which consists of the ascii column names.  The result is a
Pandas dataframe for this example of the Point filter catalog::

    >>> import pandas
    >>> df=pandas.read_csv("hst_15064_11_acs_wfc_f814w_jdjb11_point-cat.ecsv", sep=" ", header=0, comment="#")
    >>> df
            X-Center     Y-Center          RA       DEC   ID  ...   MSkyAp2  StdevAp2      FluxAp2        CI  Flags
    0    3774.738972    89.759486  313.579967 -0.183928    1  ...  0.165745  0.009700     4.732320  1.561092      1
    1    3630.522602   102.347181  313.581970 -0.183753    2  ...  0.151377  0.227345   834.948972  1.189462      4
