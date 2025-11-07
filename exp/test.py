#import kconfiglib                                  # ZephyrKconfiglib
from  esp_kconfiglib import Kconfig as kconfiglib   # esp-idf-kconfiglib 

#kconf = kconfiglib.Kconfig('Kconfig')
kconf = kconfiglib('KconfigEsp')
print('Symbols:', len(kconf.defined_syms))

