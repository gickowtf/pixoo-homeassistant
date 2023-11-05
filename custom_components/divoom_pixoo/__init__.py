import site
from pathlib import Path
package_dir = Path(__file__).resolve().parents[0]
site.addsitedir(str(package_dir))
from pixoo64 import Pixoo, FONT_GICKO, FONT_PICO_8