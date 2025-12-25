import re
import sys

GAMEBANANA = "https://gamebanana.com/tools/20722"

GITHUB = "https://github.com"
GITHUB_API = "https://api.github.com"
REPO = "remdog1/BrawlhallaModLoader"

VERSION = "0.0.0"
GIT_VERSION = None
PRERELEASE = True

if sys.platform.startswith("win"):
    import win32api

    def GetFileProperties(executable):
        props = {"FileVersion": "0.3.0", "FileFlags": 0, "ProductVersion": "0.3.0"}

        try:
            fixedInfo = win32api.GetFileVersionInfo(executable, '\\')
            props['ProductVersion'] = "{}.{}.{}".format(fixedInfo["ProductVersionMS"] >> 16,
                                                        fixedInfo["ProductVersionMS"] & 65535,
                                                        fixedInfo["ProductVersionLS"] >> 16)
            props['FileFlags'] = fixedInfo["FileFlags"]
            lang, codepage = win32api.GetFileVersionInfo(executable, '\\VarFileInfo\\Translation')[0]
            props['FileVersion'] = win32api.GetFileVersionInfo(executable, u'\\StringFileInfo\\%04X%04X\\FileVersion' %
                                                               (lang, codepage))
        except:
            pass

        return props


    if getattr(sys, 'frozen', False):
        fileProperties = GetFileProperties(sys.executable)
        VERSION = fileProperties.get("ProductVersion", "0.3.0")
        GIT_VERSION = fileProperties.get("FileVersion", "0.3.0")
        PRERELEASE = bool(fileProperties.get("FileFlags", 0) & 0x2)

else:
    def GetFileProperties(executable):
        props = {"FileVersion": None, "FileFlags": None, "ProductVersion": None}
        return props


    if getattr(sys, 'frozen', False):
        fileProperties = GetFileProperties(sys.executable)
        VERSION = fileProperties.get("ProductVersion", "0.3.0")
        GIT_VERSION = fileProperties.get("FileVersion", "0.3.0")
        PRERELEASE = bool(fileProperties.get("FileFlags", 0))


def GetDownloadUrl(assets):
    for asset in assets:
        if sys.platform.startswith("win"):
            if asset.get("name", "").endswith(".exe"):
                return asset.get("browser_download_url", None)


def _getLatest(latest):
    bodySplit = re.findall("###[^#]+", latest.get("body", ""))
    body = "\n".join([re.sub(r"### ([^\n\r]+)",
                             r'<size="14px">\1<void>',
                             frame.strip())
                      for frame in bodySplit])
    return latest.get("html_url", None), GetDownloadUrl(latest.get("assets", [])), \
           latest.get("name", None), body


def GetLatest():
    return None
