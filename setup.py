from cx_Freeze import setup, Executable

options = {
    'build_exe': {
        'includes':
        ['lxml.html', 'lxml._elementpath', 'Queue.multiprocessing']
    }
}

executables = [Executable('chancho.py', targetName='chancho.exe')]

setup(
    name='chancho',
    version='0.1',
    description="4chan image downloader",
    executables=executables,
    options=options)
