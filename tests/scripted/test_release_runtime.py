# SPDX-FileCopyrightText: 2026 Trieflow LLC
# SPDX-License-Identifier: GPL-2.0-or-later
"""Execute the root's actual runtime install logic with a synthetic discovery seam.

CMake configure/generate/install are real. Only compiler redistributable discovery
is replaced: no Windows CRT or compiler is installed on the test host.
"""
from pathlib import Path
import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[2]


class ReleaseRuntimeTest(unittest.TestCase):
    def test_actual_cmake_install_selects_debug_only_for_debug(self):
        original_open = Path.open

        def windows_locale_open(
            path, mode="r", buffering=-1, encoding=None, errors=None, newline=None
        ):
            # Preserve the failing native Windows default on every test host.
            # This is a real source-file read; explicit encodings remain honored.
            if "b" not in mode and encoding in (None, "locale"):
                encoding = "cp1252"
            return original_open(path, mode, buffering, encoding, errors, newline)

        with patch.object(Path, "open", windows_locale_open):
            source_text = (SOURCE / "CMakeLists.txt").read_text(encoding="utf-8")
        # Exercise precisely the section invoked by the application build.
        section = source_text[
            source_text.index("SET(CMAKE_INSTALL_SYSTEM_RUNTIME_DESTINATION") :
        ]
        with tempfile.TemporaryDirectory(prefix="beatquay-crt-") as temporary:
            root = Path(temporary)
            (root / "release.dll").write_bytes(b"release runtime fixture")
            (root / "debug.dll").write_bytes(b"debug runtime fixture")
            (root / "InstallRequiredSystemLibraries.cmake").write_text(
                """
set(CMAKE_INSTALL_SYSTEM_RUNTIME_LIBS "")
if(NOT CMAKE_INSTALL_DEBUG_LIBRARIES_ONLY)
 list(APPEND CMAKE_INSTALL_SYSTEM_RUNTIME_LIBS "${CMAKE_SOURCE_DIR}/release.dll")
endif()
if(CMAKE_INSTALL_DEBUG_LIBRARIES)
 list(APPEND CMAKE_INSTALL_SYSTEM_RUNTIME_LIBS "${CMAKE_SOURCE_DIR}/debug.dll")
endif()
if(NOT CMAKE_INSTALL_SYSTEM_RUNTIME_LIBS_SKIP)
 install(PROGRAMS ${CMAKE_INSTALL_SYSTEM_RUNTIME_LIBS} DESTINATION bin)
endif()
""",
                encoding="utf-8",
            )
            (root / "CMakeLists.txt").write_text(
                """cmake_minimum_required(VERSION 3.24)
project(RuntimeFixture NONE)
set(MSVC TRUE)
set(BIN_DIR bin)
list(PREPEND CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}")
"""
                + f'list(APPEND CMAKE_MODULE_PATH "{SOURCE.as_posix()}/cmake/modules")\n'
                + section,
                encoding="utf-8",
            )
            for generator in ("Ninja", "Ninja Multi-Config"):
                for config in ("Debug", "Release", "RelWithDebInfo", "MinSizeRel"):
                    with self.subTest(generator=generator, config=config):
                        build = root / (generator.replace(" ", "-") + config)
                        subprocess.run(
                            [
                                "cmake",
                                "-S",
                                str(root),
                                "-B",
                                str(build),
                                "-G",
                                generator,
                                f"-DCMAKE_BUILD_TYPE={config}",
                            ],
                            check=True,
                            capture_output=True,
                        )
                        stage = build / "stage"
                        subprocess.run(
                            [
                                "cmake",
                                "--install",
                                str(build),
                                "--config",
                                config,
                                "--prefix",
                                str(stage),
                            ],
                            check=True,
                            capture_output=True,
                        )
                        self.assertEqual(
                            (stage / "bin/release.dll").read_bytes(),
                            b"release runtime fixture",
                        )
                        self.assertEqual(
                            (stage / "bin/debug.dll").exists(), config == "Debug"
                        )
                        selection = json.loads((build / 'ms-runtime-selection.json').read_text())
                        self.assertEqual(selection['sourcePaths'], [(root / 'release.dll').as_posix()])
                        self.assertNotIn((root / 'debug.dll').as_posix(), selection['sourcePaths'])
                        self.assertEqual(selection['discoveryModule'], (root / 'InstallRequiredSystemLibraries.cmake').as_posix())


if __name__ == "__main__":
    unittest.main()
