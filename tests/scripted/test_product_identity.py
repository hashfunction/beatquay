# SPDX-FileCopyrightText: 2026 Trieflow LLC
# SPDX-License-Identifier: GPL-2.0-or-later
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[2]


class ProductIdentityTest(unittest.TestCase):
    def test_actual_windows_resource_uses_new_host_and_separate_product_version(self):
        with tempfile.TemporaryDirectory(prefix="beatquay-identity-") as temporary:
            root = Path(temporary)
            (root / "CMakeLists.txt").write_text(
                """cmake_minimum_required(VERSION 3.24)
project(lmms NONE)
set(PROJECT_AUTHOR "LMMS Developers")
set(PROJECT_COPYRIGHT "2008-2026 LMMS Developers")
set(PROJECT_URL "https://lmms.io")
set(PROJECT_NAME_UCASE "LMMS")
set(VERSION "1.3.0-alpha")
"""
                + f"""include("{SOURCE.as_posix()}/cmake/modules/BeatQuayIdentity.cmake")
configure_file("{SOURCE.as_posix()}/cmake/nsis/lmms.rc.in" "${{CMAKE_BINARY_DIR}}/lmms.rc")
"""
            )
            subprocess.run(
                ["cmake", "-S", str(root), "-B", str(root / "build"), "-G", "Ninja"],
                check=True,
                capture_output=True,
            )
            rc = (root / "build/lmms.rc").read_text()
            for text in (
                '"CompanyName",      "Trieflow LLC\\0"',
                '"ProductName",      "BeatSprig\\0"',
                '"ProductVersion",   "1.0.1\\0"',
                '"OriginalFilename", "beatsprig.exe\\0"',
                "FILEVERSION 1,0,1,0",
                "PRODUCTVERSION 1,0,1,0",
                "https://beatsprig.trieflow.com",
                "LMMS Developers",
                "ICON data/branding/beatquay.ico",
            ):
                self.assertIn(text, rc)
            self.assertNotIn('"ProductVersion",   "1.3.0', rc)

    def test_customer_and_native_test_host_share_windows_basename(self):
        with tempfile.TemporaryDirectory(prefix="beatsprig-host-identity-") as temporary:
            root = Path(temporary)
            (root / "host.cpp").write_text("int main() { return 0; }\n")
            (root / "CMakeLists.txt").write_text(
                "cmake_minimum_required(VERSION 3.24)\nproject(HostNames LANGUAGES CXX)\n"
                f'include("{SOURCE.as_posix()}/cmake/modules/BeatQuayIdentity.cmake")\n'
                "set(LMMS_BUILD_WIN32 TRUE)\n"
                "foreach(target lmms BeatQuayTemplateTest)\n"
                "add_executable(${target} host.cpp)\n"
                "beatquay_apply_host_identity(${target})\n"
                "get_target_property(name ${target} OUTPUT_NAME)\n"
                'file(APPEND "${CMAKE_BINARY_DIR}/hosts.txt" "${target}=${name}\\n")\n'
                "endforeach()\n"
                'file(WRITE "${CMAKE_BINARY_DIR}/paths.txt" "${BEATQUAY_SETTINGS_FILE}\\n${BEATQUAY_WORKSPACE}\\n${BEATQUAY_PORTABLE_WORKSPACE}\\n")\n'
            )
            subprocess.run(["cmake", "-S", str(root), "-B", str(root / "build"), "-G", "Ninja"], check=True, capture_output=True)
            self.assertEqual((root / "build/hosts.txt").read_text().splitlines(), ["lmms=beatsprig", "BeatQuayTemplateTest=beatsprig"])
            self.assertEqual((root / "build/paths.txt").read_text().splitlines(), [".beatquayrc.xml", "BeatQuay", "beatquay-workspace"])

    def test_installed_asset_paths_and_product_install_folder(self):
        import xml.etree.ElementTree as ET

        with tempfile.TemporaryDirectory(
            prefix="beatquay-installed-brand-"
        ) as temporary:
            root = Path(temporary)
            package_definitions = (
                (SOURCE / "cmake/CMakeLists.txt")
                .read_text()
                .split("# Disable strip", 1)[0]
            )
            (root / "CMakeLists.txt").write_text(
                "cmake_minimum_required(VERSION 3.24)\nproject(lmms NONE)\n"
                f'include("{SOURCE.as_posix()}/cmake/modules/BeatQuayIdentity.cmake")\n'
                + package_definitions
                + 'file(WRITE "${CMAKE_BINARY_DIR}/package.txt" "${CPACK_PACKAGE_NAME}\\n${CPACK_PACKAGE_VENDOR}\\n${CPACK_PACKAGE_VERSION}\\n${CPACK_PACKAGE_INSTALL_DIRECTORY}\\n")\n'
                + f'set(LMMS_DATA_DIR data)\nadd_subdirectory("{SOURCE.as_posix()}/data/branding" branding)\n'
            )
            subprocess.run(
                ["cmake", "-S", str(root), "-B", str(root / "build"), "-G", "Ninja"],
                check=True,
                capture_output=True,
            )
            self.assertEqual(
                (root / "build/package.txt").read_text().splitlines(),
                ["BeatSprig", "Trieflow LLC", "1.0.1", "BeatSprig"],
            )
            stage = root / "stage"
            subprocess.run(
                ["cmake", "--install", str(root / "build"), "--prefix", str(stage)],
                check=True,
                capture_output=True,
            )
            manifest = (
                ET.parse(SOURCE / "cmake/nsis/lmms.VisualElementsManifest.xml")
                .getroot()
                .find("VisualElements")
            )
            for attribute in (
                "Square150x150Logo",
                "Square70x70Logo",
                "Square44x44Logo",
            ):
                relative = manifest.attrib[attribute].replace("\\", "/")
                self.assertEqual(
                    (stage / relative).read_bytes(), (SOURCE / relative).read_bytes()
                )
            self.assertEqual(manifest.attrib["BackgroundColor"], "#101b27")
            self.assertEqual(
                {p.name for p in (stage / "data/branding").iterdir()},
                {"beatquay.svg", "beatquay-256.png", "beatquay.ico", "README.md"},
            )

    def test_windows_manifest_install_names_follow_customer_host(self):
        with tempfile.TemporaryDirectory(prefix="beatsprig-windows-manifests-") as temporary:
            root = Path(temporary)
            (root / "CMakeLists.txt").write_text(
                "cmake_minimum_required(VERSION 3.24)\nproject(lmms NONE)\n"
                f'include("{SOURCE.as_posix()}/cmake/modules/BeatQuayIdentity.cmake")\n'
                f'add_subdirectory("{SOURCE.as_posix()}/cmake/nsis" nsis)\n'
                'file(WRITE "${CMAKE_BINARY_DIR}/shortcuts.txt" "${CPACK_NSIS_INSTALLED_ICON_NAME}\\n${CPACK_PACKAGE_EXECUTABLES}\\n${CPACK_NSIS_MENU_LINKS}\\n${CPACK_NSIS_EXTRA_INSTALL_COMMANDS}")\n'
            )
            subprocess.run(["cmake", "-S", str(root), "-B", str(root / "build"), "-G", "Ninja"], check=True, capture_output=True)
            subprocess.run(["cmake", "--install", str(root / "build"), "--prefix", str(root / "stage")], check=True, capture_output=True)
            for old, new in (("lmms.exe.manifest", "beatsprig.exe.manifest"), ("lmms.VisualElementsManifest.xml", "beatsprig.VisualElementsManifest.xml")):
                self.assertEqual((root / "stage" / new).read_bytes(), (SOURCE / "cmake/nsis" / old).read_bytes())
                self.assertFalse((root / "stage" / old).exists())
            shortcuts = (root / "build/shortcuts.txt").read_text()
            self.assertEqual(shortcuts.splitlines()[:3], ["beatsprig.exe", "beatsprig.exe;BeatSprig", "beatsprig.exe;BeatSprig"])
            self.assertIn("beatsprig.exe", shortcuts)
            self.assertNotIn("lmms.exe", shortcuts)


if __name__ == "__main__":
    unittest.main()
