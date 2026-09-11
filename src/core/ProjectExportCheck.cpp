// SPDX-FileCopyrightText: 2026 Trieflow LLC
// SPDX-License-Identifier: GPL-2.0-or-later
#include "ProjectExportCheck.h"

#include <QCoreApplication>
#include <algorithm>
#include <cmath>
#include <tuple>
#include <utility>

namespace lmms
{
namespace
{
using Code = ProjectExportIssue::Code;
using Severity = ProjectExportIssue::Severity;

ProjectExportIssue issue(Code code, Severity severity, const QString& path,
	const char* message, const char* recovery)
{
	return {code, severity, path,
		QCoreApplication::translate("ProjectExportCheck", message),
		QCoreApplication::translate("ProjectExportCheck", recovery)};
}

QList<ProjectExportIssue> ordered(QList<ProjectExportIssue> issues)
{
	std::sort(issues.begin(), issues.end(), [](const auto& left, const auto& right)
	{
		return std::tie(left.severity, left.code, left.path) < std::tie(right.severity, right.code, right.path);
	});
	issues.erase(std::unique(issues.begin(), issues.end()), issues.end());
	return issues;
}
} // namespace

QList<ProjectExportIssue> ProjectExportCheck::beforeExport(const ProjectExportFacts& facts)
{
	QList<ProjectExportIssue> issues;
	if (facts.renderableTrackCount <= 0)
	{
		issues.append(issue(Code::EmptyProject, Severity::Error, {},
			QT_TRANSLATE_NOOP("ProjectExportCheck", "The project has no renderable tracks."),
			QT_TRANSLATE_NOOP("ProjectExportCheck", "Add an instrument or sample track with content before exporting.")));
	}
	else if (facts.knownSilent)
	{
		issues.append(issue(Code::SilentProject, Severity::Warning, {},
			QT_TRANSLATE_NOOP("ProjectExportCheck", "The observed project settings will produce silence."),
			QT_TRANSLATE_NOOP("ProjectExportCheck", "Review track mutes and master volume, or confirm that silence is intended.")));
	}
	const auto format = static_cast<int>(facts.format);
	if (format < 0 || format >= static_cast<int>(ProjectRenderer::ExportFileFormat::Count) || !facts.encoderAvailable)
	{
		issues.append(issue(Code::EncoderUnavailable, Severity::Error, {},
			QT_TRANSLATE_NOOP("ProjectExportCheck", "The selected audio encoder is unavailable."),
			QT_TRANSLATE_NOOP("ProjectExportCheck", "Choose a format supported by this build.")));
	}
	if (facts.timelineStartTick < 0 || facts.timelineEndTick <= facts.timelineStartTick
		|| !std::isfinite(facts.durationSeconds) || facts.durationSeconds <= 0)
	{
		issues.append(issue(Code::InvalidTimeline, Severity::Error, {},
			QT_TRANSLATE_NOOP("ProjectExportCheck", "The export range or duration is invalid."),
			QT_TRANSLATE_NOOP("ProjectExportCheck", "Choose an export range with a positive, finite duration.")));
	}
	for (const auto& resource : facts.resources)
	{
		if (!resource.exists)
		{
			issues.append(issue(Code::MissingResource, Severity::Error, resource.path,
				QT_TRANSLATE_NOOP("ProjectExportCheck", "A required project resource is missing."),
				QT_TRANSLATE_NOOP("ProjectExportCheck", "Locate or replace this resource in the project, then check again.")));
		}
		else if (!resource.readable)
		{
			issues.append(issue(Code::UnreadableResource, Severity::Error, resource.path,
				QT_TRANSLATE_NOOP("ProjectExportCheck", "A required project resource cannot be read."),
				QT_TRANSLATE_NOOP("ProjectExportCheck", "Restore read access to this resource, then check again.")));
		}
	}
	if (facts.outputPath.isEmpty())
	{
		issues.append(issue(Code::MissingOutputPath, Severity::Error, {},
			QT_TRANSLATE_NOOP("ProjectExportCheck", "No export destination was supplied."),
			QT_TRANSLATE_NOOP("ProjectExportCheck", "Choose an output file.")));
	}
	else
	{
		if (!facts.outputParentWritable)
		{
			issues.append(issue(Code::OutputParentNotWritable, Severity::Error, facts.outputPath,
				QT_TRANSLATE_NOOP("ProjectExportCheck", "The export folder is not writable."),
				QT_TRANSLATE_NOOP("ProjectExportCheck", "Choose a writable folder or restore access, then check again.")));
		}
		if (facts.outputExists)
		{
			if (!facts.outputIsRegularFile)
			{
				issues.append(issue(Code::OutputNotRegular, Severity::Error, facts.outputPath,
					QT_TRANSLATE_NOOP("ProjectExportCheck", "The export destination is not a regular file."),
					QT_TRANSLATE_NOOP("ProjectExportCheck", "Choose a different output file.")));
			}
			else if (!facts.outputWritable)
			{
				issues.append(issue(Code::OutputNotWritable, Severity::Error, facts.outputPath,
					QT_TRANSLATE_NOOP("ProjectExportCheck", "The existing output file is not writable."),
					QT_TRANSLATE_NOOP("ProjectExportCheck", "Choose another file or restore write access before confirming replacement.")));
			}
			else
			{
				issues.append(issue(Code::ExistingDestination, Severity::Warning, facts.outputPath,
					QT_TRANSLATE_NOOP("ProjectExportCheck", "The output file already exists."),
					QT_TRANSLATE_NOOP("ProjectExportCheck", "Choose another file or explicitly confirm replacement in the export dialog.")));
			}
		}
	}
	return ordered(std::move(issues));
}

QList<ProjectExportIssue> ProjectExportCheck::afterExport(const ProjectExportFacts& facts)
{
	if (facts.outputPath.isEmpty())
	{
		return {issue(Code::MissingOutputPath, Severity::Error, {},
			QT_TRANSLATE_NOOP("ProjectExportCheck", "No export destination was supplied."),
			QT_TRANSLATE_NOOP("ProjectExportCheck", "Choose an output file."))};
	}
	if (!facts.renderCompleted)
	{
		return {issue(Code::RenderNotCompleted, Severity::Error, facts.outputPath,
			QT_TRANSLATE_NOOP("ProjectExportCheck", "This render has not completed successfully."),
			QT_TRANSLATE_NOOP("ProjectExportCheck", "Wait for completion or resolve the render failure before checking the output."))};
	}
	if (!facts.outputExists)
	{
		return {issue(Code::MissingOutput, Severity::Error, facts.outputPath,
			QT_TRANSLATE_NOOP("ProjectExportCheck", "The completed render has no output file."),
			QT_TRANSLATE_NOOP("ProjectExportCheck", "Check the destination and available storage, then export again."))};
	}
	if (!facts.outputIsRegularFile)
	{
		return {issue(Code::OutputNotRegular, Severity::Error, facts.outputPath,
			QT_TRANSLATE_NOOP("ProjectExportCheck", "The export destination is not a regular file."),
			QT_TRANSLATE_NOOP("ProjectExportCheck", "Choose a different output file."))};
	}
	if (!facts.outputReadable)
	{
		return {issue(Code::OutputUnreadable, Severity::Error, facts.outputPath,
			QT_TRANSLATE_NOOP("ProjectExportCheck", "The rendered output cannot be read."),
			QT_TRANSLATE_NOOP("ProjectExportCheck", "Restore read access or export to a readable destination."))};
	}
	if (facts.outputSize <= 0)
	{
		return {issue(Code::EmptyOutput, Severity::Error, facts.outputPath,
			QT_TRANSLATE_NOOP("ProjectExportCheck", "The rendered output is empty or its size is unavailable."),
			QT_TRANSLATE_NOOP("ProjectExportCheck", "Check the encoder and available storage, then export again."))};
	}
	return {};
}
} // namespace lmms
