'''This module is a lib that can be used for log dump.'''
import sys
import os
import argparse
import re
import ntpath
import operator
import itertools
from datetime import datetime
from random import randint
from functools import reduce

MODULE_NAME = 'dutil'
def get_debug_tags(tag_upper_level, module, section, func_name):
    ''' Get data from a input file and split data on line
        @param tag_upper_level: Nullable tag from caller
        @param module: Nullable module name
        @param section: section name
        @param func_name: function name
        @return tuple of [tag, tag_next_level]
    '''
    if tag_upper_level is None:
        upper = ''
    else:
        upper = ''.join([tag_upper_level, ' -> '])
    if section is not None:
        tag = ''.join([upper, 'In ', module, '_', section, '.', func_name, ', '])
        tag_next_level = ''.join([upper, module, '_', section, '.', func_name])
    else:
        tag = ''.join([upper, 'In ', module, '.', func_name, ', '])
        tag_next_level = ''.join([upper, module, '.', func_name])
    return [tag, tag_next_level]

def get_data_from_file(tag, filename):
    ''' Get data from a input file and split data on line
        @param tag: tag from caller, set to None to disable printing in this function
        @param filename: file to read
        @return lines: lines in file splited by '\n'
    '''
    if tag is not None:
        tag = get_debug_tags(tag, MODULE_NAME, None, 'get_data_from_file')[0]
        print(tag + 'input file is ' + filename)
    f_d = open(filename, 'r')
    lines = f_d.read().splitlines()
    f_d.close()
    return lines

def get_filename(path):
    ''' Get filename from file path
        @param path: full file path contains a filename
        @return filename
    '''
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)

def get_timestamp():
    ''' Get the current timestamp
        @return: a str of current timestamp
                 in [year_month_day_hr_min_sec] format
        @note: Example 2017_10_30_15:01:50
    '''
    return datetime.now().strftime('%Y_%m_%d_%H_%M_%S')

def get_parsed_filename(filepath, module, section=None):
    ''' Get output filename based on full filepath to input dump file,
        module name and section name. A timestamp is attached too.
        @param filepath: path to input dump file
        @param module: module name, for example MSGU
        @param section: Optional, section name under module
        @return: filename for the input dump file
    '''
    filename = get_filename(filepath)
    timestamp = get_timestamp()
    decoded = 'decoded_'
    if '.' in filename:
        head = filename.split('.')[0]
    else:
        head = filename
    if section is None:
        return decoded + module + '_' + head + '_' + timestamp
    else:
        return decoded + module + '_' + section + '_' + head + '_' + timestamp

def add_mark_to_word(word, mark, interval, from_left=False):
    ''' Add a given mark to a str at given interval
        @param word: a word in str format
        @param mark: mark to add in str format
        @param interval: between how many chars in word should we add one mark
        @param from_left: optional, begin the replace from left if True
        @return word: word with mark added
        @note: Usually we want to add mark from right,
               e.g., add ',' to time unit. So default is from right
        Example
        add_mark_to_word('01001010', '_', 4), output 0100_1010
        add_mark_to_word('10150986', ',', 3), output 10,150,986
        add_mark_to_word('10150986', ',', 3, True), output 101,509,86
    '''
    flag_is_hex = False
    if re.match('^0[xX]', word) is not None:
        flag_is_hex = True
        word = re.sub('^0[xX]', '', word)
    ''' must save old length and use this
    '''
    word_len = len(word)
    if interval >= word_len:
        if flag_is_hex is True:
            return ''.join(['0x', word])
        else:
            return word
    new_word = ''
    if from_left is True:
        start = 0
        end = interval
        while end < word_len:
            new_word = ''.join([new_word, word[start:end], mark])
            start = end
            end += interval
            if end >= word_len:
                break
        new_word = ''.join([new_word, word[start:end]])
    else:
        end = word_len
        start = end - interval
        while start > 0:
            new_word = ''.join([mark, word[start:end], new_word])
            end = start
            start -= interval
            if start <= 0:
                break
        new_word = ''.join([word[0:end], new_word])
    word = new_word
    if flag_is_hex is True:
        return ''.join(['0x', word])
    else:
        return word

def replace_word_in_line_from_logh(word_list, first_log_word_idx, line_from_log_h):
    ''' Replace 0x%x, %u, %d, %08x etc from a line in from .h file by word in a list
        @param word_list: word list stores word to be replaced
        @param first_log_word_idx: offset in word list, things stored in word_list
                                   before this idx is dummy to this function
        @param line_from_log_h: a line from .h file
        @return line_from_log_h: with 0x%x, %u, %d, %08x etc replaced by word
                                 in word_list
    '''
    need_replace = re.compile('%([ud]{1})|0x0[1-8]x|(0x)?%(0[1-8])?x')
    is_decimal = re.compile('%([ud]{1})')
    # replace %u/d/x one by one, from left to right
    idx = first_log_word_idx
    while idx < len(word_list):
        # Replace %u, %d, %0(x0[1-8])x with [word]
        match_from_left = need_replace.search(line_from_log_h)
        if match_from_left is not None:
            word = match_from_left.group(0)
            if is_decimal.search(word) is not None:
                new_word = str(int(word_list[idx], 16))
            else:
                new_word = '0x' + word_list[idx]
            line_from_log_h = need_replace.sub(new_word, line_from_log_h, 1)
        else:
            break
        idx += 1
    return need_replace.sub('Unknown', line_from_log_h)

def create_def_list_from_logh(tag, filename, definition_prefix, verbose=False):
    ''' Get definition list from a header file
        @param tag: tag from caller
        @param filename: filename to the header file
        @param definition_prefix: prefix to entry in the header file
        @param verbose: optional, print additional log if True
        @return def_list: definition list created from the header file
    '''
    tag, tag_next_level = get_debug_tags(tag, MODULE_NAME, None, 'create_def_list_from_logh')
    print(tag + 'file path is: ' + filename)
    print(tag + 'prefix for definition is: ' + definition_prefix)
    def_list = []
    if verbose is True:
        prefix = re.compile(definition_prefix, re.DEBUG)
    else:
        prefix = re.compile(definition_prefix)
    lines = get_data_from_file(tag_next_level, filename)
    for line in lines:
        if prefix.search(line):
            ''' Trim each line by quotation mark, the assumption is that
                the only useful information is inside quatation mark.
                This is true for *_log.h in Luxor and Wildfire.
            '''
            drop1, useful, drop2 = line.split('\"')
            if verbose:
                print(tag + 'line before: ' + line)
                print(tag + 'line after: ' + useful)
            ''' save the trimmed string in list, index matters.
            '''
            def_list.append(useful)
    if verbose is True:
        print(tag + 'def_list is:')
        print('\n'.join(def_list))
        print(tag + 'end of def_list.')
    return def_list

def get_scsi_code_dict(tag, section, def_file_dir, verbose=False):
    ''' Get defined SCSI code from definition file and save the result to a dict
        @param tag: tag from caller
        @param section: caller's section
        @param def_file_dir
        @param verbose: optional, print additional log if True
        @return scsi_code_dict: dict of SCSI code from def_file_dir,
                key is SCSI code, value is SCSI code name.
    '''
    # SCSI_COMPL_CODE_PREFIX
    prefix = 'SCSI_COMPL_STATUS_'
    tag, tag_next_level = get_debug_tags(tag, None, section, 'get_scsi_code_dict')
    lines = get_data_from_file(tag_next_level, def_file_dir)
    re_scsi_code = re.compile('^(\s*)(' + prefix + ')([A-Z0-9_]+)(\s*)=(\s*)(0[xX])([0-9A-Fa-f]+)(,?)(\s*)$')
    scsi_code_dict = {}
    if verbose is True:
        print(tag)
    for line in lines:
        if re_scsi_code.search(line) is not None:
            if verbose is True:
                print(line)
            line = line.replace(' ', '')
            line = line.replace(',', '')
            scsi_name, scsi_code = line.split('=')
            scsi_code = int(scsi_code, 16)
            scsi_code_dict[scsi_code] = scsi_name
    return scsi_code_dict

def save_line_to_list(tag, header, ending, filename, line_length, debug = True, dump_file = None):
    ''' Save lines that are under a section from log to a list.
        @params tag: tag from caller
        @params header: starting line belongs to this section
        @params ending: last line belongs to this section
        @params filename: path to input file. Not used if dump_file is not None.
        @params line_length: how long an expected line is under this section
        @params debug: Optional debug info
        @params dump_file: Optional opened input file, param filename not used if dump file is given
		@return line_list: list of lines of reg_addr reg_val, can be empty
    '''
    tag, tag_next_level = get_debug_tags(tag, MODULE_NAME, None, 'save_line_to_list')

    # regexp tokens to be removed under the section goes here
    re_token_to_rm_list = []
    # timestamp may appear unexpectly, such as '2017-09-09 12:57:23'
    re_token_to_rm_list.append(re.compile('([0-9]{4})-([0-1]{1}[0-9]{1})-([0-3]{1}[0-9]{1})(\s?)(([0-9]{2}:){2})([0-9]{2})'))

    # RS heartbeat and BC log may appear unexpectly
    re_token_to_rm_list.append(re.compile('Heartbeat wasn\'t running. delta=[0-9]+ seconds'))
    re_token_to_rm_list.append(re.compile('(\(BC:[0-9]+\) )([0-9A-Z]+:).*'))

    line_list = []

    # Get full dump_file so we can search magu fw log from it
    if dump_file is not None:
        print(tag + 'Use dump file from caller, input {} is ignored.'.format(filename))
        lines = dump_file
    else:
        lines = get_data_from_file(tag_next_level, filename)

    # Line number starts from 1(can be set to 0)
    line_num = 1
    print(tag + 'line number starts from:', line_num)

    # flag_process_line is set to 1 within the desired dump file section
    flag_process_line = False

    pre_line = ''

    for line in lines:
        if line == header:
            if flag_process_line is True:
                # empty everything and begin again
                line_list = []
                pre_line = ''
                print(tag + 'Warnning, find 2nd section header [' + header+ '] on line ', \
                line_num, ' before section ending ' + ending)
            else:
                # begining of desired section, set flag_process_line to True
                flag_process_line = True
                print(tag + 'Find section header: ['+ header + '] on line: ', line_num)
            line_num += 1
        elif line == ending:
            if flag_process_line is False:
                if debug:
                    print(tag + 'Warnning, section ending [' + ending + '] appears on line ', \
                    line_num, ' before section header [' + header + '], skip this ending')
                line_num += 1
            else:
                 # ending of desired section, set flag_process_line to False
                flag_process_line = False
                print(tag + 'Find section ending: ['+ ending + '] on line: ', line_num)
                ''' Currently in our dump file, the log is printed out more than one time,
                    but we only have to process the log once. Therefore break after line
                    ending is found. '''
                break
        else:
            line_num += 1

        # bug fix: add the following if statement so the line just before header
        # cannot be added to line_list by accident
        if line == header:
            pre_line = ''
            continue
        # empty line in dump file is ignored, date stamp such as '2017-09-09 12:57:19' is ignored
        if line != '' and line != header and line != ending:

            # remove undesired tokens
            for re_token_rm in re_token_to_rm_list:
                line = re_token_rm.sub('', line)
            # do not use "line.strip()" because whitespace may from last line and can affect line length
            if line == '':
                continue

            # only add a line to line_list if the line belongs to the section defined
            # by header and ending
            if flag_process_line is True:
                #log $verbose '$tag add line: \[$line]'
                if len(line) == line_length:
                    # Case 1: line is a completed line, add it
                    if pre_line != '' and len(pre_line) < line_length \
                    and pre_line != header and pre_line != ending:
                        # Case 1.1: pre_line not added to line_list yet,
                        # but this line is a completed line, add pre_line first,
                        # then add this line
                        print(tag + 'Warning, pre_line ' + pre_line + \
                        ' too short, but current line is a completed line, add pre_line to list with reduced length')
                        line_list.append(pre_line)
                    # Case 1.2: add current line
                    line_list.append(line)
                elif len(line) < line_length:
                    # Case 2: line < completed length
                    if len(pre_line) < line_length and pre_line != header and pre_line != ending:
                        # Case 2.1 : pre_line and line are both not completed, append lines
                        pre_line = ''.join([pre_line, line])
                        if len(pre_line) == line_length:
                            # Case 2.1.1: After appending lines,
                            # pre_line is a completed line, add it to line_list
                            line = pre_line
                            line_list.append(line)
                        elif len(pre_line) > line_length:
                            # Case 2.1.2: After appending lines,
                            # pre_line length is too long, give a warning and add it
                            print(tag + 'Warning, line ' + pre_line + \
                            ' exceeds max length, add it to line_list with longer length')
                            line_list.append(pre_line)
                        else:
                            # Case 2.1.3: After appending lines,
                            # pre_line length too short, set line to pre_line
                            # but do not add it for now
                            line = pre_line
                    # Case 2.2: pre_line is a completed line/exceeds line length/ section header
                    # do nothing
                else:
                    # Case 3: line > completed length, give a warning and add it
                    print(tag + 'Warning, line ' + line + \
                    ' exceeds max length, add it to line_list with longer length')
                    line_list.append(line)
            # move to next line
            pre_line = line
    return line_list

def register_walk(first_reg_addr, byte_per_reg, val_per_reg, endianness, log_word_list_idx, log_word_list):
    ''' Generate a [list] of "regAddr-regValue" pairs from [log_word_list],
	    according to given params
        @param first_reg_addr: a register address
        @param byte_per_reg: how many bytes are stored statring at this register address
        @param val_per_reg: how many value/element from the [log_word_list] is stored in
		                    one register address
        @param endianness: 'little' or 'big'
        @param log_word_list_idx: the assumption is that starting from [log_word_list_idx]
		                          in the [log_word_list], all elements are valid register
                                  value in hex
        @param log_word_list: list of register values(possible also contains other things, 
		                      but the assumption is that starting from [log_word_list_idx], 
							  all elements in the list are valid register value).
        @return: list of "regAddr-regValue" pair, where the first [regAddr] in the
                 list is [first_reg_addr]
    '''
    if endianness != 'big' and endianness != 'little':
        raise AssertionError('In register_walk, expect endianness to be either "big" or "little", but actual endianness is ' + endianness)
    pair_list = []
    reg_addr = first_reg_addr
    if endianness == 'big':
        # big endian
        plus_minus_1 = 1
    else:
        # little endian
        plus_minus_1 = -1
    while log_word_list_idx < len(log_word_list):
        # count starts from 1 because we will first set value before enter "while { $count < $val_per_reg }"
        if plus_minus_1 == 1:
            # big endian
            reg_val_idx_h = log_word_list_idx
        else:
            # little endian
            reg_val_idx_h = log_word_list_idx + val_per_reg - 1
        count = 1
        value = log_word_list[reg_val_idx_h]
        log_word_list_idx += 1
        reg_val_idx_h += plus_minus_1

        while count < val_per_reg:
            # $val_per_reg many values from this line belongs to the current reg addr
            value = ''.join([value, log_word_list[reg_val_idx_h]])
            log_word_list_idx += 1
            count += 1
            reg_val_idx_h += plus_minus_1

            if log_word_list_idx > len(log_word_list):
                print('log_word_list length too short, register value will not be stored starting from register address {}'.format(pair_list[-1]))
                # remove last reg address because we do not have correct value for it
                pair_list.pop()
                return pair_list
        # store value for the addr, remember to trim all whitespace
        value = value.replace(" ", "")
        value_dec = int(value, 16)
        #print(reg_addr +' '+ value)
        pair_list.append([reg_addr, value_dec])
        if log_word_list_idx >= len(log_word_list):
            break
        else:
            # calc next address based on last address, remember the list contains addr-value pair
            # and we have just append a value for last address to the list
            # so in the list, index "end-1" stores last address
            reg_addr = pair_list[-1][0] + byte_per_reg                
    return pair_list

def reg_dump_line_to_addr_val_pair(tag, reg_dump_line, endianness, byte_per_reg, byte_per_val, val_per_line, verbose=False):
    ''' Generate a [list] of "regAddr-regValue" pairs from [log_word_list], according to given params
        @param tag: tag from caller
        @param reg_dump_line: a line of hex code from dump file's register dump
        @param endianness: 'little' or 'big'
        @param byte_per_reg: how many bytes are stored statring at this register address
        @param byte_per_val: how many bytes are stored in one value
        @param val_per_line: how many values on this line
        @param verbose: optional, print additional log if True
        @return: list of "regAddr-regValue" pair, where the first reg_addr in the list is [first_reg_addr]
        @note:
            1. byte_per_reg/byte_per_val must be > 0
            2. Do not try crazy numbers for byte_per_reg byte_per_val that does not make sense, such as byte_per_reg=5
        Example:
        set line "bf6b3100: 0029b1c0 00000002 22222222 12345678 0002004a aaaaaaaa 88888888 99999999 "
        1. reg_dump_line_to_addr_val_pair "example 1" $line 'little' 8 4 8 <- [8] byte per reg, 4 byte per value, 8 values      
            output is: bf6b3100 000000020029b1c0 bf6b3108 1234567822222222 bf6b3110 aaaaaaaa0002004a bf6b3118 9999999988888888  

        2. reg_dump_line_to_addr_val_pair "example 2" $line 'big' 8 4 8 <- [big] endian  
            output is: bf6b3100 0029b1c000000002 bf6b3108 2222222212345678 bf6b3110 0002004aaaaaaaaa bf6b3118 8888888899999999

        3. reg_dump_line_to_addr_val_pair "example 3" $line 'little' 16 4 8 <- [16] byte per reg, 4 byte per value, 8 values
            output is: bf6b3100 1234567822222222000000020029b1c0 bf6b3108 9999999988888888aaaaaaaa0002004a

        4. reg_dump_line_to_addr_val_pair "example 4" $line 'little' 4 4 8 <- [4] byte per reg, 4 byte per value, 8 values 
            output is: bf6b3100 0029b1c0 bf6b3104 00000002 bf6b3108 22222222 bf6b310c 12345678 bf6b3110 0002004a bf6b3114 aaaaaaaa bf6b3118 88888888 bf6b311c 99999999

        set line "bf6b3100: 0029 0030 0000 1111 2222 3333 1234 5678 0002 004a abcd efba aeae eaff cccc ffff " 
        5. reg_dump_line_to_addr_val_pair "example 5" $line 'little' 8 2 16 <- 8 byte per reg, [2] byte per value, 16 values
        output is: bf6b3100 1111000000300029 bf6b3108 5678123433332222 bf6b3110 efbaabcd004a0002 bf6b3118 ffffcccceaffaeae
    '''

    # How many values a register contains
    val_per_reg = int(byte_per_reg/byte_per_val)
    if val_per_reg <= 0:
        raise ValueError(tag + 'val_per_reg/byte_per_val) must > 0')
    # remove whitespace at end of the line
    reg_dump_line = reg_dump_line.rstrip()
    log_word_list = reg_dump_line.split()
    if verbose is True:
        print(tag + 'log_word_list is:')
        print('\n'.join(log_word_list))
        print(tag + 'end of log_word_list.')
    # first value is a reg address
    act_val_per_line = len(log_word_list) -1
    if act_val_per_line != val_per_line:
        print(tag + 'Warning, line ' + reg_dump_line + ' has ', act_val_per_line, 'register values splited by whitespace.')
        print('This line will not be translated.')
        return []

    first_reg_addr = log_word_list[0]
    first_reg_addr = first_reg_addr.replace(':', '')
    try:
        first_reg_addr = int(first_reg_addr, 16)
    except ValueError:
        print(tag + 'Warning, line ' + reg_dump_line + 'first word is not a valid register address')
        print('This line will not be translated.')
        return []
    return register_walk(first_reg_addr, byte_per_reg, val_per_reg, endianness, 1, log_word_list)

def bit_shift(num, position):
    ''' Shift a num to the right by position
        @param num: num to be shifted
        @param position: shift how many position to the right
        @return tuple of [num_aft_shift, num_aft_shift_in_bin_str]
        @example: 
            bit_shift(32, '5:3') output [4, '100'] (32 is 0010_0000)
            bit_shift(32, 5) output [1, '1']
    '''
    mask = 0
    flag_mask = False
    len = 0
    if type(position) is str:
        if ':' in position:
            hi, low = position.split(':')
            hi = int(hi)
            low = int(low)
            len = hi - low + 1
            if hi >= low:
                flag_mask = True
                mask = ~(~0 << (len))
                shift = low
            else:
                raise ValueError('position must be a single number or in "high:low" format')
        else:
            shift = int(position)
    else:
        shift = position
    if shift > 63:
        print('support max 64 bit shift, return the original num')
        return num, format(num, '064b')

    if flag_mask is False:
        num_ret = (num & (1 << shift)) >> (shift)
        return num_ret, format(num_ret, '01b') 
    else:
        # format length of bin(keep leading 0s)
        format_arg = '0{}b'.format(len)
        num_ret = (num >> shift) & mask
        return num_ret, format(num_ret, format_arg)

def handle_logic_token(str_val, raw_meaning):
    ''' Compare str_val and raw_meaning
        @param str_val: str of binary
        @param raw_meaning: str of meaning
        @return matched meaning, or raw_meaning if no match.
        @example:
            str_val is: '01'
            raw_meaning is:
            'When set to logic:
             00: xxx
             01: yyy
             10: zzz
             11: aaa'
            return: 'yyy'
    '''
    re_val = re.compile(''.join([str_val, ':']))
    for line in raw_meaning.splitlines():
        if re_val.match(line) is not None:
            #print("handle logic " + line)
            return re_val.sub('', line)
    return raw_meaning

def handle_parse_math_token(tag, decoded_reg_dict, verbose = False):
    ''' Replace words between @PARSE_MATH_START@ and @PARSE_MATH_END@ token with computed value.
        words in between math token must be a(+-*/)b, where a/b can be a number or a var name
        in bit_position under the same register.
        @param tag: tag from caller
        @param decoded_reg_dict: dict contains all decoded registers
        @param verbose: optional, print out additional log if True
        @return [decoded_reg_dict] with all math token removed
        @example:
            1. @PARSE_MATH_START@IU_LENGTH*256@PARSE_MATH_END@
            2. @PARSE_MATH_START@1024/8@PARSE_MATH_END@
            3. @PARSE_MATH_START@8+10@PARSE_MATH_END@ 
            In 1, if IU_LENGTH is defined somewhere in the input 
            dict, token will be replaced by calculated result.
            In 2 and 3 tokens will be replaced by calculated result.
    '''
    tag, tag_next_level = get_debug_tags(tag, MODULE_NAME, None, 'handle_parse_math_token')
    # python 3 has truediv(/) and floordiv(//), for our purpose floordiv is enough
    # also tested with truediv, up to now using truediv here does not affect result
    # let's keep it simple for now, as we usually only interested in integer operation.
    ops = { '+': operator.add, '-': operator.sub, '*': operator.mul, '/': operator.floordiv }
    re_math_token = re.compile('(@PARSE_MATH_START@)([0-9]+)([\+\-\/\*])([0-9a-zA-Z_\s]+?)(@PARSE_MATH_END@)')
    re_num = re.compile('^[0-9]+$')
    for idx, decoded_reg in decoded_reg_dict.items():
        if decoded_reg.has_bit_des is True:
            for bit_pos in decoded_reg.bit_dict.keys():
                bit_name, bit_val, bit_meaning = decoded_reg.bit_dict[bit_pos]
                match = re_math_token.search(bit_meaning)
                if match is None:
                    continue
                while match is not None:
                    #flag_dirty = True
                    flag_a_is_num = True
                    flag_b_is_num = True
                    if verbose is True:
                        print(tag + "bit_meaning needs math: " + bit_meaning)
                    words = re.findall('(\w+)', match.group(0))
                    if not words:
                        print(tag + match.group(0) + ' has no word')
                        bit_meaning = bit_meaning.replace(match.group(0), 'NO_WORD', 1)
                        match = re_math_token.search(bit_meaning)
                        continue
                    # words are @PARSE_MATH_START@, num1/var1, num2/var2, @PARSE_MATH_END@
                    # so its length must be 4. Otherwise this function cannot work
                    elif len(words) != 4:
                        print(tag + match.group(0) + ' content in math token not valid')
                        print(tag)
                        print(words)
                        bit_meaning = bit_meaning.replace(match.group(0), 'UNDEFINED', 1)
                        print(bit_meaning)
                        match = re_math_token.search(bit_meaning)
                        continue
                    if verbose is True:
                        print(tag + 'words: ')
                        print(words)
                    try:
                        a = int(words[1])
                    except ValueError:
                        a = words[1]
                        if verbose is True:
                            print('a = ' + a + ' is not a num')
                        flag_a_is_num = False
                    try:
                        b = int(words[2])
                    except ValueError:
                        b = words[2]
                        if verbose is True:
                            print('b = ' + b + ' is not a num')
                        flag_b_is_num = False
                    for bit_pos_inner in decoded_reg.bit_dict.keys():
                        bit_name_inner, bit_val_inner, bit_meaning_inner = decoded_reg.bit_dict[bit_pos_inner]
                        if flag_a_is_num is False:
                            if a in bit_name_inner:
                                for word_inner in bit_meaning_inner.split():
                                    nums = re_num.match(word_inner)
                                    if nums is not None:
                                        a = int(nums.group(0))
                                        flag_a_is_num = True
                        if flag_b_is_num is False:
                            if b in bit_name_inner:
                                for word_inner in bit_meaning_inner.split():
                                    nums = re_num.match(word_inner)
                                    if nums is not None:
                                        b = int(nums.group(0))
                                        flag_b_is_num = True
                        if flag_a_is_num is True and flag_b_is_num is True:
                            break
                    if flag_a_is_num is False or flag_b_is_num is False:
                        print(tag + 'cannot find value for a or b:')
                        print(a)
                        print(b)
                        bit_meaning = bit_meaning.replace(match.group(0), 'CAN_NOT_FIND_VALUE', 1)
                    else:
                        opers = re.findall('[\+\-\*\/]', match.group(0))
                        if not opers:
                            print(tag + "no math operator in " + match.group(0))
                            bit_meaning = bit_meaning.replace(match.group(0), 'NO_MATH_OPER', 1)
                        elif len(opers) > 1:
                            print(tag + "too many math operators in " + match.group(0))
                            bit_meaning = bit_meaning.replace(match.group(0), 'TOO_MANY_MATH_OPER', 1)
                        else:
                            if verbose is True:
                                print(tag + 'bfr ' + bit_meaning)
                            bit_meaning = bit_meaning.replace(match.group(0), str(ops[opers[0]](a, b)), 1)
                            if verbose is True:
                                print(tag + 'aft ' + bit_meaning)
                    match = re_math_token.search(bit_meaning)
                decoded_reg.add_bit_des(bit_pos, bit_name, bit_val, bit_meaning)


def save_decoded_reg_dict_to_html_table(reg_dict, fd, debug=False):
    ''' Save content in reg_dict in to a html table
        @param reg_dict: dict contains all decoded registers
        @param fd: file descriptor to which the result to be saved
        @param debug: optional, if True, then no color in bit_position cell
    '''
    fd.write('    <table class="table table-bordered">\n        <thead>\n')
    fd.write('        <tr>\n\t\t\t<th>Reg Addr</th>\n\t\t\t<th>Reg Name</th>\n\t\t\t<th>Reg Value</th>\n\t\t\t<th>Decoding</th>\n')
    fd.write('        </tr>\n        </thead>\n        <tbody>\n')
    if debug is False:
        color_list = ['#86c4f3', '#efbd58', '#97e076', '#e5d899', '#dce0e5']
        last_rand_color_idx = 0

    for reg_addr in sorted(reg_dict.keys()):
        reg = reg_dict[reg_addr]
        reg_val_str = add_mark_to_word('{:016x}'.format(reg.reg_val), '_', 4)
        fd.write('  <tr>\n')
        fd.write('    <td>0x{:06x}</td>\n    <td>{}</td>\n    <td>0x{}</td>\n'.format(reg.reg_address, reg.reg_name, reg_val_str))
        if reg.has_bit_des is True:
            fd.write('    <td>\n')
            for bit_pos in reg.bit_dict.keys():
                if debug is False:
                    rand_color_idx = randint(0, len(color_list) - 1)
                    if  rand_color_idx == last_rand_color_idx:
                        if rand_color_idx == 0:
                            last_rand_color_idx = 1
                        else:
                            last_rand_color_idx = rand_color_idx - 1
                    else:
                        last_rand_color_idx = rand_color_idx
                    bg = ' style="background-color:%s;"' % (color_list[last_rand_color_idx])
                else:
                    bg = ''
                bit_name, bit_val, bit_meaning = reg.bit_dict[bit_pos]
                bit_val = add_mark_to_word(bit_val, '_', 4)
                # e.g. <pre><b>bit[3:0]=[0000] IB_FLB_Q_AP:</b></pre>
                fd.write('        <pre{}><b>bit[{}]=[{}] {}:</b></pre>\n'.format(bg, bit_pos, bit_val, bit_name))
                for line in bit_meaning.splitlines():
                    if line.strip():
                        fd.write('        <pre{}><b>{}</b></pre>\n'.format(bg, line))
            fd.write('    </td>\n')
        fd.write('  </tr>\n')
    fd.write('\t</tbody>\n  </table>\n')


def save_reg_dump_to_html(reg_list, addr_offset, value_per_line, fd):
    ''' Save reg dump to html text center to the page horizontally
        @param reg_list: contains reg_addr, reg_val pairs
        @param addr_offset: register offset to reg_addr in reg_list(if any)
        @param value_per_line: dump how may register value per line
        @param fd: file descriptor to write the result
        @notes: .wrap must defined in html header
    '''
    idx = 0
    total_count = 0
    fd.write('<div class="wrap">\n<div class="element">\n')
    for reg_addr, reg_val in reg_list:
        if idx == 0:
            raw_reg_addr_w = '{:08x}:'.format(reg_addr + addr_offset)
            raw_reg_val_w = ''
        raw_reg_val_w = ''.join([raw_reg_val_w, ' {:08x}'.format(reg_val)])
        idx += 1
        total_count += 1
        if idx == value_per_line or total_count >= len(reg_list):
            str_write = '<p style="font-size:16px;color:#679c3e"><b>' + raw_reg_addr_w + raw_reg_val_w + '</b></p>'
            fd.write(str_write)
            idx = 0
    fd.write('</div>\n</div>\n')

def save_reg_hex_dump_to_html(reg_list, addr_offset, value_per_line, fd):
    ''' Dump register addr-value pair to html with decoded ASCII code
        @param reg_list: contains reg_addr, reg_val pairs
        @param addr_offset: register offset to reg_addr in reg_list(if any)
        @param value_per_line: dump how may register value per line
        @param fd: file descriptor to write the result
        @notes: .wrap must defined in html header
    '''
    idx = 0
    total_count = 0
    fd.write('<div class="wrap">\n<div class="element">\n')
    fd.write('<p align="center" style="font-size:16px;color:#679c3e"><b>Hex Dump</b></p>')
    for reg_addr, reg_val in reg_list:
        if idx == 0:
            raw_reg_addr_w = '{:08x}:'.format(reg_addr + addr_offset)
            raw_reg_val_w = ''
            reg_val_decode = ''
        hex_raw_reg_val = '{:08x}'.format(reg_val)
        raw_reg_val_w = ''.join([raw_reg_val_w, ' ', add_mark_to_word(hex_raw_reg_val, ' ', 2)])
        decoded_hex_val = ''
        # For each char in decoded hex val, if the char
        # can be displayed, then save the char
        # otherwise save "." as char
        for val in bytearray.fromhex(hex_raw_reg_val):
            if val < ord(' ') or val > ord('~'):
                val = ord('.')
            decoded_hex_val = ''.join([decoded_hex_val, chr(val)])
                
        reg_val_decode = ''.join([reg_val_decode, decoded_hex_val])
        idx += 1
        total_count += 1
        # display reg addr, reg val and decoded value in html
        if idx == value_per_line or total_count >= len(reg_list):
            str_write = '<p style="font-size:16px;color:#679c3e"><b>' + raw_reg_addr_w + raw_reg_val_w + '&nbsp&nbsp&nbsp&nbsp' + reg_val_decode + '</b></p>'
            fd.write(str_write)
            idx = 0
    fd.write('</div>\n</div>\n')

def llen(mlist, dim):
    ''' Return length of list in a dimension
        @param list: a multi-dimension list, element in the list might be another list
        @param dim: dimension of list
        @note: only support at most one degree list of list.
    '''
    ret = list(map(lambda e: e[dim], mlist))
    if ret:
        if type(ret[0]) is list:
            return len(reduce(lambda x, y : x + y, ret))
        else:
            return len(ret)
    return 0

def lfjoin(input_filename_list, output_filename):
    ''' Concate large files in order
        @param input_filename_list: list of path to files to be joined
        @output output_filename: path to output files
        @note: caller has to make sure the argvs are valid path to file
    '''
    with open(output_filename, 'w') as outfile:
        for fname in input_filename_list:
            with open(fname) as infile:
                for line in infile:
                    outfile.write(line)

def find_unique_reg(reg_dump_dict):
    unique_reg_addr_set = set()
    max_num = len(reg_dump_dict)
    for base_id in range(max_num):
        if base_id in reg_dump_dict:
            base_reg_dump_list = reg_dump_dict[base_id]
            for curr_id in range(base_id + 1, max_num):
                try:
                    dump_reg_list = reg_dump_dict[curr_id]
                    flag_fast_compare = True
                    if len(dump_reg_list) == len(base_reg_dump_list):
                        # if 2 lists have the same reg dump, only need to cmp values at the same index
                        # O(n)
                        for i in range(len(dump_reg_list)):
                            if dump_reg_list[i][0] == base_reg_dump_list[i][0]:
                                if dump_reg_list[i][1] != base_reg_dump_list[i][1]:
                                    unique_reg_addr_set.add(base_reg_dump_list[i][0])
                            else:
                                print((tag + 'Warning, mismatched register address %d and %d on ID %d and ID %d' \
                                % (dump_reg_list[i][0], base_reg_dump_list[i][0], curr_id, base_id)))
                                flag_fast_compare = False
                                break
                    # fast_compare cannot be used due to a mismatch in [list length]/[reg address at a index],
                    # most likely caused by incompleted dump on one or more PHY(s)
                    # O(n2)
                    if flag_fast_compare is False:
                        # filter gives a list of '[reg_addr, reg_val1], [reg_addr, reg_val2]'
                        # only interested in reg_addr, so either map to reg[0][0] or reg[1][0] 
                        unique_reg_addr_set.update(map(lambda reg: reg[0][0], \
                        filter(lambda x, y : x[0] == y[0] and x[1] != y[1], itertools.product(dump_reg_list, base_reg_dump_list))))
                except KeyError:
                    pass
            del base_reg_dump_list
    return unique_reg_addr_set

class DumpArgvWorker(object):
    ''' Handle argv for register dump.
    '''
    # Path to input dump file
    INPUT_DIR = ''
    # Path to output dir
    OUTPUT_DIR = ''
    # Include dir that contains definition files
    INCLUDE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'include')
    # Enable debugging if set to true
    DEBUG_MODE = False

    @classmethod
    def _set_input_filename(cls, filename):
        ''' Validate and set INPUT_DIR to filename
            @param filename: path to an input file, must exist
        '''
        if os.path.isfile(filename):
            cls.INPUT_DIR = filename
        else:
            print('Error, [{}] is not a valid input file'.format(filename))
            sys.exit(1)

    @classmethod
    def _set_output_dir(cls, in_file, out_dir):
        ''' Validate and set OUTPUT_DIR to out_dir
            @param in_file: path to input file
            @param out_dir: path to output dir
            @note: set OUTPUT_DIR to parent dir of input file
                   if out_dir is None or not valid
        '''
        # must first check if isfile, in case out_dir is a file
        # do NOT check with isdir here, because we may make dir later
        # if the dir not exist 
        if not out_dir or os.path.isfile(out_dir) or not os.path.dirname(out_dir):
            print('Warning, [{}] is not a valid output dirname'.format(out_dir))
            out_dir = os.path.join(os.path.dirname(os.path.abspath(in_file)))
            print('Warning, use default directory [{}] for output'.format(out_dir))
        cls.OUTPUT_DIR = out_dir
        # check if dir exists is necessary in case
        # root for OUTPUT_DIR is read-only
        if not os.path.exists(cls.OUTPUT_DIR):
            os.makedirs(cls.OUTPUT_DIR)

    @classmethod
    def _build(cls):
        ''' Default method to construct argparse arguments
            @note: if a child class need to use its own _build(),
                   then override this _build() and pass its own build()
                   as build_cb to parse() 
        '''
        parser = argparse.ArgumentParser()
        parser.add_argument("-i", "--inFile", help="path to input dump file", required=True)
        parser.add_argument("-o", "--outDir", help="path to output folder for result", default=cls.OUTPUT_DIR)
        parser.add_argument("-d", "--debug", help="enable additional log", dest='debug_mode', action='store_true')
        return parser

    @classmethod
    def parse(cls, build_cb=None):
        ''' Get args from argparse and ensure that all args defined in
            parser are valid
            @param build_cb: if not None, then use build_cb() to construct
                             argparse. Otherwise use default _build()
            @return args parsed by parser
            @note: 
                1. build_cb MUST override _build() 
                2. params defined in _build() are validate and stored after calling
                   this method
        '''
        if build_cb:
            parser = build_cb()
        else:
            parser = cls._build()

        args = parser.parse_args()
        cls._set_input_filename(args.inFile)
        cls._set_output_dir(args.inFile, args.outDir)
        cls.DEBUG_MODE = args.debug_mode

        # return args for additional argv defined 
        # in case build_cb is not None
        return args

class XMLREToken():
    # regular expression for things like 'When set to logic'
    re_logic = re.compile('When([a-zA-Z\s]+)logic:')
    # regular expression token that replace contents with hex in definition files
    re_hex_token = re.compile('@PARSE_REPLACE_VALUE_HEX_START@[a-zA-Z0-9\s_]+@PARSE_REPLACE_VALUE_HEX_END@')
    # regular expression token that replace contents with decimal in definition files 
    re_dec_token = re.compile('@PARSE_REPLACE_VALUE_START@[a-zA-Z0-9\s_]+@PARSE_REPLACE_VALUE_END@')
