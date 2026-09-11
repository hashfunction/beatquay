# SPDX-FileCopyrightText: 2026 Trieflow LLC
# SPDX-License-Identifier: GPL-2.0-or-later
cmake_minimum_required(VERSION 3.24)
project(BeatQuayProjectExportIntegration LANGUAGES CXX)
find_package(Qt6 6.11.2 EXACT REQUIRED COMPONENTS Core Test)
include(CTest)
include(GenerateExportHeader)
set(CMAKE_AUTOMOC ON)
get_filename_component(BEATQUAY_SOURCE "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)
add_library(ProjectExportIntegrationCore STATIC
    "${BEATQUAY_SOURCE}/src/core/ProjectExportCheck.cpp"
    "${BEATQUAY_SOURCE}/src/core/ProjectExportSession.cpp"
    "${BEATQUAY_SOURCE}/src/core/ExportFileIdentity.cpp"
    "${BEATQUAY_SOURCE}/src/core/ExportOutputPublication.cpp")
generate_export_header(ProjectExportIntegrationCore BASE_NAME lmms)
target_include_directories(ProjectExportIntegrationCore PUBLIC "${BEATQUAY_SOURCE}/include" "${CMAKE_CURRENT_BINARY_DIR}")
target_link_libraries(ProjectExportIntegrationCore PUBLIC Qt6::Core)
target_compile_features(ProjectExportIntegrationCore PUBLIC cxx_std_20)
add_executable(ExportProjectCheckIntegrationTest "${BEATQUAY_SOURCE}/tests/src/gui/ExportProjectCheckIntegrationTest.cpp")
target_link_libraries(ExportProjectCheckIntegrationTest PRIVATE ProjectExportIntegrationCore Qt6::Test)
if(MSVC)
    target_compile_options(ProjectExportIntegrationCore PRIVATE /W4 /WX /utf-8)
    target_compile_options(ExportProjectCheckIntegrationTest PRIVATE /W4 /WX /utf-8)
else()
    target_compile_options(ProjectExportIntegrationCore PRIVATE -Wall -Wextra -Werror)
    target_compile_options(ExportProjectCheckIntegrationTest PRIVATE -Wall -Wextra -Werror)
endif()
add_test(NAME ExportProjectCheckIntegrationTest COMMAND ExportProjectCheckIntegrationTest)
