from lyall_core import steam

LIBRARYFOLDERS = '''"libraryfolders"
{
\t"0"
\t{
\t\t"path"\t\t"{root}"
\t}
\t"1"
\t{
\t\t"path"\t\t"{sd}"
\t}
}
'''

APPMANIFEST = '''"AppState"
{
\t"appid"\t\t"1903340"
\t"name"\t\t"Clair Obscur: Expedition 33"
\t"installdir"\t\t"Expedition 33"
}
'''


def _mk_steam(tmp_path):
    root = tmp_path / ".local/share/Steam"
    sd = tmp_path / "sdcard"
    for lib in (root, sd):
        (lib / "steamapps/common").mkdir(parents=True)
    (root / "steamapps/libraryfolders.vdf").write_text(
        LIBRARYFOLDERS.replace("{root}", str(root)).replace("{sd}", str(sd)))
    (sd / "steamapps/appmanifest_1903340.acf").write_text(APPMANIFEST)
    (sd / "steamapps/common/Expedition 33").mkdir()
    return root, sd


def test_find_steam_root(tmp_path):
    root, _ = _mk_steam(tmp_path)
    assert steam.find_steam_root(str(tmp_path)) == str(root)


def test_find_steam_root_missing(tmp_path):
    assert steam.find_steam_root(str(tmp_path)) is None


def test_library_paths_include_root_and_sd(tmp_path):
    root, sd = _mk_steam(tmp_path)
    libs = steam.library_paths(str(root))
    assert str(root / "steamapps") in libs and str(sd / "steamapps") in libs


def test_installed_games(tmp_path):
    root, sd = _mk_steam(tmp_path)
    games = steam.installed_games(str(root))
    assert games[1903340]["install_path"] == str(sd / "steamapps/common/Expedition 33")
    assert games[1903340]["name"] == "Clair Obscur: Expedition 33"


def test_skips_runtime_entries(tmp_path):
    root, sd = _mk_steam(tmp_path)
    (sd / "steamapps/appmanifest_1628350.acf").write_text(
        APPMANIFEST.replace("1903340", "1628350")
        .replace("Clair Obscur: Expedition 33", "Steam Linux Runtime 3.0 (sniper)")
        .replace("Expedition 33", "SteamLinuxRuntime_sniper"))
    assert 1628350 not in steam.installed_games(str(root))
