import argparse
import mmap
import multiprocessing as mp
import os
from os import path
from queue import Empty

LOG_FILE = 'results.log'
MAX_WORKERS = 5


class FileFormat:
    def __init__(self, type, magic_numbers, header_size, **kwargs):
        self.type = type
        self.magic_numbers = magic_numbers
        self.header_size = header_size
        self.trailer = kwargs.get('trailer', None)
        self.first_skipped_bytes = kwargs.get('skip', 0)

    def __iter__(self):
        return self.magic_numbers.__iter__()

    def _adjust_starting_offset(self, offset):
        return offset - self.first_skipped_bytes

    def _get_next_offset(self, data_map, offset):
        if self.trailer is not None:
            trailer_offset = data_map.find(self.trailer, offset)
            offset = offset if trailer_offset == -1 else trailer_offset
        return offset if offset == -1 else offset + self.header_size

    def find_next_file(self, data_map):
        for magic_no in self.magic_numbers:
            current_offset = 0
            while current_offset != -1:
                if type(magic_no) is tuple:
                    start_magic, ignore_num, end_magic = magic_no
                    offset, end = search_partial_signature(data_map, current_offset, start_magic, ignore_num, end_magic)
                    next_offset = end
                else:
                    offset = search_basic_signature(data_map, current_offset, magic_no)
                    next_offset = offset

                offset = self._adjust_starting_offset(offset)
                if offset == -1:
                    break
                elif offset > -1:
                    yield offset
                current_offset = self._get_next_offset(data_map, next_offset)


class FileFormatMagicNumber:
    DOCUMENTS = [
        FileFormat('pdf', [b'%PDF-'], 5, trailer=b'%%EOF'),
        FileFormat('cfbf', [b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'], 8),
        FileFormat('doc', [b'\x31\xBE\x00'], 3),
    ]

    ARCHIVES = {
        FileFormat('7z', [b'7z\xBC\xAF\x27\x1C'], 12),
        FileFormat('rar', [b'Rar!\x1a\x07'], 12),
        FileFormat('bz2', [b'BZh'], 6),
        FileFormat('gz', [b'\x1f\x8b\x08'], 6),
        FileFormat('ms_wim', [b'MSWIM\x00\x00\x00'], 16),
        FileFormat('lib_wim', [b'WLPWM\x00\x00\x00'], 16),
        FileFormat('zip', [b'PK\x03\x04'], 8, trailer=b'PK\x05\x06'),
        FileFormat('tar', [b'ustar'], 10)
    }

    GRAPHICS = {
        FileFormat('jpg', [b'\xFF\xD8\xFF\xDB', b'\xFF\xD8\xFF\xE0', b'\xFF\xD8\xFF\xEE', b'\xFF\xD8\xFF\xE1'], 8,
                   trailer=b'\xFF\xD9'),
        FileFormat('png', [b'\x89PNG\x0D\x0A\x1A\x0A'], 8),
        FileFormat('bmp', [b'BM'], 4),
        FileFormat('gif', [b'GIF86a', b'GIF87a', b'GIF89a'], 12),
        FileFormat('tiff', [b'II*\x00', b'MM\x00*'], 8),
        FileFormat('pcx', [b'\x10\x00\x01', b'\x10\x02\x01', b'\x10\x03\x01',
                           b'\x10\x04\x01', b'\x10\x05\x01'], 6),
    }

    MEDIA = [
        FileFormat('mp3', [b'\xFF\xFB', b'\xFF\xF3', b'\xFF\xF2'], 64),
        FileFormat('mp3 with ID3 Tag', [b'ID3'], 64),
        FileFormat('wav', [(b'RIFF', 4, b'WAVE')], 24),
        FileFormat('avi', [(b'RIFF', 4, b'AVI')], 22),
        FileFormat('au', [b'.snd'], 48),
        FileFormat('wma/wmv', [b'\x30\x26\xB2\x75\x8E\x66\xCF\x11\xA6\xD9\x00\xAA\x00\x62\xCE\x6C'], 16),
        FileFormat('mp4', [b'ftypmp42'], 22, skip=4),
        FileFormat('mov', [b'ftyp3gp5', b'ftypqt'], 16, skip=4),
        FileFormat('flv', [b'FLV'], 6),
        FileFormat('mpg', [b'\x00\x00\x01\xB3'], 8),
    ]

    def __init__(self):
        self.all = list()
        self.all.extend(self.get_documents)
        self.all.extend(self.get_graphics)
        self.all.extend(self.get_archives)
        self.all.extend(self.get_media)

    @property
    def get_archives(self):
        return FileFormatMagicNumber.ARCHIVES

    @property
    def get_documents(self):
        return FileFormatMagicNumber.DOCUMENTS

    @property
    def get_graphics(self):
        return FileFormatMagicNumber.GRAPHICS

    @property
    def get_media(self):
        return FileFormatMagicNumber.MEDIA

    @property
    def get_all(self):
        return self.all


def search_basic_signature(file_map, offset, current_magic_number):
    found_offset = file_map.find(current_magic_number, offset)
    return found_offset


def search_partial_signature(file_map, offset, start_magic, ignore_num, end_magic):
    offset_start = file_map.find(start_magic, offset)
    offset_end = file_map.find(end_magic, offset)
    if offset_end - offset_start - len(start_magic) == ignore_num:
        return offset_start, offset_end
    else:
        return -1, -1


def get_file_offsets(fileno, file_format, queue):
    print("\tSearching for", file_format.type)
    file_map = mmap.mmap(fileno, 0, mmap.MAP_SHARED, mmap.ACCESS_READ)

    results = list(sorted([found_offset for found_offset in file_format.find_next_file(file_map)]))

    queue.put((file_format.type, results))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Carve common files from raw binary')
    parser.add_argument('raw_file_path', metavar='raw_file', help='path to the binary file')
    parser.add_argument('--output', default=LOG_FILE, help='file where results will be saved')
    args = parser.parse_args()

    manager = mp.Manager()
    queue = manager.Queue()

    abs_path = path.abspath(args.raw_file_path)
    file = open(abs_path, 'rb')
    fileno = file.fileno()
    os.set_inheritable(fileno, True)

    formats = FileFormatMagicNumber().get_all
    with mp.Pool(MAX_WORKERS) as p:
        p.starmap(get_file_offsets, list(map(
            lambda format: (fileno, format, queue),
            formats
        )))
    file.close()
    p.close()
    p.join()
    print(f"Saving results to {args.output}")
    with open(args.output, 'w') as log:
        log.write(f"Tested file: {abs_path}\n")
        log.write(f"Results:\n\n")
        try:
            while result := queue.get_nowait():
                if len(result[1]) > 0:
                    log.write(f'\t"{result[0]}"\n')
                    log.write(f'\tAt offsets = {", ".join(map(str, result[1]))}\n\n')
        except Empty:
            pass
        log.write("\nTested formats:\n")
        log.write(' '.join(map(lambda format: f'"{format.type}"', formats)))
