"""Tiny ELF loader (PT_LOAD segments + a few symbols) using pyelftools."""

import os

from elftools.elf.elffile import ELFFile


class ElfImage:
    def __init__(self, path):
        self.path = os.fspath(path)
        self.segments = []       # list of (load_addr, bytes)
        self.symbols = {}        # name -> address
        self.entry = 0

        with open(self.path, "rb") as fh:
            elf = ELFFile(fh)
            self.entry = elf["e_entry"]

            for seg in elf.iter_segments():
                if seg["p_type"] != "PT_LOAD":
                    continue
                data = seg.data()
                if not data:
                    continue
                # p_paddr is the load address (LMA): .data gets copied from
                # flash to RAM by the startup code, so load it at the LMA.
                addr = seg["p_paddr"] or seg["p_vaddr"]
                self.segments.append((addr, data))

            for section in elf.iter_sections():
                if section.name != ".symtab":
                    continue
                for sym in section.iter_symbols():
                    if sym.name and sym["st_value"]:
                        self.symbols[sym.name] = sym["st_value"]

    def describe(self):
        return "%s entry=0x%08x segments=%d" % (
            os.path.basename(self.path), self.entry, len(self.segments)
        )
