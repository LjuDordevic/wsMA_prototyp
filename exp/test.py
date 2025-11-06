#import kconfiglib
from  esp_kconfiglib import Kconfig as kconfiglib

#kconf = kconfiglib.Kconfig('Kconfig')
kconf = kconfiglib('KconfigEsp')
print('Symbols:', len(kconf.defined_syms))

