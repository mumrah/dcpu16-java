from functools import partial
import os
import re
import struct
import sys
import logging

if __name__ == "__main__":
    log = logging.getLogger()
    logging.basicConfig(level=logging.INFO)
    operators = {
        'SET': 0x01,
        'ADD': 0x02,
        'SUB': 0x03,
        'MUL': 0x04,
        'MLI': 0x05,
        'DIV': 0x06,
        'DVI': 0x07,
        'MOD': 0x08,
        'MDI': 0x09,
        'AND': 0x0a,
        'BOR': 0x0b,
        'XOR': 0x0c,
        'SHR': 0x0d,
        'ASR': 0x0e,
        'SHL': 0x0f,
        'IFB': 0x10,
        'IFC': 0x11,
        'IFE': 0x12,
        'IFN': 0x13,
        'IFG': 0x14,
        'IFA': 0x15,
        'IFL': 0x16,
        'IFU': 0x17,
        'ADX': 0x1a,
        'SBX': 0x1b,
        'STI': 0x1e,
        'STD': 0x1f,
    }

    special = {
        'JSR': 0x01,
        'INT': 0x08,
        'IAG': 0x09,
        'IAS': 0x0a,
        'RFI': 0x0b,
        'IAQ': 0x0c,
        'HWN': 0x10,
        'HWQ': 0x11,
        'HWI': 0x12,
    }

    registers = {
        'A': 0x00,
        'B': 0x01,
        'C': 0x02,
        'X': 0x03,
        'Y': 0x04,
        'Z': 0x05,
        'I': 0x06,
        'J': 0x07,
        'SP': 0x1b,
        'PC': 0x1c,
        'EX': 0x1d,
    }

    spec = """
    line                = label instruction | instruction

    label               = ":" [0-9a-z]+

    instruction         = operator operand_b, operand_a comment?

    operator            = "SET" | "ADD" | ...

    operand_b           = direct_register 
                        | indirect_register
                        | indirect_register_and_offset
                        | "PUSH"
                        | "PEEK"
                        | pick
                        | "SP"
                        | "PC"
                        | "EX"
                        | next_word
                        | indirect_next_word

    direct_register     = "A" | "B" | "C" | "X" | "Y" | "Z" | "I" | "J"

    indirect_register   = "[" direct_register "]"

    indirect_register_and_offset    
                        = "[" direct_register " + " direct_register | literal "]"

    literal             = dec_literal | hex_literal

    dec_literal     = \d+

    hex_literal         = "0x" [0-9a-f]+

    pick                = "PICK" literal

    next_word           = literal

    indirect_next_word  = "[" literal "]"

    operand_a           = direct_register 
                        | indirect_register
                        | indirect_register_and_offset
                        | "POP"
                        | "PEEK"
                        | pick
                        | "SP"
                        | "PC"
                        | "EX"
                        | next_word
                        | indirect_next_word
                        | literal

    comment             = ";" \w+
    """

    def literal_subpattern(name):
        return "(?:(?P<%(name)s_dec>\-?\d{1,5}) | (?P<%(name)s_hex>0x[\dA-F]{1,4}))" % {'name': name}

    pattern = """
    ^                                           # Begin
    \s?                                         # Consume spaces
    (?P<label>:\w+\s+)?                         # A subroutine label
    (?P<operator>\w+?)                          # The instruction operator
    \s+                                         # Consume at least one space
    (?:
      (?P<b_operand>                            # B operand
        (?P<b_direct_register>                  # Direct register
          [ABCXYZIJ] | PC | EX | SP | PUSH | PEEK
        )
        |
        (?P<b_pick>                             # PICK next_word
          PICK \s+ %(b_next_word)s              # Literal value (next_word)
        ) 
        |
        (?P<b_indirect_register>                # Indirect register
          \[(?:[ABCXYZIJ] | PC | EX | SP)\]
        )      
        |
        (?P<b_indirect_register_with_offset>    # Indirect register with offset
          \[
            (?P<b_indirect_register_1>[ABCXYZIJ] | PC | EX | SP)
            \s*\+\s*
            %(b_indirect_register_next_word)s   # Literal value (offset)
          \]
        )
        |
        %(b_literal)s                           # Literal value
        |
        (?P<b_indirect_hex>\[0x[\da-f]{1,4}\])  # Indirect hex address
      )
    ,       # One comma
    )?
    \s*     # Any number of spaces
      (?P<a_operand>
        (?P<a_direct_register>                  # Direct register
          [ABCXYZIJ] | PC | EX | SP | IA | POP | PEEK
        )
        |
        (?P<a_pick>                             # PICK next_word
          PICK \s+ %(a_next_word)s              # Literal value (next_word)
        ) 
        |
        (?P<a_indirect_register>                # Indirect register
          \[(?:[ABCXYZIJ] | PC | EX | SP)\]
        )
        |
        (?P<a_indirect_register_with_offset>    # Indirect register with offset
          \[
            (?P<a_indirect_register_1>[ABCXYZIJ] | PC | EX | SP | IA)
            \s*\+\s*
            %(a_indirect_register_next_word)s   # Literal value (offset)
          \]
        )
        |
        %(a_literal)s                           # Literal value
        |
        (?P<a_indirect_hex>\[0x[\da-f]{1,4}\])  # Indirect hex address
        |
        (?P<a_label>\w+)                        # Label
      )
    (?:\s*;(?P<comments>.*)\s*)?                # Comments
    $                                           # End
    """ % {
        'b_next_word': literal_subpattern('b_next_word'),
        'b_indirect_register_next_word': literal_subpattern('b_indirect_register_next_word'),
        'b_literal': literal_subpattern('b_literal'),
        'a_next_word': literal_subpattern('a_next_word'),
        'a_indirect_register_next_word': literal_subpattern('a_indirect_register_next_word'),
        'a_literal': literal_subpattern('a_literal'),
    }
    fname = sys.argv[1]
    asm = open(fname, "r").read()
    words = []
    labels = {}
    wc = 0
    for line in asm.split("\n"):
        if line.strip() == "":
            continue
        m = re.match(pattern, line.strip(), re.VERBOSE | re.I)
        if(m):
            log.debug("%s; o=%s b=%s a=%s" % (line, m.group("operator"), m.group("b_operand"), m.group("a_operand")))
            log.debug("Regex groups: %s" % m.groupdict())
            wc = wc + 1
            a = None
            b = None
            a_label = None
            a_next_word = ""
            b_next_word = ""

            if m.group("b_operand") is None:
                # Special opcode, op = 0x00, b = opcode
                op = 0x00
                b = special[m.group("operator").upper()]
            else:
                # Regular opcode
                op = operators[m.group("operator").upper()]

            # Keep track of labels' positions
            if m.group("label"):
                labels[m.group("label").strip(": ")] = wc-1

            # Read b
            if m.group("b_direct_register"):
                b = registers[m.group("b_direct_register").upper()]
            elif m.group("b_indirect_register"):
                b = registers[m.group("b_indirect_register").strip("[]").upper()] + 0x08
            elif m.group("b_indirect_register_1"):
                b = registers[m.group("b_indirect_register_1").strip("[]").upper()] + 0x10
                if m.group("b_indirect_register_next_word_dec"):
                    b_next_word = struct.pack('<h', int(m.group("b_indirect_register_next_word_dec")))
                    wc = wc + 1
                elif m.group("b_indirect_register_next_word_hex"):
                    b_next_word = struct.pack('<H', int(m.group("b_indirect_register_next_word_hex"), 16))
                    wc = wc + 1
                else:
                    raise
            elif m.group("b_literal_dec"):
                b = 0x1f
                b_next_word = struct.pack('<h', int(m.group("b_literal_dec")))
                wc = wc + 1
            elif m.group("b_literal_hex"):
                b = 0x1f
                b_next_word = struct.pack('<H', int(m.group("b_literal_hex"), 16))
                wc = wc + 1
            elif m.group("b_indirect_hex"):
                b = 0x1e
                b_next_word = struct.pack('<H', int(m.group("b_indirect_hex").strip("[]"), 16))
                wc = wc + 1
            elif m.group("b_pick"):
                if m.group("b_next_word_dec"):
                    b = 0x1a
                    b_next_word = struct.pack('<h', int(m.group("b_next_word_dec")))
                    wc = wc + 1
                elif m.group("b_next_word_hex"):
                    b = 0x1a
                    b_next_word = struct.pack('<H', int(m.group("b_next_word_hex"), 16))
                    wc = wc + 1
                else:
                    raise
            else:
                if b == 0x01:
                    # Special opcode
                    pass
                else:
                    raise

            # Read a
            if m.group("a_direct_register"):
                a = registers[m.group("a_direct_register").upper()]
            elif m.group("a_indirect_register"):
                a = registers[m.group("a_indirect_register").strip("[]").upper()] + 0x08
            elif m.group("a_indirect_register_1"):
                a = registers[m.group("a_indirect_register_1").strip("[]").upper()] + 0x10
                if m.group("a_indirect_register_next_word_dec"):
                    a_next_word = struct.pack('<h', int(m.group("a_indirect_register_next_word_dec")))
                    wc = wc + 1
                elif m.group("a_indirect_register_next_word_hex"):
                    a_next_word = struct.pack('<H', int(m.group("a_indirect_register_next_word_hex"), 16))
                    wc = wc + 1
                else:
                    raise
            elif m.group("a_literal_dec"):
                val = int(m.group("a_literal_dec"))
                if val >= -1 and val <= 30:
                    a = val + 0x21
                else:
                    a = 0x1f
                    a_next_word = struct.pack('<h', val)
                    wc = wc + 1
            elif m.group("a_literal_hex"):
                val = int(m.group("a_literal_hex"), 16)
                if val >= -1 and val <= 30:
                    a = val + 0x21
                else:
                    a = 0x1f
                    a_next_word = struct.pack('<H', val)
                    wc = wc + 1
            elif m.group("a_indirect_hex"):
                a = 0x1e
                a_next_word = struct.pack('<H', int(m.group("a_indirect_hex").strip("[]"), 16))
                wc = wc + 1
            elif m.group("a_pick"):
                if m.group("a_next_word_dec"):
                    a = 0x1a
                    a_next_word = struct.pack('<h', int(m.group("a_next_word_dec")))
                    wc = wc + 1
                elif m.group("a_next_word_hex"):
                    a = 0x1a
                    a_next_word = struct.pack('<H', int(m.group("a_next_word_hex"), 16))
                    wc = wc + 1
                else:
                    raise
            elif m.group("a_label"):
                a_label = m.group("a_label")
                wc = wc + 1
            else:
                raise

            # Read comments
            if m.group("comments"):
                log.debug("Got comments: " + m.group("comments"))
                pass

            def encode_word(o, a, a_next_word, b, b_next_word, a_label):
                log.debug("Encode word: o=%s a=%s a_next_word=%s b=%s b_next_word=%s a_label=%s" % (o, a, a_next_word, b, b_next_word, a_label))
                if (a is None) and (a_label is not None):
                    a_next_word = struct.pack('<H', labels[a_label])
                    a = 0x1f
                word = ((a & 0x3f) << 10) | ((b & 0x1f) << 5) | (o & 0x1f)
                out = ""
                out += struct.pack('<H', word)
                out += b_next_word
                out += a_next_word
                return out

            # Need to defer writing out the instructions until all the labels have
            # been read. Use partial to create a closure around these values
            words.append(partial(encode_word, op, a, a_next_word, b, b_next_word, a_label))
        else:
            log.warn("Invalid syntax: %s" % line)
    log.debug("Labels: %s" % labels)
    program = open("%s.o" % os.path.splitext(fname)[0], "wb")
    for word in words:
        program.write(word())
    program.close()
