from django.db import models
from solo.models import SingletonModel


class Configuration(SingletonModel):

    auth_token = models.CharField(max_length=1024, blank=True)
    update_frequency = models.DecimalField(blank=True, null=True,
                                           max_digits=5, decimal_places=3)
    left_motor_channel = models.IntegerField(default=0)
    right_motor_channel = models.IntegerField(default=1)
    name = models.CharField(max_length=255, blank=True)
    address = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return 'AUV Configuration'

    class Meta:
        verbose_name = "AUV Configuration"



