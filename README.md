# Carve

Simple magic number based file carver. It should work for coherent files in a raw image.

```
usage: carve.py [-h] [--output OUTPUT] raw_file

Carve common files from raw binary

positional arguments:
  raw_file         path to the binary file

optional arguments:
  -h, --help       show this help message and exit
  --output OUTPUT  file where results will be saved
```

It works in a parallel manner using Python `multiprocessing` pool.

`carve` should recognize signatures from:
- `pdf`,
- `cfbf`,
- `doc`,
- `7z`,
- `rar`,
- `bz2`,
- `gz`,
- `ms_wim`,
- `lib_wim`,
- `zip`,
- `tar`,
- `jpg`,
- `png`,
- `bmp`,
- `gif`,
- `tiff`,
- `pcx`,
- `mp3`,
- `mp3 with ID3 Tag`,
- `wav`,
- `avi`,
- `au`,
- `wma/wmv`,
- `mp4`,
- `mov`,
- `flv`,
- `mpg`.

**Please note, that for some files it might produce a lot of garbage results as it only 
searches for header signature (sometimes for a trailer if it exists).**
For small signatures like `bmp` has, it can produce a lot of false positives.