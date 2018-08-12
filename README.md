# AUV Control PI
Raspbery Pi based onboard controller for the AUV.

This is the main brains of the AUV and manages communication between
the frontend, server and the hardware/navigation systems.

## Hardware

### Controller

- [Raspberry PI 3](https://www.raspberrypi.org/products/raspberry-pi-3-model-b-plus/)
- [Navio 2](https://docs.emlid.com/navio2/)

The Navio has all the I/O controlls including an integrated GPS, and
9-axis IMU.

### Motors

- [Blue Robotics T100](https://www.bluerobotics.com/store/thrusters/t100-thruster/)
- [Speed Controller (ESC)](https://www.bluerobotics.com/store/electronics/besc30-r3/)


### RC Control

- [RadioLink T8FB + R8EH Receiver](https://www.robotshop.com/ca/en/radiolink-t8fb-24ghz-8ch-transmitter-r8eh-8ch-receiver.html)



## Sotware:

The code is broken up into individual components that communicate via
RPC + Pub/Sub using the [Crossbar WAMP](https://crossbar.io/) router
and [autobahn](https://github.com/crossbario/autobahn-python) components.

All the sensors have their own components that publish data over the
which any other component can subscribe to. The idea here is to decouple
the low level sensors and output devices from the higher level
control code which allows easy prototyping of different control
implimentations.

A Django app is provided for managing config variables in the
Django admin interfce and allowing components to get access to the
Django ORM to write data to the database and use the configurations
stored in the database.

## Development

### Local

```bash
$ docker-compose build
$ docker-compose up
```


## Raspberry PI

Follow the navio [instructions](https://docs.emlid.com/navio2/common/ardupilot/configuring-raspberry-pi/)
to setup the RasPi using the custom Navio Raspbian image:

#### Install Docker:
```bash
$ curl -fsSL get.docker.com -o get-docker.sh && sh get-docker.sh
```

Setup docker to run without root permissions:

```bash
$ sudo groupadd docker
$ sudo gpasswd -a $USER docker
$ newgrp docker
```

Test things have installed correctly try running a hello world conatiner:

```bash
$ docker run hello-world
```

#### Install Docker Compose

As of writing this the easiest way to install docker-compose on ARM
is using `pip`.


```bash
$ sudo pip install docker-compose
```

Test the installation:

```bash
$ docker-compose --version
```


#### Run AUV Control

```bash
$ git clone https://github.com/adrienemery/auv-con  trol-pi.git
$ cd auv_control_pi
$ docker-compose build
$ docker-compose up
```
