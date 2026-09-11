// SPDX-FileCopyrightText: 2026 Trieflow LLC
// SPDX-License-Identifier: GPL-2.0-or-later
#ifndef LMMS_PROJECT_EXPORT_CHECK_H
#define LMMS_PROJECT_EXPORT_CHECK_H

#include "ProjectRenderer.h"

#include <QList>
#include <QString>

namespace lmms
{

struct ProjectExportResourceFacts
{
	QString path;
	bool exists = false;
	bool readable = false;
	bool operator==(const ProjectExportResourceFacts&) const = default;
};

// An immutable-by-convention observation supplied by the caller. The checker
// never opens files, queries the song, authorizes replacement, or starts a render.
struct ProjectExportFacts
{
	int renderableTrackCount = 0;
	// Only set for an observed silent state, such as zero master volume. This is
	// not inferred from track names, missing resources, or a lack of analysis.
	bool knownSilent = false;
	qint64 timelineStartTick = 0;
	qint64 timelineEndTick = 0;
	double durationSeconds = 0;
	QList<ProjectExportResourceFacts> resources;
	ProjectRenderer::ExportFileFormat format = ProjectRenderer::ExportFileFormat::Wave;
	bool encoderAvailable = false;
	QString outputPath;
	bool outputParentWritable = false;
	bool outputExists = false;
	bool outputIsRegularFile = false;
	bool outputWritable = false;
	bool outputReadable = false;
	qint64 outputSize = 0;
	// Set only after this render succeeded and the encoder finalized/closed.
	// A thread/manager finished signal alone is not evidence of success.
	bool renderCompleted = false;

	bool operator==(const ProjectExportFacts&) const = default;
};

struct ProjectExportIssue
{
	// Explicit values are stable identifiers; append new codes without renumbering.
	enum class Code
	{
		EmptyOutput = 1,
		EmptyProject = 2,
		EncoderUnavailable = 3,
		ExistingDestination = 4,
		InvalidTimeline = 5,
		MissingOutput = 6,
		MissingOutputPath = 7,
		MissingResource = 8,
		OutputNotRegular = 9,
		OutputNotWritable = 10,
		OutputParentNotWritable = 11,
		OutputUnreadable = 12,
		RenderNotCompleted = 13,
		SilentProject = 14,
		UnreadableResource = 15
	};
	enum class Severity { Error, Warning };
	Code code;
	Severity severity;
	QString path;
	QString message;
	QString recoveryAction;

	bool operator==(const ProjectExportIssue&) const = default;
};

class LMMS_EXPORT ProjectExportCheck
{
public:
	// Deterministic order: errors before warnings, then code and exact path.
	[[nodiscard]] static QList<ProjectExportIssue> beforeExport(const ProjectExportFacts& facts);
	// Checks completion plus output presence/readability/size. It does not decode
	// audio or prove that it is non-silent, fresh, or matches the requested format.
	[[nodiscard]] static QList<ProjectExportIssue> afterExport(const ProjectExportFacts& facts);
};

} // namespace lmms

#endif // LMMS_PROJECT_EXPORT_CHECK_H
