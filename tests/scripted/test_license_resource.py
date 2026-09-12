# SPDX-FileCopyrightText: 2026 Trieflow LLC
# SPDX-License-Identifier: GPL-2.0-or-later
"""Compile the production resource selection, text reader and About license statement."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[2]


class LicenseResourceTests(unittest.TestCase):
    def test_about_displays_combined_gpl3_and_preserves_original_application_terms(self):
        with tempfile.TemporaryDirectory(prefix='beatsprig-license-resource-') as temporary:
            root = Path(temporary)
            cmake = (SOURCE / 'src/CMakeLists.txt').read_text(encoding='utf-8')
            resources = re.search(r'ADD_GEN_QRC\(LMMS_RCC_OUT lmms.qrc\n.*?\n\)', cmake, re.S).group()
            about = (SOURCE / 'src/gui/modals/AboutDialog.cpp').read_text(encoding='utf-8')
            statement = re.search(r'licenseLabel->setPlainText\(.*?;', about, re.S).group()
            embed = (SOURCE / 'src/gui/embed.cpp').read_text(encoding='utf-8')
            reader = embed[embed.index('auto getText(std::string_view name)'):embed.index('\n} // namespace lmms::embed')]
            (root / 'license_statement.inc').write_text(statement)
            (root / 'resource_reader.inc').write_text(reader)
            (root / 'CONTRIBUTORS').write_text('Resource fixture contributor\n')
            (root / 'CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.24)
project(BeatSprigLicenseResource LANGUAGES CXX)
find_package(Qt6 6.11.2 EXACT REQUIRED COMPONENTS Core Widgets)
set(QT_VERSION_MAJOR 6)
set(CMAKE_CXX_STANDARD 17)
set(CONTRIBUTORS "${CMAKE_CURRENT_SOURCE_DIR}/CONTRIBUTORS")
set(fixture_source "${CMAKE_SOURCE_DIR}")
''' + f'set(CMAKE_SOURCE_DIR "{SOURCE.as_posix()}")\n'
                + 'include("${CMAKE_SOURCE_DIR}/cmake/modules/GenQrc.cmake")\n'
                + resources + '''
set(product_source "${CMAKE_SOURCE_DIR}")
set(CMAKE_SOURCE_DIR "${fixture_source}")
add_executable(license_resource main.cpp ${LMMS_RCC_OUT})
target_link_libraries(license_resource PRIVATE Qt6::Core Qt6::Widgets)
include(CTest)
add_test(NAME original_and_combined_license COMMAND license_resource "${product_source}")
''')
            (root / 'main.cpp').write_text(r'''#include <QApplication>
#include <QDebug>
#include <QFile>
#include <QResource>
#include <QTextEdit>
#include <string_view>
namespace lmms::embed {
#include "resource_reader.inc"
}
using namespace lmms;
QString original(const QString& root, const QString& name) {
    QFile file(root + '/' + name);
    if (!file.open(QIODevice::ReadOnly)) { qFatal("Original license fixture input missing"); }
    return QString::fromUtf8(file.readAll());
}
int main(int argc, char** argv) {
    QApplication application(argc, argv);
    QTextEdit label; auto* licenseLabel = &label;
    const auto tr = [](const char* value) { return QCoreApplication::translate("AboutDialog", value); };
#include "license_statement.inc"
    const auto text = label.toPlainText();
    const auto root = QString::fromLocal8Bit(argv[1]);
    const auto combined = original(root, "distribution/native-source/COMBINED-LICENSE.md");
    const auto gpl3 = original(root, "distribution/native-source/GPL-3.0.txt");
    const auto upstream = original(root, "LICENSE.txt");
    if (!text.startsWith(combined) || !text.contains(gpl3) || !text.endsWith(upstream)) {
        qCritical("About must show the complete combined notice, GPLv3, then original GPLv2 terms");
        return 1;
    }
    if (embed::getText("AUTHORS") != original(root, "doc/AUTHORS")) {
        qCritical("Original author resource changed"); return 2;
    }
    return 0;
}
''')
            env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
            for command in (
                ['cmake', '-S', str(root), '-B', str(root / 'build'), '-G', 'Ninja', '-DCMAKE_BUILD_TYPE=Release'],
                ['cmake', '--build', str(root / 'build')],
                ['ctest', '--test-dir', str(root / 'build'), '--output-on-failure'],
            ):
                result = subprocess.run(command, env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
