"""Minimal GDB Remote Serial Protocol server for stmlab.

This is a *basic* stub: enough to attach, inspect registers/memory, set
software breakpoints, continue and step. It is not a full debugger.
"""

import socket
import threading

REG_ORDER = ["r0", "r1", "r2", "r3", "r4", "r5", "r6", "r7",
             "r8", "r9", "r10", "r11", "r12", "sp", "lr", "pc"]


class GdbStub:
    def __init__(self, machine, host="127.0.0.1", port=1234):
        self.machine = machine
        self.host = host
        self.port = port
        self.breakpoints = set()
        self._sock = None
        self._client = None
        self._running = False
        self._thread = None

    # -- packet helpers ------------------------------------------------
    @staticmethod
    def _checksum(data):
        return sum(data) & 0xFF

    def _recv_packet(self, sock):
        # Wait for '$'
        buf = b""
        while True:
            ch = sock.recv(1)
            if not ch:
                return None
            if ch == b"$":
                break
            if ch == b"\x03":          # Ctrl-C
                return "interrupt"
        data = b""
        while True:
            ch = sock.recv(1)
            if not ch:
                return None
            if ch == b"#":
                break
            data += ch
        # read 2 checksum bytes
        csum = sock.recv(2)
        try:
            expected = int(csum, 16)
        except ValueError:
            expected = -1
        if expected != self._checksum(data):
            sock.sendall(b"-")
            return self._recv_packet(sock)
        sock.sendall(b"+")
        return data.decode("ascii", "replace")

    def _send_packet(self, sock, payload):
        body = payload.encode("ascii")
        packet = b"$" + body + b"#" + ("%02x" % self._checksum(body)).encode()
        sock.sendall(packet)

    # -- register encoding ---------------------------------------------
    def _read_registers(self):
        regs = self.machine.registers()
        # GDB order: r0..r12, sp, lr, pc, cpsr(xpsr)
        order = ["r0", "r1", "r2", "r3", "r4", "r5", "r6", "r7",
                 "r8", "r9", "r10", "r11", "r12", "sp", "lr", "pc"]
        vals = [regs.get(n, 0) for n in order] + [regs.get("xpsr", 0)]
        # little-endian 4 bytes each
        out = ""
        for v in vals:
            out += "".join("%02x" % ((v >> (8 * i)) & 0xFF) for i in range(4))
        return out

    # -- command handling ----------------------------------------------
    def _handle(self, sock, packet):
        if packet == "interrupt":
            return "S05"

        if packet == "?":
            return "S05"

        if packet.startswith("qSupported"):
            return "PacketSize=4000;swbreak+;hwbreak+"

        if packet.startswith("qAttached"):
            return "1"

        if packet == "g":
            return self._read_registers()

        if packet.startswith("m"):
            # m addr,length
            try:
                addr_s, len_s = packet[1:].split(",")
                addr = int(addr_s, 16)
                length = int(len_s, 16)
            except ValueError:
                return "E01"
            data = []
            for i in range(length):
                try:
                    data.append(self.machine.peek(addr + i, 1))
                except Exception:  # noqa: BLE001
                    return "E01"
            return "".join("%02x" % b for b in data)

        if packet.startswith("M"):
            # M addr,length:XX...
            try:
                head, hexdata = packet[1:].split(":")
                addr_s, len_s = head.split(",")
                addr = int(addr_s, 16)
                length = int(len_s, 16)
            except ValueError:
                return "E01"
            if len(hexdata) != length * 2:
                return "E01"
            for i in range(length):
                self.machine.poke(addr + i, 1, int(hexdata[i * 2:(i + 1) * 2], 16))
            return "OK"

        if packet.startswith("Z0,"):
            # software breakpoint
            try:
                addr = int(packet[3:].split(",")[0], 16)
            except ValueError:
                return "E01"
            self.breakpoints.add(addr & ~1)
            return "OK"

        if packet.startswith("z0,"):
            try:
                addr = int(packet[3:].split(",")[0], 16)
            except ValueError:
                return "E01"
            self.breakpoints.discard(addr & ~1)
            return "OK"

        if packet == "c":
            # continue until breakpoint or halt
            steps = 0
            max_steps = 100_000_000
            while steps < max_steps:
                if self.machine.halted:
                    return "S05"
                pc = self.machine.pc() & ~1
                if pc in self.breakpoints:
                    return "S05"
                self.machine.run_instructions(1000)
                steps += 1000
                if self.machine.halted:
                    return "S05"
                pc = self.machine.pc() & ~1
                if pc in self.breakpoints:
                    return "S05"
            return "S05"

        if packet == "s":
            self.machine.run_instructions(1)
            return "S05"

        if packet.startswith("D"):
            return "OK"

        if packet == "k":
            self._running = False
            return ""

        # unknown
        return ""

    def _client_loop(self, sock):
        while self._running:
            packet = self._recv_packet(sock)
            if packet is None:
                break
            if packet == "":
                continue
            reply = self._handle(sock, packet)
            if reply is None:
                continue
            if reply == "":
                # for 'k' etc.
                if packet == "k":
                    break
                continue
            self._send_packet(sock, reply)
            if packet == "D":
                break
        try:
            sock.close()
        except Exception:  # noqa: BLE001
            pass

    def start(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.listen(1)
        self._running = True
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()

    def _accept_loop(self):
        while self._running:
            try:
                self._sock.settimeout(1.0)
                client, _ = self._sock.accept()
            except socket.timeout:
                continue
            except Exception:  # noqa: BLE001
                break
            self._client = client
            self._client_loop(client)
            self._client = None

    def stop(self):
        self._running = False
        if self._client is not None:
            try:
                self._client.close()
            except Exception:  # noqa: BLE001
                pass
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:  # noqa: BLE001
                pass