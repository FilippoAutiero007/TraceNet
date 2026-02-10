#!/usr/bin/python3

"""
ptexplorer.py: Convert Packet Tracer files (.pkt/.pka) to XML and vice versa

This is a wrapper module that provides a PTFile class interface
for converting between Packet Tracer binary format and XML.

Original ptexplorer by axcheron: https://github.com/axcheron/ptexplorer
Adapted for TraceNet project to provide a class-based interface.
"""

__author__ = 'axcheron (original), TraceNet (wrapper)'
__license__ = 'MIT License'
__version__ = '0.2'

import zlib
from pathlib import Path
from typing import Union


class PTFile:
    """
    Packet Tracer file handler class.
    
    Provides methods to convert between .pkt/.pka binary format and XML.
    """
    
    def __init__(self):
        """Initialize a new PTFile instance."""
        self.xml_content: str = ""
        self.binary_content: bytes = b""
    
    def open(self, filepath: Union[str, Path]) -> None:
        """
        Open a Packet Tracer binary file (.pkt/.pka) and decode to XML.
        
        Args:
            filepath: Path to the .pkt or .pka file
            
        Raises:
            FileNotFoundError: If file doesn't exist
            Exception: If decoding fails
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        with open(filepath, 'rb') as f:
            in_data = bytearray(f.read())
        
        i_size = len(in_data)
        
        out = bytearray()
        # Decrypting each byte with decreasing file length
        for byte in in_data:
            out.append((byte ^ i_size).to_bytes(4, "little")[0])
            i_size = i_size - 1
        
        # The 4 first bytes represent the size of the XML decompressed
        o_size = int.from_bytes(out[:4], byteorder='big')
        
        # Decompress the file without the 4 first bytes
        self.xml_content = zlib.decompress(out[4:]).decode('utf-8')
        
    def open_xml(self, xml_content: str) -> None:
        """
        Load XML content from a string.
        
        Args:
            xml_content: XML string to load
        """
        self.xml_content = xml_content
    
    def export_xml(self) -> str:
        """
        Export the current content as XML string.
        
        Returns:
            XML content as string
            
        Raises:
            ValueError: If no XML content is loaded
        """
        if not self.xml_content:
            raise ValueError("No XML content loaded")
        return self.xml_content
    
    def save(self, filepath: Union[str, Path]) -> None:
        """
        Save the current XML content as a Packet Tracer binary file.
        
        Args:
            filepath: Path where to save the .pkt file
            
        Raises:
            ValueError: If no XML content is loaded
        """
        if not self.xml_content:
            raise ValueError("No XML content loaded to save")
        
        filepath = Path(filepath)
        
        # Convert XML to bytes
        in_data = self.xml_content.encode('utf-8')
        i_size = len(in_data)
        
        # Convert uncompressed size to bytes
        size_bytes = i_size.to_bytes(4, 'big')
        
        # Compress the file and add the uncompressed size
        out_data = zlib.compress(in_data)
        out_data = size_bytes + out_data
        o_size = len(out_data)
        
        xor_out = bytearray()
        # Encrypting each byte with decreasing file length
        for byte in out_data:
            xor_out.append((byte ^ o_size).to_bytes(4, "little")[0])
            o_size = o_size - 1
        
        # Write to file
        with open(filepath, 'wb') as f:
            f.write(xor_out)


def ptfile_decode(infile: Union[str, Path], outfile: Union[str, Path]) -> None:
    """
    Decode a Packet Tracer file to XML.
    
    Args:
        infile: Path to input .pkt/.pka file
        outfile: Path to output XML file
    """
    pt = PTFile()
    pt.open(infile)
    with open(outfile, 'w', encoding='utf-8') as f:
        f.write(pt.export_xml())


def ptfile_encode(infile: Union[str, Path], outfile: Union[str, Path]) -> None:
    """
    Encode an XML file to Packet Tracer format.
    
    Args:
        infile: Path to input XML file
        outfile: Path to output .pkt file
    """
    with open(infile, 'r', encoding='utf-8') as f:
        xml_content = f.read()
    
    pt = PTFile()
    pt.open_xml(xml_content)
    pt.save(outfile)


# Command-line interface (for backward compatibility)
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Convert Packet Tracer files (.pkt/.pka) to XML and vice versa")
    
    group = parser.add_mutually_exclusive_group()
    
    group.add_argument("-d", "--decode", help="Converts Packet Tracer file to XML", action="store_true")
    group.add_argument("-e", "--encode", help="Converts XML to Packet Tracer File", action="store_true")
    parser.add_argument("infile", help="Packet Tracer file", action="store", type=str)
    parser.add_argument("outfile", help="Output file (XML)", action="store", type=str)
    
    args = parser.parse_args()
    
    if args.decode:
        ptfile_decode(args.infile, args.outfile)
        print(f"[*] Successfully decoded {args.infile} to {args.outfile}")
    elif args.encode:
        ptfile_encode(args.infile, args.outfile)
        print(f"[*] Successfully encoded {args.infile} to {args.outfile}")
    else:
        parser.print_help()
        exit(1)
