include(CTest)

set(CMAKE_INCLUDE_CURRENT_DIR ON)
set(CMAKE_AUTOMOC ON)

set(LMMS_TESTS
	src/core/ArrayVectorTest.cpp
	src/core/AudioBufferTest.cpp
	src/core/AudioFileOutputTest.cpp
	src/core/ExportOutputPublicationTest.cpp
	src/core/AutomatableModelTest.cpp
	src/core/MathTest.cpp
	src/core/ProjectExportCheckTest.cpp
	src/core/ProjectExportFactsCollectorTest.cpp
	src/gui/ExportProjectCheckIntegrationTest.cpp
	src/core/ProjectVersionTest.cpp
	src/core/RelativePathsTest.cpp
	src/core/RenderManagerLifecycleTest.cpp
	src/core/TimelineTest.cpp
	src/core/TrackFilenameFilterTest.cpp
	src/tracks/AutomationTrackTest.cpp
)

if(TARGET kicker AND TARGET tripleoscillator)
	list(APPEND LMMS_TESTS src/core/BeatQuayTemplateTest.cpp)
endif()

foreach(LMMS_TEST_SRC IN LISTS LMMS_TESTS)
	# TODO CMake 3.20: Use cmake_path
	get_filename_component(LMMS_TEST_NAME ${LMMS_TEST_SRC} NAME_WE)

	add_executable(${LMMS_TEST_NAME} ${LMMS_TEST_SRC})
	# Preserve individual assertions even when Windows does not forward QtTest's
	# default logger to CTest's captured stdout. Reports contain metadata only.
	add_test(NAME ${LMMS_TEST_NAME} COMMAND ${LMMS_TEST_NAME}
		-o "${CMAKE_CURRENT_BINARY_DIR}/${LMMS_TEST_NAME}.qt-test.xml,junitxml"
		-o "${CMAKE_CURRENT_BINARY_DIR}/${LMMS_TEST_NAME}.qt-test.txt,txt"
	)

	# TODO CMake 3.12: Propagate usage requirements by linking to lmmsobjs
	target_include_directories(${LMMS_TEST_NAME} PRIVATE $<TARGET_PROPERTY:lmmsobjs,INCLUDE_DIRECTORIES>)

	target_static_libraries("${LMMS_TEST_NAME}" PRIVATE lmmsobjs)
	target_link_libraries(${LMMS_TEST_NAME} PRIVATE
		${QT_LIBRARIES}
		${QT_QTTEST_LIBRARY}
	)

	target_compile_features(${LMMS_TEST_NAME} PRIVATE cxx_std_20)
	target_compile_definitions(${LMMS_TEST_NAME} PRIVATE LMMS_TESTING)
endforeach()

if(TARGET BeatQuayTemplateTest)
	# The genuine Windows synth DLLs import the exported lmms.exe core. Run
	# the actual core/QTest host under that module name in an isolated folder;
	# never load a second application's Engine globals into a differently named test.
	set_target_properties(BeatQuayTemplateTest PROPERTIES
		ENABLE_EXPORTS ON OUTPUT_NAME lmms
		RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/template-host")
	target_compile_definitions(BeatQuayTemplateTest PRIVATE
		BEATQUAY_TEMPLATE_DIR="${CMAKE_SOURCE_DIR}/data/projects/templates"
		BEATQUAY_KICKER_DIR="$<TARGET_FILE_DIR:kicker>"
		BEATQUAY_TRIPLE_DIR="$<TARGET_FILE_DIR:tripleoscillator>"
		BEATQUAY_KICKER_FILE="$<TARGET_FILE:kicker>"
		BEATQUAY_TRIPLE_FILE="$<TARGET_FILE:tripleoscillator>")
	add_dependencies(BeatQuayTemplateTest kicker tripleoscillator)
endif()

find_package(Python3 COMPONENTS Interpreter REQUIRED)
add_test(NAME CommandLineCodecTest
	COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/scripted/cli-codec-test.py"
		--executable "$<TARGET_FILE:lmms>")
