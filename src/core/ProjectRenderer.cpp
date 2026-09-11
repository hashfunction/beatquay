/*
 * ProjectRenderer.cpp - ProjectRenderer-class for easily rendering projects
 *
 * Copyright (c) 2009 Tobias Doerffel <tobydox/at/users.sourceforge.net>
 *
 * This file is part of LMMS - https://lmms.io
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public
 * License along with this program (see COPYING); if not, write to the
 * Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
 * Boston, MA 02110-1301 USA.
 *
 */


#include <QFile>
#include <type_traits>

#include "ProjectRenderer.h"
#include "AudioEngine.h"
#include "AudioFileDevice.h"
#include "OutputSettings.h"
#include "Song.h"
#include "PerfLog.h"

#include "AudioFileWave.h"
#include "AudioFileOgg.h"
#include "AudioFileMP3.h"
#include "AudioFileFlac.h"


namespace lmms
{

// Keep the lightweight public declaration identical to the encoder factory type.
static_assert(std::is_same_v<decltype(ProjectRenderer::FileEncodeDevice::m_getDevInst), AudioFileDeviceInstantiaton>);

const std::array<ProjectRenderer::FileEncodeDevice, 5> ProjectRenderer::fileEncodeDevices
{

	FileEncodeDevice{ ProjectRenderer::ExportFileFormat::Wave,
		QT_TRANSLATE_NOOP( "ProjectRenderer", "WAV (*.wav)" ),
					".wav", &AudioFileWave::getInst },
	FileEncodeDevice{ ProjectRenderer::ExportFileFormat::Flac,
		QT_TRANSLATE_NOOP("ProjectRenderer", "FLAC (*.flac)"),
		".flac",
		&AudioFileFlac::getInst
	},
	FileEncodeDevice{ ProjectRenderer::ExportFileFormat::Ogg,
		QT_TRANSLATE_NOOP( "ProjectRenderer", "OGG (*.ogg)" ),
					".ogg",
#ifdef LMMS_HAVE_OGGVORBIS
					&AudioFileOgg::getInst
#else
					nullptr
#endif
									},
	FileEncodeDevice{ ProjectRenderer::ExportFileFormat::MP3,
		QT_TRANSLATE_NOOP( "ProjectRenderer", "MP3 (*.mp3)" ),
					".mp3",
#ifdef LMMS_HAVE_MP3LAME
					&AudioFileMP3::getInst
#else
					nullptr
#endif
									},
	// Insert your own file-encoder infos here.
	// Maybe one day the user can add own encoders inside the program.

	FileEncodeDevice{ ProjectRenderer::ExportFileFormat::Count, nullptr, nullptr, nullptr }

} ;

ProjectRenderer::ProjectRenderer(
	const OutputSettings& outputSettings, ExportFileFormat exportFileFormat, const QString& outputFilename)
	: QThread(Engine::audioEngine())
	, m_fileDev(nullptr)
	, m_progress(0)
	, m_abort(false)
{
	m_result.path = outputFilename;
	const auto index = static_cast<int>(exportFileFormat);
	if (index < 0 || index >= static_cast<int>(ExportFileFormat::Count))
	{
		m_result.error = tr("The requested encoder format is invalid.");
		return;
	}
	AudioFileDeviceInstantiaton audioEncoderFactory = fileEncodeDevices[static_cast<std::size_t>(exportFileFormat)].m_getDevInst;

	if (audioEncoderFactory)
	{
		bool successful = false;

		m_fileDev = audioEncoderFactory(
					outputFilename, outputSettings, DEFAULT_CHANNELS,
					Engine::audioEngine(), successful );
		if (m_fileDev) { m_outputIdentity = m_fileDev->outputIdentity(); }
		if( !successful )
		{
			delete m_fileDev;
			m_fileDev = nullptr;
		}
	}
	if (!m_fileDev) { m_result.error = tr("The audio encoder could not open or initialize the output."); }
}

ProjectRenderer::~ProjectRenderer()
{
	if (isRunning()) { abortProcessing(); }
	finalize();
	// Before installation, this object owns the encoder. After installation,
	// AudioEngine owns it and deletes it when switching/restoring devices.
	if (!m_deviceInstalled) { delete m_fileDev; }
}

RenderOutputResult ProjectRenderer::finalize()
{
	if (m_finalized) { return m_result; }
	Q_ASSERT(QThread::currentThread() != this);
	wait();
	m_finalized = true;
	if (!m_fileDev) { return m_result; }
	m_result.encoderFinalized = m_fileDev->finalizeOutput();
	if (m_abort.load())
	{
		m_result.status = RenderStatus::Cancelled;
		m_result.partialOutputRemoved = m_fileDev->removePartialOutput();
		m_result.cleanupRecoveryPath = m_fileDev->cleanupRecoveryPath();
		if (!m_result.partialOutputRemoved)
		{
			m_result.error = tr("Rendering was cancelled, but the partial output could not be removed.");
		}
	}
	else if (m_started && m_completedNormally && m_result.encoderFinalized)
	{
		m_result.status = RenderStatus::Succeeded;
	}
	else
	{
		m_result.error = tr("Rendering did not complete or the encoder could not finalize the output.");
	}
	return m_result;
}



// Little help function for getting file format from a file extension
// (only for registered file-encoders).
ProjectRenderer::ExportFileFormat ProjectRenderer::getFileFormatFromExtension(
							const QString & _ext )
{
	int idx = 0;
	while( fileEncodeDevices[idx].m_fileFormat != ExportFileFormat::Count )
	{
		if( QString( fileEncodeDevices[idx].m_extension ) == _ext )
		{
			return( fileEncodeDevices[idx].m_fileFormat );
		}
		++idx;
	}

	return( ExportFileFormat::Wave ); // Default.
}




QString ProjectRenderer::getFileExtensionFromFormat(
		ExportFileFormat fmt )
{
	const auto index = static_cast<int>(fmt);
	if (index < 0 || index >= static_cast<int>(ExportFileFormat::Count)) { return {}; }
	return fileEncodeDevices[static_cast<std::size_t>(index)].m_extension;
}




void ProjectRenderer::startProcessing()
{

	if (isReady() && !m_started && !m_finalized)
	{
		// Have to do audio engine stuff with GUI-thread affinity in order to
		// make slots connected to sampleRateChanged()-signals being called immediately.
		Engine::audioEngine()->setAudioDevice(m_fileDev, false);
		m_deviceInstalled = m_started = true;

		start(
#ifndef LMMS_BUILD_WIN32
			QThread::HighPriority
#endif
						);

	}
}


void ProjectRenderer::run()
{
	PerfLogTimer perfLog("Project Render");

	Engine::getSong()->startExport();
	// Skip first empty buffer.
	Engine::audioEngine()->renderNextPeriod();

	m_progress = 0;

	// Now start processing
	Engine::audioEngine()->startProcessing();

	// Continually track and emit progress percentage to listeners.
	while (!Engine::getSong()->isExportDone() && !m_abort.load() && !m_fileDev->hasWriteFailure())
	{
		const auto buffer = Engine::audioEngine()->renderNextPeriod();
		m_fileDev->writeBuffer(buffer.data(), buffer.size());

		const int nprog = Engine::getSong()->getExportProgress();
		if (m_progress != nprog)
		{
			m_progress = nprog;
			emit progressChanged( m_progress );
		}
	}
	m_completedNormally = Engine::getSong()->isExportDone() && !m_abort.load() && !m_fileDev->hasWriteFailure();

	// Notify the audio engine of the end of processing.
	Engine::audioEngine()->stopProcessing();

	Engine::getSong()->stopExport();

	perfLog.end();

	// Finalization and cancellation cleanup happen after join on the owner thread.
}




void ProjectRenderer::abortProcessing()
{
	m_abort = true;
	wait();
}



void ProjectRenderer::updateConsoleProgress()
{
	constexpr int cols = 50;
	static int rot = 0;
	auto buf = std::array<char, 80>{};
	auto prog = std::array<char, cols + 1>{};

	for( int i = 0; i < cols; ++i )
	{
		prog[i] = ( i*100/cols <= m_progress ? '-' : ' ' );
	}
	prog[cols] = 0;

	const auto activity = "|/-\\";
	std::fill(buf.begin(), buf.end(), 0);
	std::snprintf(buf.data(), buf.size(), "\r|%s|    %3d%%   %c  ", prog.data(), m_progress.load(),
							activity[rot] );
	rot = ( rot+1 ) % 4;

	fprintf( stderr, "%s", buf.data() );
	fflush( stderr );
}


} // namespace lmms
