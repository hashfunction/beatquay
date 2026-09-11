# SPDX-FileCopyrightText: 2026 Trieflow LLC
# SPDX-License-Identifier: GPL-2.0-or-later
# Separate discovery from installation so multi-config generators cannot copy
# debug redistributables into a release stage. No runtime is removed by filename.
function(beatquay_install_system_runtime)
    if(NOT MSVC)
        include(InstallRequiredSystemLibraries)
        return()
    endif()
    set(CMAKE_INSTALL_UCRT_LIBRARIES TRUE)
    set(CMAKE_INSTALL_SYSTEM_RUNTIME_LIBS_SKIP TRUE)
    set(CMAKE_INSTALL_DEBUG_LIBRARIES FALSE)
    set(CMAKE_INSTALL_DEBUG_LIBRARIES_ONLY FALSE)
    include(InstallRequiredSystemLibraries)
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
