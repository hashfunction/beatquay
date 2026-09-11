// SPDX-FileCopyrightText: 2026 Trieflow LLC
// SPDX-License-Identifier: GPL-2.0-or-later
#include "ProjectExportFactsCollector.h"
#include "Engine.h"
#include "Song.h"
#include "PatternStore.h"
#include "DataFile.h"
#include "MidiClip.h"
#include "SampleClip.h"
#include <QFile>
#include <QFileInfo>
#include <algorithm>

namespace lmms
{
CollectedProjectExportFacts ProjectExportFactsCollector::collect(ProjectRenderer::ExportFileFormat format,
	const QStringList& outputPaths, bool betweenMarkers, bool exportLoop, int loopCount)
{
	auto* song = Engine::getSong();
	ProjectExportFacts base;
	base.format = format;
	const auto encoder = static_cast<int>(format);
	base.encoderAvailable = encoder >= 0 && encoder < static_cast<int>(ProjectRenderer::ExportFileFormat::Count)
		&& ProjectRenderer::fileEncodeDevices[static_cast<std::size_t>(encoder)].isAvailable();
	bool unmutedContent = false;
	qint64 endTick = 0;
	const auto collectTracks = [&](const auto& tracks, bool songTimeline)
	{
		for (auto* track : tracks)
		{
			bool content = false;
			for (auto* clip : track->getClips())
			{
				if (songTimeline && !track->isMuted() && !clip->isMuted()) { endTick = std::max(endTick, static_cast<qint64>(clip->endPosition().getTicks())); }
				if (auto* sample = dynamic_cast<SampleClip*>(clip))
				{ content |= sample->sample().sampleSize() > 0 && sample->length().getTicks() > 0; }
				if (auto* midi = dynamic_cast<MidiClip*>(clip)) { content |= !midi->empty(); }
			}
			if (content && (track->type() == Track::Type::Instrument || track->type() == Track::Type::Sample))
			{
				++base.renderableTrackCount;
				unmutedContent |= !track->isMuted();
			}
		}
	};
	collectTracks(song->tracks(), true);
	collectTracks(Engine::patternStore()->tracks(), false);
	base.knownSilent = song->masterVolume() == 0 || (base.renderableTrackCount > 0 && !unmutedContent);
	const auto& timeline = song->getTimeline(Song::PlayMode::Song);
	const auto loopBegin = static_cast<qint64>(timeline.loopBegin().getTicks());
	const auto loopEnd = static_cast<qint64>(timeline.loopEnd().getTicks());
	const qint64 ticksPerBar = song->ticksPerBar();
	endTick = ticksPerBar > 0 ? (endTick / ticksPerBar) * ticksPerBar : 0;
	if (betweenMarkers)
	{
		base.timelineStartTick = loopBegin;
		base.timelineEndTick = loopEnd;
	}
	else
	{
		if (loopCount > 1) { endTick = std::max(endTick, loopEnd); }
		base.timelineEndTick = endTick + (exportLoop ? 0 : ticksPerBar);
	}
	qint64 repeatedTicks = base.timelineEndTick - base.timelineStartTick;
	if (loopCount > 1 && loopBegin >= base.timelineStartTick && loopEnd <= base.timelineEndTick && loopEnd > loopBegin)
	{ repeatedTicks += (loopEnd - loopBegin) * static_cast<qint64>(loopCount - 1); }
	// Preflight only needs a positive finite duration. This estimate uses the
	// current tempo; it does not claim to integrate future tempo automation.
	base.durationSeconds = song->getTempo() > 0 ? TimePos::ticksToMilliseconds(static_cast<double>(repeatedTicks), song->getTempo()) / 1000.0 : 0;
	DataFile document(DataFile::Type::SongProject);
	song->saveState(document, document.content());
	Engine::patternStore()->saveState(document, document.content());
	CollectedProjectExportFacts collected;
	if (!song->projectFileName().isEmpty()) { collected.protectedPaths.append(song->projectFileName()); }
	for (const auto& path : document.resourceReferences())
	{
		QFile resource(path);
		const bool regular = QFileInfo(path).isFile();
		base.resources.append({path, regular, regular && resource.open(QIODevice::ReadOnly)});
		collected.protectedPaths.append(path);
	}
	for (const auto& path : outputPaths)
	{
		auto facts = base;
		facts.outputPath = path;
		const QFileInfo output(path);
		facts.outputParentWritable = QFileInfo(output.absolutePath()).isDir() && QFileInfo(output.absolutePath()).isWritable();
		collected.outputs.append(facts);
	}
	return collected;
}
} // namespace lmms
