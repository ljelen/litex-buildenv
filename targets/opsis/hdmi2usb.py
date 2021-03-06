from migen.fhdl.decorators import ClockDomainsRenamer
from litex.soc.integration.soc_core import mem_decoder
from litex.soc.interconnect import stream

from gateware.encoder import EncoderDMAReader, EncoderBuffer, Encoder
from gateware.streamer import USBStreamer

from targets.opsis.video import SoC as BaseSoC


class HDMI2USBSoC(BaseSoC):
    mem_map = {**BaseSoC.mem_map, **{
        "encoder": 0xd0000000,
    }}

    def __init__(self, platform, *args, **kwargs):
        BaseSoC.__init__(self, platform, *args, **kwargs)

        encoder_port = self.sdram.crossbar.get_port()
        self.submodules.encoder_reader = EncoderDMAReader(encoder_port)
        self.add_csr("encoder_reader")
        encoder_cdc = stream.AsyncFIFO([("data", 128)], 4)
        encoder_cdc = ClockDomainsRenamer({"write": "sys",
                                           "read": "encoder"})(encoder_cdc)
        encoder_buffer = ClockDomainsRenamer("encoder")(EncoderBuffer())
        encoder = Encoder(platform)
        encoder_streamer = USBStreamer(platform, platform.request("fx2"))
        self.submodules += encoder_cdc, encoder_buffer, encoder, encoder_streamer
        self.add_csr("encoder")

        self.comb += [
            self.encoder_reader.source.connect(encoder_cdc.sink),
            encoder_cdc.source.connect(encoder_buffer.sink),
            encoder_buffer.source.connect(encoder.sink),
            encoder.source.connect(encoder_streamer.sink)
        ]
        self.add_wb_slave(self.mem_map["encoder"], encoder.bus)
        self.add_memory_region("encoder",
            self.mem_map["encoder"], 0x2000, type="io")

        self.platform.add_period_constraint(encoder_streamer.cd_usb.clk, 10.0)

        encoder_streamer.cd_usb.clk.attr.add("keep")
        self.crg.cd_encoder.clk.attr.add("keep")
        self.platform.add_false_path_constraints(
            self.crg.cd_sys.clk,
            self.crg.cd_encoder.clk,
            encoder_streamer.cd_usb.clk)


SoC = HDMI2USBSoC
