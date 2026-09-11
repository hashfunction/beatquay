/*
 * RenderManager.h - Provides a uniform interface for rendering the project or
 *                   individual tracks for the CLI and GUI.
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

#ifndef LMMS_RENDER_MANAGER_H
#define LMMS_RENDER_MANAGER_H

#include <memory>
#include <vector>

#include "ProjectRenderer.h"
#include "OutputSettings.h"


namespace lmms
{

class Track;

class RenderManager : public QObject
{
	Q_OBJECT
public:
	RenderManager(const OutputSettings& outputSettings, ProjectRenderer::ExportFileFormat fmt, QString outputPath);

	~RenderManager() override;

	/// Export all unmuted tracks into a single file
	void renderProject();

	/// Export all unmuted tracks into individual file
	void renderTracks();

	void abortProcessing();
	bool isComplete() const { return m_complete; }
	const RenderResult& result() const { return m_result; }

signals:
	void progressChanged( int );
	// Emitted once after all worker/encoder/device/mute cleanup. Includes failed
	// startup and cancellation; finished alone remains a compatibility signal.
	void completed(const lmms::RenderResult& result);
	void finished();

private slots:
	void renderNextTrack();
	void updateConsoleProgress();

private:
	QString pathForTrack( const Track *track, int num );
	void restoreMutedState();

	bool render(const QString& outputPath);
	void finalizeActiveRenderer();
	void complete(RenderStatus status);
	void restoreAudioDevice();

	const OutputSettings m_outputSettings;
	ProjectRenderer::ExportFileFormat m_format;
	QString m_outputPath;

	std::unique_ptr<ProjectRenderer> m_activeRenderer;

	std::vector<Track*> m_tracksToRender;
	std::vector<Track*> m_unmuted;
	bool m_started = false;
	bool m_complete = false;
	bool m_deviceStored = true;
	RenderResult m_result;
} ;


} // namespace lmms

#endif // LMMS_RENDER_MANAGER_H
