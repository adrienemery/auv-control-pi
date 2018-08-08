from ..ahrs import AHRS


def test_ahrs():
    ahrs = AHRS()
    accel = [-0.010, 0.268, 9.81]
    gyro = [-0.042, 0.019, 0.015]
    mag = [-16.566, 42.852, -50.302]
    ahrs.update(accel, gyro, mag)
    # TODO assert something

