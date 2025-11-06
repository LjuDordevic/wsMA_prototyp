import kconfiglib

kconf = kconfiglib.Kconfig('Kconfig')
print('Symbols:', len(kconf.defined_syms))

