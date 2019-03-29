from __future__ import division, print_function, absolute_import

import numpy as np


def _image_tv(x, axis=0, n_points=3):
    """ Computes total variation (TV) of matrix x along axis a in two
    directions.

    Parameters
    ----------
    x : 2D ndarray
        matrix x
    axis : int (0 or 1)
        Axis along which TV will be calculated. Default a is set to 0.
    n_points : int
        Number of points to be included in TV calculation.

    Returns
    -------
    ptv : 2D ndarray
        Total variation calculated from the right neighbors of each point
    ntv : 2D ndarray
        Total variation calculated from the left neighbors of each point

    Note
    ----
    This function was created to deal with gibbs artefacts of MR images.
    Assuming that MR images are reconstructed from estimates of their Fourier
    expansion coefficients, during TV calculation matrix x can taken as and
    periodic signal. In this way ntv values on the image left boundary is
    computed using the time series values on the right boundary and ptv values
    are computed using the time series values on the left boundary.
    """
    if axis:
        xs = x.copy()
    else:
        xs = x.T.copy()

    # Add copies of the data so that data extreme points are also analysed
    xs = np.concatenate((xs[:, (-n_points-1):], xs, xs[:, 0:(n_points+1)]),
                        axis=1)

    ptv = np.absolute(xs[:, (n_points+1):(-n_points-1)] -
                      xs[:, (n_points+2):(-n_points)])
    ntv = np.absolute(xs[:, (n_points+1):(-n_points-1)] -
                      xs[:, (n_points):(-n_points-2)])
    for n in range(1, n_points):
        ptv = ptv + np.absolute(xs[:, (n_points+1+n):(-n_points-1+n)] -
                                xs[:, (n_points+2+n):(-n_points+n)])
        ntv = ntv + np.absolute(xs[:, (n_points+1-n):(-n_points-1-n)] -
                                xs[:, (n_points-n):(-n_points-2-n)])

    if axis:
        return ptv, ntv
    else:
        return ptv.T, ntv.T


def _gibbs_removal_1d(x, axis=0, n_points=3):
    """ Decreases gibbs ringing along an axis 'a' using fourier sub-shifts.

    Parameters
    ----------
    x : 2D ndarray
        Matrix x.
    axis : int (0 or 1)
        Axis along which gibbs oscillations will be reduced. Default a is set
        to 0 (i.e. gibbs are reduce along axis y).
    n_points : int, optional
        Number of neighbour points to access local TV (see note). Default is
        set to 3.

    Returns
    -------
    xc : 2D ndarray
        Matrix with gibbs oscillations reduced along an axis 'a'.

    Note
    ----
    This function decreases the effects of gibbs oscillations based on the
    analysis of local total variation (TV). Although artefact correction is
    done based on two adjanced points for each voxel, total variation should be
    accessed in a larger range of neigbors. If you want to adjust the number
    of the neigbors to be considered in TV calculation please change
    parameter nn.
    """
    ssamp = np.linspace(0.02, 0.9, num=45)

    if axis:
        xs = x.copy()
    else:
        xs = x.T.copy()

    # TV for shift zero (baseline)
    tvr, tvl = _image_tv(xs, axis=1, n_points=n_points)
    tvp = np.minimum(tvr, tvl)
    tvn = tvp.copy()

    # Find optimal shift for gibbs removal
    isp = xs.copy()
    isn = xs.copy()
    sp = np.zeros(xs.shape)
    sn = np.zeros(xs.shape)
    N = xs.shape[1]
    c = np.fft.fftshift(np.fft.fft2(xs))
    k = np.linspace(-N/2, N/2-1, num=N)
    k = (2.0j * np.pi * k) / N
    for s in ssamp:
        # Access positive shift for given s
        img_p = abs(np.fft.ifft2(np.fft.fftshift(c * np.exp(k*s))))
        tvsr, tvsl = _image_tv(img_p, axis=1, n_points=n_points)
        tvs_p = np.minimum(tvsr, tvsl)

        # Access negative shift for given s
        img_n = abs(np.fft.ifft2(np.fft.fftshift(c * np.exp(-k*s))))
        tvsr, tvsl = _image_tv(img_n, axis=1, n_points=n_points)
        tvs_n = np.minimum(tvsr, tvsl)

        # Update positive shift params
        isp[tvp > tvs_p] = img_p[tvp > tvs_p]
        sp[tvp > tvs_p] = s
        tvp[tvp > tvs_p] = tvs_p[tvp > tvs_p]

        # Update negative shift params
        isn[tvn > tvs_n] = img_n[tvn > tvs_n]
        sn[tvn > tvs_n] = s
        tvn[tvn > tvs_n] = tvs_n[tvn > tvs_n]

    # check non-zero sub-voxel shifts
    idx = np.nonzero(sp + sn)

    # use positive and negative optimal sub-voxel shifts to interpolate to
    # original grid points
    xs[idx] = (isp[idx] - isn[idx])/(sp[idx] + sn[idx])*sn[idx] + isn[idx]

    if axis:
        return xs
    else:
        return xs.T


def _weights(shape):
    """ Computes the weights necessary to combine two images processed by
    the 1D gibbs removal procedure along two different axis [1]_.

    Parameters
    ----------
    shape : tuple
        shape of the image

    Returns
    -------
    G0 : 2D ndarray
        Weights for the image corrected along axis 0.
    G1 : 2D ndarray
        Weights for the image corrected along axis 1.

    References
    ----------
    .. [1] Kellner E, Dhital B, Kiselev VG, Reisert M. Gibbs-ringing artifact
           removal based on local subvoxel-shifts. Magn Reson Med. 2016
           doi: 10.1002/mrm.26054.
    """
    G0 = np.zeros(shape)
    G1 = np.zeros(shape)
    k = np.linspace(-np.pi, np.pi, num=shape[0])

    # Middle points
    K1, K0 = np.meshgrid(k[1:-1], k[1:-1])
    cosk0 = 1.0 + np.cos(K0)
    cosk1 = 1.0 + np.cos(K1)
    G1[1:-1, 1:-1] = cosk0 / (cosk0+cosk1)
    G0[1:-1, 1:-1] = cosk1 / (cosk0+cosk1)

    # Boundaries
    G1[1:-1, 0] = G1[1:-1, -1] = 1
    G1[0, 0] = G1[-1, -1] = G1[0, -1] = G1[-1, 0] = 1/2
    G0[0, 1:-1] = G0[-1, 1:-1] = 1
    G0[0, 0] = G0[-1, -1] = G0[0, -1] = G0[-1, 0] = 1/2

    return G0, G1


def _gibbs_removal_2d(image, n_points=3, G0=None, G1=None):
    """ Decreases gibbs ringing of a 2D image.

    Parameters
    ----------
    image : 2D ndarray
        Matrix cotaining the 2D image.
    n_points : int, optional
        Number of neighbour points to access local TV (see note). Default is
        set to 3.
    G0 : 2D ndarray, optional.
        Weights for the image corrected along axis 1. If not given, the
        function estimates them using function :func:`_weights`
    G1 : 2D ndarray
        Weights for the image corrected along axis 1. If not given, the
        function estimates them using function :func:`_weights`

    Returns
    -------
    imagec : 2D ndarray
        Matrix with gibbs oscillations reduced along axis a.
    tv : 2D ndarray
        Global TV which show variation not removed by the algorithm (edges,
        anatomical variation, non-oscillatory component of gibbs artefact
        normally present in image background, etc.)

    Note
    ----
    This function decreases the effects of gibbs oscillations based on the
    analysis of local total variation (TV) along the two axis of the image.
    Although artefact correction is done based on each point primary adjanced
    neighbors, total variation should be accessed in a larger range of
    neigbors. If you want to adjust the number of the neigbors to be
    considered in TV calculation please change parameter nn.

    References
    ----------
    Please cite the following articles
    .. [1] Neto Henriques, R., 2018. Advanced Methods for Diffusion MRI Data
           Analysis and their Application to the Healthy Ageing Brain
           (Doctoral thesis). https://doi.org/10.17863/CAM.29356
    .. [2] Kellner E, Dhital B, Kiselev VG, Reisert M. Gibbs-ringing artifact
           removal based on local subvoxel-shifts. Magn Reson Med. 2016
           doi: 10.1002/mrm.26054.
    """
    if np.any(G0) is None or np.any(G1) is None:
        G0, G1 = _weights(image.shape)

    img_c1 = _gibbs_removal_1d(image, axis=1, n_points=n_points)
    img_c0 = _gibbs_removal_1d(image, axis=0, n_points=n_points)

    C1 = np.fft.fft2(img_c1)
    C0 = np.fft.fft2(img_c0)
    imagec = abs(np.fft.ifft2(np.fft.fftshift(C1)*G1 + np.fft.fftshift(C0)*G0))

    return imagec


def gibbs_removal(vol, slice_axis=2, n_points=3):
    """ Suppresses gibbs ringing artefacts of images volumes.

    Parameters
    ----------
    vol : ndarray ([X, Y]), ([X, Y, Z]) or ([X, Y, Z, g])
        Matrix containing one volume (3D) or multiple (4D) volumes of images.
    slice_axis : int (0, 1, or 2)
        Data axis corresponding to the number of acquired slices. Default is
        set to the third axis
    n_points : int, optional
        Number of neighbour points to access local TV (see note). Default is
        set to 3.

    Returns
    -------
    vol : ndarray ([X, Y]), ([X, Y, Z]) or ([X, Y, Z, g])
        Matrix containing one volume (3D) or multiple (4D) volumes of corrected
        images.

    Notes
    -----
    For 4D matrix last element should always correspond to the number of
    diffusion gradient directions.

    References
    ----------
    Please cite the following articles
    .. [1] Neto Henriques, R., 2018. Advanced Methods for Diffusion MRI Data
           Analysis and their Application to the Healthy Ageing Brain
           (Doctoral thesis). https://doi.org/10.17863/CAM.29356
    .. [2] Kellner E, Dhital B, Kiselev VG, Reisert M. Gibbs-ringing artifact
           removal based on local subvoxel-shifts. Magn Reson Med. 2016
           doi: 10.1002/mrm.26054.
    """
    nd = vol.ndim

    # check the axis corresponding to different slices
    # 1) This axis cannot be larger than 2
    if slice_axis > 2:
        raise ValueError("Different slices have to be organized along" +
                         "one of the 3 first matrix dimensions")

    # 2) If this is not 2, swap axis so that different slices are ordered
    # along axis 2. Note that swapping is not required if data is already a
    # single image
    elif slice_axis < 2 and nd > 2:
        vol = np.swapaxes(vol, slice_axis, 2)

    # check matrix dimension
    if nd == 4:
        inishap = vol.shape
        vol = vol.reshape((inishap[0], inishap[1], inishap[2]*inishap[3]))
    elif nd > 4:
        raise ValueError("Data have to be a 4D, 3D or 2D matrix")
    elif nd < 2:
        raise ValueError("Data is not an image")

    # Produce weigthing functions for 2D gibbs removal
    shap = vol.shape
    G0, G1 = _weights(shap[:2])

    # Run gibbs removal of 2D images
    if nd == 2:
        vol = _gibbs_removal_2d(vol, n_points=n_points, G0=G0, G1=G1)
    else:
        for vi in range(shap[2]):
            vol[:, :, vi] = _gibbs_removal_2d(vol[:, :, vi], n_points=n_points,
                                              G0=G0, G1=G1)

    # Reshape data to original format
    if nd == 4:
        vol = vol.reshape(inishap)
    if slice_axis < 2:
        vol = np.swapaxes(vol, slice_axis, 2)

    return vol
