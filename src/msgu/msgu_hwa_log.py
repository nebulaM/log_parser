import os
import sys
import re
import xml.etree.ElementTree as ET
import src.msgu.msgu_common as cm
import src.msgu.msgu_html as mhtml
from ..shared import dutil as ut
from ..shared import struct as REG
sys.path.append(os.path.dirname(sys.argv[0]))

class HWALog(cm.MSGULog):
    SECTION = 'hwa_log'
    DEFINITION_FILE_DIR = os.path.join(cm.MSGULog.INCLUDE_DIR, 'doc', 'msgu', 'MSGU_HWA_REG.xml')
    LOG_HEADER = '# MSGU HWA Registers'
    LOG_ENDING = '# MSGU_HWA - IB IU Context RAM'
    # HWA addr 0x0 = MSGU addr 0x2b0000
    HWA_ADDRESS_OFFSET = 0x2b0000

    BYTE_PER_REG = 8

    # Outbound FIFO from [LINK]
    LIST_HWA_OB_FIFO = ["OB_IU HQA Descriptor FIFO",
                        "OB_IU Read Descriptor FIFO",
                        "OB_IU Write MFA FIFO",
                        "OB_IU Pending Producer Index FIFO",
                        "OB_IU Read Response FIFO",
                        "OB_IU Read DMA Completion FIFO",
                        "OB_IU Free MFA FIFO Instance",
                        "OB_IU DMA Write Descriptor FIFO",
                        "OB_IU DMA Write Response FIFO",
                        "OB_IU Write DMA Completion FIFO",
                        "OB_IU Working Producer Index FIFO",
                        "OB_PI Write DMA Completion FIFO",
                        "OB_PI HQA Descriptor FIFO",
                        "OB_PI DMA write Response FIFO",
                        "OB_PI Local copy Index FIFO",
                        "OB Free Local buffer pointer FIFO"]
    # Inbound FIFO from [LINK]
    LIST_HWA_IB_FIFO = ["IB_IU HQA Descriptor FIFO",
                        "IB_IU MFA FIFO",
                        "IB_IU Pending Consumer Index FIFO",
                        "IB_IU Read DMA Descriptor FIFO",
                        "IB_IU DMA Read Response FIFO",
                        "IB_IU DMA Read completion FIFO",
                        "IB_IU DMA Write Descriptor FIFO",
                        "IB_IU DMA Write Response FIFO",
                        "IB_IU DMA Write Completion FIFO",
                        "IB_IU DMA Write Completion Descriptor FIFO",
                        "IB_IU Write MFA FIFO",
                        "IB_IU Working copy Index FIFO",
                        "IB_IU IET FIFO",
                        "IB_CI Write DMA Completion FIFO",
                        "IB_CI HQA Descriptor FIFO",
                        "IB_CI DMA write Response FIFO",
                        "IB_CI Local copy Index FIFO",
                        "Clear valid request FIFO",
                        "Clear valid response FIFO",
                        "Clear valid DMA completion FIFO",
                        "IB IU Completion response FIFO",
                        "IB IU DMA completion response FIFO"]
    reg_list = []
    def __init__(self):
        self.FINAL_ADDRESS_OFFSET = self.MSGU_ADDRESS_OFFSET + self.HWA_ADDRESS_OFFSET
    
    @classmethod
    def _handle_parse_q_expand_token(cls, str_val, raw_meaning, token):
        is_ib = True
        offset = 0
        meaning_ret = ''
        if '_IBIX_' in token:
            offset = 13
        elif '_OBIX_' in token:
            is_ib = False
            offset = 11
        elif '_OB_' in token:
            is_ib = False

        for i in range(0, len(str_val)):
            idx = len(str_val) + offset - i -1
            if is_ib is True:
                fifo_name = cls.LIST_HWA_IB_FIFO[idx]
            else:
                fifo_name = cls.LIST_HWA_OB_FIFO[idx]
            meaning = ut.handle_logic_token(str_val[i], raw_meaning)
            meaning_ret = ''.join([meaning_ret, fifo_name, ':', meaning, '\n'])
        return meaning_ret

    @classmethod
    def _post_spec_reg_handler_3000_3020(cls, decoded_reg, r_access, w_access):
        ''' special hwa register 3000 and 3020 after decoding regs '''
        bit_name, bit_val, bit_meaning = decoded_reg.bit_dict['3:0']
        if r_access is True:
            bit_meaning = re.sub('FW does not have READ.*READ access.', \
            'FW has READ access to inbound free local buffer, HWA does not.', \
            bit_meaning)
        if w_access is True:
            bit_meaning = re.sub('FW does not have WRITE.*WRITE access.', \
            'FW has WRITE access to inbound free local buffer, HWA does not.', \
            bit_meaning)
        decoded_reg.add_bit_des('3:0', bit_name, bit_val, bit_meaning)

    @classmethod
    def _post_spec_reg_handler_3100_3180(cls, decoded_reg):
        ''' special hwa register 3100 and 3180 after decoding regs '''
        bit_val, bit_val_str = ut.bit_shift(decoded_reg.reg_val, '63:32')
        if bit_val == 0:
            block = 'eGSM'
        elif bit_val == 2:
            block = 'PCSx L2 cache'
        elif bit_val >= 8 and bit_val <= 11:
            block = 'DDR'
        else:
            block = 'N/A'
        bit_name, bit_val, bit_meaning = decoded_reg.bit_dict['63:32']
        bit_meaning = re.sub('this.*block', block, bit_meaning)
        decoded_reg.add_bit_des('63:32', bit_name, bit_val, bit_meaning)

    @classmethod
    def _post_spec_reg_handler_3140(cls, decoded_reg):
        ''' special hwa register 3140 after decoding regs '''
        bit_val, bit_val_str = ut.bit_shift(decoded_reg.reg_val, 20)
        if bit_val == 1:
            bit_name, bit_val, bit_meaning = decoded_reg.bit_dict['15:0']
            decoded_reg.add_bit_des('15:0', bit_name, bit_val, \
            "This field is invalid because RD_IB_IU_HDR is set to 1.")
    
    @classmethod
    def get_def_list(cls):
        tree = ET.parse(cls.DEFINITION_FILE_DIR)
        root = tree.getroot()
        reg_list = []
        for reg in root.findall('register'):
            reg_name = reg.find('reg_name').text
            reg_addr = reg.find('reg_address').text
            #print reg_name
            #print reg_addr
            this_reg = REG.DefReg(reg_addr, reg_name)
            reg_bits = reg.find('reg_bits')
            if reg_bits is not None:
                for reg_bit in reg_bits.findall('reg_bit'):
                    bit_pos = reg_bit.find('bit_position').text
                    bit_name = reg_bit.find('bit_name').text
                    bit_des = reg_bit.find('bit_description')
                    bit_meaning = ''
                    if bit_des is not None:
                        for p in bit_des:
                            '''
                                add '\n' to split lines, this is useful to
                                split meanings with 'When set to logic'
                            '''
                            bit_meaning = ''.join([bit_meaning, p.text, '\n'])
                    #print bit_pos
                    #print bit_name
                    #print bit_meaning
                    this_reg.add_bit_des(bit_pos, bit_name, bit_meaning)
            reg_list.append(this_reg)
        if cls.DEBUG_MODE is True:
            for reg in reg_list:
                print hex(reg.reg_address)
                print reg.reg_name
                if reg.has_bit_des is True:
                    bit_dict = reg.bit_dict
                    for key in bit_dict.keys():
                        print key
                        print bit_dict[key]
        return reg_list

    @classmethod
    def get_reg_meaning(cls, tag, crash_dump_reg_list, definition_list):
        tag, tag_next_level = ut.get_debug_tags(tag, cls.MODULE, cls.SECTION, 'get_reg_meaning')
        # q_expand token is special for HWA, other sections should not use this token
        re_q_expand_token = re.compile('@PARSE_([IO]B(IX)?)_Q_EXPAND@')
        
        hwa_addr_offset = cls.MSGU_ADDRESS_OFFSET + cls.HWA_ADDRESS_OFFSET
        decoded_reg_dict = {}
        spec_ib_r_access = False
        spec_ib_w_access = False
        spec_ob_r_access = False
        spec_ob_w_access = False
        for reg_addr, reg_val in crash_dump_reg_list:
            # calc by addr in PD's HWA standalone doc, becasue def xml file stores that addr.
            reg_addr_hwa = reg_addr - hwa_addr_offset

            # pre handle special regs
            # refer to [LINK]
            if reg_addr_hwa == 0x3060:
                # The following bit position defines the parameter
                # For example bit 20 of 0x3060 is spec_ib_r_access
                spec_ib_r_access = True if (ut.bit_shift(reg_val, 20)[0] == 1) else False
                spec_ib_w_access = True if (ut.bit_shift(reg_val, 21)[0] == 1) else False
                spec_ob_r_access = True if (ut.bit_shift(reg_val, 52)[0] == 1) else False
                spec_ob_w_access = True if (ut.bit_shift(reg_val, 53)[0] == 1) else False

            # normal handle regs
            for reg in definition_list:
                if reg.reg_address == reg_addr_hwa:
                    # store decoded address as addr in PD document: cpu_addr - MSGU_ADDRESS_OFFSET.
                    decoded_reg = REG.DecodedReg(reg_addr - cls.MSGU_ADDRESS_OFFSET, reg.reg_name, reg_val)
                    if cls.DEBUG_MODE is True:
                        print hex(decoded_reg.reg_address)
                        print decoded_reg.reg_name

                    if reg.has_bit_des is True:
                        for bit_pos in reg.bit_dict.keys():
                            bit_name, raw_bit_meaning = reg.bit_dict[bit_pos]
                            bit_val, bit_val_str = ut.bit_shift(reg_val, bit_pos)
                            bit_meaning = raw_bit_meaning
                            match = re_q_expand_token.search(bit_meaning)
                            if match is not None:
                                bit_meaning = cls._handle_parse_q_expand_token(bit_val_str, bit_meaning, match.group(0))

                            if cls.re_logic.search(bit_meaning) is not None:
                                bit_meaning = ut.handle_logic_token(bit_val_str, bit_meaning)
                            if cls.re_hex_token.search(bit_meaning) is not None:
                                hex_digit = len(bit_val_str) >> 2
                                if (len(bit_val_str) % 4) != 0:
                                    hex_digit += 1
                                hex_format = ''.join(['0x{:0', str(hex_digit), 'x}'])
                                bit_meaning = cls.re_hex_token.sub(hex_format.format(bit_val), bit_meaning)
                            bit_meaning = cls.re_dec_token.sub(str(bit_val), bit_meaning)
                            if cls.DEBUG_MODE is True:
                                print bit_pos
                                print bit_val_str
                                print bit_meaning
                            # add bit_val_str instead of bit_val
                            decoded_reg.add_bit_des(bit_pos, bit_name, bit_val_str, bit_meaning)
                    decoded_reg_dict[decoded_reg.reg_address] = decoded_reg

        # post handle special regs and change the meaning with the one defined in handler.
        # refer to [LINK]
        if not decoded_reg_dict:
            print tag + 'Warnning, HWA section is empty'
        else:
            try:
                cls._post_spec_reg_handler_3000_3020(decoded_reg_dict[0x2b3000], spec_ib_r_access, spec_ib_w_access)
            except KeyError:
                print tag + 'register 0x2b3000 not found in log'
            try:
                cls._post_spec_reg_handler_3000_3020(decoded_reg_dict[0x2b3020], spec_ob_r_access, spec_ob_w_access)
            except KeyError:
                print tag + 'register 0x2b3020 not found in log'
            try:
                cls._post_spec_reg_handler_3100_3180(decoded_reg_dict[0x2b3100])
            except KeyError:
                print tag + 'register 0x2b3100 not found in log'
            try:
                cls._post_spec_reg_handler_3100_3180(decoded_reg_dict[0x2b3180])
            except KeyError:
                print tag + 'register 0x2b3180 not found in log'
            try:    
                cls._post_spec_reg_handler_3140(decoded_reg_dict[0x2b3140])
            except KeyError:
                print tag + 'register 0x2b3140 not found in log'
            ut.handle_parse_math_token(tag_next_level, decoded_reg_dict)
        return decoded_reg_dict

    @classmethod
    def save_result(cls, tag, decoded_reg_dict, standalone):
        if standalone is True:
            filename = ut.get_parsed_filename(cls.INPUT_DIR, cls.MODULE, cls.SECTION) + '.html'
            filename = os.path.join(cls.OUTPUT_DIR, filename)
            fd = open(filename, 'w')
            fd.write(mhtml.get_hwa_standalone_header(cls.INPUT_DIR))
            ut.save_decoded_reg_dict_to_html_table(decoded_reg_dict, fd, True)
            fd.write(mhtml.get_hwa_standalone_ending())
            fd.close()
            print tag + 'result saved in ' + filename
        else:
            fd = open(cls.common_out_filename, 'a')
            fd.write(mhtml.get_hwa_group_header())
            ut.save_decoded_reg_dict_to_html_table(decoded_reg_dict, fd, cls.DEBUG_MODE)
            fd.write(mhtml.get_hwa_group_ending())
            fd.close()

    def run(self, standalone=True):
        if standalone is True:
            self.set_input_params()
        tag, tag_next_level = ut.get_debug_tags(None, self.MODULE, self.SECTION, 'run')
        print tag + 'parser starts'
        crash_dump_reg_list = self.get_reg_val_list(tag_next_level, self.LOG_HEADER, self.LOG_ENDING, self.BYTE_PER_REG)
        
        if not crash_dump_reg_list:
            print tag + 'parser ends, no log for this section'
            return False

        definition_reg_list = self.get_def_list()

        decoded_reg_dict = self.get_reg_meaning(tag_next_level, crash_dump_reg_list, definition_reg_list)
        self.save_result(tag_next_level, decoded_reg_dict, standalone)

        print tag + 'parser ends'
        return True

# if entry point is this script, then run this script independently from other parsers.
if __name__ == '__main__':
    this = HWALog()
    this.run()
