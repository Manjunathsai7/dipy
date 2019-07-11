
import numpy as np
import numpy.testing as npt

from scipy.ndimage.interpolation import map_coordinates
from dipy.core.interpolation import (trilinear_interpolate4d,
                                     interpolate_scalar_2d,
                                     interpolate_scalar_3d,
                                     interpolate_vector_2d,
                                     interpolate_vector_3d,
                                     interpolate_scalar_nn_2d,
                                     interpolate_scalar_nn_3d)
from dipy.align import floating


def test_trilinear_interpolate():
    """This tests that the trilinear interpolation returns the correct values.
    """
    a, b, c = np.random.random(3)

    def linear_function(x, y, z):
        return a * x + b * y + c * z

    N = 6
    x, y, z = np.mgrid[:N, :N, :N]
    data = np.empty((N, N, N, 2))
    data[..., 0] = linear_function(x, y, z)
    data[..., 1] = 99.

    # Use a point not near the edges
    point = np.array([2.1, 4.8, 3.3])
    out = trilinear_interpolate4d(data, point)
    expected = [linear_function(*point), 99.]
    npt.assert_array_almost_equal(out, expected)

    # Pass in out ourselves
    out[:] = -1
    trilinear_interpolate4d(data, point, out)
    npt.assert_array_almost_equal(out, expected)

    # use a point close to an edge
    point = np.array([-.1, -.1, -.1])
    expected = [0., 99.]
    out = trilinear_interpolate4d(data, point)
    npt.assert_array_almost_equal(out, expected)

    # different edge
    point = np.array([2.4, 5.4, 3.3])
    # On the edge 5.4 get treated as the max y value, 5.
    expected = [linear_function(point[0], 5., point[2]), 99.]
    out = trilinear_interpolate4d(data, point)
    npt.assert_array_almost_equal(out, expected)

    # Test index errors
    point = np.array([2.4, 5.5, 3.3])
    npt.assert_raises(IndexError, trilinear_interpolate4d, data, point)
    point = np.array([2.4, -1., 3.3])
    npt.assert_raises(IndexError, trilinear_interpolate4d, data, point)


def test_interpolate_scalar_2d():
    np.random.seed(5324989)
    sz = 64
    target_shape = (sz, sz)
    image = np.empty(target_shape, dtype=floating)
    image[...] = np.random.randint(0, 10, np.size(image)).reshape(target_shape)

    extended_image = np.zeros((sz + 2, sz + 2), dtype=floating)
    extended_image[1:sz + 1, 1:sz + 1] = image[...]

    # Select some coordinates inside the image to interpolate at
    nsamples = 200
    locations =\
        np.random.ranf(2 * nsamples).reshape((nsamples, 2)) * (sz + 2) - 1.0
    extended_locations = locations + 1.0  # shift coordinates one voxel

    # Call the implementation under test
    interp, inside = interpolate_scalar_2d(image, locations)

    # Call the reference implementation
    expected = map_coordinates(extended_image, extended_locations.transpose(),
                               order=1)

    npt.assert_array_almost_equal(expected, interp)

    # Test interpolation stability along the boundary
    epsilon = 5e-8
    for k in range(2):
        for offset in [0, sz - 1]:
            delta = ((np.random.ranf(nsamples) * 2) - 1) * epsilon
            locations[:, k] = delta + offset
            locations[:, (k + 1) % 2] = np.random.ranf(nsamples) * (sz - 1)
            interp, inside = interpolate_scalar_2d(image, locations)

            locations[:, k] = offset
            expected = map_coordinates(image, locations.transpose(), order=1)
            npt.assert_array_almost_equal(expected, interp)
            if offset == 0:
                expected_flag = np.array(delta >= 0, dtype=np.int32)
            else:
                expected_flag = np.array(delta <= 0, dtype=np.int32)
            npt.assert_array_almost_equal(expected_flag, inside)


def test_interpolate_scalar_nn_2d():
    np.random.seed(1924781)
    sz = 64
    target_shape = (sz, sz)
    image = np.empty(target_shape, dtype=floating)
    image[...] = np.random.randint(0, 10, np.size(image)).reshape(target_shape)
    # Select some coordinates to interpolate at
    nsamples = 200
    locations =\
        np.random.ranf(2 * nsamples).reshape((nsamples, 2)) * (sz + 2) - 1.0

    # Call the implementation under test
    interp, inside = interpolate_scalar_nn_2d(image, locations)

    # Call the reference implementation
    expected = map_coordinates(image, locations.transpose(), order=0)

    npt.assert_array_almost_equal(expected, interp)

    # Test the 'inside' flag
    for i in range(nsamples):
        if (locations[i, 0] < 0 or locations[i, 0] > (sz - 1)) or\
           (locations[i, 1] < 0 or locations[i, 1] > (sz - 1)):
            npt.assert_equal(inside[i], 0)
        else:
            npt.assert_equal(inside[i], 1)


def test_interpolate_scalar_nn_3d():
    np.random.seed(3121121)
    sz = 64
    target_shape = (sz, sz, sz)
    image = np.empty(target_shape, dtype=floating)
    image[...] = np.random.randint(0, 10, np.size(image)).reshape(target_shape)
    # Select some coordinates to interpolate at
    nsamples = 200
    locations =\
        np.random.ranf(3 * nsamples).reshape((nsamples, 3)) * (sz + 2) - 1.0

    # Call the implementation under test
    interp, inside = interpolate_scalar_nn_3d(image, locations)

    # Call the reference implementation
    expected = map_coordinates(image, locations.transpose(), order=0)

    npt.assert_array_almost_equal(expected, interp)

    # Test the 'inside' flag
    for i in range(nsamples):
        expected_inside = 1
        for axis in range(3):
            if (locations[i, axis] < 0 or locations[i, axis] > (sz - 1)):
                expected_inside = 0
                break
        npt.assert_equal(inside[i], expected_inside)


def test_interpolate_scalar_3d():
    np.random.seed(9216326)
    sz = 64
    target_shape = (sz, sz, sz)
    image = np.empty(target_shape, dtype=floating)
    image[...] = np.random.randint(0, 10, np.size(image)).reshape(target_shape)

    extended_image = np.zeros((sz + 2, sz + 2, sz + 2), dtype=floating)
    extended_image[1:sz + 1, 1:sz + 1, 1:sz + 1] = image[...]

    # Select some coordinates inside the image to interpolate at
    nsamples = 800
    locations =\
        np.random.ranf(3 * nsamples).reshape((nsamples, 3)) * (sz + 2) - 1.0
    extended_locations = locations + 1.0  # shift coordinates one voxel

    # Call the implementation under test
    interp, inside = interpolate_scalar_3d(image, locations)

    # Call the reference implementation
    expected = map_coordinates(extended_image, extended_locations.transpose(),
                               order=1)

    npt.assert_array_almost_equal(expected, interp)

    # Test interpolation stability along the boundary
    epsilon = 5e-8
    for k in range(3):
        for offset in [0, sz - 1]:
            delta = ((np.random.ranf(nsamples) * 2) - 1) * epsilon
            locations[:, k] = delta + offset
            locations[:, (k + 1) % 3] = np.random.ranf(nsamples) * (sz - 1)
            locations[:, (k + 2) % 3] = np.random.ranf(nsamples) * (sz - 1)
            interp, inside = interpolate_scalar_3d(image, locations)

            locations[:, k] = offset
            expected = map_coordinates(image, locations.transpose(), order=1)
            npt.assert_array_almost_equal(expected, interp)

            if offset == 0:
                expected_flag = np.array(delta >= 0, dtype=np.int32)
            else:
                expected_flag = np.array(delta <= 0, dtype=np.int32)
            npt.assert_array_almost_equal(expected_flag, inside)


def test_interpolate_vector_3d():
    np.random.seed(7711219)
    sz = 64
    target_shape = (sz, sz, sz)
    field = np.empty(target_shape + (3,), dtype=floating)
    field[...] =\
        np.random.randint(0, 10, np.size(field)).reshape(target_shape + (3,))

    extended_field = np.zeros((sz + 2, sz + 2, sz + 2, 3), dtype=floating)
    extended_field[1:sz + 1, 1:sz + 1, 1:sz + 1] = field
    # Select some coordinates to interpolate at
    nsamples = 800
    locations =\
        np.random.ranf(3 * nsamples).reshape((nsamples, 3)) * (sz + 2) - 1.0
    extended_locations = locations + 1

    # Call the implementation under test
    interp, inside = interpolate_vector_3d(field, locations)

    # Call the reference implementation
    expected = np.zeros_like(interp)
    for i in range(3):
        expected[..., i] = map_coordinates(extended_field[..., i],
                                           extended_locations.transpose(),
                                           order=1)

    npt.assert_array_almost_equal(expected, interp)

    # Test interpolation stability along the boundary
    epsilon = 5e-8
    for k in range(3):
        for offset in [0, sz - 1]:
            delta = ((np.random.ranf(nsamples) * 2) - 1) * epsilon
            locations[:, k] = delta + offset
            locations[:, (k + 1) % 3] = np.random.ranf(nsamples) * (sz - 1)
            locations[:, (k + 2) % 3] = np.random.ranf(nsamples) * (sz - 1)
            interp, inside = interpolate_vector_3d(field, locations)

            locations[:, k] = offset
            for i in range(3):
                expected[..., i] = map_coordinates(field[..., i],
                                                   locations.transpose(),
                                                   order=1)
            npt.assert_array_almost_equal(expected, interp)

            if offset == 0:
                expected_flag = np.array(delta >= 0, dtype=np.int32)
            else:
                expected_flag = np.array(delta <= 0, dtype=np.int32)
            npt.assert_array_almost_equal(expected_flag, inside)


def test_interpolate_vector_2d():
    np.random.seed(1271244)
    sz = 64
    target_shape = (sz, sz)
    field = np.empty(target_shape + (2,), dtype=floating)
    field[...] =\
        np.random.randint(0, 10, np.size(field)).reshape(target_shape + (2,))
    extended_field = np.zeros((sz + 2, sz + 2, 2), dtype=floating)
    extended_field[1:sz + 1, 1:sz + 1] = field
    # Select some coordinates to interpolate at
    nsamples = 200
    locations =\
        np.random.ranf(2 * nsamples).reshape((nsamples, 2)) * (sz + 2) - 1.0
    extended_locations = locations + 1

    # Call the implementation under test
    interp, inside = interpolate_vector_2d(field, locations)

    # Call the reference implementation
    expected = np.zeros_like(interp)
    for i in range(2):
        expected[..., i] = map_coordinates(extended_field[..., i],
                                           extended_locations.transpose(),
                                           order=1)

    npt.assert_array_almost_equal(expected, interp)

    # Test interpolation stability along the boundary
    epsilon = 5e-8
    for k in range(2):
        for offset in [0, sz - 1]:
            delta = ((np.random.ranf(nsamples) * 2) - 1) * epsilon
            locations[:, k] = delta + offset
            locations[:, (k + 1) % 2] = np.random.ranf(nsamples) * (sz - 1)
            interp, inside = interpolate_vector_2d(field, locations)

            locations[:, k] = offset
            for i in range(2):
                expected[..., i] = map_coordinates(field[..., i],
                                                   locations.transpose(),
                                                   order=1)
            npt.assert_array_almost_equal(expected, interp)

            if offset == 0:
                expected_flag = np.array(delta >= 0, dtype=np.int32)
            else:
                expected_flag = np.array(delta <= 0, dtype=np.int32)
            npt.assert_array_almost_equal(expected_flag, inside)


if __name__ == "__main__":
    npt.run_module_suite()
