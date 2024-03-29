"""
Implementation of a set of filters.

Implemented filters:
- Gabor filters
- Gaussian filters
- Laplacian of Gaussians filters
- Schmid filters

All the above filters should better be applied with symmetric padding when
convolved with target images.

Yujia Li, 08/2013
"""

import numpy as np
from skimage.filters import gabor_kernel
from skimage import color
import scipy.signal as sg
import matplotlib.pyplot as plt

def make_gabor_filters(n_freq, n_orient, base_freq=1,
        freq_factor=np.sqrt(2), offset=0):
    """
    Generate Gabor filter bank.

    n_freq: number of different frequencies
    n_orient: number of different orientations
    base_freq: base frequency
    freq_factor: the multiplicative factor used to derive frequencies, the
        frequencies used will be base_freq, base_freq/freq_factor,
        base_freq/freq_factor^2, ...
    offset: phase offset, almost always set to 0

    Return: kernels, a list of kernel matrices. Different frequencies
        corresponds to different scales. So the kernel matrices will be of
        different sizes. The length of this list will be n_freq x n_orient x 2
    """
    kernels = []
    n_kernels = n_freq * n_orient * 2

    for i_freq in range(n_freq):
        freq = 1.0 * base_freq / freq_factor**i_freq
        for i_orient in range(n_orient):
            theta = np.pi * i_orient / n_orient

            kernel = gabor_kernel(freq, theta, offset=offset)
            ki = kernel.imag - kernel.imag.sum() / kernel.imag.size
            kr = kernel.real - kernel.real.sum() / kernel.real.size
            kernels.append(ki / np.abs(ki).max())
            kernels.append(kr / np.abs(kr).max())

    return kernels

def show_gabor_filters(kernels, n_freq, n_orient):
    """
    Display the generated Gabor filter bank in a grid of n_freq x n_orient sub
    plots.
    """
    show_filters(kernels, n_freq, n_orient*2)

def show_filters(kernels, n_rows, n_cols):
    """
    Display the generated filter bank on a grid of n_rows x n_cols sub plots.
    """
    plt.figure()
    for i_row in range(n_rows):
        for i_col in range(n_cols):
            idx = i_row * n_cols + i_col
            plt.subplot(n_rows, n_cols, idx+1)
            plt.imshow(kernels[idx], cmap='gray', interpolation='nearest')
    plt.show()

def make_gaussian_filters(n_sigma, base_sigma=1, sigma_factor=np.sqrt(2)):
    """
    Generate rotation invariant Gaussian filters on different scales.

    The standard deviation of the Gaussian sigma=base_sigma * sigma_factor**k
    for the kth filter.

    Return: a list of n_sigma Gaussian filters.
    """
    kernels = []
    for i in range(n_sigma):
        sigma = base_sigma * sigma_factor**i
        xmax = int(2*sigma)

        x, y = np.meshgrid(np.arange(-xmax, xmax+1, 1), np.arange(xmax, -xmax-1,-1))

        k = 1.0 / (2 * np.pi * sigma**2) * np.exp(-(x**2 + y**2)/(2*sigma**2))
        k = k / k.sum()

        kernels.append(k)

    return kernels

def make_log_filters(n_sigma, base_sigma=1, sigma_factor=np.sqrt(2)):
    """
    Generate Laplacian of Gaussian filters on different scales.

    Sigma: the standard deviation of the Gaussian.

    n_sigma: number of scales to use
    base_sigma, sigma_factor: sigma of the kth filter will be sigma * sigma_factor**k

    Return a list of n_sigma LoG filters.
    """
    kernels = []
    for i in range(n_sigma):
        sigma = base_sigma * sigma_factor**i
        xmax = int(3*sigma)

        x, y = np.meshgrid(np.arange(-xmax, xmax+1, 1), np.arange(xmax, -xmax-1,-1))

        a = (x**2 + y**2)/(2*sigma**2)
        k = -(1 - a) * np.exp(-a) / (np.pi * sigma**4)
        k = k - k.sum() / k.size

        kernels.append(k / np.abs(k).max())

    return kernels

def make_schmid_filters():
    """
    Generate Schmid filter bank.

    Take a look at http://www.robots.ox.ac.uk/~vgg/research/texclass/filters.html
    for more details.

    Return a list of 13 filters on different scales.
    """
    sigma_tau = [(2,1), (4,1), (4,2), (6,1), (6,2), (6,3), (8,1),
            (8,2), (8,3), (10,1), (10,2), (10,3), (10,4)]

    kernels = []
    for sigma, tau in sigma_tau:
        xmax = int(sigma*2)
        x, y = np.meshgrid(np.arange(-xmax, xmax+1, 1), np.arange(xmax, -xmax-1,-1))

        k = np.cos(np.pi * tau * np.sqrt(x**2 + y**2) / sigma) * np.exp(-(x**2 + y**2) / (2 * sigma**2))
        k = k - k.sum() / k.size

        kernels.append(k / np.abs(k).max())

    return kernels

def apply_filter_bank(im, filters, window_size=1):
    """
    (im, filters, window_size=1) -> resp

    Apply a filter bank to a given image and collect filter responses.

    filters: a list of filter kernels, can be of different sizes
    window_size: size of a local window patch which will be extracted as
        features, should be an odd integer.

    resp will be a matrix with size Height x Width x (#filters + 6)
    6=3(RGB)+3(Lab) is the number of color features.
    """
    # window size should be odd
    assert window_size % 2 == 1

    dim_rgb = 3*window_size*window_size
    dim_lab = 3
    dim_loc = 2
    dim_filters = len(filters)

    dim_total = dim_rgb + dim_lab + dim_loc + dim_filters

    sx, sy = im.shape[:2]
    n_pix = sx * sy
    resp = np.zeros((n_pix, dim_total), dtype=np.single)
    dim_id = 0

    if len(im.shape) < 3 or im.shape[2] == 1:
        newim = np.zeros((im.shape[0], im.shape[1], 3), dtype=np.single)
        newim[:,:,0] = im
        newim[:,:,1] = im
        newim[:,:,2] = im
        im = newim

    # RGB colors
    if window_size == 1:
        resp[:,dim_id:dim_id+dim_rgb] = 1.0 * im.reshape(n_pix, 3) / 255
        dim_id += dim_rgb
    else:
        half_size = window_size / 2
        sx, sy, _ = im.shape

        # pad image
        im_temp = np.empty((sx + window_size - 1, sy + window_size - 1, 3), dtype=im.dtype)
        im_temp[half_size:half_size + sx, half_size:half_size + sy,:] = im
        # 4 corners
        im_temp[:half_size, :half_size,:] = im[0,0,:]
        im_temp[:half_size, -half_size:,:] = im[0,-1,:]
        im_temp[-half_size:, :half_size,:] = im[-1,0,:]
        im_temp[-half_size:, -half_size:,:] = im[-1,-1,:]
        # 4 edges
        im_temp[half_size:-half_size, :half_size, :] = im[:, half_size-1::-1, :]
        im_temp[:half_size, half_size:-half_size, :] = im[half_size-1::-1, :, :]
        im_temp[half_size:-half_size, -half_size:, :] = im[:, :-half_size-1:-1, :]
        im_temp[-half_size:, half_size:-half_size, :] = im[:-half_size-1:-1, :, :]

        for ix in range(window_size):
            for iy in range(window_size):
                resp[:,dim_id:dim_id+3] = 1.0 * im_temp[ix:ix+sx, iy:iy+sy].reshape(n_pix, 3) / 255
                dim_id += 3

    # CIE Lab colors
    resp[:,dim_id:dim_id+dim_lab] = 1.0 * color.rgb2lab(im).reshape(n_pix, 3) / 255
    dim_id += dim_lab

    # Normalized location feature
    loc_x = np.tile(np.arange(sx)[:,np.newaxis], [1,sy]).astype(np.single)
    if sx > 1:
        loc_x /= (sx - 1)
    loc_y = np.tile(np.arange(sy), [sx,1]).astype(np.single)
    if sy > 1:
        loc_y /= (sy - 1)
    resp[:,dim_id] = loc_x.flatten()
    resp[:,dim_id+1] = loc_y.flatten()
    dim_id += dim_loc

    # other filters, apply to gray image only
    gray = im.mean(axis=2) / 255
    for i in range(dim_filters):
        resp[:,dim_id+i] = sg.convolve2d(gray, filters[i], mode='same', boundary='symm').flatten()

    return resp

def filter_response(imlist, window_size=1, imsz=None, verbose=1):
    """
    Apply a bank of filters to a set of images.

    imlist can be a list of images of size Height x Width x 3 or a matrix of
    size N x (3*H*W). If imlist uses a matrix representation, then imsz should
    be set to (H,W) otherwise imsz should be None

    window_size: size of a window to extract color features from. The whole
        window will be used as a part of the feature vector.

    verbose: if set to a number greater than 0, it will progress information
        will be printed.

    Return a list of filter responses. Each element in the list is a matrix of
    size (H*W)*D where D is the dimensionality of the feature vector.
    """
    kernels = []

    # Gabor filters
    n_freq = 4
    n_orient = 6
    kernels.extend(make_gabor_filters(n_freq, n_orient))

    # S filters
    kernels.extend(make_schmid_filters())

    # Gaussian filters
    kernels.extend(make_gaussian_filters(4))

    # LoG filters
    kernels.extend(make_log_filters(4))

    resp = []

    for i in range(len(imlist)):
        if imsz == None:
            resp.append(apply_filter_bank(imlist[i], kernels, window_size))
        else:
            resp.append(apply_filter_bank(imlist[i].reshape(imsz[0], imsz[1], 3), kernels, window_size))

        if verbose > 0:
            print('Processed %d images...' % (i+1))

    return resp

def extract_color_features(imlist, window_size=1, imsz=None, verbose=1):
    """
    Extract color feature for a list of images.

    See filter_response for details about the input and output formats.
    """
    kernels = []
    resp = []

    for i in range(len(imlist)):
        if imsz == None:
            resp.append(apply_filter_bank(imlist[i], kernels, window_size))
        else:
            resp.append(apply_filter_bank(imlist[i].reshape(imsz[0], imsz[1], 3), kernels, window_size))

        if verbose > 0:
            print('Processed %d images...' % (i+1))

    return resp
