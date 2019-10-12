"""Test becquerel's Spectrum."""

from __future__ import print_function
import pytest
import datetime
import numpy as np
from uncertainties import ufloat, UFloat, unumpy
import becquerel as bq
from parsers_test import SAMPLES

TEST_DATA_LENGTH = 256
TEST_COUNTS = 4
TEST_GAIN = 8.23
TEST_EDGES_KEV = np.arange(TEST_DATA_LENGTH + 1) * TEST_GAIN


def make_data(lam=TEST_COUNTS, size=TEST_DATA_LENGTH):
    """Build a vector of random counts."""

    floatdata = np.random.poisson(lam=lam, size=size)
    return floatdata.astype(np.int)


def make_spec(t, lt=None, lam=TEST_COUNTS):
    """Get spectrum to use in parameterized tests.

    Pytest Note:
        one might think you could do:
        @pytest.mark.parametrize('spec1, spec2', [
            (uncal_spec, uncal_spec),
            (cal_spec, cal_spec)
        ])
        def test_add(spec1, spec2):
            ...

        but you can't put fixtures inside parametrize(). Thus the fixtures
        call this function for simplicity.

    """

    if t == 'uncal':
        return bq.Spectrum(make_data(lam=lam), livetime=lt)
    elif t == 'cal':
        return bq.Spectrum(
            make_data(lam=lam), bin_edges_kev=TEST_EDGES_KEV, livetime=lt)
    elif t == 'cal_new':
        return bq.Spectrum(
            make_data(lam=lam), livetime=lt,
            bin_edges_kev=np.arange(TEST_DATA_LENGTH + 1) * 0.67)
    elif t == 'cal_cps':
        return bq.Spectrum(
            cps=make_data(lam=lam), bin_edges_kev=TEST_EDGES_KEV, livetime=lt)
    elif t == 'uncal_long':
        return bq.Spectrum(
            make_data(lam=lam, size=TEST_DATA_LENGTH * 2), livetime=lt)
    elif t == 'uncal_cps':
        return bq.Spectrum(cps=make_data(lam=lam), livetime=lt)
    elif t == 'data':
        return make_data()
    else:
        return t


@pytest.fixture
def spec_data():
    """Build a vector of random counts."""

    return make_data()


@pytest.fixture
def uncal_spec(spec_data):
    """Generate an uncalibrated spectrum."""

    return make_spec('uncal')


@pytest.fixture
def uncal_spec_2(spec_data):
    """Generate an uncalibrated spectrum (2nd instance)."""

    return make_spec('uncal')


@pytest.fixture
def uncal_spec_cps(spec_data):
    """Generate an uncalibrated spectrum with cps data."""

    return make_spec('uncal_cps')


@pytest.fixture
def uncal_spec_long(spec_data):
    """Generate an uncalibrated spectrum, of longer length."""

    return make_spec('uncal_long')


@pytest.fixture
def cal_spec(spec_data):
    """Generate a calibrated spectrum."""

    return make_spec('cal')


@pytest.fixture
def cal_spec_2(spec_data):
    """Generate a calibrated spectrum (2nd instance)."""

    return make_spec('cal')


# -----------------------------------------------------------------------------
# File IO
# -----------------------------------------------------------------------------


@pytest.fixture
def cal_spec_cps(spec_data):
    """Generate a calibrated spectrum with cps data."""

    return bq.Spectrum(cps=spec_data, bin_edges_kev=TEST_EDGES_KEV)


class TestSpectrumFromFile(object):
    """Test Spectrum.from_file() class method."""

    def run_from_file(self, extension):
        """Run the test of from_file() for files with the given extension."""
        filenames = SAMPLES.get(extension, [])
        assert len(filenames) >= 1
        for filename in filenames:
            spec = bq.Spectrum.from_file(filename)
            assert spec.livetime is not None

    def test_spe(self):
        """Test Spectrum.from_file for SPE file........................."""
        with pytest.warns(bq.parsers.SpectrumFileParsingWarning):
            self.run_from_file('.spe')

    def test_spc(self):
        """Test Spectrum.from_file for SPC file........................."""

        self.run_from_file('.spc')

    def test_cnf(self):
        """Test Spectrum.from_file for CNF file........................."""

        self.run_from_file('.cnf')

    def test_error(self):
        """Test _get_file_object() raises error for bad file type"""

        with pytest.raises(NotImplementedError):
            bq.Spectrum.from_file('foo.bar')


# ----------------------------------------------
#         Test Spectrum.__init__()
# ----------------------------------------------

def test_uncal(uncal_spec):
    """Test simple uncalibrated construction."""

    assert len(uncal_spec.counts) == TEST_DATA_LENGTH
    assert not uncal_spec.is_calibrated


def test_uncal_cps(uncal_spec_cps):
    """Test simple uncalibrated construction w CPS. More CPS tests later"""

    assert len(uncal_spec_cps.cps) == TEST_DATA_LENGTH
    assert not uncal_spec_cps.is_calibrated


def test_cal(cal_spec):
    """Test simple calibrated construction."""

    assert len(cal_spec.counts) == TEST_DATA_LENGTH
    assert len(cal_spec.bin_edges_kev) == TEST_DATA_LENGTH + 1
    assert len(cal_spec.energies_kev) == TEST_DATA_LENGTH
    assert cal_spec.is_calibrated


def test_init_exceptions(spec_data):
    """Test errors on initialization."""

    with pytest.raises(bq.SpectrumError):
        bq.Spectrum([])
    with pytest.raises(bq.SpectrumError):
        bq.Spectrum(cps=[])
    with pytest.raises(bq.SpectrumError):
        bq.Spectrum(spec_data, bin_edges_kev=TEST_EDGES_KEV[:-1])
    with pytest.raises(bq.SpectrumError):
        bq.Spectrum(cps=spec_data, bin_edges_kev=TEST_EDGES_KEV[:-1])
    with pytest.raises(bq.SpectrumError):
        bq.Spectrum(spec_data, cps=spec_data)
    with pytest.raises(bq.SpectrumError):
        bq.Spectrum(bin_edges_kev=TEST_EDGES_KEV)

    bad_edges = TEST_EDGES_KEV.copy()
    bad_edges[12] = bad_edges[9]
    with pytest.raises(ValueError):
        bq.Spectrum(spec_data, bin_edges_kev=bad_edges)


def test_uncalibrated_exception(uncal_spec):
    """Test UncalibratedError."""

    with pytest.raises(bq.UncalibratedError):
        uncal_spec.energies_kev


def test_negative_input(spec_data):
    """Make sure negative values in counts throw an exception,
       and exception is not raised if uncs are provided."""

    neg_spec = spec_data[:]
    neg_spec[::2] *= -1
    neg_uncs = np.where(neg_spec < 0, np.nan, 1)

    with pytest.raises(bq.SpectrumError):
        spec = bq.Spectrum(neg_spec)

    spec = bq.Spectrum(neg_spec, uncs=neg_uncs)
    assert np.any(spec.counts_vals < 0)
    assert np.any(np.isnan(spec.counts_uncs))


# ----------------------------------------------
#      Test Spectrum.from_listmode behavior
# ----------------------------------------------

# It's easy to introduce off-by-one errors in histogramming, so run quite a few
# sanity checks here.
def test_listmode():
    NBINS = 100
    MEAN = 1000.
    STDDEV = 50.
    NSAMPLES = 10000
    XMIN, XMAX = 0., 2000.
    BW = (XMAX - XMIN) / (1.0 * NBINS)
    lmd = np.random.normal(MEAN, STDDEV, NSAMPLES)

    # test with args
    spec0 = bq.Spectrum.from_listmode(lmd, bins=NBINS, xmin=XMIN, xmax=XMAX)
    assert len(spec0) == NBINS
    assert np.isclose(spec0.bin_widths[0], BW)
    assert spec0.bin_edges_kev[0] == XMIN
    assert spec0.bin_edges_kev[-1] == XMAX
    assert len(spec0.bin_edges_kev) == NBINS + 1
    assert spec0.has_uniform_bins()
    assert spec0.find_bin(XMIN) == 0
    assert spec0.find_bin(XMIN + BW/4.0) == 0
    assert spec0.find_bin(XMAX - BW/4.0) == NBINS - 1
    with pytest.raises(AssertionError):
        spec0.find_bin(XMAX)
    with pytest.raises(AssertionError):
        spec0.find_bin(XMIN - BW/4.0)

    # test without args
    spec1 = bq.Spectrum.from_listmode(lmd)
    assert len(spec1) == int(np.ceil(max(lmd)))

    # test non-uniform bins
    NEDGES = NBINS + 1
    log_bins = np.logspace(1, 4, num=NEDGES, base=10.0)
    spec2 = bq.Spectrum.from_listmode(lmd, bins=log_bins)
    assert len(spec2) == NBINS
    assert spec2.has_uniform_bins() is False
    assert spec2.find_bin(1e1) == 0
    assert spec2.find_bin(1e1 + 1e-9) == 0
    assert spec2.find_bin(1e4 - 1e-9) == NBINS - 1


# ----------------------------------------------
#      Test Spectrum repr behavior
# ----------------------------------------------

def test_repr(cal_spec):
    repr(cal_spec)


def test_str(cal_spec):
    str(cal_spec)


# ----------------------------------------------
#      Test Spectrum livetime properties
# ----------------------------------------------

@pytest.fixture(params=[86400, 300.6, 0.88])
def livetime(request):
    return request.param


def test_livetime_arg(spec_data, livetime):
    """Test manual livetime input."""

    spec = bq.Spectrum(spec_data, livetime=livetime)
    assert spec.livetime == livetime


def test_livetime_arg_cps(spec_data, livetime):
    """Test manual livetime input with CPS."""

    cps = spec_data / float(livetime)
    spec = bq.Spectrum(cps=cps, livetime=livetime)
    assert spec.livetime == livetime


def test_no_livetime(spec_data):
    """Test livetime property when not specified."""

    spec = bq.Spectrum(spec_data)
    assert spec.livetime is None

    cps_spec = bq.Spectrum(cps=spec_data / 300.6)
    assert cps_spec.livetime is None


# ----------------------------------------------
#     Test start_time, stop_time, realtime
# ----------------------------------------------

@pytest.mark.parametrize('start, stop', [
    (datetime.datetime(2017, 1, 1, 17, 0, 3),
     datetime.datetime(2017, 1, 1, 18, 0, 3)),
    ('2017-01-19 17:21:00', '2017-01-20 14:19:32'),
    (datetime.datetime(2017, 1, 1, 0, 30, 0, 385), '2017-01-01 12:44:22')
])
@pytest.mark.parametrize('rt', [3600, 2345.6])
def test_acqtime_construction(spec_data, start, stop, rt):
    """Test construction with 2 out of 3 of start, stop, and realtime."""

    bq.Spectrum(spec_data, start_time=start, stop_time=stop)
    bq.Spectrum(spec_data, start_time=start, realtime=rt)
    bq.Spectrum(spec_data, realtime=rt, stop_time=stop)


@pytest.mark.parametrize('start, stop, rt, expected_err', [
    ('2017-01-19 17:21:00', '2017-01-20 17:21:00', 86400, bq.SpectrumError),
    ('2017-01-19 17:21:00', '2017-01-18 17:21:00', None, ValueError),
])
def test_bad_acqtime_construction(spec_data, start, stop, rt, expected_err):
    """Test bad construction of a spectrum with start, stop, or realtimes."""

    with pytest.raises(expected_err):
        bq.Spectrum(spec_data, start_time=start, stop_time=stop, realtime=rt)


def test_bad_realtime_livetime(spec_data):
    """Test error of livetime > realtime."""

    with pytest.raises(ValueError):
        bq.Spectrum(spec_data, livetime=300, realtime=290)


# ----------------------------------------------
#         Test uncertainties in Spectrum
# ----------------------------------------------

def test_construct_float_int(spec_data):
    """Construct spectrum with non-UFloats (float and int)."""

    spec = bq.Spectrum(spec_data)
    assert isinstance(spec.counts[0], UFloat)
    spec = bq.Spectrum(spec_data.astype(float))
    assert isinstance(spec.counts[0], UFloat)


def test_construct_ufloat(spec_data):
    """Construct spectrum with UFloats"""

    ucounts = unumpy.uarray(spec_data, np.ones_like(spec_data))
    spec = bq.Spectrum(ucounts)
    assert isinstance(spec.counts[0], UFloat)
    assert spec.counts[0].std_dev == 1


def test_construct_float_int_uncs(spec_data):
    """Construct spectrum with non-UFloats and specify uncs."""

    uncs = np.ones_like(spec_data)
    spec = bq.Spectrum(spec_data, uncs=uncs)
    assert isinstance(spec.counts[0], UFloat)
    uncs2 = np.array([c.std_dev for c in spec.counts])
    assert np.allclose(uncs2, 1)


def test_construct_errors(spec_data):
    """Construct spectrum with UFloats plus uncs and get an error."""

    uncs = np.ones_like(spec_data)
    ucounts = unumpy.uarray(spec_data, uncs)
    with pytest.raises(bq.core.utils.UncertaintiesError):
        bq.Spectrum(ucounts, uncs=uncs)

    ucounts[0] = 1
    with pytest.raises(bq.core.utils.UncertaintiesError):
        bq.Spectrum(ucounts)


def test_properties(spec_data):
    """Test counts_vals and counts_uncs."""

    spec = bq.Spectrum(spec_data)
    assert isinstance(spec.counts[0], UFloat)
    assert np.allclose(spec.counts_vals, spec_data)
    expected_uncs = np.sqrt(spec_data)
    expected_uncs[expected_uncs == 0] = 1
    assert np.allclose(spec.counts_uncs, expected_uncs)

    uncs = spec_data
    ucounts = unumpy.uarray(spec_data, uncs)
    spec = bq.Spectrum(ucounts)
    assert np.allclose(spec.counts_vals, spec_data)
    assert np.allclose(spec.counts_uncs, uncs)

    uncs = np.ones_like(spec_data)
    spec = bq.Spectrum(spec_data, uncs=uncs)
    assert np.allclose(spec.counts_uncs, uncs)


# ----------------------------------------------
#         Test Spectrum.bin_widths
# ----------------------------------------------

def test_bin_widths(cal_spec):
    """Test Spectrum.bin_widths"""

    cal_spec.bin_widths
    assert len(cal_spec.bin_widths) == len(cal_spec.counts)
    assert np.allclose(cal_spec.bin_widths, TEST_GAIN)


def test_bin_width_error(uncal_spec):
    """Test Spectrum.bin_widths error"""

    with pytest.raises(bq.UncalibratedError):
        uncal_spec.bin_widths


# ----------------------------------------------
#         Test Spectrum CPS and CPS/keV
# ----------------------------------------------

@pytest.mark.parametrize('construction_kwargs', [
    {'livetime': 300.0},
    {'livetime': 300.0,
     'bin_edges_kev': TEST_EDGES_KEV},
])
def test_cps(spec_data, construction_kwargs):
    """Test cps property and uncertainties on uncal and cal spectrum."""

    spec = bq.Spectrum(spec_data, **construction_kwargs)
    spec.cps
    spec.cps_vals
    spec.cps_uncs
    assert np.all(spec.counts_vals == spec_data)
    assert np.allclose(spec.cps_vals, spec_data / spec.livetime)
    assert np.allclose(spec.cps_uncs, spec.counts_uncs / spec.livetime)


def test_cpskev(spec_data, livetime):
    """Test cpskev property and uncertainties"""

    spec = bq.Spectrum(spec_data, livetime=livetime,
                       bin_edges_kev=TEST_EDGES_KEV)
    spec.cpskev
    spec.cpskev_vals
    spec.cpskev_uncs
    assert np.allclose(
        spec.cpskev_vals, spec_data / spec.bin_widths / float(livetime))
    assert np.allclose(
        spec.cpskev_uncs, spec.counts_uncs / spec.bin_widths / float(livetime))


def test_cps_cpsspec(spec_data, livetime):
    """Test cps property of CPS-style spectrum."""

    spec = bq.Spectrum(cps=spec_data / float(livetime))
    assert spec.cps is not None
    assert np.all(spec.cps_vals == spec_data / float(livetime))
    assert np.all(np.isnan(spec.cps_uncs))
    with pytest.raises(bq.SpectrumError):
        spec.counts
    with pytest.raises(bq.SpectrumError):
        spec.counts_vals
    with pytest.raises(bq.SpectrumError):
        spec.counts_uncs


def test_cps_errors(uncal_spec):
    """Test errors in CPS."""

    with pytest.raises(bq.SpectrumError):
        uncal_spec.cps


def test_cpskev_errors(spec_data):
    """Test errors in CPS/keV."""

    spec = bq.Spectrum(spec_data, livetime=300.9)
    with pytest.raises(bq.UncalibratedError):
        spec.cpskev


# ----------------------------------------------
#   Test addition and subtraction of spectra
# ----------------------------------------------

@pytest.mark.parametrize('lt1, lt2', [
    (300, 600),
    (12.6, 0.88),
    (300, 12.6),
    (12.6, None),
    (None, None)])
@pytest.mark.parametrize('type1, type2', [
    ('uncal', 'uncal'),
    ('cal', 'cal')])
def test_add(type1, type2, lt1, lt2):
    """Test addition of spectra"""

    spec1, spec2 = (make_spec(type1, lt=lt1),
                    make_spec(type2, lt=lt2))

    if lt1 and lt2:
        tot = spec1 + spec2
        assert tot.livetime == lt1 + lt2
    else:
        with pytest.warns(bq.SpectrumWarning):
            tot = spec1 + spec2
        assert tot.livetime is None
    assert np.all(tot.counts == spec1.counts + spec2.counts)
    assert np.all(tot.counts_vals ==
                  spec1.counts_vals + spec2.counts_vals)


@pytest.mark.parametrize('type1, type2, expected_error', [
    ('uncal', 'cal', bq.SpectrumError),
    ('uncal', 'uncal_long', bq.SpectrumError),
    ('uncal', 'data', TypeError),
    ('data', 'uncal', TypeError),
    ('uncal', 5, TypeError),
    (5, 'cal', TypeError),
    ('cal', 'asdf', TypeError),
    ('asdf', 'uncal', TypeError),
    ('uncal', 'data', TypeError),
    ('cal', 'cal_new', NotImplementedError)
])
def test_add_sub_errors(type1, type2, expected_error):
    """Test addition and subtraction that causes errors"""

    spec1, spec2 = make_spec(type1), make_spec(type2)
    with pytest.raises(expected_error):
        spec1 + spec2
    with pytest.raises(expected_error):
        spec1 - spec2


@pytest.mark.parametrize('type1, type2', [
    ('uncal', 'uncal'),
    ('cal', 'cal')])
def test_add_uncs(type1, type2):
    """Test uncertainties on addition of uncal spectra"""

    spec1, spec2 = make_spec(type1), make_spec(type2)

    with pytest.warns(bq.SpectrumWarning):
        tot = spec1 + spec2

    uncs = np.sqrt(spec1.counts_uncs**2 + spec2.counts_uncs**2)
    assert np.allclose(tot.counts_uncs, uncs)


@pytest.mark.parametrize('type1, type2, lt1, lt2', [
    ('uncal_cps', 'uncal_cps', 300, 12.6),
    ('uncal_cps', 'uncal_cps', None, 12.6),
    ('uncal_cps', 'uncal_cps', None, None)])
def test_add_sub_cps(type1, type2, lt1, lt2):
    """Test addition and subtraction of CPS spectra"""

    spec1, spec2 = (make_spec(type1, lt=lt1),
                    make_spec(type2, lt=lt2))

    tot = spec1 + spec2
    assert np.all(tot.cps_vals == spec1.cps_vals + spec2.cps_vals)
    assert tot.livetime is None

    diff = spec1 - spec2
    assert diff.livetime is None
    assert np.all(diff.cps_vals == spec1.cps_vals - spec2.cps_vals)


@pytest.mark.parametrize('type1, type2, lt1, lt2', [
    ('uncal', 'uncal_cps', None, None),
    ('uncal_cps', 'uncal', None, None),
    ('uncal', 'uncal_cps', 300, None),
    ('uncal_cps', 'uncal', None, 300),
    ('uncal', 'uncal_cps', 300, 600),
    ('uncal_cps', 'uncal', 600, 300)])
def test_adddition_errors(type1, type2, lt1, lt2):
    """Test errors during addition of mixed spectra"""

    spec1, spec2 = (make_spec(type1, lt=lt1),
                    make_spec(type2, lt=lt2))

    with pytest.raises(bq.SpectrumError):
        spec1 + spec2


@pytest.mark.parametrize('lt1, lt2', [
    (300, 600),
    (12.6, 0.88),
    (300, 12.6)])
@pytest.mark.parametrize('type1, type2', [
    ('uncal', 'uncal'),
    ('cal', 'cal')])
def test_subtract_counts(type1, type2, lt1, lt2):
    """Test Spectrum subtraction with counts"""

    spec1, spec2 = (make_spec(type1, lt=lt1),
                    make_spec(type2, lt=lt2))
    with pytest.warns(bq.SpectrumWarning):
        diff = spec1 - spec2
    assert diff.livetime is None
    assert np.allclose(diff.cps_vals, spec1.cps_vals - spec2.cps_vals)
    assert np.all(diff.cps_uncs > spec1.cps_uncs)
    assert np.all(diff.cps_uncs > spec2.cps_uncs)


@pytest.mark.parametrize('type1, type2, lt1, lt2', [
    ('uncal', 'uncal_cps', None, None),
    ('uncal_cps', 'uncal', None, None),
    ('uncal', 'uncal_cps', None, 300),
    ('uncal_cps', 'uncal', 300, None),
    ('uncal', 'uncal_cps', 300, None),
    ('uncal_cps', 'uncal', None, 300)])
def test_subtract_errors(type1, type2, lt1, lt2):
    """Test errors/warnings during subtraction of mixed spectra"""

    spec1, spec2 = (make_spec(type1, lt=lt1),
                    make_spec(type2, lt=lt2))
    if lt1 is None and lt2 is None:
        with pytest.raises(bq.SpectrumError):
            diff = spec1 - spec2
    else:
        with pytest.warns(bq.SpectrumWarning):
            diff = spec1 - spec2
        assert diff.livetime is None


# ----------------------------------------------
#  Test multiplication and division of spectra
# ----------------------------------------------

@pytest.mark.parametrize('factor', [0.88, 1, 2, 43.6])
@pytest.mark.parametrize('spectype', ['uncal', 'cal'])
def test_basic_mul_div(spectype, factor):
    """
    Basic multiplication/division of uncalibrated spectrum by a scalar.
    """

    spec = make_spec(spectype)

    mult_left = spec * factor
    assert np.allclose(mult_left.counts_vals, factor * spec.counts_vals)
    assert np.allclose(mult_left.counts_uncs, factor * spec.counts_uncs)
    assert mult_left.livetime is None

    mult_right = factor * spec
    assert np.allclose(mult_right.counts_vals, factor * spec.counts_vals)
    assert np.allclose(mult_right.counts_uncs, factor * spec.counts_uncs)
    assert mult_right.livetime is None

    div = spec / factor
    assert np.allclose(div.counts_vals, spec.counts_vals / factor)
    assert np.allclose(div.counts_uncs, spec.counts_uncs / factor)
    assert div.livetime is None


@pytest.mark.parametrize('factor', [0.88, 1, 2, 43.6])
def test_cps_mul_div(uncal_spec_cps, factor):
    """Multiplication/division of a CPS spectrum."""

    mult_left = uncal_spec_cps * factor
    assert np.allclose(mult_left.cps_vals, factor * uncal_spec_cps.cps_vals)
    assert mult_left.livetime is None

    mult_right = factor * uncal_spec_cps
    assert np.allclose(mult_right.cps_vals, factor * uncal_spec_cps.cps_vals)
    assert mult_right.livetime is None

    div = uncal_spec_cps / factor
    assert np.allclose(div.cps_vals, uncal_spec_cps.cps_vals / factor)
    assert div.livetime is None


@pytest.mark.parametrize('factor', [
    ufloat(0.88, 0.01),
    ufloat(1, 0.1),
    ufloat(43, 1)])
@pytest.mark.parametrize('spectype', ['uncal', 'cal'])
def test_uncal_mul_div_uncertainties(spectype, factor):
    """
    Multiplication/division of uncal spectrum by a scalar with uncertainty.
    """

    spec = make_spec(spectype)

    mult_left = spec * factor
    assert np.allclose(
        mult_left.counts_vals, factor.nominal_value * spec.counts_vals)
    assert np.all(
        (mult_left.counts_uncs > factor.nominal_value * spec.counts_uncs) |
        (spec.counts_vals == 0))
    assert mult_left.livetime is None

    mult_right = factor * spec
    assert np.allclose(
        mult_right.counts_vals, factor.nominal_value * spec.counts_vals)
    assert np.all(
        (mult_right.counts_uncs > factor.nominal_value * spec.counts_uncs) |
        (spec.counts_vals == 0))
    assert mult_right.livetime is None

    div = spec / factor
    assert np.allclose(
        div.counts_vals, spec.counts_vals / factor.nominal_value)
    assert np.all(
        (div.counts_uncs > spec.counts_uncs / factor.nominal_value) |
        (spec.counts_vals == 0))
    assert div.livetime is None


@pytest.mark.parametrize('type1, type2, error', [
    ('uncal', 'uncal', TypeError),
    ('uncal', 'asdf', TypeError),
    ('uncal', 'data', TypeError),
    ('uncal', 0, ValueError),
    ('uncal', np.inf, ValueError),
    ('uncal', np.nan, ValueError),
    ('uncal', ufloat(0, 1), ValueError),
    ('uncal', ufloat(np.inf, np.nan), ValueError)])
def test_mul_div_errors(type1, type2, error):
    """Multiplication/division errors."""

    spec, bad_factor = make_spec(type1), make_spec(type2)

    with pytest.raises(error):
        spec * bad_factor

    with pytest.raises(error):
        bad_factor * spec

    with pytest.raises(error):
        spec / bad_factor


# ----------------------------------------------
#         Test Spectrum.calibrate_like
# ----------------------------------------------

def test_calibrate_like(uncal_spec, cal_spec):
    """Test calibrate_like with an uncalibrated spectrum."""

    uncal_spec.calibrate_like(cal_spec)
    assert uncal_spec.is_calibrated
    assert np.all(uncal_spec.bin_edges_kev == cal_spec.bin_edges_kev)


def test_recalibrate_like(cal_spec):
    """Test calibrate_like with an already calibrated spectrum."""

    cal_new = make_spec('cal_new')
    edges1 = cal_spec.bin_edges_kev
    cal_spec.calibrate_like(cal_new)
    assert cal_spec.is_calibrated
    assert np.all(cal_spec.bin_edges_kev == cal_new.bin_edges_kev)
    assert cal_spec.bin_edges_kev[-1] != edges1[-1]


def test_calibrate_like_error(uncal_spec, uncal_spec_2):
    """Test that calibrate_like raises an error if arg is uncalibrated"""

    with pytest.raises(bq.UncalibratedError):
        uncal_spec.calibrate_like(uncal_spec_2)


def test_calibrate_like_copy(uncal_spec, cal_spec):
    """Test that calibrate_like makes a copy of the bin edges"""

    uncal_spec.calibrate_like(cal_spec)
    assert uncal_spec.bin_edges_kev is not cal_spec.bin_edges_kev
    cal_spec.rm_calibration()
    assert uncal_spec.is_calibrated


# ----------------------------------------------
#         Test Spectrum.combine_bins
# ----------------------------------------------

@pytest.mark.parametrize('spectype', ['uncal', 'cal', 'uncal_cps'])
def test_combine_bins(spectype):
    """Test combine_bins with no padding."""

    spec = make_spec(spectype)

    f = 8
    combined = spec.combine_bins(f)

    assert len(combined) == TEST_DATA_LENGTH / f
    if spec._counts is not None:
        assert combined.counts_vals[0] == np.sum(spec.counts_vals[:f])
        assert np.sum(combined.counts_vals) == np.sum(spec.counts_vals)
    else:
        assert combined.cps_vals[0] == np.sum(spec.cps_vals[:f])
        assert np.sum(combined.cps_vals) == np.sum(spec.cps_vals)


@pytest.mark.parametrize('spectype', ['uncal', 'cal', 'uncal_cps'])
def test_combine_bins_padding(spectype):
    """Test combine_bins with padding (an uneven factor)."""

    spec = make_spec(spectype)

    f = 10
    combined = spec.combine_bins(f)
    assert len(combined) == np.ceil(float(TEST_DATA_LENGTH) / f)
    if spec._counts is not None:
        assert combined.counts_vals[0] == np.sum(spec.counts_vals[:f])
        assert np.sum(combined.counts_vals) == np.sum(spec.counts_vals)
    else:
        assert combined.cps_vals[0] == np.sum(spec.cps_vals[:f])
        assert np.sum(combined.cps_vals) == np.sum(spec.cps_vals)


# calibration methods tested in energycal_test.py

# ----------------------------------------------
#         Test Spectrum.downsample
# ----------------------------------------------

@pytest.mark.parametrize('spectype', ['uncal', 'cal'])
@pytest.mark.parametrize('f', [2, 1.5, 999.99])
def test_downsample(spectype, f):
    """Test Spectrum.downsample on uncalibrated and calibrated spectra"""

    spec = make_spec(spectype, lam=1000)
    s1 = np.sum(spec.counts_vals)
    spec2 = spec.downsample(f)
    s2 = np.sum(spec2.counts_vals)
    r = float(s2) / s1
    five_sigma = 5 * np.sqrt(s1 / f) / (s1 / f)

    assert np.isclose(r, 1.0 / f, atol=five_sigma)


def test_no_downsample(cal_spec):
    """Test that downsample(1) doesn't do anything"""

    s1 = np.sum(cal_spec.counts_vals)
    spec2 = cal_spec.downsample(1.0)
    s2 = np.sum(spec2.counts_vals)
    assert s1 == s2


def test_zero_downsample(cal_spec):
    """Test that downsample(very large number) gives 0"""

    spec2 = cal_spec.downsample(10**10)
    s2 = np.sum(spec2.counts_vals)
    assert s2 == 0


def test_downsample_handle_livetime(cal_spec):
    """Test handle_livetime behavior"""

    f = 2
    test_livetime = 300.0
    cal_spec.livetime = test_livetime

    spec2 = cal_spec.downsample(f)
    assert spec2.livetime is None

    spec3 = cal_spec.downsample(f, handle_livetime='preserve')
    assert spec3.livetime == cal_spec.livetime

    spec4 = cal_spec.downsample(f, handle_livetime='reduce')
    assert spec4.livetime == cal_spec.livetime / f


def test_downsample_error(cal_spec):
    """Test that downsample(<1) raises ValueError"""

    with pytest.raises(ValueError):
        cal_spec.downsample(0.5)


def test_downsample_cps_error(uncal_spec_cps):
    """Test that downsampling a CPS spectrum gives a SpectrumError"""

    with pytest.raises(bq.SpectrumError):
        uncal_spec_cps.downsample(12)


def test_downsample_handle_livetime_error(uncal_spec):
    """Test bad value of handle_livetime"""

    with pytest.raises(ValueError):
        uncal_spec.downsample(5, handle_livetime='asdf')


# ----------------------------------------------
#         Test Spectrum.__len__
# ----------------------------------------------


@pytest.fixture(params=[1, 8, 256, 16384])
def length(request):
    return request.param


def test_len(length):
    """Test len(spectrum)"""

    floatdata = np.random.poisson(lam=TEST_COUNTS, size=length)
    spec = bq.Spectrum(floatdata.astype(int))
    assert len(spec) == length


def test_len_cps(length, livetime):
    """Test len(spectrum) for a CPS-based spectrum"""

    floatdata = np.random.poisson(lam=TEST_COUNTS, size=length)
    spec = bq.Spectrum(cps=floatdata / livetime)
    assert len(spec) == length


# ----------------------------------------------
#         Test Spectrum.copy
# ----------------------------------------------

def test_copy_uncal(uncal_spec):
    """Test copy method on uncal spectrum"""

    uncal2 = uncal_spec.copy()
    assert np.all(uncal2.counts_vals == uncal_spec.counts_vals)
    assert np.all(uncal2.counts_uncs == uncal_spec.counts_uncs)
    assert uncal2 is not uncal_spec
    assert uncal2.counts is not uncal_spec.counts
    assert uncal2.counts[0] is not uncal_spec.counts[0]


def test_copy_cal(cal_spec):
    """Test copy method on cal spectrum"""

    cal2 = cal_spec.copy()
    assert np.all(cal2.counts_vals == cal_spec.counts_vals)
    assert np.all(cal2.counts_uncs == cal_spec.counts_uncs)
    assert np.all(cal2.bin_edges_kev == cal_spec.bin_edges_kev)
    assert cal2 is not cal_spec
    assert cal2.counts is not cal_spec.counts
    assert cal2.counts[0] is not cal_spec.counts[0]
    assert cal2.bin_edges_kev is not cal_spec.bin_edges_kev


# ----------------------------------------------
#         Test Spectrum.rebin
# ----------------------------------------------

@pytest.fixture(
    params=[
        TEST_EDGES_KEV.copy(),
        TEST_EDGES_KEV.copy()[1:-2],
        np.linspace(
            TEST_EDGES_KEV.min(),
            TEST_EDGES_KEV.max(),
            len(TEST_EDGES_KEV) + 10)],
    ids=[
        "same edges",
        "subset of edges",
        "same bounds more bins"])
def rebin_new_edges(request):
    return request.param.astype(np.float)


@pytest.fixture(
    params=[
        'interpolation',
        'listmode'],
    ids=[
        "interpolation method",
        "listmode method"])
def rebin_method(request):
    return request.param


@pytest.fixture(
    params=[
        ('uncal', 300),
        ('uncal', None),
        ('cal_cps', None)],
    ids=[
        "uncalibrated spectrum with livetime",
        "uncalibrated spectrum without livetime",
        "calibrated spectrum with cps"])
def rebin_spectrum_failure(request):
    return make_spec(request.param[0], lt=request.param[1])


def test_spectrum_rebin_failure(rebin_spectrum_failure, rebin_new_edges,
                                rebin_method):
    with pytest.raises(bq.SpectrumError):
        rebin_spectrum_failure.rebin(rebin_new_edges, method=rebin_method,
                                     zero_pad_warnings=False)


@pytest.fixture(
    params=[
        ('cal', 300),
        ('cal', None),
        ('cal_cps', 300)],
    ids=[
        "calibrated spectrum with livetime",
        "calibrated spectrum without livetime",
        "calibrated spectrum with cps and livetime"])
def rebin_spectrum_success(request):
    return make_spec(request.param[0], lt=request.param[1])


def test_spectrum_rebin_success(rebin_spectrum_success, rebin_new_edges,
                                rebin_method):
    kwargs = dict(out_edges=rebin_new_edges, method=rebin_method,
                  zero_pad_warnings=False)
    if ((rebin_spectrum_success._counts is None) and
            (rebin_method == 'listmode')):
        with pytest.warns(bq.SpectrumWarning):
            spec = rebin_spectrum_success.rebin(**kwargs)
    else:
        spec = rebin_spectrum_success.rebin(**kwargs)
    assert np.isclose(rebin_spectrum_success.counts_vals.sum(),
                      spec.counts_vals.sum())
    if rebin_spectrum_success.livetime is None:
        assert spec.livetime is None
    else:
        assert np.isclose(rebin_spectrum_success.livetime, spec.livetime)


# ----------------------------------------------
#         Test Spectrum.rebin_like
# ----------------------------------------------


def test_spectrum_rebin_like():
    spec1 = make_spec('cal')
    spec2 = make_spec('cal_new')
    assert np.any(~np.isclose(spec1.bin_edges_kev, spec2.bin_edges_kev))
    spec2_rebin = spec2.rebin_like(spec1)
    assert np.all(np.isclose(spec1.bin_edges_kev, spec2_rebin.bin_edges_kev))
    assert np.isclose(spec2.counts_vals.sum(), spec2_rebin.counts_vals.sum())
