from django.db import models
from solo.models import SingletonModel


class Configuration(SingletonModel):

    auv_id = models.UUIDField(blank=True, null=True)
    auth_token = models.CharField(max_length=1024, blank=True)
    update_frequency = models.DecimalField(blank=True, null=True,
                                           max_digits=5, decimal_places=3)
    left_motor_channel = models.IntegerField(default=0)
    right_motor_channel = models.IntegerField(default=1)
    trim = models.IntegerField(default=0)
    name = models.CharField(max_length=255, blank=True)
    address = models.CharField(max_length=255, blank=True)
    crossbar_url = models.CharField(max_length=255, default='ws://localhost:8000/ws')
    crossbar_realm = models.CharField(max_length=255, default='realm1')

    # auto pilot config vars
    kP = models.FloatField(blank=True, default=1)
    kI = models.FloatField(blank=True, default=0)
    kD = models.FloatField(blank=True, default=0)
    target_waypoint_distance = models.FloatField(blank=True, default=60)
    pid_error_debounce = models.FloatField(blank=True, default=5)

    magbias_x = models.FloatField(blank=True, default=0)
    magbias_y = models.FloatField(blank=True, default=0)
    magbias_z = models.FloatField(blank=True, default=0)
    declination = models.FloatField(blank=True, default=0)
    board_offset = models.FloatField(blank=True, default=0)

    def __str__(self):
        return 'AUV Configuration'

    class Meta:
        verbose_name = "AUV Configuration"


class AUVLog(models.Model):

    timestamp = models.DateTimeField(auto_now_add=True)
    left_motor_speed = models.IntegerField(blank=True, null=True)
    left_motor_duty_cycle = models.IntegerField(blank=True, null=True)
    right_motor_speed = models.IntegerField(blank=True, null=True)
    right_motor_duty_cycle = models.IntegerField(blank=True, null=True)
    throttle = models.IntegerField(blank=True, null=True)
    turn_speed = models.IntegerField(blank=True, null=True)


class GPSLog(models.Model):

    timestamp = models.DateTimeField(auto_now_add=True)
    lat = models.DecimalField(max_digits=9, decimal_places=6)
    lon = models.DecimalField(max_digits=9, decimal_places=6)
    height_sea = models.DecimalField(max_digits=9, decimal_places=6)
    height_ellipsoid = models.DecimalField(max_digits=9, decimal_places=6)
    horizontal_accruacy = models.DecimalField(max_digits=9, decimal_places=6)
    vertiacl_accruracy = models.DecimalField(max_digits=9, decimal_places=6)

