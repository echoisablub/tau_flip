"""Read the last acquisition from the RTO2014 over LAN into a CSV for tau_analyse.py.

Untested sketch. Usage: python tau_scope.py tau_25C_O000.csv
Needs: pip install pyvisa pyvisa-py. Set SCOPE_IP first.
ch1 = frame trigger line, ch2 = PD behind the PBS, ch3 = reference PD.
"""
import sys

import numpy as np
import pyvisa

SCOPE_IP = "192.168.x.x"

rto = pyvisa.ResourceManager("@py").open_resource(f"TCPIP::{SCOPE_IP}::INSTR")
rto.timeout = 120000
rto.write("FORM:DATA REAL,32")
rto.write("FORM:BORD LSBF")


def read(ch):
    return rto.query_binary_values(f"CHAN{ch}:DATA?", datatype="f",
                                   is_big_endian=False, container=np.array)


x0, x1, n, _ = rto.query("CHAN1:DATA:HEAD?").split(",")
t = np.linspace(float(x0), float(x1), int(n))
out = sys.argv[1] if len(sys.argv) > 1 else "trace.csv"
np.savetxt(out, np.column_stack([t, read(1), read(2), read(3)]),
           delimiter=",", header="t,ch1,ch2,ch3", comments="")
print(f"wrote {out}: {n} points")
