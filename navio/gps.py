from . import ublox


class GPS:

    def __init__(self):

        self.ubl = ublox.UBlox("spi:0.0", baudrate=5000000, timeout=2)

        self.ubl.configure_poll_port()
        self.ubl.configure_poll(ublox.CLASS_CFG, ublox.MSG_CFG_USB)
        # self.ubl.configure_poll(ublox.CLASS_MON, ublox.MSG_MON_HW)

        self.ubl.configure_port(port=ublox.PORT_SERIAL1, inMask=1, outMask=0)
        self.ubl.configure_port(port=ublox.PORT_USB, inMask=1, outMask=1)
        self.ubl.configure_port(port=ublox.PORT_SERIAL2, inMask=1, outMask=0)
        self.ubl.configure_poll_port()
        self.ubl.configure_poll_port(ublox.PORT_SERIAL1)
        self.ubl.configure_poll_port(ublox.PORT_SERIAL2)
        self.ubl.configure_poll_port(ublox.PORT_USB)
        self.ubl.configure_solution_rate(rate_ms=1000)

        self.ubl.set_preferred_dynamic_model(None)
        self.ubl.set_preferred_usePPP(None)

        self.ubl.configure_message_rate(ublox.CLASS_NAV, ublox.MSG_NAV_POSLLH, 1)
        self.ubl.configure_message_rate(ublox.CLASS_NAV, ublox.MSG_NAV_PVT, 1)
        self.ubl.configure_message_rate(ublox.CLASS_NAV, ublox.MSG_NAV_STATUS, 1)
        self.ubl.configure_message_rate(ublox.CLASS_NAV, ublox.MSG_NAV_SOL, 1)
        self.ubl.configure_message_rate(ublox.CLASS_NAV, ublox.MSG_NAV_VELNED, 1)
        self.ubl.configure_message_rate(ublox.CLASS_NAV, ublox.MSG_NAV_SVINFO, 1)
        self.ubl.configure_message_rate(ublox.CLASS_NAV, ublox.MSG_NAV_VELECEF, 1)
        self.ubl.configure_message_rate(ublox.CLASS_NAV, ublox.MSG_NAV_POSECEF, 1)
        self.ubl.configure_message_rate(ublox.CLASS_RXM, ublox.MSG_RXM_RAW, 1)
        self.ubl.configure_message_rate(ublox.CLASS_RXM, ublox.MSG_RXM_SFRB, 1)
        self.ubl.configure_message_rate(ublox.CLASS_RXM, ublox.MSG_RXM_SVSI, 1)
        self.ubl.configure_message_rate(ublox.CLASS_RXM, ublox.MSG_RXM_ALM, 1)
        self.ubl.configure_message_rate(ublox.CLASS_RXM, ublox.MSG_RXM_EPH, 1)
        self.ubl.configure_message_rate(ublox.CLASS_NAV, ublox.MSG_NAV_TIMEGPS, 5)
        self.ubl.configure_message_rate(ublox.CLASS_NAV, ublox.MSG_NAV_CLOCK, 5)
        # self.ubl.configure_message_rate(ublox.CLASS_NAV, ublox.MSG_NAV_DGPS, 5)

        self.msg = None

    def update(self):
        self.msg = self.ubl.receive_message()

        if self.msg.name() == "NAV_POSLLH":
            outstr = str(self.msg).split(",")[1:]
            outstr = "".join(outstr)

        if self.msg.name() == "NAV_STATUS":
            outstr = str(self.msg).split(",")[1:2]
            outstr = "".join(outstr)
        return self.msg
