from gnuradio import gr
import pmt

class blk(gr.basic_block):
    def __init__(self, tb=None):  # primeste top_block ca argument
        gr.basic_block.__init__(self,
            name="Update_Variables",
            in_sig=[],
            out_sig=[])

        self.tb = tb  # salvează referinta la top_block

        self.message_port_register_in(pmt.intern("freq_in"))
        self.message_port_register_in(pmt.intern("samp_in"))
        self.message_port_register_in(pmt.intern("gain_in"))

        self.set_msg_handler(pmt.intern("freq_in"), self.handle_freq)
        self.set_msg_handler(pmt.intern("samp_in"), self.handle_samp)
        self.set_msg_handler(pmt.intern("gain_in"), self.handle_gain)

    def handle_freq(self, msg):
        try:
            new_freq = float(pmt.to_python(msg))
            if self.tb is not None:
                self.tb.uhd_usrp_source_0.set_center_freq(new_freq, 0)
                print(f"[GNU] Frecventa actualizata la {new_freq} Hz")
            else:
                print("[GNU] self.tb e None, nu se poate modifica frecventa")
        except Exception as e:
            print(f"[GNU] Eroare la setarea frecventei: {e}")

    def handle_samp(self, msg):
        try:
            new_sr = float(pmt.to_python(msg))
            if self.tb is not None:
                self.tb.uhd_usrp_source_0.set_samp_rate(new_sr)
                print(f"[GNU] Sample rate actualizat la {new_sr} Hz")
            else:
                print("[GNU] self.tb e None, nu se poate modifica sample rate")
        except Exception as e:
            print(f"[GNU] Eroare la setarea sample rate: {e}")

    def handle_gain(self, msg):
        try:
            new_gain = float(pmt.to_python(msg))
            if self.tb is not None:
                self.tb.uhd_usrp_source_0.set_gain(new_gain, 0)
                print(f"[GNU] Gain actualizat la {new_gain} dB")
            else:
                print("[GNU] self.tb e None, nu se poate modifica gain")
        except Exception as e:
            print(f"[GNU] Eroare la setarea gain-ului: {e}")

