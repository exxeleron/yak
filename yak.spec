# -*- mode: python -*-
a = Analysis(['scripts/yak.py'],
             pathex=['.'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)

a.datas += [('LICENSE', 'LICENSE', '.')]
a.datas += [('yak_complete_bash.sh', 'scripts/yak_complete_bash.sh', '.')]

pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='yak',
          debug=False,
          strip=None,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name='yak')
