"""
    Run 'python cxfreezesetup.py build' to create a executable with cx_Freeze.
"""

from cx_Freeze import setup, Executable

OPTIONS = {
    'build_exe': {
        'includes': [
            'Queue.multiprocessing', 'idna.idnadata', 'lxml._elementpath',
            'lxml.html'
        ]
    }
}

EXECUTABLES = [Executable('chancho.py', targetName='chancho.exe')]

setup(
    name='chancho',
    version='0.1',
    description="4chan image downloader",
    executables=EXECUTABLES,
    options=OPTIONS)
