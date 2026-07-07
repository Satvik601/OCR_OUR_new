"""Object detection and OCR-based segmentation of old newspaper archives.

Pipeline stages (each in its own module, each with a swappable backend):

    preprocessing -> layout -> filtering -> ocr -> export -> evaluation

See ARCHITECTURE.md for data flow and the output JSON schema.
"""

__version__ = "0.1.0"
