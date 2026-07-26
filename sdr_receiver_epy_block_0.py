from gnuradio import gr
import pmt
import numpy as np

class blk(gr.basic_block):
    def __init__(self):
        gr.basic_block.__init__(self,
            name="Command_Parser",
            in_sig=[(np.uint8, 1)], 
            out_sig=[])

        # porturi de iesire
        self.message_port_register_out(pmt.intern("freq_out"))
        self.message_port_register_out(pmt.intern("samp_out"))
        self.message_port_register_out(pmt.intern("gain_out"))

        # buffer pentru concatenarea streamului 
        self.partial_buffer = b""

    def general_work(self, input_items, output_items):
        in0 = input_items[0]

        if len(in0) == 0:
            return 0

        self.partial_buffer += bytes(in0)

        while b'\n' in self.partial_buffer:
            line, self.partial_buffer = self.partial_buffer.split(b'\n', 1)
            try:
                data_str = line.decode().strip()
                parts = data_str.split(",")

                if len(parts) != 3:
                    print(f"[GNU] Comanda invalida: {data_str}")
                    continue

                freq = float(parts[0])
                samp_rate = float(parts[1])
                gain = float(parts[2])

                print(f"[GNU] Comanda primita: freq={freq}, sr={samp_rate}, gain={gain}")

                # publicare catre urmatorul bloc
                self.message_port_pub(pmt.intern("freq_out"), pmt.from_double(freq))
                self.message_port_pub(pmt.intern("samp_out"), pmt.from_double(samp_rate))
                self.message_port_pub(pmt.intern("gain_out"), pmt.from_double(gain))

            except Exception as e:
                print(f"[GNU] Eroare la prelucrarea comenzii: {e}")

        self.consume(0, len(in0))
        return len(in0)

