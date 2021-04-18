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