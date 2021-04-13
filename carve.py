import argparse
from os import path

import numpy as np

MAGIC_NUMBERS = {
    '7z': bytearray([ord('7'), ord('z'), 0xBC, 0xAF, 0x27, 0x1C]),
    'rar': bytearray([ord('R'), ord('a'), ord('r'), ord('!')]),
    'bz2': bytearray([ord('B'), ord('Z'), ord('h')]),
}


def get_file_offsets(data: np.array, start_offset: int, magic_num: bytearray):
    offset_data = data[start_offset:]
    data_size, signature_size = offset_data.size, len(magic_num)

    sequence = np.arange(signature_size)
    sliding_indice_matrix = np.arange(data_size - signature_size + 1)[:, None] + sequence
    matched_sequences = (offset_data[sliding_indice_matrix] == magic_num).all(1)

    if matched_sequences.any() > 0:
        return np.where(np.convolve(matched_sequences, np.ones(signature_size, dtype=np.byte)) > 0)[0][::signature_size] + start_offset
    else:
        return []


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Carve common files from raw binary')
    parser.add_argument('raw_file_path', metavar='raw_file',
                        help='path to the binary file')
    args = parser.parse_args()
    abs_path = path.abspath(args.raw_file_path)
    data = np.fromfile(abs_path, dtype=np.dtype('<B'))
    arch_7z_start = get_file_offsets(data, 0, MAGIC_NUMBERS['7z'])
    arch_rar_start = get_file_offsets(data, 0, MAGIC_NUMBERS['rar'])
    arch_bz2_start = get_file_offsets(data, 0, MAGIC_NUMBERS['bz2'])
    print(arch_rar_start, arch_7z_start)
