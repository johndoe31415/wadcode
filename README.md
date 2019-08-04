# wadcode
wadcode is a WAD Compiler/Decompiler. It is supposed to disassemble WAD files
that provide all the resources for games like Doom into individual files that
can then be edited. Ideally it should be able to recompile those files back
into a WAD to use.

## Usage
To decompile a WAD file into the internal resources:

```
usage: ./wadcode decompile [--no-unpack] [--verbose] [--help]
                           wadfile directory

Decompile a WAD file into its resources

positional arguments:
  wadfile      Input WAD file that is decompiled.
  directory    Input directory in which WAD resources are written.

optional arguments:
  --no-unpack  Do not unpack any inner blobs (e.g., convert images to PNG
               files), extract everything as stored internally.
  --verbose    Increase verbosity. Can be specified multiple times.
  --help       Show this help page.
```

For example:

```
$ ./wadcode decompile DOOM.WAD /tmp/my-doom-wad
```

Then you can easily edit all files in that directory (/tmp/my-doom-wad), and
recompile them afterwards:

```
usage: ./wadcode compile [--verbose] [--help] directory wadfile

Compile a WAD file from resources

positional arguments:
  directory  Input directory that should be compiled to a WAD.
  wadfile    Output WAD file that is created after compilation.

optional arguments:
  --verbose  Increase verbosity. Can be specified multiple times.
  --help     Show this help page.
```

For example:

```
$ ./wadcode compile /tmp/my-doom-wad MODIFIED_DOOM.WAD
```

## Dependencies
wadcode requires the pypng package to be installed.

## License
GNU-GPL 3.
