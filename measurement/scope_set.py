"""Send SCPI settings to the scope, then print the ones that matter."""
import socket, sys
s = socket.create_connection(("169.254.211.142", 5025), timeout=5)
f = s.makefile("rb")
for c in sys.argv[1:]:
    s.sendall((c + "\n").encode())
s.sendall(b"*OPC?\n"); f.readline()
for q in ["TIM:RANG?","TIM:REF?","ACQ:RES?","ACQ:POIN:VAL?","CHAN2:SCAL?","CHAN2:OFFS?","CHAN3:SCAL?","CHAN3:OFFS?","SYST:ERR?"]:
    s.sendall((q + "\n").encode()); print(q, f.readline().decode().strip())
