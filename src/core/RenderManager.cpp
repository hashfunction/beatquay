/*
 * RenderManager - exporting logic common between the CLI and GUI.
 *
 * Copyright (c) 2015 Ryan Roden-Corrent <ryan/at/rcorre.net>
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

#include <QDir>
#include <QFileInfo>
#include <QRegularExpression>
#include <QPointer>
#include <algorithm>

#include "RenderManager.h"
#include "AudioEngine.h"

#include "PatternStore.h"
#include "Song.h"


namespace lmms
{
namespace
{
std::vector<Track*> unmutedRenderTracks()
{
	std::vector<Track*> result;
	const auto add = [&](const auto& tracks)
	{
		for (auto* track : tracks)
		{
			if (!track->isMuted() && (track->type() == Track::Type::Instrument || track->type() == Track::Type::Sample))
			{ result.push_back(track); }
		}
	};
	add(Engine::getSong()->tracks());
	add(Engine::patternStore()->tracks());
	return result;
}
} // namespace

RenderManager::RenderManager(
	const OutputSettings& outputSettings, ProjectRenderer::ExportFileFormat fmt, QString outputPath,
	QList<ExportDestinationSnapshot> authorizedOutputs, QStringList protectedPaths)
	: m_outputSettings(outputSettings)
	, m_format(fmt)
	, m_outputPath(outputPath)
	, m_authorizedOutputs(std::move(authorizedOutputs))
	, m_protectedPaths(std::move(protectedPaths))
{
	Engine::audioEngine()->storeAudioDevice();
}

RenderManager::~RenderManager()
{
	if (m_activeRenderer)
	{
		disconnect(m_activeRenderer.get(), nullptr, this, nullptr);
		m_activeRenderer->abortProcessing();
		finalizeActiveRenderer();
	}
	restoreMutedState();
	restoreAudioDevice();
}

void RenderManager::abortProcessing()
{
	if (m_complete) { return; }
	if (m_activeRenderer)
	{
		disconnect(m_activeRenderer.get(), nullptr, this, nullptr);
		m_activeRenderer->abortProcessing();
		finalizeActiveRenderer();
	}
	complete(RenderStatus::Cancelled);
}

void RenderManager::finalizeActiveRenderer()
{
	if (!m_activeRenderer) { return; }
	auto output = m_activeRenderer->finalize();
	m_activeRenderer.reset();
	if (m_activePublication)
	{
		if (output.status == RenderStatus::Succeeded && output.encoderFinalized)
		{
			const auto publication = m_activePublication->publish();
			output.path = publication.path;
			output.bytes = publication.bytes;
			output.previousOutputPath = publication.previousOutputPath;
			output.retainedPartialPath = publication.retainedPartialPath;
			if (!publication.published) { output.status = RenderStatus::Failed; output.error = publication.error; }
		}
		else
		{
			QString retained;
			if (!m_activePublication->discard(retained))
			{
				output.retainedPartialPath = retained;
				output.error += tr(" A partial render or unknown staging entry was preserved; review its reported path.");
			}
			output.path = m_activePublication->destinationPath();
		}
		m_activePublication.reset();
	}
	m_result.outputs.append(output);
}

void RenderManager::restoreAudioDevice()
{
	if (!m_deviceStored) { return; }
	Engine::audioEngine()->restoreAudioDevice();
	m_deviceStored = false;
}

void RenderManager::complete(RenderStatus status)
{
	if (m_complete) { return; }
	m_complete = true;
	m_result.status = status;
	m_tracksToRender.clear();
	restoreMutedState();
	restoreAudioDevice();
	// Listeners may delete the manager, including the existing dialog accept().
	// Publish an independent value after cleanup and never access a deleted owner.
	const auto result = m_result;
	QPointer<RenderManager> guard(this);
	emit completed(result);
	if (guard && status != RenderStatus::Cancelled) { emit finished(); }
}

// Called to render each new track when rendering tracks individually.
void RenderManager::renderNextTrack()
{
	if (m_complete) { return; } // A queued finish may outlive a cancellation.
	finalizeActiveRenderer();
	while (!m_tracksToRender.empty())
	{
		// pop the next track from our rendering queue
		Track* renderTrack = m_tracksToRender.back();
		m_tracksToRender.pop_back();

		// mute everything but the track we are about to render
		for (auto track : m_unmuted)
		{
			track->setMuted(track != renderTrack);
		}

		// for multi-render, prefix each output file with a different number
		int trackNum = m_tracksToRender.size() + 1;

		if (render(pathForTrack(renderTrack, trackNum, m_format, m_outputPath))) { return; }
		// A failed startup is a failed output, not a successful empty completion.
		// Preserve the existing batch behavior of attempting the remaining tracks.
		finalizeActiveRenderer();
	}
	const bool success = !m_result.outputs.isEmpty()
		&& std::all_of(m_result.outputs.begin(), m_result.outputs.end(), [](const auto& output)
		{ return output.status == RenderStatus::Succeeded; });
	if (m_result.outputs.isEmpty()) { m_result.error = tr("No unmuted renderable tracks were found."); }
	complete(success ? RenderStatus::Succeeded : RenderStatus::Failed);
}

// Render the song into individual tracks
void RenderManager::renderTracks()
{
	if (m_started || m_complete) { return; }
	m_started = true;
	m_unmuted = unmutedRenderTracks();

	// copy the list of unmuted tracks into our rendering queue.
	// we need to remember which tracks were unmuted to restore state at the end.
	m_tracksToRender = m_unmuted;

	renderNextTrack();
}

// Render the song into a single track
void RenderManager::renderProject()
{
	if (m_started || m_complete) { return; }
	m_started = true;
	if (!render(m_outputPath))
	{
		finalizeActiveRenderer();
		complete(RenderStatus::Failed);
	}
}

bool RenderManager::render(const QString& outputPath)
{
	auto renderPath = outputPath;
	if (!m_authorizedOutputs.isEmpty())
	{
		const auto destination = std::find_if(m_authorizedOutputs.begin(), m_authorizedOutputs.end(), [&](const auto& target)
		{ return target.path == QDir::cleanPath(QFileInfo(outputPath).absoluteFilePath()); });
		QString error;
		if (destination == m_authorizedOutputs.end()) { error = tr("This output was not included in the confirmed export."); }
		else
		{
			m_activePublication = std::make_unique<ExportOutputPublication>(*destination, m_protectedPaths);
			if (m_activePublication->prepare(error)) { renderPath = m_activePublication->stagingPath(); }
		}
		if (!error.isEmpty())
		{
			RenderOutputResult output;
			output.path = outputPath; output.error = error;
			m_result.outputs.append(output);
			m_activePublication.reset();
			return false;
		}
	}
	auto rendererSettings = m_outputSettings;
	if (m_activePublication) { rendererSettings.setRequireNewFile(true); }
	m_activeRenderer = std::make_unique<ProjectRenderer>(rendererSettings, m_format, renderPath);
	if (m_activePublication && m_activeRenderer->outputIdentity())
	{ m_activePublication->claimOutput(*m_activeRenderer->outputIdentity()); }

	if( m_activeRenderer->isReady() )
	{
		// pass progress signals through
		connect( m_activeRenderer.get(), SIGNAL(progressChanged(int)),
				this, SIGNAL(progressChanged(int)));

		// when it is finished, render the next track.
		// if we have not queued any tracks, renderNextTrack will just clean up
		connect( m_activeRenderer.get(), SIGNAL(finished()),
				this, SLOT(renderNextTrack()));

		m_activeRenderer->startProcessing();
		return true;
	}
	else
	{
		qDebug( "Renderer failed to acquire a file device!" );
		return false;
	}
}

// Unmute all tracks that were muted while rendering tracks
void RenderManager::restoreMutedState()
{
	while (!m_unmuted.empty())
	{
		Track* restoreTrack = m_unmuted.back();
		m_unmuted.pop_back();
		restoreTrack->setMuted( false );
	}
}

// Determine the output path for a track when rendering tracks individually
QString RenderManager::pathForTrack(const Track *track, int num, ProjectRenderer::ExportFileFormat format, const QString& directory)
{
	QString extension = ProjectRenderer::getFileExtensionFromFormat(format);
	QString name = track->name();
	name = name.remove(QRegularExpression(FILENAME_FILTER));
	name = QString( "%1_%2%3" ).arg( num ).arg( name ).arg( extension );
	return QDir(directory).filePath(name);
}

QStringList RenderManager::outputPaths(ProjectRenderer::ExportFileFormat format, const QString& path, bool tracks)
{
	if (!tracks) { return {QFileInfo(path).absoluteFilePath()}; }
	QStringList paths;
	const auto selected = unmutedRenderTracks();
	for (std::size_t i = 0; i < selected.size(); ++i)
	{ paths.append(QFileInfo(pathForTrack(selected[i], static_cast<int>(i + 1), format, path)).absoluteFilePath()); }
	return paths;
}

void RenderManager::updateConsoleProgress()
{
	if ( m_activeRenderer )
	{
		m_activeRenderer->updateConsoleProgress();

		int totalNum = m_unmuted.size();
		if ( totalNum > 0 )
		{
			// we are rendering multiple tracks, append a track counter to the output
			int trackNum = totalNum - m_tracksToRender.size();
			fprintf( stderr, "(%d/%d)", trackNum, totalNum );
		}
	}
}


} // namespace lmms
