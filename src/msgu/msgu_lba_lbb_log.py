import os
import sys
import re
import src.msgu.msgu_common as cm
import src.msgu.msgu_html as mhtml
from ..shared import dutil as ut
from ..shared import struct as IU
sys.path.append(os.path.dirname(sys.argv[0]))

class LBALBBLog(cm.MSGULog):
    SECTION = 'lba_lbb_log'
    LBA_DEFINITION_IU_DIR = os.path.join(cm.MSGULog.INCLUDE_DIR, 'doc', 'msgu', 'MSGU_LBA_IU.cfg')
    LBA_DEFINITION_FUNC_DIR = os.path.join(cm.MSGULog.INCLUDE_DIR, 'doc', 'msgu', 'MSGU_LBA_ADMIN_IU_FUNC_CODE.cfg')

    UNDEFINED_CODE = 'UNKNOWN IU CODE' 
    LBA_LOG_HEADER = '# LBA Memory'
    LBA_LOG_ENDING = '# LBB Memory'
    
    LBA_ADDRESS_OFFSET = 0xbf660000
    BYTE_PER_REG = 4
    # IU size is in bytes
    IU_SIZE = 128
    # Each IU buffer size
    IU_BUF_SIZE = 2048
    # number of IU buffer
    IU_BUF_NUM = 8

    # common header size in byte, 
    # this is the header for iu type and length only
    IU_COMMON_HEADER_SIZE = 4

    # total header size in byte
    ADMIN_IU_TOTAL_HEADER_SIZE = 64
    AIO_IU_TOTAL_HEADER_SIZE = 64
    RS_IU_TOTAL_HEADER_SIZE = 16

    # some RS IUs have special header size
    RS_REPORT_GEN_IU_TOTAL_HEADER_SIZE = 32
    RS_SCSI_CMD_VENDOR_REQ_IU_TOTAL_HEADER_SIZE = 64
    # special RS IU code
    RS_REPORT_GEN_IU_CODE = 0x1
    RS_SCSI_CMD_VENDOR_REQ_IU_CODE = 0x14

    # some of the IUs have SGL, currently all SGL has four 32-bit
    # fields, so 16 bytes in total
    SGL_SIZE = 16

    # admin IU reg location for function code
    # assume 32-bit register
    ADMIN_IU_FUNC_CODE_POSITION_IN_32_BIT_REG = 3

    # list of HBA IU
    AIO_IU_LIST = [0x15, 0x16, 0x17]
    # list of Admin IU
    ADMIN_IU_LIST = [0x60]
    # list of function code for Admin IU, function code should be defined in LBA_DEFINITION_FUNC_DIR
    ADMIN_IU_FUNC_CODE_LIST = [0x0, 0x1, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17]
    # list of RS IU
    RS_IU_LIST = [0x1, 0x13, 0x14, 0x72, 0x73, 0x74]
    # list of IUs with SGL
    IU_WITH_SGL_LIST = [0x15, 0x1, 0x14, 0x72, 0x73]

    LBB_DEFINITION_IU_DIR = os.path.join(cm.MSGULog.INCLUDE_DIR, 'doc', 'msgu', 'MSGU_LBB_IU.cfg')
    LBB_LOG_HEADER = '# LBB Memory'
    LBB_LOG_ENDING = '# MSGU HWA Registers'
    LBB_ADDRESS_OFFSET = 0xbf668000
    
    @classmethod
    def get_def_iu_dict(cls, tag, def_file_dir, verbose=False):
        tag, tag_next_level = ut.get_debug_tags(None, cls.MODULE, cls.SECTION, 'get_def_list')
        lines = ut.get_data_from_file(tag_next_level, def_file_dir)
        ''' Header in def file
            Example: [HBA_IU_TYPE_SCSI_TM_REQ, 0x16] '''
        re_iu_cfg = re.compile('\[([A-Z0-9_]+),(\s)?(0[xX])([0-9a-f]+)\]')
        def_iu_dict = {}
        this_iu = None
        flag_add_iu_to_dict = False
        for line in lines:
            # skip lines start with a "#" and empty lines in def file
            if '#' in line or not line.strip():
                continue
            try:
                # try to find iu header in def file in format [NAME, CODE]
                # for example [HBA_IU_TYPE_SCSI_TM_REQ, 0x16].
                # once the name and code of iu are found, create a new DefIU
                # for this iu so we can refer the meaning of it in the future
                # the block look for "[" "," and "]" to determine iu header
                line = re_iu_cfg.match(line).group(0).replace('[', '')
                line = line.replace(']', '')
                line = line.replace(' ','')
                iu_name, iu_code = line.split(',')
                # add prev iu read from def file to iu dict if prev
                # iu exists
                if flag_add_iu_to_dict is True and this_iu is not None:
                    def_iu_dict[this_iu.iu_code] = this_iu
                    flag_add_iu_to_dict =  False
                this_iu = IU.DefIU(iu_name, iu_code)
                del iu_name, iu_code
                flag_add_iu_to_dict = True
                continue
            except:
                # line is not a header in def file, it can be a line
                # that stores iu info, check if the line is a "register
                # address", "bit position" or "bit description" and store
                # the info in proper field for this iu
                pass
            if 'reg_address=' in line or 'reg_addr=' in line:
                dummy, this_reg_addr = line.split('=')
                this_iu.add_reg(this_reg_addr)
            elif '.pos=' in line:
                front, bit_pos = line.split('=')
                bit_name, dummy = front.split('.')
                bit_name = (bit_name.replace('_', ' ')).title()
            elif '.des=' in line:
                dummy, bit_des = line.split('=')
                this_iu.add_bit_des(this_reg_addr, bit_pos, bit_name, bit_des)

        # check if prev iu exists once again, after the whole file is read
        # otherwise last iu in def file cannot be added to iu dict
        if flag_add_iu_to_dict is True and this_iu is not None:
            def_iu_dict[this_iu.iu_code] = this_iu
            del this_iu
            flag_add_iu_to_dict = False

        # print out all ius in iu dict if verbose is enabled
        if verbose is True:
            print tag + 'def_list after read the def file'
            for iu_idx in def_iu_dict.keys():
                iu = def_iu_dict[iu_idx]
                print 'IU name: ' + iu.iu_name
                print 'IU code: ', iu.iu_code
                if iu.has_reg is True:
                    for reg_addr, reg in iu.reg_dict.iteritems():
                        print reg.reg_address
                        print reg.reg_name
                        if reg.has_bit_des is True:
                            for bit_pos in reg.bit_dict.keys():
                                bit_name, bit_des = reg.bit_dict[bit_pos]
                                print bit_pos + ' ' + bit_name
                                print bit_des
        return def_iu_dict
    @classmethod
    def special_handler_admin_iu_func_code_0x00(cls, iu):
        # register that contains "Sgl Desc Type" bit field 
        # in admin IU func code document
        sgl_des_reg_addr = 0x3c
        try:
            # try to find SGL des register in an admin iu 
            # with function code 0x3c
            reg = iu.reg_dict[sgl_des_reg_addr]
            if reg.has_bit_des is True:
                for bit_pos in reg.bit_dict:
                    bit_name, bit_val, bit_meaning = reg.bit_dict[bit_pos]
                    if 'When set to logic:' in bit_meaning \
                    and 'SGL type is' in bit_meaning:
                        bit_meaning = 'Reserved'
                        reg.bit_dict[bit_pos] = [bit_name, bit_val, bit_meaning]
                        break
        except KeyError:
            print 'special_handler_admin_iu_func_code_0x00: Warning, register 0x{:02x} not found'.format(sgl_des_reg_addr)

    @classmethod
    def special_reg_list_handler_spanning_iu(cls, tag, start_addr, addr_offset, crash_dump_reg_list, verbose=False):
        reg_addr_val_for_this_iu = []
        flag_start_list = False
        iu_buf_size = cls.IU_BUF_SIZE
        # only IU_SIZE number of register per IU buffer are 
        # currently in use in spanning case
        useful_regs_per_iu_buf = cls.IU_SIZE / cls.BYTE_PER_REG
        common_iu_header_length_in_byte = cls.IU_COMMON_HEADER_SIZE
        idx = 0
        # loop through crash dump list and find out 
        # the registers belong to this spanning iu
        # the result is saved in reg_addr_val_for_this_iu
        while idx < len(crash_dump_reg_list):
            reg_addr, reg_val = crash_dump_reg_list[idx]
            reg_addr -= addr_offset
            if reg_addr == start_addr:
                flag_start_list = True
                total_length = ut.bit_shift(reg_val, '31:16')[0] + common_iu_header_length_in_byte
            if flag_start_list is True:
                # useful_reg_idx_offset defines offset for
                # registers actually used in an IU buffer
                # the rest of registers in IU buffer are not
                # used by spanning iu
                for useful_reg_idx_offset in range(useful_regs_per_iu_buf):
                    reg_addr, reg_val = crash_dump_reg_list[idx + useful_reg_idx_offset]
                    reg_addr -= addr_offset
                    reg_addr_val_for_this_iu.append([reg_addr, reg_val])
                idx += iu_buf_size/cls.BYTE_PER_REG
                # substract used IU buffer space from total length
                total_length -= useful_regs_per_iu_buf * cls.BYTE_PER_REG
                # all spanning elements are stored in reg_addr_val_for_this_iu once 
                # total_length hits 0
                if total_length <= 0:
                    break
            else:
                idx += 1
        if verbose is True:
            print tag + ' reg_addr_val_for_this_iu:'
            for reg_addr_debug, reg_val_debug in reg_addr_val_for_this_iu:
                print '{:08x}'.format(reg_addr_debug) + ':{:08x}'.format(reg_val_debug)
        return reg_addr_val_for_this_iu


    @classmethod
    def get_reg_meaning(cls, tag, crash_dump_reg_list, addr_offset, def_iu_dict, admin_func_code_dict, verbose=False):
        tag, tag_next_level = ut.get_debug_tags(tag, cls.MODULE, cls.SECTION, 'get_reg_meaning')
        iu_size = cls.IU_SIZE
        iu_buf_size = cls.IU_BUF_SIZE
        iu_count = cls.IU_BUF_NUM
        # Currently, only iu_size(128 bytes) of space is actually used in 
        # each buffer for iu(124 bytes excluding common header).
        # Remove iu_spanning_threshold once spanning is fixed in log 
        # and spanning uses the full iu_buf_size.
        iu_spanning_threshold = iu_size - cls.IU_COMMON_HEADER_SIZE

        decoded_iu_list = []
        list_of_ius = []
        reg_addr_val_for_this_iu = []
        count = 0
        start_addr = count * iu_buf_size
        end_addr = 0xffffffff
        # Last address belongs to current iu
        last_addr_for_curr_iu = (count + 1) * iu_buf_size - cls.BYTE_PER_REG
        flag_start_list = False
        for reg_addr, reg_val in crash_dump_reg_list:
            # Substract offset for easy debugging
            reg_addr = reg_addr - addr_offset
            if reg_addr == start_addr and reg_val == 0:
                start_addr += iu_buf_size
                continue
            elif reg_addr == start_addr:
                length = ut.bit_shift(reg_val, '31:16')[0]
                # Rewrite this if statement once spanning is fixed in log and uses the full buffer size
                if length > iu_spanning_threshold:
                    list_of_ius.append(cls.special_reg_list_handler_spanning_iu(tag_next_level, start_addr, addr_offset, crash_dump_reg_list))
                    # Spanning can take more than one iu buffer,
                    # so end_addr for this iu is calculated as follows.
                    # Note that once spanning is fixed in log, we should divide
                    # by iu_buf_size instead of iu_size
                    end_addr = ((length - iu_spanning_threshold) / iu_size) * iu_buf_size
                    if (length - iu_spanning_threshold) % iu_size > 0:
                        end_addr += iu_buf_size
                    # Now update start_addr for next iu based on end_addr for this iu
                    start_addr = end_addr + cls.BYTE_PER_REG
                    continue
                else:    
                    flag_start_list = True
                    end_addr = start_addr + length
                    reg_addr_val_for_this_iu = []
            elif reg_addr == end_addr:
                reg_addr_val_for_this_iu.append([reg_addr, reg_val])
                flag_start_list = False
                # spanning
                if end_addr - start_addr > iu_size:
                    start_addr = end_addr + cls.BYTE_PER_REG
                    start_addr += (iu_size - (start_addr % iu_size))
                # not spanning
                else:
                    start_addr += iu_size
                if verbose is True:
                    print tag + 'iu num ', count
                    for reg_addr_debug, reg_val_debug in reg_addr_val_for_this_iu:
                        print '{:08x}'.format(reg_addr_debug) + ':{:08x}'.format(reg_val_debug)
                #decoded_iu_list.append(cls.get_this_iu_meaning(tag_next_level, reg_addr_val_for_this_iu, def_iu_dict, admin_func_code_dict))
                list_of_ius.append(reg_addr_val_for_this_iu)
                reg_addr_val_for_this_iu = []               
            if flag_start_list is True:
                reg_addr_val_for_this_iu.append([reg_addr, reg_val])
            
            if reg_addr == last_addr_for_curr_iu:
                decoded_this_iu = []
                for iu_reg_list in list_of_ius:
                    decoded_this_iu.append(cls.get_this_iu_meaning(tag_next_level, iu_reg_list, def_iu_dict, admin_func_code_dict))

                decoded_iu_list.extend(decoded_this_iu)
                list_of_ius = []
                count += 1
                start_addr = count * iu_buf_size
                last_addr_for_curr_iu = (count + 1) * iu_buf_size - cls.BYTE_PER_REG
            if count > iu_count:
                break
        return decoded_iu_list

    @classmethod 
    def get_this_iu_meaning(cls, tag, reg_list_for_iu, def_iu_dict, admin_func_code_dict):
        ''' Decode this iu based on IU code.
            If IU code not belongs to any of the Admin, AIO or RS IU, then return IU without decoding.
        '''
        tag, tag_next_level = ut.get_debug_tags(tag, cls.MODULE, cls.SECTION, 'explain_this_iu')
        if not reg_list_for_iu:
            return []
        first_reg_val = reg_list_for_iu[0][1]
        iu_code = ut.bit_shift(first_reg_val, '7:0')[0]
        iu_length = ut.bit_shift(first_reg_val, '32:16')[0]

        if iu_code in cls.AIO_IU_LIST:
            return cls.decode_aio_iu(tag_next_level, iu_code, iu_length, reg_list_for_iu, def_iu_dict)
        elif iu_code in cls.RS_IU_LIST:
            return cls.decode_rs_iu(tag_next_level, iu_code, iu_length, reg_list_for_iu, def_iu_dict)
        elif iu_code in cls.ADMIN_IU_LIST:
            return cls.decode_admin_iu(tag_next_level, iu_code, iu_length, reg_list_for_iu, def_iu_dict, admin_func_code_dict)
        else:
            return cls.decode_normal_iu(tag_next_level, iu_code, iu_length, reg_list_for_iu, def_iu_dict)
    
    @classmethod
    def decode_normal_iu(cls, tag, iu_code, iu_length, reg_list_for_iu, def_iu_dict):
        tag, tag_next_level = ut.get_debug_tags(tag, cls.MODULE, cls.SECTION, 'decode_normal_iu')
        first_reg_addr = reg_list_for_iu[0][0]
        if iu_code in def_iu_dict:
            this_iu = def_iu_dict[iu_code]
            decoded_reg_dict = {}
            for reg_addr, reg_val in reg_list_for_iu:
                # use first reg addr as offset when looking for the def from iu_dict,
                # because reg addr in iu dict always starts from 0
                iu_def_reg = this_iu.get_reg(reg_addr - first_reg_addr)
                if iu_def_reg is not None:
                    #decoded_reg = IU.DecodedReg(reg_addr, 'N/A', reg_val)
                    if iu_def_reg.has_bit_des is True:
                        # only add reg if it has bit des
                        decoded_reg = IU.DecodedReg(reg_addr, 'N/A', reg_val)
                        for bit_pos in iu_def_reg.bit_dict.keys():
                            bit_name, raw_bit_meaning = iu_def_reg.bit_dict[bit_pos]
                            bit_val, bit_val_str = ut.bit_shift(reg_val, bit_pos)
                            bit_meaning = raw_bit_meaning
                            if cls.re_logic.search(bit_meaning) is not None:
                                bit_meaning = ut.handle_logic_token(bit_val_str, bit_meaning)
                            if cls.re_hex_token.search(bit_meaning) is not None:
                                hex_digit = len(bit_val_str) >> 2
                                if (len(bit_val_str) % 4) != 0:
                                    hex_digit += 1
                                hex_format = ''.join(['0x{:0', str(hex_digit), 'x}'])
                                bit_meaning = cls.re_hex_token.sub(hex_format.format(bit_val), bit_meaning)
                            bit_meaning = cls.re_dec_token.sub(str(bit_val), bit_meaning)
                            decoded_reg.add_bit_des(bit_pos, bit_name, bit_val_str, bit_meaning)
                        decoded_reg_dict[decoded_reg.reg_address] = decoded_reg
            ut.handle_parse_math_token(tag_next_level, decoded_reg_dict)
            # after decoding all meanings for this iu, create a new decoded iu object and return it
            return IU.DecodedIU(this_iu.iu_name, iu_code, iu_length, reg_list_for_iu, decoded_reg_dict)
        else:
            # iu_code is not in iu_dict, return as an unknown iu
            return IU.DecodedIU(cls.UNDEFINED_CODE, iu_code, iu_length, reg_list_for_iu, None)
    
    @classmethod
    def decode_admin_iu(cls, tag, iu_code, iu_length, reg_list_for_iu, def_iu_dict, admin_func_code_dict):
        ''' Admin iu does not have SGL, but has different function code. 
            Decode according to IU code and Function code
        '''
        tag, tag_next_level = ut.get_debug_tags(tag, cls.MODULE, cls.SECTION, 'decode_admin_iu')
        decoded_iu = cls.decode_normal_iu(tag_next_level, iu_code, iu_length, reg_list_for_iu, def_iu_dict)
        # the function code is stored at 3rd 32-bit field, position '23:16'
        if len(reg_list_for_iu) >= 3:
            func_code_val = reg_list_for_iu[2][1]
            func_code = ut.bit_shift(func_code_val, '23:16')[0]
            iu_func_part = cls.decode_normal_iu(tag_next_level, func_code, iu_length, reg_list_for_iu, admin_func_code_dict)
            # this special function code contains a bit meaning that can not easily
            # handled by common decoding function, use a special function to
            # decode it
            if func_code == 0x00:
                cls.special_handler_admin_iu_func_code_0x00(iu_func_part)
            # update decoded iu dict and iu name with function code
            decoded_iu.reg_dict.update(iu_func_part.reg_dict)
            decoded_iu.iu_name = ''.join([decoded_iu.iu_name, '_', iu_func_part.iu_name])
        return decoded_iu

    @classmethod
    def decode_aio_iu(cls, tag, iu_code, iu_length, reg_list_for_iu, def_iu_dict):
        tag, tag_next_level = ut.get_debug_tags(tag, cls.MODULE, cls.SECTION, 'decode_aio_iu')
        decoded_iu = cls.decode_normal_iu(tag_next_level, iu_code, iu_length, reg_list_for_iu, def_iu_dict)
        if iu_code in cls.IU_WITH_SGL_LIST:
            common_header_size_in_byte = cls.IU_COMMON_HEADER_SIZE
            total_header_size_in_byte = cls.AIO_IU_TOTAL_HEADER_SIZE
            print tag + 'IU ' + hex(iu_code) + ' has SGL'
            # iu_length does not include common header, add it and then substract total header size
            # to get sgl size
            sgl_length_in_byte = iu_length + common_header_size_in_byte - total_header_size_in_byte
            print tag + 'SGL length in byte is ', sgl_length_in_byte
            decoded_iu = cls.decode_iu_sgl(tag_next_level, decoded_iu, reg_list_for_iu, sgl_length_in_byte, total_header_size_in_byte)
        return decoded_iu

    @classmethod
    def decode_rs_iu(cls, tag, iu_code, iu_length, reg_list_for_iu, def_iu_dict):
        tag, tag_next_level = ut.get_debug_tags(tag, cls.MODULE, cls.SECTION, 'decode_rs_iu')
        decoded_iu = cls.decode_normal_iu(tag_next_level, iu_code, iu_length, reg_list_for_iu, def_iu_dict)
        if iu_code in cls.IU_WITH_SGL_LIST:
            # refer to [DOC] and [DOC]
            if iu_code == cls.RS_REPORT_GEN_IU_CODE:
                total_header_size_in_byte = cls.RS_REPORT_GEN_IU_TOTAL_HEADER_SIZE
            elif iu_code == cls.RS_SCSI_CMD_VENDOR_REQ_IU_CODE:
                total_header_size_in_byte = cls.RS_SCSI_CMD_VENDOR_REQ_IU_TOTAL_HEADER_SIZE
            else:
                total_header_size_in_byte = cls.RS_IU_TOTAL_HEADER_SIZE
            common_header_size_in_byte = cls.IU_COMMON_HEADER_SIZE
            print tag + 'IU ' + hex(iu_code) + ' has SGL'
            # iu_length does not include common header, add it and then substract total header size
            # to get sgl size
            sgl_length_in_byte = iu_length + common_header_size_in_byte - total_header_size_in_byte
            print tag + 'SGL length in byte is ', sgl_length_in_byte
            decoded_iu = cls.decode_iu_sgl(tag_next_level, decoded_iu, reg_list_for_iu, sgl_length_in_byte, total_header_size_in_byte)
        return decoded_iu
    @classmethod
    def decode_iu_sgl(cls, tag, decoded_iu, reg_list_for_iu, sgl_length_in_byte, offset_in_byte):
        tag = ut.get_debug_tags(tag, cls.MODULE, cls.SECTION, 'decode_iu_sgl')[0]
        single_sgl_in_byte = cls.SGL_SIZE
        offset = offset_in_byte /  cls.BYTE_PER_REG
        reg_per_sgl = cls.SGL_SIZE/cls.BYTE_PER_REG
        if sgl_length_in_byte < single_sgl_in_byte or \
        len(reg_list_for_iu)*cls.BYTE_PER_REG < (offset_in_byte + sgl_length_in_byte):
            print tag + 'Warning, SGL len in byte is {}, reg list len in byte for SGL is {}'\
            .format(sgl_length_in_byte, len(reg_list_for_iu)*cls.BYTE_PER_REG - offset_in_byte)
            #return decoded_iu
        idx = 0
        # loop through list of registers for this iu and save
        # all SGLs for this IU to decoded iu 
        while (offset + idx + reg_per_sgl - 1) < len(reg_list_for_iu):
            sgl_des_addr_lo = reg_list_for_iu[offset + idx][1]
            sgl_des_addr_hi = reg_list_for_iu[offset + idx + 1][1]
            sgl_des_len = reg_list_for_iu[offset + idx + 2][1]
            sgl_des_ctrl = reg_list_for_iu[offset + idx + 3][1]
            #print tag + '{:08x} {:08x} {} {:08x} '.format(sgl_des_addr_lo, sgl_des_addr_hi, sgl_des_len, sgl_des_ctrl)
            decoded_iu.add_sgl(sgl_des_addr_lo, sgl_des_addr_hi, sgl_des_len, sgl_des_ctrl)
            sgl_length_in_byte -= single_sgl_in_byte
            if sgl_length_in_byte < single_sgl_in_byte:
                break
            idx += reg_per_sgl
        return decoded_iu

    @classmethod
    def save_decoded_iu_to_html_iu_table(cls, iu, fd, debug=False):
        ''' Save decoded iu to html table similar to the table in IU document
            @param iu: decoded IU
            @param fd: file descriptor to which the result to be saved
            @param debug: if True, then additional log will be printed
            @output: fd will have the iu table after this function is called
            @note:
            1. This function write one IU per function call.
            2. The assumption is that each row in table is 8-bit,
               AND bit position for a single bit description does not cross 8-bit boundary
               if the length of bit position only occupies two rows.
               Otherwise result cannot be properly displayed.
               Example of valid bit position:
                 a.pos=5:2   -> with in one 8-bit cell(cell for bit 0-7)
                 a.pos=12:10 -> with in one 8-bit cell(cell for bit 15-8)
                    7 6 5 4 3 2 1 0
                  0
                  1       t t t
                  2
                  3
                 a.pos=15:8  -> with in one 8-bit cell(cell for bit 15-8)
                    7 6 5 4 3 2 1 0
                  0
                  1 t t t t t t t t
                  2
                  3
                 a.pos=23:0  -> cross 8-bit boundary, in three 8-bit cell
                 (cell for bit 24-16, 15-8, 7-0)
                    7 6 5 4 3 2 1 0
                  0 t t t t t t t t
                  1 t t t t t t t t
                  2 t t t t t t t t
                  3
                 special.pos=26:6  -> cross 8-bit boundary, both lower and upper bounds
                 are not a multiple of 8, but have at least one completed row,
                 displayed as:
                    7 6 5 4 3 2 1 0
                  0 * *
                  1 t t t t t t t t
                  2           * * *
                  3
                  where "t" means "text for special", and "*" on row 0 is
                  "See next cell for details.";
                  "*" on row 2 is "See previous cell for details.".
               Example of NOT valid bit position:
                 bad.pos=12:7 -> cross 8-bit boundary, both lower and upper bounds are not
                 a multiple of 8, and does not have a completed row. This will cause problem.
        '''
        # max bit per row, do not change this number
        # otherwise this function may broken
        # currently 8 and 16 works
        max_bit_per_row = 8
        # max bit per reg, do not change this number
        # otherwise this function may broken
        max_bit_per_reg = 32

        fd.write('<h3 align="center" style="color:green">%s</h3>\n' %(iu.iu_name))
        if iu.reg_dict is None:
            return
        # we have max_bit_per_row + 1 cells(an additional cell for "Byte\Bit") in table
        # so each cell occupies the following percentage of space in a row
        percent_bit = 100/(max_bit_per_row + 1)
        # most of the time, 100.0/(max_bit_per_row + 1) is not an integer,
        # should the number greater than 0.5 in its decimal part,
        # add 1 more percentage to the result
        if 100.0/(max_bit_per_row + 1) > (percent_bit + 0.5):
            percent_bit += 1
        percent_title = 100 - percent_bit*max_bit_per_row
        str_table_hdr = '''        <thead>
            <tr>
                <th width="{}%">Byte\Bit</th>'''.format(percent_title)
        for i in range(max_bit_per_row):
            str_table_hdr = ''.join([str_table_hdr, '\n                <th width="{}%">{}</th>'\
            .format(percent_bit, max_bit_per_row - 1 - i)])
        str_table_hdr = ''.join([str_table_hdr, '\n            </tr>\n'])
        fd.write('    <table class="table table-bordered">\n')
        fd.write(str_table_hdr)
        fd.write('        </thead>\n        <tbody>\n')

        # how many rows per reg
        num_of_row = max_bit_per_reg/max_bit_per_row

        sorted_reg_list = sorted(iu.reg_dict.iterkeys())
        # normalize reg address based on first reg address
        norm_last_reg_addr = sorted_reg_list[-1] - sorted_reg_list[0]
        # divide by 4 since 4 byte per reg
        iter_count = norm_last_reg_addr >> 2

        idx = 0
        row_count = 0
        if debug is True:
            print "itercount ", iter_count
        while idx <= iter_count:
            reg_addr = sorted_reg_list[0] + (idx << 2)
            try:
                # try find the reg in DefIU's reg dict
                # and save the meaning for each bit field
                # in that reg
                reg = iu.reg_dict[reg_addr]
                if reg.has_bit_des is True:
                    expected_bit_pos = 0
                    new_bit_list = []
                    for bit_pos in reg.bit_dict.keys():
                        if ':' in bit_pos:
                            hi, low = bit_pos.split(':')
                            hi = int(hi)
                            low = int(low)
                        else:
                            low = int(bit_pos)
                            hi = low
                        # if low bit not match expected bit,
                        # gap in between will be filled with dummy
                        # bit field, so we can display the result
                        # in a proper format
                        if expected_bit_pos < low:
                            # case 1: 1 bit gap between low bit and expected bit
                            if expected_bit_pos == low - 1:
                                add_bit_pos = str(expected_bit_pos)
                                new_bit_list.append([add_bit_pos, '', '0', ''])
                            # case 2: more than 1 bit gap between low bit and expected bit
                            else:
                                # case 2.1: the bit gap does not exceed max_bit_per_row boundary
                                # simply fill the bit gap with dummy staff
                                if (low - 1)/max_bit_per_row == expected_bit_pos/max_bit_per_row:
                                    add_bit_pos = str(low - 1) + ':' + str(expected_bit_pos)
                                    new_bit_list.append([add_bit_pos, '', '0', ''])
                                # case 2.1: the bit gap does not exceed max_bit_per_row boundary
                                # regonize the bit gap boundary first, and then fill the bit 
                                # gap with dummy staff. Otherwise result cannot be displayed properly
                                else:
                                    # boundary is stored in tmp_bit_pos
                                    tmp_bit_pos = (expected_bit_pos/max_bit_per_row) * max_bit_per_row + max_bit_per_row
                                    # fill the first half of bit gap in last row
                                    add_bit_pos = str(tmp_bit_pos - 1) + ':' + str(expected_bit_pos)
                                    new_bit_list.append([add_bit_pos, '', '0', ''])
                                    # then fill the second half of bit gap in current row
                                    add_bit_pos = str(low - 1) + ':' + str(tmp_bit_pos)
                                    new_bit_list.append([add_bit_pos, '', '0', ''])
                        # after bit gap between expected_bit_pos and low bit
                        # is filled, we can update expected_bit_pos to next bit after
                        # high bit position, because between low and high bit are meaning
                        # for current bit field
                        expected_bit_pos = hi + 1
                        bit_name, bit_val, bit_meaning = reg.bit_dict[bit_pos]
                        new_bit_list.append([bit_pos, bit_name, bit_val, bit_meaning])
                    # once we loop over all bit fields, if expected_bit_pos is still
                    # less than max_bit_per_reg, then fill the remaing bits with dummy staff
                    # so we can properly display the result
                    if expected_bit_pos < max_bit_per_reg:
                        add_bit_pos = str(max_bit_per_reg - 1) + ':' + str(expected_bit_pos)
                        new_bit_list.append([add_bit_pos, '', '0', ''])
                    write_bit_list = []
                    # now all bit fields are properly handled, start prepare
                    # the list of things to be written to the result file
                    for bit_pos, bit_name, bit_val, bit_meaning in new_bit_list:
                        flag_append_high_bit = False
                        # by default, assume bit_pos is for single bit,
                        # so it takes 1 col in a row
                        row_span = 1
                        col_span = 1
                        if ':' in bit_pos:
                            hi, low = bit_pos.split(':')
                            hi = int(hi)
                            low = int(low)
                            total_bit = hi - low
                            # divide by max_bit_per_row, add one as bit starts from 0
                            row_span = (total_bit/max_bit_per_row) + 1
                            if row_span > 1:
                                low_div_remain = low % max_bit_per_row
                                hi_div_remain = hi % max_bit_per_row
                                if low_div_remain == 0 and \
                                hi_div_remain == (max_bit_per_row - 1):
                                    col_span = max_bit_per_row
                                else:
                                    if low_div_remain > 0:
                                        col_span = low/max_bit_per_row + max_bit_per_row - low_div_remain
                                        str_write = '    <td rowspan="%d" colspan="%d"><p><b>%s:</b> See next cell for details.</p></td>\n' % \
                                        (1, col_span, bit_name)
                                        # meaning for cell in low bit_pos, if bit_pos exceeds row boundary
                                        write_bit_list.append([1, col_span, low, str_write])
                                        row_span -= 1
                                        col_span = max_bit_per_row
                                        low = low/max_bit_per_row + max_bit_per_row
                                    if hi_div_remain < (max_bit_per_row - 1):
                                        row_span -= 1
                                        col_span = max_bit_per_row
                                        flag_append_high_bit = True
                            else:
                                col_span = total_bit + 1
                        else:
                            low = int(bit_pos)
                            hi = low

                        if row_span >= 1:
                            if bit_name == '':
                                str_write = '    <td rowspan="%d" colspan="%d"><pre>Reserved</pre></td>\n'\
                                %(row_span, col_span)
                            else:
                                bit_val_hex = hex(int(bit_val, 2))
                                bit_val_str = ut.add_mark_to_word(bit_val, '_', 4)
                                str_write = '    <td rowspan="%d" colspan="%d"><p>[%s] [0b_%s]</p><p><b>%s: %s</b></p></td>\n' % \
                                (row_span, col_span, bit_val_hex, bit_val_str, bit_name, bit_meaning)
                            # meaning for cell within row boundary
                            write_bit_list.append([row_span, col_span, low, str_write])
                        if flag_append_high_bit is True:
                            flag_append_high_bit = False
                            # row_span less than one means previously meaning is not 
                            # appended to file, need to save the meaning here
                            if row_span < 1:
                                flag_write_whole_meaning = True
                            # meaning already save as part of previous bit cell
                            else:
                                flag_write_whole_meaning = False
                            row_span = 1
                            col_span = hi_div_remain + 1
                            low = hi - hi_div_remain
                            if flag_write_whole_meaning is True:
                                bit_val_hex = hex(int(bit_val, 2))
                                bit_val_str = ut.add_mark_to_word(bit_val, '_', 4)
                                str_write = '    <td rowspan="%d" colspan="%d"><p>[%s] [0b_%s]</p><p><b>%s: %s</b></p></td>\n' % \
                                (row_span, col_span, bit_val_hex, bit_val_str, bit_name, bit_meaning)
                            else:
                                str_write = '    <td rowspan="%d" colspan="%d"><p><b>%s:</b> See previous cell for details.</p></td>\n' % \
                                (row_span, col_span, bit_name)
                            # meaning for cell in high bit_pos, if bit_pos exceeds row boundary
                            write_bit_list.append([row_span, col_span, low, str_write])

                    if debug is True:
                        for row_span, col_span, low, str_write in write_bit_list:
                            print "rowspan %d colspan %d low %d str %s"\
                            %(row_span, col_span, low, str_write)
                        del row_span, col_span, low, str_write
                    # write result
                    flag_one_row = False
                    prev_row = 0
                    one_row_list = []
                    for row_span, col_span, low, str_write in write_bit_list:
                        curr_row = low/max_bit_per_row
                        # handle meanings occupy less than 1 completed row
                        # from prev_row
                        if prev_row != curr_row and flag_one_row is True:
                            flag_one_row = False
                            # reversed due to the way html table works
                            for stored_str_write in reversed(one_row_list):
                                fd.write(stored_str_write)
                            fd.write('  </tr>\n')
                            del stored_str_write
                            one_row_list = []
                        # case 1: the meaning occupies at least 1 completed row
                        if col_span == max_bit_per_row:
                            # write meaning that expaand the whole line
                            fd.write('  <tr>\n    <td>%d</td>\n' % (row_count))
                            fd.write(str_write)
                            fd.write('  </tr>\n')
                            row_count += 1
                            # case 1.1: the meaning occupies more than 1 completed row
                            # fill the remaining rows
                            if row_span > 1:
                                row_span_stop = row_count + row_span - 1
                                while row_count < row_span_stop:
                                    fd.write('  <tr>\n    <td>%d</td>\n  </tr>\n' % (row_count))
                                    row_count += 1
                                del row_span_stop
                            # case 1.2: the meaning occupies exactly 1 completed row, 
                            # do nothing since the meaning has already been written at the begining

                        # case 2: the meaning occupies less than 1 completed row
                        # set flag_one_row to true and append all menaings belong to this row
                        # to a list, handle the list after we enter next row
                        else:
                            if flag_one_row is False:
                                fd.write('  <tr>\n    <td>%d</td>\n' % (row_count))
                                row_count += 1
                                flag_one_row = True
                            one_row_list.append(str_write)
                        prev_row = curr_row
                    # check meanings occupy less than 1 completed row
                    # from prev_row once again after we leave the loop
                    # for write_bit_list, in case last row consisted of
                    #  meanings occupy less than 1 completed row
                    if flag_one_row is True:
                        flag_one_row = False
                        for stored_str_write in reversed(one_row_list):
                            fd.write(stored_str_write)
                        fd.write('  </tr>\n')
                    del one_row_list, flag_one_row 
            # no bit_pos, fill in with reserved
            except KeyError:
                fd.write('  <tr>\n    <td>%d</td>\n' % (row_count))
                row_count += 1
                
                fd.write('    <td rowspan="%d" colspan="%d"><pre>Reserved</pre></td>\n  </tr>\n' % (num_of_row, max_bit_per_row))
                for inner_loop in range(1, num_of_row):
                    fd.write('  <tr>\n    <td>%d</td>\n  </tr>\n' % (row_count))
                    row_count += 1
            idx += 1
        fd.write('\t</tbody>\n  </table>\n')

        if iu.has_sgl is True:
            fd.write('<p>This IU has SGL:</p>')
            fd.write('    <table class="table table-bordered">\n')
            fd.write('''        <thead>
            <tr>
                <th>Arrtibute</th>
                <th>Value</th>
                </tr>\n''')
            fd.write('        </thead>\n        <tbody>\n')
            count = 0
            for addr_lo, addr_hi, length, ctrl in iu.sgl_list:
                fd.write('    <tr><td colspan="2">SGL {}</td>'.format(count))
                fd.write('    <tr><td>Address Low</td>    <td>0x{:08x}</td></tr>'.format(addr_lo))
                fd.write('    <tr><td>Address High</td>    <td>0x{:08x}</td></tr>'.format(addr_hi))
                fd.write('    <tr><td>Data Length</td>    <td>{} bytes of data at address 0x{:08x}_{:08x}</td></tr>'\
                .format(length, addr_hi, addr_lo))
                fd.write('    <tr><td>Control</td>    <td>0x{:08x}</td></tr>'.format(ctrl))
                count += 1
            fd.write('\t</tbody>\n  </table>\n')

    @classmethod
    def save_decoded_iu_to_html(cls, iu, fd):
        fd.write('<h2 align="center" style="color:green">%s</h2>\n' %(iu.iu_name))
        fd.write('<div class="wrap">\n<div class="element">\n')
        if iu.reg_dict is None:
            return
        for reg_addr in sorted(iu.reg_dict.iterkeys()):
            reg = iu.reg_dict[reg_addr]
            if reg.has_bit_des is True:
                for bit_pos in reg.bit_dict.keys():
                    bit_name, bit_val, bit_meaning = reg.bit_dict[bit_pos]
                    bit_val_hex = hex(int(bit_val, 2))
                    bit_val = add_mark_to_word(bit_val, '_', 4)
                    str_write = '    <p style="font-size:14px;color:#679c3e"><b>%s [%s] %s: %s</b></p>\n' % \
                    (bit_val_hex, bit_val, bit_name, bit_meaning)
                    fd.write(str_write)
        fd.write('</div>\n</div>\n')

    @classmethod
    def save_result(cls, tag, lba_decoded_iu_list, lbb_decoded_iu_list, standalone):
        if standalone is True:
            filename = ut.get_parsed_filename(cls.INPUT_DIR, cls.MODULE, cls.SECTION) + '.html'
            filename = os.path.join(cls.OUTPUT_DIR, filename)
            fd = open(filename, 'w')
            fd.write(mhtml.get_lba_lbb_standalone_header(cls.INPUT_DIR))
        else:
            fd = open(cls.common_out_filename, 'a')
            fd.write(mhtml.get_lba_lbb_group_header())
        
        iu_count = 0
        for this_iu in lba_decoded_iu_list:
            fd.write('<h2 align="center" style="color:orange">LBA Information Unit %d</h2>\n' \
            %(iu_count))
            #ut.reg_dump_to_html_save(this_iu.raw_reg_list, cls.LBA_ADDRESS_OFFSET, 8, fd)
            ut.save_reg_hex_dump_to_html(this_iu.raw_reg_list, cls.LBA_ADDRESS_OFFSET, 4, fd)
            #if this_iu.reg_dict is not None:
                #cls.decoded_reg_dict_to_html_table_save(this_iu.reg_dict, fd, True)
            cls.save_decoded_iu_to_html_iu_table(this_iu, fd)
            iu_count += 1
        iu_count = 0
        for this_iu in lbb_decoded_iu_list:
            fd.write('<h2 align="center" style="color:orange">LBB Information Unit %d</h2>\n' \
            %(iu_count))
            #ut.reg_dump_to_html_save(this_iu.raw_reg_list, cls.LBB_ADDRESS_OFFSET, 8, fd)
            ut.save_reg_hex_dump_to_html(this_iu.raw_reg_list, cls.LBB_ADDRESS_OFFSET, 4, fd)
            #if this_iu.reg_dict is not None:
                #cls.decoded_reg_dict_to_html_table_save(this_iu.reg_dict, fd, True)
            cls.save_decoded_iu_to_html_iu_table(this_iu, fd)
            iu_count += 1

        if standalone is True:
            fd.write(mhtml.get_lba_lbb_standalone_ending())
            fd.close()
            print tag + 'result saved in ' + filename
        else:
            fd.write(mhtml.get_lba_lbb_group_ending())
            fd.close()

    def run(self, standalone=True):
        if standalone is True:
            self.set_input_params()
        tag, tag_next_level = ut.get_debug_tags(None, self.MODULE, self.SECTION, 'run')
        print tag + 'parser starts'
        # LBA section
        lba_crash_dump_reg_list = self.get_reg_val_list(tag_next_level, self.LBA_LOG_HEADER, self.LBA_LOG_ENDING, self.BYTE_PER_REG)
        if not lba_crash_dump_reg_list:
            pass
        else:
            lba_def_iu_dict = self.get_def_iu_dict(tag_next_level, self.LBA_DEFINITION_IU_DIR, self.DEBUG_MODE)
            lba_admin_func_code_dict = self.get_def_iu_dict(tag_next_level, self.LBA_DEFINITION_FUNC_DIR, self.DEBUG_MODE)
            lba_decoded_iu_list = self.get_reg_meaning(tag_next_level, lba_crash_dump_reg_list, self.LBA_ADDRESS_OFFSET, \
            lba_def_iu_dict, lba_admin_func_code_dict, self.DEBUG_MODE)
        
        # LBB section
        lbb_crash_dump_reg_list = self.get_reg_val_list(tag_next_level, self.LBB_LOG_HEADER, self.LBB_LOG_ENDING, self.BYTE_PER_REG)
        if not lbb_crash_dump_reg_list and not lba_crash_dump_reg_list:
            print tag + 'parser ends, no log for this section'
            return False
        elif not lbb_crash_dump_reg_list:
            pass
        else:    
            lbb_def_iu_dict = self.get_def_iu_dict(tag_next_level, self.LBB_DEFINITION_IU_DIR, self.DEBUG_MODE)
            lbb_decoded_iu_list = self.get_reg_meaning(tag_next_level, lbb_crash_dump_reg_list, self.LBB_ADDRESS_OFFSET, \
            lbb_def_iu_dict, None, self.DEBUG_MODE)

        # save both LBA and LBB result
        self.save_result(tag_next_level, lba_decoded_iu_list, lbb_decoded_iu_list, standalone)
        print tag + 'parser ends'
        return True

# if entry point is this script, then run this script independently from other parsers.
if __name__ == '__main__':
    this = LBALBBLog()
    this.run()
