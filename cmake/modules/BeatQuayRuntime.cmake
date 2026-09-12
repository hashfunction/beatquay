# SPDX-FileCopyrightText: 2026 Trieflow LLC
# SPDX-License-Identifier: GPL-2.0-or-later
# Separate discovery from installation so multi-config generators cannot copy
# debug redistributables into a release stage. No runtime is removed by filename.
function(beatquay_runtime_json_string output value)
    string(REPLACE "\\" "\\\\" escaped "${value}")
    string(REPLACE "\"" "\\\"" escaped "${escaped}")
    string(REPLACE "\n" "\\n" escaped "${escaped}")
    string(REPLACE "\r" "\\r" escaped "${escaped}")
    string(REPLACE "\t" "\\t" escaped "${escaped}")
    set(${output} "\"${escaped}\"" PARENT_SCOPE)
endfunction()

function(beatquay_install_system_runtime)
    if(NOT MSVC)
        include(InstallRequiredSystemLibraries)
        return()
    endif()
    set(CMAKE_INSTALL_UCRT_LIBRARIES TRUE)
    set(CMAKE_INSTALL_SYSTEM_RUNTIME_LIBS_SKIP TRUE)
    set(CMAKE_INSTALL_DEBUG_LIBRARIES FALSE)
    set(CMAKE_INSTALL_DEBUG_LIBRARIES_ONLY FALSE)
    include(InstallRequiredSystemLibraries RESULT_VARIABLE runtime_discovery_module)
    # Record the exact release inputs already selected by CMake. This receipt
    # does not change the selected files or either installation rule below.
    set(runtime_sources "[]")
    set(runtime_index 0)
    foreach(runtime_path IN LISTS CMAKE_INSTALL_SYSTEM_RUNTIME_LIBS)
        beatquay_runtime_json_string(runtime_value "${runtime_path}")
        string(JSON runtime_sources SET "${runtime_sources}" ${runtime_index} "${runtime_value}")
        math(EXPR runtime_index "${runtime_index} + 1")
    endforeach()
    set(runtime_selection "{\"schemaVersion\":1}")
    string(JSON runtime_selection SET "${runtime_selection}" sourcePaths "${runtime_sources}")
    file(SHA256 "${runtime_discovery_module}" runtime_discovery_sha256)
    foreach(runtime_pair IN ITEMS
            "cmakeVersion;${CMAKE_VERSION}" "discoveryModule;${runtime_discovery_module}"
            "discoveryModuleSha256;${runtime_discovery_sha256}"
            "msvcRedistRoot;${MSVC_REDIST_DIR}" "windowsKitsRoot;${WINDOWS_KITS_DIR}"
            "architecture;${CMAKE_MSVC_ARCH}" "buildType;${CMAKE_BUILD_TYPE}")
        list(GET runtime_pair 0 runtime_key)
        list(LENGTH runtime_pair runtime_pair_length)
        set(runtime_text "")
        if(runtime_pair_length GREATER 1)
            list(GET runtime_pair 1 runtime_text)
        endif()
        beatquay_runtime_json_string(runtime_value "${runtime_text}")
        string(JSON runtime_selection SET "${runtime_selection}" "${runtime_key}" "${runtime_value}")
    endforeach()
    file(WRITE "${CMAKE_BINARY_DIR}/ms-runtime-selection.json" "${runtime_selection}\n")
    if(CMAKE_INSTALL_SYSTEM_RUNTIME_LIBS)
        install(PROGRAMS ${CMAKE_INSTALL_SYSTEM_RUNTIME_LIBS}
            DESTINATION "${CMAKE_INSTALL_SYSTEM_RUNTIME_DESTINATION}")
    endif()
    # A Debug application can also load release-built third-party DLLs, hence
    # the release runtime above remains available in Debug configurations.
    if(CMAKE_CONFIGURATION_TYPES OR CMAKE_BUILD_TYPE STREQUAL "Debug")
        set(CMAKE_INSTALL_SYSTEM_RUNTIME_LIBS "")
        set(CMAKE_INSTALL_DEBUG_LIBRARIES TRUE)
        set(CMAKE_INSTALL_DEBUG_LIBRARIES_ONLY TRUE)
        include(InstallRequiredSystemLibraries)
        if(CMAKE_INSTALL_SYSTEM_RUNTIME_LIBS)
            install(PROGRAMS ${CMAKE_INSTALL_SYSTEM_RUNTIME_LIBS}
                DESTINATION "${CMAKE_INSTALL_SYSTEM_RUNTIME_DESTINATION}"
                CONFIGURATIONS Debug)
        endif()
    endif()
endfunction()
