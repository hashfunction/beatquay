# SPDX-FileCopyrightText: 2026 Trieflow LLC
# SPDX-License-Identifier: GPL-2.0-or-later
"""Execute the root's actual runtime install logic with a synthetic discovery seam.

CMake configure/generate/install are real. Only compiler redistributable discovery
is replaced: no Windows CRT or compiler is installed on the test host.
"""
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[2]


class ReleaseRuntimeTest(unittest.TestCase):
    def test_actual_cmake_install_selects_debug_only_for_debug(self):
        source_text = (SOURCE / "CMakeLists.txt").read_text()
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
"""
            )
            (root / "CMakeLists.txt").write_text(
                """cmake_minimum_required(VERSION 3.24)
project(RuntimeFixture NONE)
set(MSVC TRUE)
set(BIN_DIR bin)
list(PREPEND CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}")
"""
                + f'list(APPEND CMAKE_MODULE_PATH "{SOURCE.as_posix()}/cmake/modules")\n'
                + section
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


if __name__ == "__main__":
    unittest.main()
