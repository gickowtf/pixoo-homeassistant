# _bdf.py
import os
import logging
from typing import Dict, Any, List, Tuple, Optional, Union

_LOGGER = logging.getLogger(__name__)

# Typographical fallback mapping for when a font is missing specific Unicode glyphs
TYPOGRAPHY_FALLBACKS = {
    '’': "'",
    '‘': "'",
    '“': '"',
    '”': '"',
    '—': '-',
    '–': '-',
    '…': '...',
    '→': '->',
    '←': '<-',
    '↑': '^',
    '↓': 'v',
}


def normalize_typography(s: str) -> str:
    """Fallback helper to normalize unicode quotes and dashes when font lacks glyphs."""
    if not isinstance(s, str):
        s = str(s)
    for src, dst in TYPOGRAPHY_FALLBACKS.items():
        s = s.replace(src, dst)
    return s


def load_bdf_font(path: str) -> Optional[Dict[str, Any]]:
    """Parse a BDF (Bitmap Distribution Format) font file into a structured dictionary."""
    if not os.path.exists(path):
        _LOGGER.warning("BDF font file not found: %s", path)
        return None

    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception as e:
        _LOGGER.error("Failed to read BDF font from %s: %s", path, e)
        return None

    properties: Dict[str, Any] = {}
    glyphs: Dict[str, Dict[str, Any]] = {}
    bounding_box = (0, 0, 0, 0)
    global_dwidth = 0
    in_properties = False

    i = 0
    num_lines = len(lines)
    while i < num_lines:
        line = lines[i].strip()

        if line.startswith('FONTBOUNDINGBOX'):
            try:
                parts = [int(p) for p in line.split()[1:]]
                bounding_box = (parts[0], parts[1], parts[2], parts[3])
            except Exception:
                pass

        elif line.startswith('DWIDTH') and not in_properties:
            try:
                global_dwidth = int(line.split()[1])
            except Exception:
                pass

        elif line.startswith('STARTPROPERTIES'):
            in_properties = True

        elif line.startswith('ENDPROPERTIES'):
            in_properties = False

        elif in_properties:
            parts = line.split(None, 1)
            if len(parts) == 2:
                key, val = parts[0], parts[1].strip('"')
                try:
                    properties[key] = int(val)
                except ValueError:
                    properties[key] = val

        elif line.startswith('STARTCHAR'):
            char_name = line[9:].strip() if len(line) > 9 else ""
            encoding = None
            dwidth = global_dwidth or (bounding_box[0] if bounding_box[0] > 0 else 4)
            bbx = (0, 0, 0, 0)
            bitmap: List[str] = []
            i += 1

            while i < num_lines and not lines[i].strip().startswith('ENDCHAR'):
                sub = lines[i].strip()
                if sub.startswith('ENCODING'):
                    try:
                        parts = sub.split()[1:]
                        enc_val = int(parts[0])
                        if enc_val >= 0:
                            encoding = enc_val
                        elif len(parts) > 1 and int(parts[1]) >= 0:
                            encoding = int(parts[1])
                    except Exception:
                        pass
                elif sub.startswith('DWIDTH'):
                    try:
                        dwidth = int(sub.split()[1])
                    except Exception:
                        pass
                elif sub.startswith('BBX'):
                    try:
                        parts = [int(p) for p in sub.split()[1:]]
                        bbx = (parts[0], parts[1], parts[2], parts[3])
                    except Exception:
                        pass
                elif sub == 'BITMAP':
                    i += 1
                    while i < num_lines and not lines[i].strip().startswith('ENDCHAR'):
                        hex_val = lines[i].strip()
                        if hex_val:
                            bit_str = bin(int(hex_val, 16))[2:].zfill(len(hex_val) * 4)
                            bitmap.append(bit_str[:bbx[0]])
                        i += 1
                    break
                i += 1

            char_key = None
            if encoding is not None and encoding >= 0:
                try:
                    char_key = chr(encoding)
                except (ValueError, OverflowError):
                    pass

            if char_key is None and char_name:
                if char_name.startswith("U+") or char_name.startswith("u+"):
                    try:
                        char_key = chr(int(char_name[2:], 16))
                    except Exception:
                        pass
                elif char_name.startswith("uni") and len(char_name) == 7:
                    try:
                        char_key = chr(int(char_name[3:], 16))
                    except Exception:
                        pass
                elif len(char_name) == 1:
                    char_key = char_name

            if char_key is not None:
                glyphs[char_key] = {
                    'width': dwidth,
                    'bbx': bbx,
                    'bitmap': bitmap,
                }

        i += 1

    return {
        'properties': properties,
        'bounding_box': bounding_box,
        'glyphs': glyphs,
    }


class BdfFont:
    """Represents a BDF bitmap font with character metrics and drawing capabilities."""

    def __init__(self, name: str, data: Dict[str, Any], file_path: str = ""):
        self.name = name
        self.file_path = file_path
        self.properties = data.get('properties', {})
        self.bounding_box = data.get('bounding_box', (0, 0, 0, 0))
        self.glyphs = data.get('glyphs', {})

        # Font metrics
        self.ascent = int(self.properties.get('FONT_ASCENT', self.bounding_box[1] or 7))
        self.descent = int(self.properties.get('FONT_DESCENT', abs(self.bounding_box[3]) if self.bounding_box[3] < 0 else 2))
        self.cap_height = int(self.properties.get('CAP_HEIGHT', 0))

        # Baseline offset calculation: distance from top of character bounds to baseline
        if self.cap_height > 0:
            self.baseline_offset = self.cap_height - 1
        elif 'A' in self.glyphs and self.glyphs['A']['bbx'][1] > 0:
            a_bbx = self.glyphs['A']['bbx']
            self.baseline_offset = (a_bbx[1] + a_bbx[3]) - 1
        elif '0' in self.glyphs and self.glyphs['0']['bbx'][1] > 0:
            z_bbx = self.glyphs['0']['bbx']
            self.baseline_offset = (z_bbx[1] + z_bbx[3]) - 1
        else:
            self.baseline_offset = max(0, self.ascent - 1)

        # Line height
        self.line_height = self.ascent + self.descent
        if self.line_height <= 0:
            self.line_height = self.bounding_box[1] if self.bounding_box[1] > 0 else 8

    def supports(self, char: str) -> bool:
        """Check if character is supported by the font directly or via fallback."""
        if char in self.glyphs:
            return True
        if char in TYPOGRAPHY_FALLBACKS and TYPOGRAPHY_FALLBACKS[char] in self.glyphs:
            return True
        return char.upper() in self.glyphs

    def get_glyph_bdf(self, char: str) -> Optional[Dict[str, Any]]:
        """Retrieve raw BDF glyph data, checking font first, then fallback hierarchy."""
        # 1. Exact character match (preserves Unicode curly quotes, dashes, accents)
        if char in self.glyphs:
            return self.glyphs[char]

        # 2. Typography fallback
        if char in TYPOGRAPHY_FALLBACKS and TYPOGRAPHY_FALLBACKS[char] in self.glyphs:
            return self.glyphs[TYPOGRAPHY_FALLBACKS[char]]

        # 3. Uppercase fallback
        if char.upper() in self.glyphs:
            return self.glyphs[char.upper()]

        # 4. Unknown character fallback
        return self.glyphs.get('?')

    def get_char_width(self, char: str) -> int:
        """Get character advance width in pixels."""
        if char == ' ':
            if ' ' in self.glyphs:
                return self.glyphs[' ']['width']
            return 2
        g = self.get_glyph_bdf(char)
        if g is not None:
            return g['width']
        return 3

    def get_text_width(self, text: str) -> int:
        """Calculate total pixel width of text string."""
        if not text:
            return 0
        return sum(self.get_char_width(c) for c in str(text))

    def get_glyph(self, char: str) -> Optional[List[int]]:
        """Backward compatibility: convert BDF glyph into flat bit-matrix list."""
        g = self.get_glyph_bdf(char)
        if g is None:
            return None

        w, h, _, _ = g['bbx']
        if w <= 0 or h <= 0 or not g['bitmap']:
            return [g['width']]

        flat = []
        for row in g['bitmap']:
            for bit in row:
                flat.append(1 if bit == '1' else 0)
        flat.append(w)
        return flat

    def get_line_height(self) -> int:
        return self.line_height

    def draw_character(self, pixoo: Any, character: str, xy: Tuple[int, int], rgb: Tuple[int, int, int]) -> int:
        """Draw a character onto a Pixoo display instance."""
        if character == ' ':
            return self.get_char_width(' ')

        g = self.get_glyph_bdf(character)
        if g is None:
            return self.get_char_width('?')

        w, h, xoff, yoff = g['bbx']
        baseline_y = xy[1] + self.baseline_offset
        top = baseline_y - yoff - h + 1
        left = xy[0] + xoff

        for r_idx, row in enumerate(g['bitmap']):
            for c_idx, bit in enumerate(row):
                if bit == '1':
                    pixoo.draw_pixel((left + c_idx, top + r_idx), rgb)

        return g['width']

    def draw_text(
        self,
        pixoo: Any,
        text: str,
        xy: Tuple[int, int] = (0, 0),
        rgb: Tuple[int, int, int] = (255, 255, 255),
        align: str = "left",
    ) -> int:
        """Draw multi-line text onto a Pixoo instance."""
        lines = str(text).split('\n')
        y_offset = 0

        for line in lines:
            if align == "center":
                x_offset = int(self.get_text_width(line) / 2) * -1
            elif align == "right":
                x_offset = self.get_text_width(line) * -1
            else:
                x_offset = 0

            cx = xy[0] + x_offset
            for char in line:
                advance = self.draw_character(pixoo, char, (cx, xy[1] + y_offset), rgb)
                cx += advance

            y_offset += self.line_height

        return y_offset

    def __getitem__(self, item: str) -> Optional[List[int]]:
        return self.get_glyph(item)

    def __contains__(self, item: str) -> bool:
        return self.supports(item)


class BitMatrixFont:
    """Wrapper around original bit-matrix fonts (FONT_PICO_8, FONT_GICKO, etc.)."""

    def __init__(self, name: str, raw_dict: Dict[str, List[int]], force_uppercase: bool = False):
        self.name = name
        self.raw_dict = raw_dict
        self.force_uppercase = force_uppercase
        self._calculate_height()

    def _calculate_height(self) -> None:
        dummy = self.raw_dict.get('0', self.raw_dict.get('A'))
        if dummy and len(dummy) > 1 and dummy[-1] > 0:
            self.height = int((len(dummy) - 1) / dummy[-1])
        else:
            self.height = 5
        self.line_height = self.height + 1

    def _normalize_char(self, char: str) -> str:
        return char.upper() if self.force_uppercase else char

    def _normalize_text(self, text: str) -> str:
        return str(text).upper() if self.force_uppercase else str(text)

    def supports(self, char: str) -> bool:
        c = self._normalize_char(char)
        if c in self.raw_dict:
            return True
        if c in TYPOGRAPHY_FALLBACKS and TYPOGRAPHY_FALLBACKS[c] in self.raw_dict:
            return True
        return c.upper() in self.raw_dict

    def get_glyph(self, char: str) -> Optional[List[int]]:
        c = self._normalize_char(char)
        if c in self.raw_dict:
            return self.raw_dict[c]
        if c in TYPOGRAPHY_FALLBACKS and TYPOGRAPHY_FALLBACKS[c] in self.raw_dict:
            return self.raw_dict[TYPOGRAPHY_FALLBACKS[c]]
        if c.upper() in self.raw_dict:
            return self.raw_dict[c.upper()]
        return None

    def get_glyph_bdf(self, char: str) -> Optional[Dict[str, Any]]:
        matrix = self.get_glyph(char)
        if matrix is None:
            return None
        w = matrix[-1]
        h = int((len(matrix) - 1) / w) if w > 0 else 0
        bitmap = []
        for row in range(h):
            row_bits = []
            for col in range(w):
                idx = row * w + col
                row_bits.append('1' if idx < len(matrix) - 1 and matrix[idx] == 1 else '0')
            bitmap.append(''.join(row_bits))
        return {
            'width': w + 1,
            'bbx': (w, h, 0, 0),
            'bitmap': bitmap,
        }

    def get_char_width(self, char: str) -> int:
        g = self.get_glyph(char)
        if g is not None:
            return g[-1]
        return 0

    def get_text_width(self, text: str) -> int:
        norm_text = self._normalize_text(text)
        length = 0
        for char in norm_text:
            length += self.get_char_width(char) + 1
        return max(0, length - 1)

    def get_line_height(self) -> int:
        return self.line_height

    def draw_character(self, pixoo: Any, character: str, xy: Tuple[int, int], rgb: Tuple[int, int, int]) -> int:
        matrix = self.get_glyph(character)
        if matrix is not None:
            x_size = matrix[-1]
            for index, bit in enumerate(matrix):
                if bit == 1 and index != len(matrix) - 1:
                    local_x = index % x_size
                    local_y = int(index / x_size)
                    pixoo.draw_pixel((xy[0] + local_x, xy[1] + local_y), rgb)
            return x_size + 1
        return 0

    def draw_text(
        self,
        pixoo: Any,
        text: str,
        xy: Tuple[int, int] = (0, 0),
        rgb: Tuple[int, int, int] = (255, 255, 255),
        align: str = "left",
    ) -> int:
        norm_text = self._normalize_text(text)
        y_offset = 0
        for line in norm_text.split("\n"):
            if align == "center":
                x_offset = int(self.get_text_width(line) / 2) * -1
            elif align == "right":
                x_offset = self.get_text_width(line) * -1
            else:
                x_offset = 0

            cx = xy[0] + x_offset
            for char in line:
                advance = self.draw_character(pixoo, char, (cx, xy[1] + y_offset), rgb)
                cx += advance

            y_offset += self.line_height

        return y_offset

    def __getitem__(self, item: str) -> Optional[List[int]]:
        return self.get_glyph(item)

    def __contains__(self, item: str) -> bool:
        return self.supports(item)


class FontManager:
    """
    Central manager for BDF and bit-matrix fonts.
    Supports case-insensitive lookups, lazy on-demand BDF loading,
    and wrapping hardcoded dictionary fonts.
    """

    _instance: Optional['FontManager'] = None

    def __init__(self, scan_dirs: Optional[List[str]] = None):
        self._fonts: Dict[str, Union[BdfFont, BitMatrixFont]] = {}
        self._display_names: Dict[str, str] = {}
        self._available_bdf_files: Dict[str, Tuple[str, str]] = {}  # key -> (display_name, file_path)
        self._register_builtins()

        if scan_dirs:
            self.scan_directories(scan_dirs)

    @classmethod
    def get_instance(cls, scan_dirs: Optional[List[str]] = None) -> 'FontManager':
        if cls._instance is None:
            cls._instance = FontManager(scan_dirs)
        elif scan_dirs:
            cls._instance.scan_directories(scan_dirs)
        return cls._instance

    def _register_builtins(self) -> None:
        """Register the built-in bit-matrix fonts."""
        from ._font import FONT_PICO_8, FONT_GICKO, FIVE_PIX, ELEVEN_PIX, CLOCK, PIX24

        builtins = [
            ("PICO_8", FONT_PICO_8),
            ("GICKO", FONT_GICKO),
            ("FIVE_PIX", FIVE_PIX),
            ("ELEVEN_PIX", ELEVEN_PIX),
            ("CLOCK", CLOCK),
            ("PIX24", PIX24),
        ]

        for name, font_dict in builtins:
            self.register_matrix_font(name, font_dict, force_uppercase=False)

    def register_matrix_font(self, name: str, font_dict: Dict[str, List[int]], force_uppercase: bool = False) -> BitMatrixFont:
        """Register a hardcoded bit-matrix font under its lowercase name"""
        matrix_font = BitMatrixFont(name, font_dict, force_uppercase=force_uppercase)
        key = name.lower().replace("font_", "")
        self._fonts[key] = matrix_font
        self._fonts[f"font_{key}"] = matrix_font
        self._display_names[key] = name
        return matrix_font

    def register_bdf_font(self, bdf_font: BdfFont) -> None:
        """Register a BdfFont instance by its lowercase name"""
        key = bdf_font.name.lower()
        self._fonts[key] = bdf_font
        self._display_names[key] = bdf_font.name
        _LOGGER.debug("Registered BDF font '%s' from %s", bdf_font.name, bdf_font.file_path)

    def load_bdf_file(self, file_path: str, font_name: Optional[str] = None) -> Optional[BdfFont]:
        """Load, parse, and register a BDF font file into memory."""
        if not os.path.isfile(file_path):
            return None

        if font_name is None:
            font_name = os.path.splitext(os.path.basename(file_path))[0]

        data = load_bdf_font(file_path)
        if data is None or not data.get('glyphs'):
            _LOGGER.warning("Could not find any glyphs in BDF file: %s", file_path)
            return None

        bdf_font = BdfFont(font_name, data, file_path)
        self.register_bdf_font(bdf_font)
        return bdf_font

    def scan_directory(self, dir_path: str) -> int:
        """Scan a single directory for .bdf font files and index them for lazy loading."""
        if not os.path.isdir(dir_path):
            return 0

        count = 0
        try:
            for entry in os.listdir(dir_path):
                if entry.lower().endswith('.bdf'):
                    full_path = os.path.join(dir_path, entry)
                    if os.path.isfile(full_path):
                        font_name = os.path.splitext(entry)[0]
                        key = font_name.lower()
                        self._available_bdf_files[key] = (font_name, full_path)
                        self._display_names[key] = font_name
                        count += 1
        except Exception as e:
            _LOGGER.error("Error scanning font directory %s: %s", dir_path, e)

        return count

    def scan_directories(self, dir_paths: List[str]) -> int:
        """
        Scan multiple directories in order.
        User-provided fonts in later directories will override bundled fonts if they share the same name.
        """
        total = 0
        for dir_path in dir_paths:
            if dir_path and os.path.isdir(dir_path):
                _LOGGER.debug("Scanning font directory: %s", dir_path)
                loaded = self.scan_directory(dir_path)
                total += loaded
                _LOGGER.debug("Indexed %d fonts from %s", loaded, dir_path)
        return total

    def get_font(self, name: Union[str, Any], fallback: bool = True) -> Optional[Union[BdfFont, BitMatrixFont]]:
        """
        Look up a font by name (case-insensitive).
        Loads BDF fonts lazily into memory upon first request.
        """
        if isinstance(name, (BdfFont, BitMatrixFont)):
            return name

        if isinstance(name, dict):
            return BitMatrixFont("custom_dict", name)

        if not isinstance(name, str) or not name.strip():
            return self._fonts.get("pico_8") if fallback else None

        clean_name = name.strip().lower().replace("font_", "")

        # 1. Return already loaded BDF font from memory cache
        if clean_name in self._fonts and isinstance(self._fonts[clean_name], BdfFont):
            return self._fonts[clean_name]

        # 2. Check if indexed BDF file exists (lazy load BDF, upgrading any built-in fallback)
        if clean_name in self._available_bdf_files:
            disp_name, fpath = self._available_bdf_files.pop(clean_name)
            font = self.load_bdf_file(fpath, disp_name)
            if font is not None:
                return font

        # 3. Check if already registered in memory (e.g. built-in bit-matrix fonts)
        if clean_name in self._fonts:
            return self._fonts[clean_name]

        # 4. Try hyphen/underscore variations (e.g. pico-8 -> pico_8)
        alt_name = clean_name.replace("-", "_")
        if alt_name in self._fonts and isinstance(self._fonts[alt_name], BdfFont):
            return self._fonts[alt_name]
        if alt_name in self._available_bdf_files:
            disp_name, fpath = self._available_bdf_files.pop(alt_name)
            font = self.load_bdf_file(fpath, disp_name)
            if font is not None:
                return font
        if alt_name in self._fonts:
            return self._fonts[alt_name]

        if fallback:
            _LOGGER.warning("Unknown font '%s', falling back to PICO_8.", name)
            return self._fonts.get("pico_8")

        return None

    def list_fonts(self) -> List[str]:
        """Return a sorted list of registered display font names."""
        return sorted(set(self._display_names.values()))

    def __contains__(self, name: str) -> bool:
        if not isinstance(name, str):
            return False
        clean_name = name.strip().lower().replace("font_", "")
        return clean_name in self._fonts or clean_name in self._available_bdf_files


__all__ = (
    "BdfFont",
    "BitMatrixFont",
    "FontManager",
    "load_bdf_font",
    "normalize_typography",
)
