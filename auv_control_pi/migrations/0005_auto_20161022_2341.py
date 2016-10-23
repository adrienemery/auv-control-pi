# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2016-10-22 23:41
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auv_control_pi', '0004_configuration_auv_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuration',
            name='crossbar_realm',
            field=models.CharField(default='realm1', max_length=255),
        ),
        migrations.AddField(
            model_name='configuration',
            name='crossbar_url',
            field=models.URLField(default='ws://localhost:8080/ws', max_length=255),
        ),
    ]
