# Generated by Django 2.1 on 2018-11-01 01:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auv_control_pi', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AUVLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('left_motor_speed', models.IntegerField(blank=True, null=True)),
                ('left_motor_duty_cycle', models.IntegerField(blank=True, null=True)),
                ('right_motor_speed', models.IntegerField(blank=True, null=True)),
                ('right_motor_duty_cycle', models.IntegerField(blank=True, null=True)),
                ('throttle', models.IntegerField(blank=True, null=True)),
                ('turn_speed', models.IntegerField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='GPSLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('lat', models.DecimalField(decimal_places=6, max_digits=9)),
                ('lon', models.DecimalField(decimal_places=6, max_digits=9)),
                ('height_sea', models.DecimalField(decimal_places=6, max_digits=9)),
                ('height_ellipsoid', models.DecimalField(decimal_places=6, max_digits=9)),
                ('horizontal_accruacy', models.DecimalField(decimal_places=6, max_digits=9)),
                ('vertiacl_accruracy', models.DecimalField(decimal_places=6, max_digits=9)),
            ],
        ),
        migrations.AddField(
            model_name='configuration',
            name='trim',
            field=models.IntegerField(default=0),
        ),
    ]