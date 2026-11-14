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


def source_location(path, addr):
    """Return (file, line) for an address using DWARF debug info, or None."""
    try:
        with open(path, "rb") as fh:
            elf = ELFFile(fh)
            if not elf.has_dwarf_info():
                return None
            dwarf = elf.get_dwarf_info()
            res = dwarf.line_program_for_address(addr)
            if res is None:
                return None
            lp = res[1] if isinstance(res, tuple) else res
            prev = None
            for entry in lp.entries:
                if entry.state is None:
                    continue
                if entry.state.address > addr:
                    break
                prev = entry.state
            if prev is None or not prev.line:
                return None
            file_index = prev.file
            if file_index == 0 or file_index > len(lp.header.file_entry):
                return None
            fe = lp.header.file_entry[file_index - 1]
            name = fe.name.decode("utf-8", "replace")
            if fe.dir_index and fe.dir_index <= len(lp.header.include_directory):
                dname = lp.header.include_directory[fe.dir_index - 1].decode(
                    "utf-8", "replace")
                name = os.path.join(dname, name)
            return (name, prev.line)
    except Exception:  # noqa: BLE001
        return None
